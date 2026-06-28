from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, Scheme, UserScheme, UserProfile
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent
from app.agents.prep_agent import ApplicationPreparationAgent
from app.agents.legal_agent import LegalPolicyAgent
from app.agents.translator_agent import AITranslatorAgent
from pydantic import BaseModel

router = APIRouter(prefix="/schemes", tags=["schemes"])

discovery_agent = SchemeDiscoveryAgent()
eligibility_agent = EligibilityVerificationAgent()
prep_agent = ApplicationPreparationAgent()
legal_agent = LegalPolicyAgent()
translator_agent = AITranslatorAgent()

class SaveSchemeIn(BaseModel):
    scheme_id: int
    status: str  # "saved" or "applied"

@router.get("/all", response_model=List[Scheme])
def get_all_schemes(session: Session = Depends(get_session)):
    return session.exec(select(Scheme)).all()

@router.get("/recommendations")
def get_recommended_schemes(
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile must be initialized first")
        
    schemes = session.exec(select(Scheme)).all()
    # Rank schemes
    ranked = discovery_agent.rank_schemes_for_profile(profile, schemes)
    
    # Format response
    results = []
    for item in ranked:
        sch = item["scheme"]
        
        # Translate values dynamically if lang is Hindi
        title = sch.title
        description = sch.description
        benefit_details = sch.benefit_details
        eligibility_status = item["eligibility_status"]
        eligibility_explanation = item["eligibility_explanation"]
        
        if lang.lower() == "hi":
            title = translator_agent.translate(title, "hi")
            description = translator_agent.translate(description, "hi")
            benefit_details = translator_agent.translate(benefit_details, "hi")
            eligibility_status = translator_agent.translate(eligibility_status, "hi")
            eligibility_explanation = translator_agent.translate(eligibility_explanation, "hi")
            
        results.append({
            "id": sch.id,
            "title": title,
            "description": description,
            "department": sch.department,
            "ministry": sch.ministry,
            "benefit_type": sch.benefit_type,
            "benefit_details": benefit_details,
            "eligibility_status": eligibility_status,
            "eligibility_score": item["eligibility_score"],
            "eligibility_explanation": eligibility_explanation,
            "required_documents": sch.required_documents,
            "complexity": sch.complexity,
            "eli15_explanation": sch.eli15_explanation,
            "deadlines": sch.deadlines
        })
    return results

@router.get("/search")
def search_schemes(
    q: str = Query("", description="Natural language search query"),
    lang: str = Query("en", description="Target language: en or hi"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    schemes = session.exec(select(Scheme)).all()
    
    matched = discovery_agent.search_schemes(q, schemes)
    ranked = discovery_agent.rank_schemes_for_profile(profile, matched)
    
    results = []
    for item in ranked:
        sch = item["scheme"]
        
        # Translate values dynamically if lang is Hindi
        title = sch.title
        description = sch.description
        benefit_details = sch.benefit_details
        eligibility_status = item["eligibility_status"]
        eligibility_explanation = item["eligibility_explanation"]
        
        if lang.lower() == "hi":
            title = translator_agent.translate(title, "hi")
            description = translator_agent.translate(description, "hi")
            benefit_details = translator_agent.translate(benefit_details, "hi")
            eligibility_status = translator_agent.translate(eligibility_status, "hi")
            eligibility_explanation = translator_agent.translate(eligibility_explanation, "hi")
            
        results.append({
            "id": sch.id,
            "title": title,
            "description": description,
            "benefit_type": sch.benefit_type,
            "benefit_details": benefit_details,
            "eligibility_status": eligibility_status,
            "eligibility_score": item["eligibility_score"],
            "eligibility_explanation": eligibility_explanation,
            "required_documents": sch.required_documents,
            "complexity": sch.complexity
        })
    return results

@router.post("/status")
def update_scheme_status(
    data: SaveSchemeIn,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Save a scheme to favorites or apply to it."""
    scheme = session.exec(select(Scheme).where(Scheme.id == data.scheme_id)).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
        
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    
    # Verify current eligibility details
    elig = eligibility_agent.verify(profile, scheme)
    prep = prep_agent.prepare_application_kit(profile, scheme)
    
    # Check if relation already exists
    statement = select(UserScheme).where(
        UserScheme.user_id == current_user.id,
        UserScheme.scheme_id == data.scheme_id
    )
    relation = session.exec(statement).first()
    
    if not relation:
        relation = UserScheme(
            user_id=current_user.id,
            scheme_id=data.scheme_id,
            status=data.status,
            eligibility_score=elig["score"],
            eligibility_status=elig["status"],
            eligibility_explanation=elig["explanation"],
            missing_documents=scheme.required_documents, # initially all missing
            application_draft={"cover_letter": prep["cover_letter"]},
            timeline=prep["timeline"]
        )
    else:
        relation.status = data.status
        relation.eligibility_score = elig["score"]
        relation.eligibility_status = elig["status"]
        relation.eligibility_explanation = elig["explanation"]
        relation.application_draft = {"cover_letter": prep["cover_letter"]}
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
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    
    comparison_data = []
    for sid in ids:
        scheme = session.exec(select(Scheme).where(Scheme.id == sid)).first()
        if scheme:
            elig = eligibility_agent.verify(profile, scheme)
            prep = prep_agent.prepare_application_kit(profile, scheme)
            
            title = scheme.title
            benefits = scheme.benefit_details
            eligibility_status = elig["status"]
            eligibility_explanation = elig["explanation"]
            steps = scheme.steps
            
            if lang.lower() == "hi":
                title = translator_agent.translate(title, "hi")
                benefits = translator_agent.translate(benefits, "hi")
                eligibility_status = translator_agent.translate(eligibility_status, "hi")
                eligibility_explanation = translator_agent.translate(eligibility_explanation, "hi")
                steps = [translator_agent.translate(st, "hi") for st in steps]
                
            comparison_data.append({
                "id": scheme.id,
                "title": title,
                "benefits": benefits,
                "benefit_type": scheme.benefit_type,
                "eligibility_status": eligibility_status,
                "eligibility_score": elig["score"],
                "eligibility_explanation": eligibility_explanation,
                "documents": scheme.required_documents,
                "complexity": scheme.complexity,
                "timeline_days": prep["timeline"].get("estimated_days", 14),
                "application_steps": steps
            })
            
    return comparison_data
