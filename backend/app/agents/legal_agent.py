from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile

class LegalPolicyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Legal Policy Agent",
            description="Simplifies complex government criteria and eligibility fine print into layman or ELI15 language."
        )

    def simplify_rules(self, scheme: Scheme, profile: UserProfile = None) -> str:
        """
        Generate a simplified (Explain Like I'm 15) breakdown of the eligibility rules.
        """
        # We can construct a detailed but simple rule breakdown
        rules = scheme.eligibility_rules
        simplified_clauses = []
        
        # Age
        min_age = rules.get("min_age")
        max_age = rules.get("max_age")
        if min_age and max_age:
            simplified_clauses.append(f"You must be between **{min_age} and {max_age} years old**.")
        elif min_age:
            simplified_clauses.append(f"You must be at least **{min_age} years old**.")
        elif max_age:
            simplified_clauses.append(f"You must be under **{max_age} years old**.")
            
        # Income
        max_income = rules.get("max_annual_income")
        if max_income:
            simplified_clauses.append(f"Your household annual income should not be more than **₹{max_income:,.2f}**.")
            if profile and profile.annual_income > max_income:
                diff = profile.annual_income - max_income
                simplified_clauses.append(f"*(Note: You exceed this limit by ₹{diff:,.2f})*")
        else:
            simplified_clauses.append("There is no strict income limit, but you should not be paying professional income tax.")

        # Occupation
        occ_whitelist = rules.get("occupation_whitelist")
        if occ_whitelist:
            jobs = ", ".join(occ_whitelist)
            simplified_clauses.append(f"Your main job must be one of: **{jobs}**.")
            
        # Category
        cat_whitelist = rules.get("category_whitelist")
        if cat_whitelist:
            cats = ", ".join(cat_whitelist)
            simplified_clauses.append(f"You must belong to one of these communities: **{cats}**.")
            
        # Land
        if rules.get("owns_land_required"):
            simplified_clauses.append("You must own agricultural/farming land.")
            
        # Exclusions
        if rules.get("excludes_government_employees"):
            simplified_clauses.append("No one in your family should have a permanent government job.")
            
        if rules.get("excludes_taxpayers"):
            simplified_clauses.append("No one in your family should be paying income tax.")

        intro = f"Here is the simple breakdown for **{scheme.title}**:"
        list_items = "\n".join([f"- {clause}" for clause in simplified_clauses])
        
        fallback_eli15 = f"{intro}\n\n{list_items}\n\n**Official Rule Explanation:**\n{scheme.eli15_explanation}"

        if self.use_real_ai:
            try:
                system_instruction = (
                    "You are a helpful youth educator. Simplify complicated legal government policy rules into "
                    "extremely simple, clear, and engaging language. Avoid heavy jargon. Break down calculations if any."
                )
                prompt = (
                    f"Scheme Title: {scheme.title}\n"
                    f"Detailed Eligibility Rules: {rules}\n"
                    f"Citizen Profile: {profile.__dict__ if profile else 'Not Provided'}\n"
                    f"Simplify these rules."
                )
                ai_eli15 = self.run_llm(prompt, system_instruction)
                return ai_eli15
            except Exception:
                pass # fallback

        return fallback_eli15
