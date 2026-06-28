from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.models import Document, Scheme, UserScheme, Reminder

class DeadlineMonitoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Deadline Monitoring Agent",
            description="Monitors scheme application deadlines, document expirations, and triggers active reminders."
        )

    def scan_deadlines_and_expiries(
        self, 
        user_schemes: List[UserScheme], 
        user_docs: List[Document],
        reminders: List[Reminder]
    ) -> Dict[str, Any]:
        """
        Scan and assemble active alerts for upcoming scheme deadlines, expiring vault documents,
        and user scheduled reminders.
        """
        now = datetime.utcnow()
        alerts = []
        timeline_events = []
        
        # 1. Check scheme application deadlines and applied scheme milestones
        for us in user_schemes:
            scheme = us.scheme
            
            if us.status in ["discovered", "saved"]:
                deadline_info = scheme.deadlines
                if deadline_info and deadline_info.get("end_date"):
                    try:
                        end_date = datetime.strptime(deadline_info["end_date"], "%Y-%m-%d")
                        days_left = (end_date - now).days
                        
                        if 0 <= days_left <= 30:
                            alerts.append({
                                "type": "scheme_deadline",
                                "severity": "High" if days_left <= 7 else "Medium",
                                "title": f"Upcoming Deadline: {scheme.title}",
                                "description": f"The application period ends in {days_left} days ({deadline_info['end_date']}).",
                                "target_id": scheme.id,
                                "days_left": days_left
                            })
                            
                        timeline_events.append({
                            "title": f"Apply to {scheme.title}",
                            "date": end_date,
                            "type": "deadline",
                            "completed": False
                        })
                    except Exception:
                        pass # unparseable date format

            elif us.status == "applied":
                # Generate milestone timeline for applied schemes
                applied_date = us.created_at or now
                
                # Stage 1: Application submitted (completed)
                timeline_events.append({
                    "title": f"Application Submitted: {scheme.title}",
                    "date": applied_date,
                    "type": "application",
                    "completed": True
                })
                
                # Stage 2: Document verification (in progress — 7 days after application)
                verification_date = applied_date + timedelta(days=7)
                timeline_events.append({
                    "title": f"Document Verification: {scheme.title}",
                    "date": verification_date,
                    "type": "verification",
                    "completed": now >= verification_date
                })
                
                # Stage 3: Eligibility review (14 days after application)
                review_date = applied_date + timedelta(days=14)
                timeline_events.append({
                    "title": f"Eligibility Review: {scheme.title}",
                    "date": review_date,
                    "type": "review",
                    "completed": now >= review_date
                })
                
                # Stage 4: Approval/Disbursement (30 days after application)
                timeline_info = us.timeline or {}
                est_days = timeline_info.get("estimated_days", 30)
                approval_date = applied_date + timedelta(days=est_days)
                timeline_events.append({
                    "title": f"Expected Approval: {scheme.title}",
                    "date": approval_date,
                    "type": "approval",
                    "completed": us.status == "approved"
                })
                
                # Alert if verification is upcoming
                verif_days_left = (verification_date - now).days
                if 0 <= verif_days_left <= 7:
                    alerts.append({
                        "type": "verification_due",
                        "severity": "High" if verif_days_left <= 2 else "Medium",
                        "title": f"Verification Due: {scheme.title}",
                        "description": f"Document verification stage is due in {verif_days_left} days. Ensure all required documents are uploaded in the vault.",
                        "target_id": scheme.id,
                        "days_left": verif_days_left
                    })

        # 2. Check document expiries
        for doc in user_docs:
            if doc.expiry_date:
                days_left = (doc.expiry_date - now).days
                if days_left < 0:
                    alerts.append({
                        "type": "document_expired",
                        "severity": "High",
                        "title": f"Expired Document: {doc.file_name}",
                        "description": f"Your {doc.category.upper()} document expired on {doc.expiry_date.strftime('%Y-%m-%d')}.",
                        "target_id": doc.id,
                        "days_left": days_left
                    })
                elif 0 <= days_left <= 60:
                    alerts.append({
                        "type": "document_expiry",
                        "severity": "High" if days_left <= 15 else "Medium",
                        "title": f"Expiring Soon: {doc.file_name}",
                        "description": f"Your {doc.category.upper()} document will expire in {days_left} days ({doc.expiry_date.strftime('%Y-%m-%d')}).",
                        "target_id": doc.id,
                        "days_left": days_left
                    })
                
                timeline_events.append({
                    "title": f"{doc.category.replace('_', ' ').title()} Expiry",
                    "date": doc.expiry_date,
                    "type": "document_expiry",
                    "completed": False
                })

        # 3. Check reminders
        for rem in reminders:
            if not rem.is_completed:
                days_left = (rem.trigger_date - now).days
                if days_left >= -1: # active or just passed
                    alerts.append({
                        "type": "user_reminder",
                        "severity": "High" if days_left <= 1 else "Low",
                        "title": rem.title,
                        "description": rem.description,
                        "target_id": rem.id,
                        "days_left": max(0, days_left)
                    })
                
                timeline_events.append({
                    "title": rem.title,
                    "date": rem.trigger_date,
                    "type": "reminder",
                    "completed": rem.is_completed
                })

        # Sort timeline events by date ascending
        timeline_events.sort(key=lambda x: x["date"])
        
        # Convert date to string for JSON serialization
        for ev in timeline_events:
            ev["date"] = ev["date"].strftime("%Y-%m-%d")

        return {
            "alerts": alerts,
            "timeline_events": timeline_events
        }
