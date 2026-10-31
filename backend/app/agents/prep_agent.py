import json
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile
from app.services.privacy import redact_pii


class ApplicationPreparationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Application Preparation Agent",
            description="Prepares checklists, cover letters, and submission timelines for scheme applications.",
        )

    def prepare_application_kit(
        self,
        profile: UserProfile,
        scheme: Scheme,
        document_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        steps = scheme.steps or [
            "Gather the required certificates.",
            "Register on the official benefits portal.",
            "Fill in the details and upload the required documents.",
            "Submit the application and save the reference number.",
        ]

        applicant_name = (getattr(profile, "full_name", None) or "").strip() or "[Applicant Name]"
        state = getattr(profile, "state", None) or "[State]"
        occupation = getattr(profile, "occupation", None) or "[Occupation]"
        income = getattr(profile, "annual_income", None)
        income_text = f"₹{income:,.0f}" if income is not None else "[annual income]"

        checklist = (document_result or {}).get("checklist", [])
        missing = (document_result or {}).get("missing", [])
        if checklist:
            missing_labels = [
                item["required_label"]
                for item in checklist
                if item.get("status") in {"Missing", "Expired"}
            ]
            if missing_labels:
                document_paragraph = (
                    "The following documents are still pending and will be submitted as soon as they are available: "
                    + ", ".join(missing_labels)
                    + "."
                )
            else:
                document_paragraph = (
                    "The required documents currently available in my vault are enclosed for verification."
                )
        else:
            document_paragraph = (
                "I will upload the documents listed in the scheme checklist before submitting the application."
            )

        cover_letter = (
            "To,\n"
            "The Competent Authority / Scheme Officer,\n"
            f"Department of {scheme.department}\n\n"
            f"Subject: Application for {scheme.title}\n\n"
            "Respected Sir/Madam,\n\n"
            f"I am {applicant_name}, residing in {state}. I am applying for the benefits under "
            f"the '{scheme.title}' scheme. My current occupation is {occupation} and my annual "
            f"household income is {income_text}.\n\n"
            f"{document_paragraph}\n\n"
            "Kindly review my application and guide me if any additional document or clarification "
            "is required. I understand that eligibility and approval are decided only by the "
            "concerned department after official verification.\n\n"
            "Thanking you,\n"
            "Sincerely,\n"
            f"{applicant_name}\n"
            "Email: [User Email]\n"
            "Mobile: [User Mobile]"
        )

        if scheme.complexity == "Low":
            timeline = {
                "estimated_days": 10,
                "note": "Indicative only; actual processing depends on the department.",
                "stages": [
                    {"name": "Online submission", "duration": "1-2 days"},
                    {"name": "Local authority validation", "duration": "3-5 days"},
                    {"name": "Benefit disbursement", "duration": "3 days"},
                ],
            }
        elif scheme.complexity == "High":
            timeline = {
                "estimated_days": 45,
                "note": "Indicative only; loan and verification timelines vary by bank and district.",
                "stages": [
                    {"name": "Application and proposal submission", "duration": "7 days"},
                    {"name": "Field verification / interview", "duration": "14 days"},
                    {"name": "Committee approvals", "duration": "14 days"},
                    {"name": "Bank disbursal", "duration": "10 days"},
                ],
            }
        else:
            timeline = {
                "estimated_days": 21,
                "note": "Indicative only; actual processing depends on the department.",
                "stages": [
                    {"name": "Application and form validation", "duration": "4 days"},
                    {"name": "Block-level verification", "duration": "7 days"},
                    {"name": "State nodal approval", "duration": "10 days"},
                ],
            }

        if self.use_real_ai:
            try:
                safe_profile = redact_pii(
                    json.dumps(
                        {
                            "full_name": applicant_name,
                            "state": state,
                            "occupation": occupation,
                            "annual_income": income,
                            "category": getattr(profile, "category", None),
                        },
                        default=str,
                    )
                )
                system_instruction = (
                    "You are an Indian government-benefits caseworker. Write a concise, formal cover letter. "
                    "Use only the supplied facts. Never claim that documents are uploaded if they are missing. "
                    "Never promise approval. Include a line that the department makes the final decision. "
                    "Return only the letter text."
                )
                prompt = (
                    f"Citizen facts: {safe_profile}\n"
                    f"Scheme: {scheme.title}\nDepartment: {scheme.department}\n"
                    f"Missing/expired documents: {', '.join(missing) if missing else 'none recorded'}\n"
                    f"Draft letter to improve:\n{cover_letter}"
                )
                ai_letter = self.run_llm(prompt, system_instruction).strip()
                if ai_letter:
                    cover_letter = ai_letter
            except Exception:
                pass

        return {
            "steps": steps,
            "cover_letter": cover_letter,
            "timeline": timeline,
            "complexity": scheme.complexity,
            "checklist": checklist,
            "missing_documents": missing,
            "disclaimer": "Eligibility and approval are decided by the concerned department after official verification.",
        }
