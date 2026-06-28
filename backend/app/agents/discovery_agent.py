from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models import Scheme, UserProfile

class SchemeDiscoveryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Scheme Discovery Agent",
            description="Searches, ranks, and matches relevant government schemes based on the citizen's profile."
        )

    def search_schemes(self, query: str, schemes: List[Scheme]) -> List[Scheme]:
        """Perform semantic and natural language keywords filtering over schemes list."""
        if not query:
            return schemes
            
        query_lower = query.lower()
        matched = []
        for scheme in schemes:
            score = 0
            title_lower = scheme.title.lower()
            desc_lower = scheme.description.lower()
            tags_lower = [t.lower() for t in scheme.tags]
            
            # Simple keyword matching scoring
            if query_lower in title_lower:
                score += 50
            if query_lower in desc_lower:
                score += 20
            for tag in tags_lower:
                if query_lower in tag or tag in query_lower:
                    score += 15
            
            # Sub-word matches
            query_words = query_lower.split()
            for qw in query_words:
                if qw in title_lower:
                    score += 10
                if qw in desc_lower:
                    score += 3
                    
            if score > 0:
                matched.append((scheme, score))
                
        # Sort matched schemes by search score descending
        matched.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in matched]


    def rank_schemes_for_profile(self, profile: UserProfile, schemes: List[Scheme]) -> List[Dict[str, Any]]:
        """
        Rank schemes based on citizen profile. Calculates:
        - Eligibility score (based on criteria matching)
        - Sorts by: eligibility_score (desc), benefits, complexity, deadline.
        """
        ranked = []
        for scheme in schemes:
            rules = scheme.eligibility_rules
            # Score calculations
            score = 100.0
            reasons = []
            status = "Eligible"
            missing_docs = []

            # 0. HARD BLOCK: Minors (under 18) are ineligible for all government welfare schemes
            if profile.age < 18:
                score = 0.0
                status = "Not Eligible"
                reasons.append(
                    f"Applicant must be at least 18 years of age to apply for government welfare schemes. "
                    f"Current age ({profile.age}) does not meet the minimum adult eligibility threshold. "
                    f"A parent or legal guardian may apply on behalf of the minor where applicable."
                )
                # Skip all further checks — minors cannot apply
                ranked.append({
                    "scheme": scheme,
                    "eligibility_score": 0.0,
                    "eligibility_status": "Not Eligible",
                    "eligibility_explanation": " ".join(reasons),
                    "required_documents": scheme.required_documents
                })
                continue
            
            # 1. State check
            if scheme.state != "Central" and profile.state != "All" and scheme.state.lower() != profile.state.lower():
                score -= 60
                status = "Not Eligible"
                reasons.append(f"Scheme is for residents of {scheme.state}, but you reside in {profile.state}.")
            
            # 2. Income Check
            max_income = rules.get("max_annual_income")
            if max_income is not None:
                if profile.annual_income > max_income:
                    diff = profile.annual_income - max_income
                    score -= 50
                    status = "Not Eligible"
                    reasons.append(f"Annual income ₹{profile.annual_income:,.2f} exceeds the scheme limit of ₹{max_income:,.2f} by ₹{diff:,.2f}.")
                elif profile.annual_income > (max_income * 0.8):
                    # Close to the limit
                    score -= 10
                    status = "Likely Eligible"
                    reasons.append(f"Income is close to the scheme limit of ₹{max_income:,.2f}.")
            
            # 3. Age Checks (scheme-specific min/max beyond the 18+ hard floor)
            min_age = rules.get("min_age")
            max_age = rules.get("max_age")
            if min_age is not None and profile.age < min_age:
                score -= 40
                status = "Not Eligible"
                reasons.append(f"Age {profile.age} is below minimum requirement of {min_age} years.")
            if max_age is not None and profile.age > max_age:
                score -= 40
                status = "Not Eligible"
                reasons.append(f"Age {profile.age} is above maximum limit of {max_age} years.")

            # 4. Occupation whitelist
            occ_list = rules.get("occupation_whitelist")
            if occ_list:
                if profile.occupation not in occ_list:
                    score -= 40
                    status = "Not Eligible"
                    reasons.append(f"Scheme requires occupation to be one of {occ_list}, but your occupation is '{profile.occupation}'.")
                else:
                    score += 5 # preferred match

            # 5. Category whitelist
            cat_list = rules.get("category_whitelist")
            if cat_list and profile.category not in cat_list:
                score -= 40
                status = "Not Eligible"
                reasons.append(f"Scheme requires social category {cat_list}, but your category is {profile.category}.")

            # 6. Land ownership check
            land_req = rules.get("owns_land_required")
            if land_req and not profile.owns_land:
                score -= 30
                status = "Not Eligible"
                reasons.append("Scheme requires land ownership, but you do not own land.")

            # 7. Exclusions
            if rules.get("excludes_government_employees") and profile.occupation == "Salaried":
                score -= 20
                status = "Likely Eligible"
                reasons.append("Verify you are not a government employee (government servants are excluded).")
                
            if rules.get("excludes_taxpayers") and profile.annual_income > 250000:
                score -= 20
                status = "Likely Eligible"
                reasons.append("Income Taxpayers are excluded from this scheme.")

            # 8. STATE-BASED CUSTOM RULES
            # Apply additional state-specific policy conditions that modify eligibility
            state_lower = profile.state.lower() if profile.state else ""

            # Bihar: Stricter BPL income threshold for welfare schemes
            if state_lower == "bihar":
                if profile.annual_income > 120000 and max_income and max_income >= 200000:
                    score -= 5
                    reasons.append("Bihar state advisory: BPL threshold in Bihar is lower (₹1,20,000). Your income is above the state BPL line but within the central scheme limit.")
                # Bihar gives priority to SC/ST applicants
                if profile.category in ["SC", "ST"]:
                    score += 8
                    reasons.append("Bihar state policy grants priority processing for SC/ST category applicants.")

            # Uttar Pradesh: Marginal farmer land area rule
            elif state_lower == "uttar pradesh":
                if profile.owns_land and profile.land_area_hectares > 2.0:
                    # UP classifies >2 hectares as non-marginal farmer
                    if occ_list and "Farmer" in occ_list:
                        score -= 10
                        reasons.append("UP state rule: Farmers with landholding >2 hectares are classified as non-marginal and face additional verification under state policy.")
                # UP gives additional weightage for EWS
                if profile.category == "EWS":
                    score += 5
                    reasons.append("UP state policy provides preferential access for Economically Weaker Section (EWS) applicants.")

            # Rajasthan: Senior citizen bonus and women artisan support
            elif state_lower == "rajasthan":
                if profile.age >= 60:
                    score += 10
                    reasons.append("Rajasthan state policy: Senior citizens (60+) receive priority processing and additional state-level benefits.")
                if profile.occupation == "Artisan":
                    score += 7
                    reasons.append("Rajasthan state initiative: Artisans and traditional craftspeople qualify for state-supplemented skill and credit programs.")

            # Maharashtra: Urban vendor and business owner focus
            elif state_lower == "maharashtra":
                if profile.occupation in ["Street Vendor", "Business Owner"]:
                    score += 6
                    reasons.append("Maharashtra state policy: Urban micro-entrepreneurs and street vendors receive accelerated processing under DISHA state initiative.")
                if profile.annual_income > 300000:
                    score -= 5
                    reasons.append("Maharashtra advisory: Income above ₹3,00,000 may require additional state income verification beyond central requirements.")

            # Delhi: Urban-focused, no land-based schemes apply
            elif state_lower == "delhi":
                if profile.owns_land and profile.land_area_hectares > 0:
                    score -= 5
                    reasons.append("Delhi advisory: Agricultural land records in NCT Delhi undergo additional urban-land-use verification.")
                if profile.occupation == "Student":
                    score += 5
                    reasons.append("Delhi state policy: Student applicants in NCT receive priority under Delhi government's education supplement programs.")

            # Madhya Pradesh: Tribal welfare and farmer focus
            elif state_lower == "madhya pradesh":
                if profile.category == "ST":
                    score += 10
                    reasons.append("MP state policy: Scheduled Tribe applicants receive top priority under state tribal welfare integration programs.")
                if profile.occupation == "Farmer" and profile.owns_land:
                    score += 5
                    reasons.append("MP state initiative: Landholding farmers qualify for additional state crop insurance and input subsidy convergence.")

            # Gujarat: MSME and business-friendly
            elif state_lower == "gujarat":
                if profile.occupation in ["Business Owner", "Artisan"]:
                    score += 7
                    reasons.append("Gujarat state policy: MSME and artisan entrepreneurs receive enhanced credit guarantee support under state industrial policy.")
                if profile.is_disabled:
                    score += 5
                    reasons.append("Gujarat state welfare: Persons with disabilities receive supplementary state benefits on top of central scheme entitlements.")

            # Karnataka: IT/education hub bonus
            elif state_lower == "karnataka":
                if profile.is_student or profile.occupation == "Student":
                    score += 8
                    reasons.append("Karnataka state policy: Students receive enhanced scholarship support through state-central convergence programs.")
                if profile.category in ["SC", "ST", "OBC"]:
                    score += 5
                    reasons.append("Karnataka state directive: Reserved category applicants receive priority under state backward classes welfare department.")

            # Adjust status based on score
            if score < 40:
                status = "Not Eligible"
            elif score < 75:
                status = "Likely Eligible"
            else:
                status = "Eligible"
                
            if not reasons:
                reasons.append("Matches all basic demographic criteria.")

            # Prepare document matching check
            ranked.append({
                "scheme": scheme,
                "eligibility_score": max(0.0, min(100.0, score)),
                "eligibility_status": status,
                "eligibility_explanation": " ".join(reasons),
                "required_documents": scheme.required_documents
            })

        # Sort ranked results: Eligible/Likely first, then by score desc
        # Exclude completely ineligible schemes or place them at the end
        ranked.sort(key=lambda x: (
            0 if x["eligibility_status"] == "Eligible" else 
            1 if x["eligibility_status"] == "Likely Eligible" else 
            2 if x["eligibility_status"] == "Missing Information" else 3,
            -x["eligibility_score"]
        ))
        
        return ranked
