from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.agents.deadline_agent import DeadlineMonitoringAgent
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.core.db import get_session
from app.models import Document, Reminder, Scheme, User, UserProfile, UserScheme
from app.routes.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])
deadline_agent = DeadlineMonitoringAgent()
discovery_agent = SchemeDiscoveryAgent()

BENEFIT_ESTIMATES = {
    "pm-kisan": 6000,
    "ayushman": 500000,
    "mudra": 100000,
    "post-matric": 25000,
    "awas": 120000,
    "svanidhi": 10000,
    "vishwakarma": 15000,
    "garib kalyan": 8000,
}


@router.get("")
def get_analytics(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        return {
            "unlocked_benefit_amount": 0,
            "estimated_benefit_amount": 0,
            "benefit_estimate_note": "Create a profile to see estimated benefits.",
            "schemes_discovered_count": 0,
            "schemes_evaluated_count": 0,
            "status_breakdown": {
                "Eligible": 0,
                "Potentially Eligible": 0,
                "Insufficient Information": 0,
                "Not Eligible": 0,
            },
            "benefit_breakdown": [],
            "pending_documents_count": 0,
            "documents_count": 0,
            "upcoming_deadlines_count": 0,
            "success_rate": None,
            "applied_count": 0,
            "approved_count": 0,
        }

    schemes = session.exec(select(Scheme)).all()
    ranked = discovery_agent.rank_schemes_for_profile(profile, schemes)
    status_breakdown = {
        status: sum(1 for item in ranked if item["eligibility_status"] == status)
        for status in [
            "Eligible",
            "Potentially Eligible",
            "Insufficient Information",
            "Not Eligible",
        ]
    }

    user_relations = session.exec(
        select(UserScheme).where(UserScheme.user_id == current_user.id)
    ).all()
    user_docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()
    reminders = session.exec(select(Reminder).where(Reminder.user_id == current_user.id)).all()
    scan_result = deadline_agent.scan_deadlines_and_expiries(user_relations, user_docs, reminders)

    estimated_benefit_amount = 0
    benefit_breakdown = []
    for item in ranked:
        if item["eligibility_status"] not in {"Eligible", "Potentially Eligible"}:
            continue
        title_lower = item["scheme"].title.lower()
        for keyword, value in BENEFIT_ESTIMATES.items():
            if keyword in title_lower:
                estimated_benefit_amount += value
                benefit_breakdown.append(
                    {"name": item["scheme"].title, "value": value}
                )
                break

    applied_count = sum(1 for relation in user_relations if relation.status in {"applied", "approved"})
    approved_count = sum(1 for relation in user_relations if relation.status == "approved")
    pending_documents_count = sum(
        len(relation.missing_documents or [])
        for relation in user_relations
        if relation.status in {"saved", "applied"}
    )
    success_rate = (
        round((approved_count / applied_count) * 100.0, 1) if applied_count > 0 else None
    )

    return {
        # Kept for older clients, but this is an estimate, not money already received.
        "unlocked_benefit_amount": estimated_benefit_amount,
        "estimated_benefit_amount": estimated_benefit_amount,
        "benefit_estimate_note": (
            "Estimated maximum value of schemes marked Eligible or Potentially Eligible. "
            "It is not a guarantee of payment or approval."
        ),
        "schemes_discovered_count": status_breakdown["Eligible"] + status_breakdown["Potentially Eligible"],
        "schemes_evaluated_count": len(ranked),
        "status_breakdown": status_breakdown,
        "benefit_breakdown": benefit_breakdown,
        "pending_documents_count": pending_documents_count,
        "documents_count": len(user_docs),
        "upcoming_deadlines_count": len(scan_result["alerts"]),
        "success_rate": success_rate,
        "applied_count": applied_count,
        "approved_count": approved_count,
        "alerts": scan_result["alerts"][:5],
        "timeline_events": scan_result["timeline_events"],
    }
