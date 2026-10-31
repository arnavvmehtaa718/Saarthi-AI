import json
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile
from app.services.privacy import redact_pii

EDUCATION_ORDER = {
    "illiterate": 0,
    "primary": 1,
    "metric": 2,
    "matric": 2,
    "senior secondary": 3,
    "higher secondary": 3,
    "graduate": 4,
    "post graduate": 5,
    "postgraduate": 5,
}

STATUS_SCORES = {
    "Eligible": 100.0,
    "Potentially Eligible": 70.0,
    "Insufficient Information": 40.0,
    "Not Eligible": 10.0,
}


def _profile_value(profile: UserProfile, field: str, default=None):
    if profile is None:
        return default
    value = getattr(profile, field, default)
    return default if value is None else value


def _profile_snapshot(profile: UserProfile) -> Dict[str, Any]:
    fields = [
        "full_name",
        "state",
        "district",
        "age",
        "gender",
        "annual_income",
        "category",
        "occupation",
        "educational_level",
        "is_student",
        "owns_land",
        "land_area_hectares",
        "employment_status",
        "is_disabled",
        "disability_percentage",
        "has_ration_card",
        "is_rural",
        "owns_house",
        "family_beneficiary_count",
        "has_business_plan",
        "is_government_employee",
    ]
    return {field: getattr(profile, field, None) for field in fields}


class EligibilityVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Eligibility Verification Agent",
            description="Runs deterministic eligibility rules and produces transparent reasoning traces.",
        )

    def _check(
        self,
        checks: List[Dict[str, Any]],
        criteria: str,
        required: str,
        actual: Any,
        passed: Optional[bool],
        impact: str,
    ) -> None:
        checks.append(
            {
                "criteria": criteria,
                "required": required,
                "actual": actual,
                "passed": passed,
                "impact": impact,
            }
        )

    def verify(self, profile: UserProfile, scheme: Scheme) -> Dict[str, Any]:
        """Evaluate one scheme. The rule engine, not the LLM, decides status."""
        rules = scheme.eligibility_rules or {}
        checks: List[Dict[str, Any]] = []
        critical_failures: List[str] = []
        unknowns: List[str] = []
        warnings: List[str] = []

        if profile is None:
            return {
                "status": "Insufficient Information",
                "score": STATUS_SCORES["Insufficient Information"],
                "explanation": "Create a citizen profile before checking eligibility.",
                "checks": [],
                "missing_information": ["profile"],
                "warnings": [],
                "decision_source": "deterministic_rules",
            }

        # Residency
        if scheme.state and scheme.state.lower() != "central":
            state = (_profile_value(profile, "state", "") or "").strip()
            if not state or state.lower() == "all":
                unknowns.append("state of residence")
                self._check(
                    checks,
                    "State residency",
                    scheme.state,
                    "Not provided",
                    None,
                    "MISSING INFORMATION: state required",
                )
            elif state.lower() != scheme.state.lower():
                critical_failures.append(
                    f"scheme is limited to residents of {scheme.state}, but your profile says {state}"
                )
                self._check(
                    checks,
                    "State residency",
                    scheme.state,
                    state,
                    False,
                    "CRITICAL: resident of the scheme state required",
                )
            else:
                self._check(
                    checks,
                    "State residency",
                    scheme.state,
                    state,
                    True,
                    "Passed",
                )

        # Age
        age = _profile_value(profile, "age")
        min_age = rules.get("min_age")
        max_age = rules.get("max_age")
        if min_age is not None or max_age is not None:
            if age is None or age <= 0:
                unknowns.append("age")
                self._check(
                    checks,
                    "Age",
                    f"{min_age or 0} to {max_age or 'no upper limit'} years",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: age required",
                )
            else:
                if min_age is not None:
                    passed = age >= min_age
                    if not passed:
                        critical_failures.append(f"age {age} is below the minimum of {min_age}")
                    self._check(
                        checks,
                        "Minimum age",
                        f">= {min_age} years",
                        f"{age} years",
                        passed,
                        "Passed" if passed else "CRITICAL: below minimum age",
                    )
                if max_age is not None:
                    passed = age <= max_age
                    if not passed:
                        critical_failures.append(f"age {age} is above the maximum of {max_age}")
                    self._check(
                        checks,
                        "Maximum age",
                        f"<= {max_age} years",
                        f"{age} years",
                        passed,
                        "Passed" if passed else "CRITICAL: above maximum age",
                    )

        # Income
        max_income = rules.get("max_annual_income")
        annual_income = _profile_value(profile, "annual_income")
        if max_income is not None:
            if annual_income is None or annual_income <= 0:
                unknowns.append("annual household income")
                self._check(
                    checks,
                    "Annual income limit",
                    f"<= ₹{max_income:,.0f}",
                    "Not confirmed",
                    None,
                    "MISSING INFORMATION: income required",
                )
            elif annual_income > max_income:
                critical_failures.append(
                    f"annual income ₹{annual_income:,.0f} exceeds the limit of ₹{max_income:,.0f}"
                )
                self._check(
                    checks,
                    "Annual income limit",
                    f"<= ₹{max_income:,.0f}",
                    f"₹{annual_income:,.0f}",
                    False,
                    "CRITICAL: income exceeds limit",
                )
            else:
                passed = True
                if annual_income > max_income * 0.8:
                    warnings.append(
                        f"income ₹{annual_income:,.0f} is close to the ₹{max_income:,.0f} limit and may need verification"
                    )
                self._check(
                    checks,
                    "Annual income limit",
                    f"<= ₹{max_income:,.0f}",
                    f"₹{annual_income:,.0f}",
                    passed,
                    "Passed" if not warnings else "Passed with verification note",
                )

        # Occupation
        occupations = rules.get("occupation_whitelist")
        if occupations:
            occupation = (_profile_value(profile, "occupation", "") or "").strip()
            if not occupation or occupation.lower() in {"unknown", "none"}:
                unknowns.append("occupation")
                self._check(
                    checks,
                    "Occupation",
                    f"One of {', '.join(occupations)}",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: occupation required",
                )
            else:
                passed = occupation in occupations
                if not passed:
                    critical_failures.append(
                        f"occupation '{occupation}' is not one of {', '.join(occupations)}"
                    )
                self._check(
                    checks,
                    "Occupation",
                    f"One of {', '.join(occupations)}",
                    occupation,
                    passed,
                    "Passed" if passed else "CRITICAL: occupation mismatch",
                )

        # Social category
        categories = rules.get("category_whitelist")
        if categories:
            category = (_profile_value(profile, "category", "") or "").strip()
            if not category or category.lower() in {"unknown", "none"}:
                unknowns.append("social category")
                self._check(
                    checks,
                    "Social category",
                    f"One of {', '.join(categories)}",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: category required",
                )
            else:
                passed = category in categories
                if not passed:
                    critical_failures.append(
                        f"social category {category} is not one of {', '.join(categories)}"
                    )
                self._check(
                    checks,
                    "Social category",
                    f"One of {', '.join(categories)}",
                    category,
                    passed,
                    "Passed" if passed else "CRITICAL: category mismatch",
                )

        # Explicit boolean requirements
        if "is_student" in rules:
            required_student = bool(rules.get("is_student"))
            is_student = _profile_value(profile, "is_student", False)
            passed = bool(is_student) == required_student
            if not passed:
                critical_failures.append(
                    "applicant must be a student" if required_student else "students are excluded from this scheme"
                )
            self._check(
                checks,
                "Student status",
                "Student" if required_student else "Not a student",
                "Student" if is_student else "Not a student",
                passed,
                "Passed" if passed else "CRITICAL: student status mismatch",
            )

        if "is_disabled" in rules:
            required_disabled = bool(rules.get("is_disabled"))
            is_disabled = _profile_value(profile, "is_disabled", False)
            passed = bool(is_disabled) == required_disabled
            if not passed:
                critical_failures.append(
                    "applicant must have a disability" if required_disabled else "applicants with a disability are excluded"
                )
            self._check(
                checks,
                "Disability status",
                "Person with disability" if required_disabled else "Not disabled",
                "Person with disability" if is_disabled else "Not disabled",
                passed,
                "Passed" if passed else "CRITICAL: disability status mismatch",
            )

        # Land ownership
        if rules.get("owns_land_required"):
            owns_land = _profile_value(profile, "owns_land")
            if owns_land is None:
                unknowns.append("land ownership")
                self._check(
                    checks,
                    "Land ownership",
                    "Required",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: land ownership required",
                )
            else:
                if not owns_land:
                    critical_failures.append("scheme requires land ownership")
                self._check(
                    checks,
                    "Land ownership",
                    "Required",
                    "Yes" if owns_land else "No",
                    bool(owns_land),
                    "Passed" if owns_land else "CRITICAL: land ownership required",
                )

        # House ownership (rule value is the required state)
        if "owns_house" in rules:
            required_owns_house = bool(rules.get("owns_house"))
            owns_house = _profile_value(profile, "owns_house")
            if owns_house is None:
                unknowns.append("house ownership")
                self._check(
                    checks,
                    "House ownership",
                    "Owns a house" if required_owns_house else "Does not own a pucca house",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: house ownership required",
                )
            else:
                passed = bool(owns_house) == required_owns_house
                if not passed:
                    critical_failures.append(
                        "house ownership does not match the scheme requirement"
                    )
                self._check(
                    checks,
                    "House ownership",
                    "Owns a house" if required_owns_house else "Does not own a pucca house",
                    "Yes" if owns_house else "No",
                    passed,
                    "Passed" if passed else "CRITICAL: house ownership mismatch",
                )

        # Rural / urban residency
        if rules.get("is_rural") is True:
            is_rural = _profile_value(profile, "is_rural")
            if is_rural is None:
                unknowns.append("rural residence")
                self._check(
                    checks,
                    "Rural residence",
                    "Rural",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: rural residence required",
                )
            else:
                if not is_rural:
                    critical_failures.append("scheme is limited to rural residents")
                self._check(
                    checks,
                    "Rural residence",
                    "Rural",
                    "Rural" if is_rural else "Urban",
                    bool(is_rural),
                    "Passed" if is_rural else "CRITICAL: rural residence required",
                )

        if rules.get("is_urban") is True:
            is_rural = _profile_value(profile, "is_rural")
            if is_rural is None:
                unknowns.append("urban residence")
                self._check(
                    checks,
                    "Urban residence",
                    "Urban",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: urban residence required",
                )
            else:
                passed = not is_rural
                if not passed:
                    critical_failures.append("scheme is limited to urban residents")
                self._check(
                    checks,
                    "Urban residence",
                    "Urban",
                    "Urban" if not is_rural else "Rural",
                    passed,
                    "Passed" if passed else "CRITICAL: urban residence required",
                )

        # Ration card
        if rules.get("has_ration_card") is True:
            has_ration = _profile_value(profile, "has_ration_card")
            if has_ration is None:
                unknowns.append("ration card status")
                self._check(
                    checks,
                    "Ration card",
                    "Active ration card",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: ration card status required",
                )
            else:
                if not has_ration:
                    critical_failures.append("scheme requires an active ration card")
                self._check(
                    checks,
                    "Ration card",
                    "Active ration card",
                    "Yes" if has_ration else "No",
                    bool(has_ration),
                    "Passed" if has_ration else "CRITICAL: ration card required",
                )

        # Business plan
        if rules.get("requires_business_plan"):
            has_plan = _profile_value(profile, "has_business_plan")
            if has_plan is None:
                unknowns.append("business plan readiness")
                self._check(
                    checks,
                    "Business plan",
                    "A business plan/proposal",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: business plan status required",
                )
            elif not has_plan:
                warnings.append(
                    "a business plan/project report is required before the loan application"
                )
                self._check(
                    checks,
                    "Business plan",
                    "A business plan/proposal",
                    "Not ready",
                    False,
                    "ACTION REQUIRED: prepare a business plan",
                )
            else:
                self._check(
                    checks,
                    "Business plan",
                    "A business plan/proposal",
                    "Ready",
                    True,
                    "Passed",
                )

        # Family beneficiary cap
        max_family = rules.get("max_family_beneficiary_count")
        if max_family is not None:
            count = _profile_value(profile, "family_beneficiary_count")
            if count is None:
                unknowns.append("number of family members who already benefit")
                self._check(
                    checks,
                    "Family beneficiary limit",
                    f"<= {max_family} family member(s)",
                    "Not provided",
                    None,
                    "MISSING INFORMATION: family beneficiary count required",
                )
            else:
                passed = count <= max_family
                if not passed:
                    critical_failures.append(
                        f"{count} family members already benefit; the limit is {max_family}"
                    )
                self._check(
                    checks,
                    "Family beneficiary limit",
                    f"<= {max_family} family member(s)",
                    str(count),
                    passed,
                    "Passed" if passed else "CRITICAL: family beneficiary limit exceeded",
                )

        # Education
        min_education = rules.get("min_education_completed")
        if min_education:
            education = (_profile_value(profile, "educational_level", "") or "").strip().lower()
            if not education or education == "none":
                unknowns.append("education level")
                self._check(
                    checks,
                    "Minimum education",
                    min_education,
                    "Not provided",
                    None,
                    "MISSING INFORMATION: education level required",
                )
            else:
                current_rank = EDUCATION_ORDER.get(education)
                required_rank = EDUCATION_ORDER.get(str(min_education).lower())
                if current_rank is None or required_rank is None:
                    warnings.append(
                        f"education level '{education}' could not be compared automatically"
                    )
                    self._check(
                        checks,
                        "Minimum education",
                        str(min_education),
                        education,
                        None,
                        "MANUAL VERIFICATION: unrecognised education level",
                    )
                else:
                    passed = current_rank >= required_rank
                    if not passed:
                        critical_failures.append(
                            f"education level '{education}' is below the required '{min_education}'"
                        )
                    self._check(
                        checks,
                        "Minimum education",
                        str(min_education),
                        education,
                        passed,
                        "Passed" if passed else "CRITICAL: education requirement not met",
                    )

        # Exclusions
        if rules.get("excludes_government_employees"):
            is_gov = _profile_value(profile, "is_government_employee")
            if is_gov is True:
                critical_failures.append("government employees are excluded from this scheme")
                self._check(
                    checks,
                    "Government employee exclusion",
                    "Not a government employee",
                    "Government employee",
                    False,
                    "CRITICAL: excluded category",
                )
            elif is_gov is None:
                warnings.append(
                    "confirm that no family member is a government employee, because they are excluded"
                )
                self._check(
                    checks,
                    "Government employee exclusion",
                    "Not a government employee",
                    "Not confirmed",
                    None,
                    "VERIFY: exclusion applies",
                )
            else:
                self._check(
                    checks,
                    "Government employee exclusion",
                    "Not a government employee",
                    "Not a government employee",
                    True,
                    "Passed",
                )

        if rules.get("excludes_taxpayers"):
            if annual_income is None or annual_income <= 0:
                warnings.append("confirm that you are not an income-tax payer")
                self._check(
                    checks,
                    "Income-tax payer exclusion",
                    "Not an income-tax payer",
                    "Not confirmed",
                    None,
                    "VERIFY: exclusion applies",
                )
            elif annual_income > 250000:
                critical_failures.append("income-tax payers are excluded from this scheme")
                self._check(
                    checks,
                    "Income-tax payer exclusion",
                    "Not an income-tax payer",
                    f"Income ₹{annual_income:,.0f}",
                    False,
                    "CRITICAL: likely taxpayer",
                )
            else:
                self._check(
                    checks,
                    "Income-tax payer exclusion",
                    "Not an income-tax payer",
                    "Below taxpayer threshold",
                    True,
                    "Passed",
                )

        if rules.get("is_disabled_preferred") and not _profile_value(profile, "is_disabled", False):
            warnings.append(
                "persons with disabilities receive priority; non-disabled applicants may be considered later"
            )
            self._check(
                checks,
                "Disability priority",
                "Priority for persons with disabilities",
                "General category",
                True,
                "LOWER PRIORITY: not disqualifying",
            )

        if rules.get("is_household_rural_vulnerable"):
            is_rural = _profile_value(profile, "is_rural")
            if is_rural is None:
                warnings.append(
                    "rural/vulnerable household status needs confirmation against SECC/NFSA records"
                )
                self._check(
                    checks,
                    "Rural vulnerable household",
                    "SECC/NFSA verification",
                    "Not confirmed",
                    None,
                    "VERIFY: household status",
                )
            elif is_rural:
                self._check(
                    checks,
                    "Rural vulnerable household",
                    "SECC/NFSA verification",
                    "Rural",
                    True,
                    "Passed",
                )
            else:
                warnings.append(
                    "urban households may still qualify through SECC/NFSA; local verification is required"
                )
                self._check(
                    checks,
                    "Rural vulnerable household",
                    "SECC/NFSA verification",
                    "Urban",
                    None,
                    "VERIFY: local records",
                )

        if critical_failures:
            status = "Not Eligible"
        elif unknowns:
            status = "Insufficient Information"
        elif warnings:
            status = "Potentially Eligible"
        else:
            status = "Eligible"

        explanation_parts = []
        if critical_failures:
            explanation_parts.append("You do not currently meet these requirements:")
            explanation_parts.extend(f"- {reason}" for reason in critical_failures)
        elif unknowns:
            explanation_parts.append("More information is needed before a reliable decision:")
            explanation_parts.extend(f"- {item}" for item in unknowns)
        else:
            explanation_parts.append("All required rule checks passed.")
        if warnings:
            explanation_parts.append("Notes for verification:")
            explanation_parts.extend(f"- {warning}" for warning in warnings)
        explanation_parts.append(
            "This is a preliminary rule-based assessment, not an official government decision."
        )
        explanation = "\n".join(explanation_parts)

        decision_source = "deterministic_rules"
        if self.use_real_ai:
            try:
                safe_profile = redact_pii(json.dumps(_profile_snapshot(profile), default=str))
                system_instruction = (
                    "You are a careful Indian government-benefits caseworker. "
                    "Explain the supplied deterministic decision in plain language. "
                    "Do not change the status, invent eligibility, or promise approval. "
                    "Use short bullet points and mention what the citizen should verify."
                )
                prompt = (
                    f"Citizen profile (PII redacted): {safe_profile}\n"
                    f"Scheme: {scheme.title}\n"
                    f"Deterministic status: {status}\n"
                    f"Rule checks: {json.dumps(checks, default=str)}\n"
                    f"Draft explanation: {explanation}"
                )
                ai_explanation = self.run_llm(prompt, system_instruction).strip()
                if ai_explanation:
                    explanation = ai_explanation
                    decision_source = "deterministic_rules+gemma_explanation"
            except Exception:
                pass

        return {
            "status": status,
            "score": STATUS_SCORES[status],
            "explanation": explanation,
            "checks": checks,
            "missing_information": unknowns,
            "warnings": warnings,
            "decision_source": decision_source,
        }
