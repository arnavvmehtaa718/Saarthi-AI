from typing import Dict, Any, List
import json
from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile

class ApplicationPreparationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Application Preparation Agent",
            description="Prepares step-by-step checklists, cover letters, and submission timelines for applying to welfare schemes."
        )

    def prepare_application_kit(self, profile: UserProfile, scheme: Scheme) -> Dict[str, Any]:
        """
        Generate submission guide, cover letter, order of tasks, and approval timeline.
        """
        steps = scheme.steps if scheme.steps else [
            "Gather required certificates.",
            "Register on the benefits portal.",
            "Fill details and upload documentation.",
            "Submit the application and record reference ID."
        ]
        
        # Format custom cover letter
        cover_letter = (
            f"To,\n"
            f"The Competent Authority / Scheme Officer,\n"
            f"Government of India / Department of {scheme.department}\n\n"
            f"Subject: Application for registration under {scheme.title}\n\n"
            f"Respected Sir/Madam,\n\n"
            f"I am writing to formally apply for the benefits under the '{scheme.title}' scheme. "
            f"My name is {profile.gender or 'Applicant'}, residing in state {profile.state}. "
            f"I confirm that my current occupation is '{profile.occupation}' and my annual household income is "
            f"₹{profile.annual_income:,.2f}, which aligns with the eligibility thresholds defined for this program.\n\n"
            f"I have uploaded all the required documents, including my Aadhaar card and relevant certificate credentials. "
            f"Kindly review my application and initiate the registration process.\n\n"
            f"Thanking you,\n"
            f"Sincerely,\n"
            f"[Applicant Name / Signature]\n"
            f"Email: [User Email]\n"
            f"Mobile: [User Mobile]"
        )
        
        # Build timeline
        # Complex schemes take longer, simple schemes are fast
        timeline = {}
        if scheme.complexity == "Low":
            timeline = {
                "estimated_days": 10,
                "stages": [
                    {"name": "Online Submission & Biometric Link", "duration": "1-2 days"},
                    {"name": "Local Authority Validation", "duration": "3-5 days"},
                    {"name": "Direct Benefit Account Disbursement", "duration": "3 days"}
                ]
            }
        elif scheme.complexity == "High":
            timeline = {
                "estimated_days": 45,
                "stages": [
                    {"name": "Application & Business Proposal Submission", "duration": "7 days"},
                    {"name": "Field Officer Verification & Interview", "duration": "14 days"},
                    {"name": "District Committee Approvals", "duration": "14 days"},
                    {"name": "Bank Disbursal & Collateral Exception Waiver", "duration": "10 days"}
                ]
            }
        else: # Medium
            timeline = {
                "estimated_days": 21,
                "stages": [
                    {"name": "Application & Form Validation", "duration": "4 days"},
                    {"name": "Block Level Verification", "duration": "7 days"},
                    {"name": "State Node Disbursal Approval", "duration": "10 days"}
                ]
            }

        # Use AI-powered writing if available
        if self.use_real_ai:
            try:
                system_instruction = (
                    "You are an expert caseworker. Write a highly professional cover letter "
                    "tailored to the citizen profile and the scheme. Customize the steps and "
                    "timeline instructions to be highly specific."
                )
                prompt = (
                    f"Citizen Profile: {json.dumps(profile.__dict__, default=str)}\n"
                    f"Scheme Details: {scheme.title} (Complexity: {scheme.complexity})\n"
                    f"Generate a customized cover letter, a step-by-step checklist, and timeline stages."
                )
                ai_resp = self.run_llm(prompt, system_instruction)
                # Keep local structured structure but replace letter text if desired
                cover_letter = ai_resp
            except Exception:
                pass # fallback

        return {
            "steps": steps,
            "cover_letter": cover_letter,
            "timeline": timeline,
            "complexity": scheme.complexity
        }
