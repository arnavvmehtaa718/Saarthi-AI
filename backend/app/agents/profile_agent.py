from typing import Dict, Any, List
import json
from app.agents.base import BaseAgent
from app.models import UserProfile
from pydantic import BaseModel, Field

class ProfileExtractionSchema(BaseModel):
    state: str = Field(description="Indian State Name or 'All'", default="All")
    district: str | None = Field(description="District name if mentioned", default=None)
    age: int | None = Field(description="Age of the citizen as integer", default=None)
    gender: str = Field(description="Male, Female, Transgender, or General", default="General")
    annual_income: float | None = Field(description="Annual household income in Indian Rupees", default=None)
    category: str = Field(description="General, OBC, SC, ST, or EWS", default="General")
    occupation: str = Field(description="Farmer, Student, Artisan, Business Owner, Salaried, Unemployed, Street Vendor", default="Unemployed")
    is_student: bool = Field(description="Whether the citizen is a student", default=False)
    owns_land: bool = Field(description="Whether the citizen owns agricultural land", default=False)
    land_area_hectares: float = Field(description="Area of land owned in hectares", default=0.0)
    is_disabled: bool = Field(description="Whether the citizen has a physical or mental disability", default=False)
    disability_percentage: float = Field(description="Percentage of disability if applicable", default=0.0)
    disability_type: str | None = Field(description="Type of disability", default=None)
    explanation: str = Field(description="Brief explanation of what was updated and what is missing", default="")

class CitizenProfileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Citizen Profile Agent",
            description="Analyzes user communications and profiles to extract demographic and socio-economic information."
        )

    def extract_profile_from_text(self, text: str, current_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract profile information from natural language input."""
        if self.use_real_ai:
            system_instruction = (
                "You are an expert citizen caseworker. Extract profile data from the text. "
                "Update the current profile with new information. Do not overwrite existing "
                "valid values unless the user explicitly contradicts them. If the income is described in lakh, convert to number (e.g. 2 lakh = 200000)."
            )
            prompt = (
                f"Current profile data:\n{json.dumps(current_profile, indent=2)}\n\n"
                f"User input text:\n{text}\n\n"
                f"Extract and return the updated fields."
            )
            try:
                res_txt = self.run_llm(prompt, system_instruction, response_schema=ProfileExtractionSchema)
                extracted_data = json.loads(res_txt)
                
                # Merge with current profile
                updated_profile = current_profile.copy()
                for key, val in extracted_data.items():
                    if val is not None and key != "explanation":
                        updated_profile[key] = val
                updated_profile["explanation"] = extracted_data.get("explanation", "Profile updated.")
                return updated_profile
            except Exception as e:
                # Log error and fall back to mock extraction
                pass
                
        # Mock / Rule-based fallback
        updated_profile = current_profile.copy()
        text_lower = text.lower()
        explanation_parts = []
        
        # Simple keywords/regex extraction
        if "farmer" in text_lower or "kisan" in text_lower:
            updated_profile["occupation"] = "Farmer"
            updated_profile["owns_land"] = True
            explanation_parts.append("Occupation updated to Farmer.")
            
        if "student" in text_lower or "college" in text_lower or "school" in text_lower:
            updated_profile["occupation"] = "Student"
            updated_profile["is_student"] = True
            explanation_parts.append("Profile marked as Student.")
            
        if "street vendor" in text_lower or "vendor" in text_lower or "seller" in text_lower:
            updated_profile["occupation"] = "Street Vendor"
            explanation_parts.append("Occupation updated to Street Vendor.")
            
        if "artisan" in text_lower or "craft" in text_lower or "carpenter" in text_lower or "tailor" in text_lower:
            updated_profile["occupation"] = "Artisan"
            explanation_parts.append("Occupation updated to Artisan.")
            
        if "business" in text_lower or "entrepreneur" in text_lower or "shop" in text_lower:
            updated_profile["occupation"] = "Business Owner"
            explanation_parts.append("Occupation updated to Business Owner.")

        # States
        states = ["uttar pradesh", "bihar", "maharashtra", "karnataka", "delhi", "madhya pradesh", "rajasthan", "gujarat", "tamil nadu", "west bengal"]
        for s in states:
            if s in text_lower:
                updated_profile["state"] = s.title()
                explanation_parts.append(f"State set to {s.title()}.")
                break

        # Categories
        if "obc" in text_lower:
            updated_profile["category"] = "OBC"
            explanation_parts.append("Category set to OBC.")
        elif "sc" in text_lower:
            updated_profile["category"] = "SC"
            explanation_parts.append("Category set to SC.")
        elif "st" in text_lower:
            updated_profile["category"] = "ST"
            explanation_parts.append("Category set to ST.")
        elif "ews" in text_lower:
            updated_profile["category"] = "EWS"
            explanation_parts.append("Category set to EWS.")
        elif "general" in text_lower:
            updated_profile["category"] = "General"

        # Age parsing
        import re
        age_match = re.search(r'(\d+)\s*(?:years old|yrs|yr|year old|age)', text_lower)
        if not age_match:
            age_match = re.search(r'age\s*(?:is\s*)?(\d+)', text_lower)
        if age_match:
            age = int(age_match.group(1))
            updated_profile["age"] = age
            explanation_parts.append(f"Age set to {age}.")

        # Income parsing (lakh or direct rupees)
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lacs|lac)', text_lower)
        if lakh_match:
            income = float(lakh_match.group(1)) * 100000
            updated_profile["annual_income"] = income
            explanation_parts.append(f"Annual income set to ₹{income:,.2f}.")
        else:
            income_match = re.search(r'(?:income|earn|earning)\s*(?:is\s*)?(?:rs\.?|inr|₹)?\s*(\d{4,8})', text_lower)
            if income_match:
                income = float(income_match.group(1))
                updated_profile["annual_income"] = income
                explanation_parts.append(f"Annual income set to ₹{income:,.2f}.")

        # Disability
        if "disabled" in text_lower or "disability" in text_lower or "handicap" in text_lower:
            updated_profile["is_disabled"] = True
            explanation_parts.append("Disabled flag set to True.")
            pct_match = re.search(r'(\d+)\s*%', text_lower)
            if pct_match:
                updated_profile["disability_percentage"] = float(pct_match.group(1))
                explanation_parts.append(f"Disability percentage set to {pct_match.group(1)}%.")

        if not explanation_parts:
            explanation_parts.append("Extracted profile details from chat.")
            
        updated_profile["explanation"] = " ".join(explanation_parts)
        return updated_profile

    def get_missing_fields(self, profile: UserProfile) -> List[str]:
        """Check what crucial fields are missing for benefit discovery."""
        missing = []
        if not profile.state or profile.state == "All":
            missing.append("state")
        if not profile.age:
            missing.append("age")
        if profile.annual_income == 0.0:
            # We don't know if it's actually 0 or just not filled.
            missing.append("annual_income")
        if not profile.category:
            missing.append("category")
        if not profile.occupation:
            missing.append("occupation")
        return missing
