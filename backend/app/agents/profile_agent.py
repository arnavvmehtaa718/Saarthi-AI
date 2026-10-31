import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, extract_json
from app.models import UserProfile


class ProfileExtractionSchema(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Citizen's full name if stated")
    state: Optional[str] = Field(default=None, description="Indian state name if stated")
    district: Optional[str] = Field(default=None, description="District if stated")
    age: Optional[int] = Field(default=None, description="Age in years if stated")
    gender: Optional[str] = Field(default=None, description="Male, Female, Transgender, or Other")
    annual_income: Optional[float] = Field(
        default=None, description="Annual household income in INR if stated"
    )
    category: Optional[str] = Field(default=None, description="General, OBC, SC, ST, or EWS")
    occupation: Optional[str] = Field(
        default=None,
        description="Farmer, Student, Artisan, Business Owner, Salaried, Unemployed, or Street Vendor",
    )
    educational_level: Optional[str] = Field(
        default=None,
        description="Illiterate, Primary, Metric, Senior Secondary, Graduate, or Post Graduate",
    )
    is_student: Optional[bool] = Field(default=None)
    owns_land: Optional[bool] = Field(default=None)
    land_area_hectares: Optional[float] = Field(default=None)
    is_disabled: Optional[bool] = Field(default=None)
    disability_percentage: Optional[float] = Field(default=None)
    disability_type: Optional[str] = Field(default=None)
    has_ration_card: Optional[bool] = Field(default=None)
    is_rural: Optional[bool] = Field(default=None)
    owns_house: Optional[bool] = Field(default=None)
    family_beneficiary_count: Optional[int] = Field(default=None)
    has_business_plan: Optional[bool] = Field(default=None)
    is_government_employee: Optional[bool] = Field(default=None)
    explanation: str = Field(default="", description="Short note on what was updated or still missing")


class CitizenProfileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Citizen Profile Agent",
            description="Extracts demographic and socio-economic profile fields from natural language.",
        )

    def _merge_ai_result(
        self, current_profile: Dict[str, Any], extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        updated = current_profile.copy()
        explanation = extracted.pop("explanation", "") if isinstance(extracted, dict) else ""
        allowed = set(ProfileExtractionSchema.model_fields)
        changed = []
        for key, value in extracted.items():
            if key not in allowed or key == "explanation" or value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
            if current_profile.get(key) != value:
                updated[key] = value
                changed.append(key)
        if changed:
            updated["explanation"] = explanation or f"Updated: {', '.join(sorted(changed))}."
        else:
            updated["explanation"] = explanation or "No new profile fields were found in this message."
        return updated

    def extract_profile_from_text(
        self,
        text: str,
        current_profile: Dict[str, Any],
        chat_context: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if self.use_real_ai:
            system_instruction = (
                "You are a careful Indian citizen caseworker. Extract only facts the user explicitly states. "
                "Do not infer or overwrite values that are not mentioned. Omit unknown fields entirely. "
                "Convert '2 lakh' to 200000. Use only the allowed enum values. "
                "Never guess a name, category, income, or disability status."
            )
            prompt = (
                f"Current profile:\n{json.dumps(current_profile, indent=2, default=str)}\n\n"
                f"Recent conversation:\n{json.dumps(chat_context or [], indent=2, default=str)}\n\n"
                f"New user message:\n{text}\n\n"
                "Return only the fields that are explicitly stated in the new message."
            )
            try:
                raw = self.run_llm(prompt, system_instruction, response_schema=ProfileExtractionSchema)
                extracted = extract_json(raw)
                return self._merge_ai_result(current_profile, extracted)
            except Exception:
                pass

        updated = current_profile.copy()
        text_lower = text.lower()
        notes: List[str] = []

        def set_field(field: str, value: Any, note: str) -> None:
            if current_profile.get(field) != value:
                updated[field] = value
                notes.append(note)

        name_match = re.search(
            r"\b(?:my name is|name is|i am called)\s+([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,2})",
            text,
            re.IGNORECASE,
        )
        if name_match:
            candidate = name_match.group(1).strip(" .")
            if candidate.lower() not in {
                "a farmer",
                "a student",
                "a vendor",
                "an artisan",
                "unemployed",
                "from",
            }:
                set_field("full_name", candidate, f"Name set to {candidate}.")

        # Occupation. Specific phrases are checked before broad words.
        if re.search(r"\b(street vendor|vendor|seller|rehdi|patri)\b", text_lower):
            set_field("occupation", "Street Vendor", "Occupation set to Street Vendor.")
        elif re.search(r"\b(artisan|craftsperson|carpenter|tailor|potter|goldsmith|barber)\b", text_lower):
            set_field("occupation", "Artisan", "Occupation set to Artisan.")
        elif re.search(r"\b(farmer|kisan|agriculture|farming)\b", text_lower):
            set_field("occupation", "Farmer", "Occupation set to Farmer.")
            set_field("owns_land", True, "Land ownership marked as yes.")
        elif re.search(r"\b(student|college student|school student|studying|pursuing)\b", text_lower):
            set_field("occupation", "Student", "Occupation set to Student.")
            set_field("is_student", True, "Student status marked as yes.")
        elif re.search(r"\b(business owner|entrepreneur|shop owner|run a shop|own a shop)\b", text_lower):
            set_field("occupation", "Business Owner", "Occupation set to Business Owner.")
        elif re.search(r"\b(salaried|private job|office job|employee)\b", text_lower):
            set_field("occupation", "Salaried", "Occupation set to Salaried.")
        elif re.search(r"\b(unemployed|no job|jobless|without work)\b", text_lower):
            set_field("occupation", "Unemployed", "Occupation set to Unemployed.")

        states = [
            "andhra pradesh",
            "arunachal pradesh",
            "assam",
            "bihar",
            "chhattisgarh",
            "goa",
            "gujarat",
            "haryana",
            "himachal pradesh",
            "jharkhand",
            "karnataka",
            "kerala",
            "madhya pradesh",
            "maharashtra",
            "manipur",
            "meghalaya",
            "mizoram",
            "nagaland",
            "odisha",
            "punjab",
            "rajasthan",
            "sikkim",
            "tamil nadu",
            "telangana",
            "tripura",
            "uttar pradesh",
            "uttarakhand",
            "west bengal",
            "delhi",
            "jammu and kashmir",
            "ladakh",
            "puducherry",
            "chandigarh",
        ]
        for state in states:
            if re.search(rf"\b{re.escape(state)}\b", text_lower):
                set_field("state", state.title(), f"State set to {state.title()}.")
                break

        if re.search(r"\bobc\b", text_lower):
            set_field("category", "OBC", "Category set to OBC.")
        elif re.search(r"\bsc\b", text_lower):
            set_field("category", "SC", "Category set to SC.")
        elif re.search(r"\bst\b", text_lower):
            set_field("category", "ST", "Category set to ST.")
        elif re.search(r"\bews\b", text_lower):
            set_field("category", "EWS", "Category set to EWS.")
        elif re.search(r"\bgeneral\b", text_lower):
            set_field("category", "General", "Category set to General.")

        age_match = re.search(
            r"(\d{1,3})\s*(?:years?\s*old|yrs?|year old)", text_lower
        ) or re.search(r"\bage\s*(?:is\s*)?(\d{1,3})\b", text_lower)
        if age_match:
            age = int(age_match.group(1))
            if 0 <= age <= 120:
                set_field("age", age, f"Age set to {age}.")

        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lacs|lac)", text_lower)
        if lakh_match:
            income = float(lakh_match.group(1)) * 100000
            set_field("annual_income", income, f"Annual income set to ₹{income:,.0f}.")
        else:
            income_match = re.search(
                r"(?:income|earn|earning|salary)\s*(?:is\s*)?(?:rs\.?|inr|₹)?\s*(\d{4,9})",
                text_lower,
            )
            if income_match:
                income = float(income_match.group(1))
                set_field("annual_income", income, f"Annual income set to ₹{income:,.0f}.")

        if re.search(r"\b(disabled|disability|handicap|divyang)\b", text_lower):
            set_field("is_disabled", True, "Disability status marked as yes.")
            pct_match = re.search(r"(\d{1,3})\s*%", text_lower)
            if pct_match and 0 <= int(pct_match.group(1)) <= 100:
                set_field(
                    "disability_percentage",
                    float(pct_match.group(1)),
                    f"Disability percentage set to {pct_match.group(1)}%.",
                )

        if re.search(r"\bration card\b", text_lower):
            if re.search(r"\b(no|don't have|do not have|without)\b[^.]{0,20}\bration card\b", text_lower):
                set_field("has_ration_card", False, "Ration card marked as not available.")
            else:
                set_field("has_ration_card", True, "Ration card marked as available.")

        if re.search(r"\b(village|rural|gram panchayat|farmland)\b", text_lower):
            set_field("is_rural", True, "Residence marked as rural.")
        elif re.search(r"\b(city|urban|town|municipal)\b", text_lower):
            set_field("is_rural", False, "Residence marked as urban.")

        if re.search(r"\b(no house|homeless|don't own a house|do not own a house)\b", text_lower):
            set_field("owns_house", False, "House ownership marked as no.")
        elif re.search(r"\b(own house|own a house|pucca house|my house)\b", text_lower):
            set_field("owns_house", True, "House ownership marked as yes.")

        family_match = re.search(
            r"(\d{1,2})\s*(?:family members|people in my family|beneficiaries)", text_lower
        )
        if family_match:
            set_field(
                "family_beneficiary_count",
                int(family_match.group(1)),
                "Family beneficiary count updated.",
            )

        if re.search(r"\b(business plan|project report)\b", text_lower):
            if re.search(r"\b(no|don't have|do not have)\b[^.]{0,25}\b(business plan|project report)\b", text_lower):
                set_field("has_business_plan", False, "Business plan marked as not ready.")
            else:
                set_field("has_business_plan", True, "Business plan marked as ready.")

        if re.search(r"\b(not a government employee|private sector|private job)\b", text_lower):
            set_field("is_government_employee", False, "Government-employee status marked as no.")
        elif re.search(r"\b(government employee|govt employee|government job|sarkari naukri)\b", text_lower):
            set_field("is_government_employee", True, "Government-employee status marked as yes.")

        if notes:
            updated["explanation"] = " ".join(notes)
        else:
            updated["explanation"] = "No new profile fields were found in this message."
        return updated

    def get_missing_fields(self, profile: UserProfile) -> List[str]:
        missing = []
        if not profile.state or profile.state == "All":
            missing.append("state")
        if not profile.age:
            missing.append("age")
        if profile.annual_income == 0.0:
            missing.append("annual_income")
        if not profile.category:
            missing.append("category")
        if not profile.occupation:
            missing.append("occupation")
        return missing
