from typing import Dict, Any, List
import json
from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile

class EligibilityVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Eligibility Verification Agent",
            description="Performs micro-targeting eligibility logic and generates clear reasoning traces."
        )

    def verify(self, profile: UserProfile, scheme: Scheme) -> Dict[str, Any]:
        """Verify eligibility and generate a reasoning trace."""
        # Standard rule evaluation
        rules = scheme.eligibility_rules
        trace = []
        checks = []
        is_eligible = True
        status = "Eligible"
        
        # State Check
        state_match = True
        if scheme.state != "Central" and profile.state != "All":
            state_match = scheme.state.lower() == profile.state.lower()
            if not state_match:
                is_eligible = False
                checks.append({
                    "criteria": "State residency",
                    "required": scheme.state,
                    "actual": profile.state,
                    "passed": False,
                    "impact": "CRITICAL: Resident required"
                })
                trace.append(f"Residency verification failed: Scheme requires state '{scheme.state}' but user is in '{profile.state}'.")
            else:
                checks.append({
                    "criteria": "State residency",
                    "required": scheme.state,
                    "actual": profile.state,
                    "passed": True,
                    "impact": "Passed"
                })

        # Income Check
        max_income = rules.get("max_annual_income")
        if max_income is not None:
            income_passed = profile.annual_income <= max_income
            if not income_passed:
                is_eligible = False
                checks.append({
                    "criteria": "Annual Income Limit",
                    "required": f"<= ₹{max_income:,.2f}",
                    "actual": f"₹{profile.annual_income:,.2f}",
                    "passed": False,
                    "impact": "CRITICAL: Exceeds threshold"
                })
                trace.append(f"Income threshold failed: User earns ₹{profile.annual_income:,.2f}, limit is ₹{max_income:,.2f}.")
            else:
                checks.append({
                    "criteria": "Annual Income Limit",
                    "required": f"<= ₹{max_income:,.2f}",
                    "actual": f"₹{profile.annual_income:,.2f}",
                    "passed": True,
                    "impact": "Passed"
                })

        # Age check
        min_age = rules.get("min_age")
        max_age = rules.get("max_age")
        if min_age is not None:
            age_passed = profile.age >= min_age
            if not age_passed:
                is_eligible = False
                checks.append({
                    "criteria": "Minimum Age",
                    "required": f">= {min_age} years",
                    "actual": f"{profile.age} years",
                    "passed": False,
                    "impact": "CRITICAL: Underage"
                })
                trace.append(f"Minimum age limit failed: User age is {profile.age}, requires at least {min_age}.")
            else:
                checks.append({
                    "criteria": "Minimum Age",
                    "required": f">= {min_age} years",
                    "actual": f"{profile.age} years",
                    "passed": True,
                    "impact": "Passed"
                })
        
        if max_age is not None:
            age_passed = profile.age <= max_age
            if not age_passed:
                is_eligible = False
                checks.append({
                    "criteria": "Maximum Age",
                    "required": f"<= {max_age} years",
                    "actual": f"{profile.age} years",
                    "passed": False,
                    "impact": "CRITICAL: Overage"
                })
                trace.append(f"Maximum age limit failed: User age is {profile.age}, limit is {max_age}.")
            else:
                checks.append({
                    "criteria": "Maximum Age",
                    "required": f"<= {max_age} years",
                    "actual": f"{profile.age} years",
                    "passed": True,
                    "impact": "Passed"
                })

        # Occupation Check
        occ_list = rules.get("occupation_whitelist")
        if occ_list:
            occ_passed = profile.occupation in occ_list
            if not occ_passed:
                is_eligible = False
                checks.append({
                    "criteria": "Occupation Match",
                    "required": f"One of {', '.join(occ_list)}",
                    "actual": profile.occupation,
                    "passed": False,
                    "impact": "CRITICAL: Occupation mismatch"
                })
                trace.append(f"Occupation check failed: User occupation is '{profile.occupation}' but scheme requires {occ_list}.")
            else:
                checks.append({
                    "criteria": "Occupation Match",
                    "required": f"One of {', '.join(occ_list)}",
                    "actual": profile.occupation,
                    "passed": True,
                    "impact": "Passed"
                })

        # Category Check
        cat_list = rules.get("category_whitelist")
        if cat_list:
            cat_passed = profile.category in cat_list
            if not cat_passed:
                is_eligible = False
                checks.append({
                    "criteria": "Social Category",
                    "required": f"One of {', '.join(cat_list)}",
                    "actual": profile.category,
                    "passed": False,
                    "impact": "CRITICAL: Social category mismatch"
                })
                trace.append(f"Category check failed: User category is {profile.category} but scheme requires {cat_list}.")
            else:
                checks.append({
                    "criteria": "Social Category",
                    "required": f"One of {', '.join(cat_list)}",
                    "actual": profile.category,
                    "passed": True,
                    "impact": "Passed"
                })

        # Disability check
        is_disabled_preferred = rules.get("is_disabled_preferred")
        if is_disabled_preferred and not profile.is_disabled:
            checks.append({
                "criteria": "Disability preference",
                "required": "Preferred (Disabled)",
                "actual": "General",
                "passed": True,
                "impact": "LOWER PRIORITY: Non-disabled applicants get secondary priority"
            })
            trace.append("Note: Persons with disabilities are prioritized. You may apply but approval takes longer.")

        # Determine Final Status
        if not is_eligible:
            status = "Not Eligible"
        else:
            # Let's check if there is some "Likely Eligible" or "Missing Info" cases
            # If user profile has missing fields that could disqualify them, set as Missing Information
            # For example, if annual income is exactly 0 and max_annual_income is configured, we might want confirmation
            if profile.annual_income == 0.0 and max_income is not None:
                status = "Missing Information"
                trace.append("Action Required: Please verify your annual household income to confirm eligibility.")
            else:
                status = "Eligible"

        # AI-powered refinement of explanation if available
        explanation = " ".join(trace) if trace else "All basic demographic, income, and occupation checks passed."
        if self.use_real_ai:
            try:
                system_instruction = (
                    "You are a legal caseworker explaining eligibility decisions. "
                    "Make sure your tone is helpful, precise, and completely objective. "
                    "Explain exactly why the citizen is eligible or ineligible. Use clear bullet points."
                )
                prompt = (
                    f"Citizen Profile: {json.dumps(profile.__dict__, default=str)}\n"
                    f"Scheme Details: {scheme.title}\n"
                    f"Eligibility Rules: {json.dumps(rules)}\n"
                    f"Evaluation Trace: {json.dumps(checks)}\n"
                    f"Determine status and rewrite the caseworker explanation in markdown."
                )
                ai_explanation = self.run_llm(prompt, system_instruction)
                explanation = ai_explanation
            except Exception:
                pass # fallback to rule explanation

        return {
            "status": status,
            "explanation": explanation,
            "checks": checks,
            "score": 100.0 if status == "Eligible" else (70.0 if status == "Likely Eligible" else (50.0 if status == "Missing Information" else 10.0))
        }
