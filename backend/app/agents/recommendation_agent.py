from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.models import UserProfile, Scheme

class RecommendationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Recommendation Agent",
            description="Recommends alternative schemes, private NGO scholarships, and microfinance solutions."
        )
        
        # High-fidelity database of private alternative programs, NGO aids, and microfinance
        self.ngo_programs = [
            {
                "title": "Buddy4Study Foundation Scholarships",
                "description": "A private scholarship aggregator matching corporate CSR funds to low-income students.",
                "benefit_type": "Scholarship",
                "benefit_details": "₹10,000 to ₹50,000 per year for school and college tuition fees.",
                "eligibility": "Students with family income < ₹3.6 Lakh, minimum 50% marks in last exam.",
                "url": "https://www.buddy4study.com/"
            },
            {
                "title": "Tata Trusts Individual Grants for Education",
                "description": "Financial assistance for students pursuing higher studies in India.",
                "benefit_type": "Scholarship",
                "benefit_details": "Partial or full tuition fee reimbursement.",
                "eligibility": "SC/ST/OBC and general low-income students pursuing undergraduate or postgraduate studies.",
                "url": "https://www.tatatrusts.org/"
            },
            {
                "title": "Rang De Micro-loans for Rural Livelihoods",
                "description": "A peer-to-peer micro-lending platform providing low-interest credit to artisans, farmers, and women.",
                "benefit_type": "Loan",
                "benefit_details": "Collateral-free working capital loans of ₹5,000 to ₹25,000 at 4-8% flat interest.",
                "eligibility": "Rural women, street vendors, small farmers, and traditional artisans.",
                "url": "https://www.rangde.in/"
            },
            {
                "title": "Nirmaan Organization Skill Development Program",
                "description": "Vocational skill training and job placement services for unemployed youth.",
                "benefit_type": "Skill Development",
                "benefit_details": "Free training in IT, retail management, logistics, or sewing, plus job placement.",
                "eligibility": "Unemployed youth aged 18-30, minimum 8th class pass.",
                "url": "https://nirmaan.org/"
            }
        ]

    def recommend_alternatives(self, profile: UserProfile, matching_government_schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Produce alternative suggestions if government schemes are limited or not applicable.
        """
        recommendations = []
        
        # Analyze profile
        is_student = profile.is_student or profile.occupation == "Student"
        is_farmer = profile.occupation == "Farmer"
        is_woman = profile.gender.lower() == "female"
        is_unemployed = profile.occupation in ["Unemployed", "Student"]
        is_low_income = profile.annual_income < 300000.0

        # Filter NGO programs
        for program in self.ngo_programs:
            reason = "Recommended for you"
            match = False
            
            if is_student and program["benefit_type"] == "Scholarship":
                match = True
                reason = "Based on your student status, this NGO program can help support your tuition fees."
            elif (is_farmer or profile.occupation == "Street Vendor" or profile.occupation == "Artisan") and program["title"].startswith("Rang De"):
                match = True
                reason = "As a micro-entrepreneur / worker, you can access low-interest collateral-free loans here."
            elif is_unemployed and program["benefit_type"] == "Skill Development":
                match = True
                reason = "This program offers free vocational training and job placement to boost your career options."
            elif is_low_income and program["benefit_type"] == "Scholarship" and profile.annual_income < 250000:
                match = True
                reason = "Matches your household income bracket for financial aid."

            if match:
                rec_item = program.copy()
                rec_item["recommendation_reason"] = reason
                recommendations.append(rec_item)

        return recommendations
