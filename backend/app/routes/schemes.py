from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.document_agent import DocumentIntelligenceAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent
from app.agents.prep_agent import ApplicationPreparationAgent
from app.agents.translator_agent import AITranslatorAgent
from app.core.db import get_session
from app.models import Document, Scheme, User, UserProfile, UserScheme
from app.routes.deps import get_current_user

router = APIRouter(prefix="/schemes", tags=["schemes"])

discovery_agent = SchemeDiscoveryAgent()
eligibility_agent = EligibilityVerificationAgent()
document_agent = DocumentIntelligenceAgent()
prep_agent = ApplicationPreparationAgent()
translator_agent = AITranslatorAgent()

ALLOWED_USER_SCHEME_STATUSES = {"saved", "applied"}


class SaveSchemeIn(BaseModel):
    scheme_id: int
    status: str


def translate(value: str, lang: str) -> str:
    return translator_agent.translate(value, "hi") if lang.lower() == "hi" else value


def scheme_source_fields(scheme: Scheme) -> Dict[str, Any]:
    return {
        "state": scheme.state,
        "application_url": scheme.application_url,
        "source_url": scheme.source_url or scheme.application_url,
        "source_note": scheme.source_note
        or "Official rules may change. Verify details on the department portal before applying.",
        "effective_date": scheme.effective_date,
        "tags": scheme.tags,
    }


def build_scheme_payload(
    item: Dict[str, Any],
    lang: str = "en",
    include_steps: bool = True,
) -> Dict[str, Any]:
    scheme = item["scheme"]
    payload = {
        "id": scheme.id,
        "title": translate(scheme.title, lang),
        "description": translate(scheme.description, lang),
        "department": scheme.department,
        "ministry": scheme.ministry,
        "benefit_type": scheme.benefit_type,
        "benefit_details": translate(scheme.benefit_details, lang),
        "eligibility_status": translate(item["eligibility_status"], lang),
        "eligibility_code": item["eligibility_status"],
        "eligibility_score": item["eligibility_score"],
        "eligibility_explanation": translate(item["eligibility_explanation"], lang),
        "eligibility_checks": item.get("checks", []),
        "missing_information": item.get("missing_information", []),
        "warnings": item.get("warnings", []),
        "required_documents": scheme.required_documents,
        "complexity": scheme.complexity,
        "eli15_explanation": translate(scheme.eli15_explanation, lang),
        "deadlines": scheme.deadlines,
        "decision_source": item.get("decision_source", "deterministic_rules"),
    }
    payload.update(scheme_source_fields(scheme))
    if include_steps:
        payload["steps"] = [translate(step, lang) for step in (scheme.steps or [])]
    return payload


@router.get("/all", response_model=List[Scheme])
def get_all_schemes(session: Session = Depends(get_session)):
    return session.exec(select(Scheme)).all()


@router.get("/recommendations")
def get_recommended_schemes(
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile must be initialized first")

    schemes = session.exec(select(Scheme)).all()
    ranked = discovery_agent.rank_schemes_for_profile(profile, schemes)
    return [build_scheme_payload(item, lang, include_steps=False) for item in ranked]


@router.get("/search")
def search_schemes(
    q: str = Query("", description="Natural language search query"),
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    schemes = session.exec(select(Scheme)).all()
    matched = discovery_agent.search_schemes(q, schemes)
    ranked = discovery_agent.rank_schemes_for_profile(profile, matched)
    return [build_scheme_payload(item, lang, include_steps=False) for item in ranked]


@router.post("/status")
def update_scheme_status(
    data: SaveSchemeIn,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if data.status not in ALLOWED_USER_SCHEME_STATUSES:
        raise HTTPException(status_code=400, detail="Status must be 'saved' or 'applied'.")

    scheme = session.exec(select(Scheme).where(Scheme.id == data.scheme_id)).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile must be initialized first")

    docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()
    document_result = document_agent.analyze_documents(docs, scheme)
    eligibility = eligibility_agent.verify(profile, scheme)
    prep = prep_agent.prepare_application_kit(profile, scheme, document_result)

    relation = session.exec(
        select(UserScheme).where(
            UserScheme.user_id == current_user.id,
            UserScheme.scheme_id == data.scheme_id,
        )
    ).first()

    draft = {
        "cover_letter": prep["cover_letter"],
        "checklist": prep["checklist"],
        "steps": prep["steps"],
        "disclaimer": prep["disclaimer"],
    }
    if not relation:
        relation = UserScheme(
            user_id=current_user.id,
            scheme_id=data.scheme_id,
            status=data.status,
            eligibility_score=eligibility["score"],
            eligibility_status=eligibility["status"],
            eligibility_explanation=eligibility["explanation"],
            missing_documents=document_result["missing"],
            application_draft=draft,
            timeline=prep["timeline"],
        )
    else:
        relation.status = data.status
        relation.eligibility_score = eligibility["score"]
        relation.eligibility_status = eligibility["status"]
        relation.eligibility_explanation = eligibility["explanation"]
        relation.missing_documents = document_result["missing"]
        relation.application_draft = draft
        relation.timeline = prep["timeline"]

    session.add(relation)
    session.commit()
    session.refresh(relation)
    return relation


@router.get("/compare")
def compare_schemes(
    ids: List[int] = Query(..., description="List of scheme IDs to compare"),
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()

    comparison_data = []
    for scheme_id in ids:
        scheme = session.exec(select(Scheme).where(Scheme.id == scheme_id)).first()
        if not scheme:
            continue
        eligibility = eligibility_agent.verify(profile, scheme)
        document_result = document_agent.analyze_documents(docs, scheme)
        prep = prep_agent.prepare_application_kit(profile, scheme, document_result)
        comparison_data.append(
            {
                "id": scheme.id,
                "title": translate(scheme.title, lang),
                "benefits": translate(scheme.benefit_details, lang),
                "benefit_type": scheme.benefit_type,
                "eligibility_status": translate(eligibility["status"], lang),
                "eligibility_code": eligibility["status"],
                "eligibility_score": eligibility["score"],
                "eligibility_explanation": translate(eligibility["explanation"], lang),
                "documents": scheme.required_documents,
                "missing_documents": document_result["missing"],
                "checklist": document_result["checklist"],
                "readiness_score": document_result["readiness_score"],
                "complexity": scheme.complexity,
                "timeline_days": prep["timeline"].get("estimated_days"),
                "timeline": prep["timeline"],
                "cover_letter": prep["cover_letter"],
                "application_steps": [translate(step, lang) for step in (scheme.steps or [])],
                "application_url": scheme.application_url,
                "source_url": scheme.source_url or scheme.application_url,
                "source_note": scheme.source_note,
                "disclaimer": prep["disclaimer"],
            }
        )
    return comparison_data


@router.get("/{scheme_id}")
def get_scheme_detail(
    scheme_id: int,
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    scheme = session.exec(select(Scheme).where(Scheme.id == scheme_id)).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()
    eligibility = eligibility_agent.verify(profile, scheme)
    document_result = document_agent.analyze_documents(docs, scheme)
    prep = prep_agent.prepare_application_kit(profile, scheme, document_result)

    return {
        "id": scheme.id,
        "title": translate(scheme.title, lang),
        "description": translate(scheme.description, lang),
        "department": scheme.department,
        "ministry": scheme.ministry,
        "benefit_type": scheme.benefit_type,
        "benefit_details": translate(scheme.benefit_details, lang),
        "eligibility_status": translate(eligibility["status"], lang),
        "eligibility_code": eligibility["status"],
        "eligibility_score": eligibility["score"],
        "eligibility_explanation": translate(eligibility["explanation"], lang),
        "eligibility_checks": eligibility["checks"],
        "missing_information": eligibility["missing_information"],
        "warnings": eligibility["warnings"],
        "required_documents": scheme.required_documents,
        "checklist": document_result["checklist"],
        "missing_documents": document_result["missing"],
        "readiness_score": document_result["readiness_score"],
        "complexity": scheme.complexity,
        "steps": [translate(step, lang) for step in (scheme.steps or [])],
        "deadlines": scheme.deadlines,
        "eli15_explanation": translate(scheme.eli15_explanation, lang),
        "timeline": prep["timeline"],
        "cover_letter": prep["cover_letter"],
        "disclaimer": prep["disclaimer"],
        "decision_source": eligibility["decision_source"],
        **scheme_source_fields(scheme),
    }
