from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, UserScheme, Document, Scheme, UserProfile
from app.agents.deadline_agent import DeadlineMonitoringAgent

router = APIRouter(prefix="/analytics", tags=["analytics"])
deadline_agent = DeadlineMonitoringAgent()

@router.get("")
def get_analytics(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        return {
            "unlocked_benefit_amount": 0,
            "schemes_discovered_count": 0,
            "pending_documents_count": 0,
            "upcoming_deadlines_count": 0,
            "success_rate": 0
        }

    # Fetch all available central schemes from DB
    schemes = session.exec(select(Scheme)).all()
    from app.agents.discovery_agent import SchemeDiscoveryAgent
    discovery_agent = SchemeDiscoveryAgent()
    ranked = discovery_agent.rank_schemes_for_profile(profile, schemes)

    # Fetch user relations and docs
    user_relations = session.exec(select(UserScheme).where(UserScheme.user_id == current_user.id)).all()
    user_docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()
    
    # Deadlines Alert Scan
    reminders = current_user.reminders
    scan_res = deadline_agent.scan_deadlines_and_expiries(user_relations, user_docs, reminders)
    upcoming_deadlines_count = len(scan_res["alerts"])
    
    # Calculate matches count
    schemes_discovered_count = sum(1 for r in ranked if r["eligibility_status"] in ["Eligible", "Likely Eligible"])
    
    # Estimate financial benefits unlocked
    benefit_map = {
        "pm-kisan": 6000,
        "ayushman": 500000,
        "mudra": 100000, # Shishu / Kishor base guess
        "post-matric": 25000,
        "awas": 120000,
        "svanidhi": 10000,
        "vishwakarma": 15000,
        "garib kalyan": 8000
    }
    
    unlocked_benefit_amount = 0
    for r in ranked:
        if r["eligibility_status"] in ["Eligible", "Likely Eligible"]:
            title_lower = r["scheme"].title.lower()
            matched_value = 0
            for keyword, val in benefit_map.items():
                if keyword in title_lower:
                    matched_value = val
                    break
            if matched_value == 0:
                matched_value = 5000 # default fallback benefit
            unlocked_benefit_amount += matched_value
            
    # Count pending documents in document vault
    # If the user has applied schemes, sum their actual missing documents
    pending_documents_count = 0
    applied_count = 0
    approved_count = 0
    
    for us in user_relations:
        if us.status == "applied":
            applied_count += 1
            pending_documents_count += len(us.missing_documents)
        elif us.status == "approved":
            applied_count += 1
            approved_count += 1

    success_rate = 100
    if applied_count > 0:
        success_rate = int((approved_count / applied_count) * 100.0)
    elif schemes_discovered_count > 0:
        success_rate = 85
    else:
        success_rate = 50

    return {
        "unlocked_benefit_amount": unlocked_benefit_amount,
        "schemes_discovered_count": schemes_discovered_count,
        "pending_documents_count": pending_documents_count,
        "upcoming_deadlines_count": upcoming_deadlines_count,
        "success_rate": success_rate,
        "alerts": scan_res["alerts"][:5], # top 5 alerts
        "timeline_events": scan_res["timeline_events"]
    }
