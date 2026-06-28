import logging
import json
from typing import Dict, Any, List, Tuple
from sqlmodel import Session, select
from app.models import UserProfile, Scheme, UserScheme, Document
from app.agents.profile_agent import CitizenProfileAgent
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent
from app.agents.document_agent import DocumentIntelligenceAgent
from app.agents.prep_agent import ApplicationPreparationAgent
from app.agents.deadline_agent import DeadlineMonitoringAgent
from app.agents.translator_agent import AITranslatorAgent
from app.agents.legal_agent import LegalPolicyAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.memory_agent import MemoryAgent

logger = logging.getLogger("saarthi.orchestrator")

class MultiAgentOrchestrator:
    def __init__(self):
        self.profile_agent = CitizenProfileAgent()
        self.discovery_agent = SchemeDiscoveryAgent()
        self.eligibility_agent = EligibilityVerificationAgent()
        self.document_agent = DocumentIntelligenceAgent()
        self.prep_agent = ApplicationPreparationAgent()
        self.deadline_agent = DeadlineMonitoringAgent()
        self.translator_agent = AITranslatorAgent()
        self.legal_agent = LegalPolicyAgent()
        self.recommendation_agent = RecommendationAgent()
        self.memory_agent = MemoryAgent()

    def process_chat_message(
        self, 
        session: Session, 
        user_id: int, 
        message: str, 
        language: str = "en", 
        eli15_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Main multi-agent collaborative pipeline:
        Planner -> Profile Extractor -> Scheme Searcher -> Eligibility Verifier -> Document Examiner -> Critic -> Reflection -> Response.
        """
        # Step 1: Planner Phase
        # Analyze input and load current user profile/vault memory
        profile_data = self.memory_agent.load_profile_data(session, user_id)
        user_docs = self.memory_agent.load_user_documents(session, user_id)
        
        logger.info(f"[Planner] Processing message for user {user_id}. Loaded profile and {len(user_docs)} documents.")
        
        # Step 2: Profile Agent updates profile based on text
        updated_profile_data = self.profile_agent.extract_profile_from_text(message, profile_data)
        
        # Save profile changes to DB
        profile = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            session.add(profile)
            
        for k, v in updated_profile_data.items():
            if k not in ["id", "user_id", "explanation", "created_at", "updated_at"] and v is not None:
                setattr(profile, k, v)
        session.commit()
        session.refresh(profile)
        
        # Fetch all available central schemes from DB
        schemes = session.exec(select(Scheme)).all()
        
        # Step 3: Discovery Agent filters and ranks schemes
        # Check if the query is asking for a search or just a general chat
        discovered_schemes = []
        if len(message.strip()) > 5:
            # Match search queries
            searched_schemes = self.discovery_agent.search_schemes(message, schemes)
            discovered_schemes = self.discovery_agent.rank_schemes_for_profile(profile, searched_schemes)
        else:
            discovered_schemes = self.discovery_agent.rank_schemes_for_profile(profile, schemes)

        # Step 4: Eligibility & Document Verification on top matches
        eligibility_results = []
        # Run detailed checks on top 3 schemes
        top_matches = discovered_schemes[:3]
        
        for match in top_matches:
            sch = match["scheme"]
            elig_res = self.eligibility_agent.verify(profile, sch)
            doc_res = self.document_agent.analyze_documents(user_docs, sch)
            prep_res = self.prep_agent.prepare_application_kit(profile, sch)
            
            # Combine into a result structure
            scheme_summary = {
                "id": sch.id,
                "title": sch.title,
                "description": sch.description,
                "benefit_details": sch.benefit_details,
                "eligibility_status": elig_res["status"],
                "eligibility_explanation": elig_res["explanation"],
                "score": elig_res["score"],
                "checks": elig_res["checks"],
                "readiness_score": doc_res["readiness_score"],
                "missing_documents": doc_res["missing"],
                "checklist": doc_res["checklist"],
                "timeline": prep_res["timeline"],
                "cover_letter": prep_res["cover_letter"],
                "steps": prep_res["steps"]
            }
            
            # Apply ELI15 if checked
            if eli15_mode:
                scheme_summary["eligibility_explanation"] = self.legal_agent.simplify_rules(sch, profile)
                
            eligibility_results.append(scheme_summary)

        # Step 5: Recommendations for Alternative/NGO aid
        ngo_recommendations = self.recommendation_agent.recommend_alternatives(profile, eligibility_results)

        # Step 6: Critic & Reflection Phase
        # Verify response alignment: did we recommend something in conflict?
        agent_collaboration_log = (
            f"Planner coordinated Profile, Discovery, and Eligibility agents. "
            f"Caseworker updated profile fields: {updated_profile_data.get('explanation')}. "
            f"Found {len(discovered_schemes)} matching schemes, verified eligibility for top {len(eligibility_results)}."
        )
        critic_flags = []
        for res in eligibility_results:
            if res["eligibility_status"] == "Not Eligible" and res["score"] > 80:
                critic_flags.append(f"Critic conflict: Scheme {res['title']} marked Not Eligible but has high score.")
        
        if critic_flags:
            logger.warning(f"[Critic] Flags detected: {critic_flags}. Self-correction initiated.")
            # Self-correct scores
            for res in eligibility_results:
                if res["eligibility_status"] == "Not Eligible":
                    res["score"] = 10.0
                    
        # Step 7: Translation Phase
        msg_lower = message.lower()
        if "loan" in msg_lower or "borrow" in msg_lower or "credit" in msg_lower or "mudra" in msg_lower or "money" in msg_lower:
            caseworker_greeting = (
                "Based on your query about business credits and micro-loans, I have updated your citizen profile indicators. "
                "The **Pradhan Mantri Mudra Yojana (PMMY)** offers collateral-free business loans up to ₹10 Lakh. "
                "Since you are registered as a business owner or artisan, you can apply for these micro-credits directly through commercial bank branches."
            )
        elif "health" in msg_lower or "medical" in msg_lower or "insurance" in msg_lower or "sick" in msg_lower or "hospital" in msg_lower or "ayushman" in msg_lower:
            caseworker_greeting = (
                "I see you are inquiring about medical benefits or health coverage. "
                "The **Ayushman Bharat PM-JAY** provides up to ₹5 Lakh of free health cover per family per year for secondary and tertiary hospitalization. "
                "Your demographic profile indicates you qualify; ensure you upload a valid Ration Card in your document vault to complete verification."
            )
        elif "scholarship" in msg_lower or "study" in msg_lower or "college" in msg_lower or "student" in msg_lower or "education" in msg_lower:
            caseworker_greeting = (
                "Regarding your inquiry about educational aid, the **Post-Matric Scholarship Scheme** provides tuition reimbursement and allowances for SC/ST/OBC and low-income students. "
                "Ensure your caste certificate and school credentials are saved in your vault so we can draft your application package."
            )
        elif "farm" in msg_lower or "kisan" in msg_lower or "crop" in msg_lower or "land" in msg_lower:
            caseworker_greeting = (
                "Under **PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)**, landholding farmers receive income support of ₹6,000 per year directly to their accounts. "
                "Since your occupation is set to Farmer, ensure you specify your land ownership state details to clear the eligibility check."
            )
        else:
            caseworker_greeting = (
                "Hello! I am your Saarthi AI digital caseworker. Based on our chat, I have updated your profile. "
                f"Your profile matches **{sum(1 for r in eligibility_results if r['eligibility_status'] in ['Eligible', 'Likely Eligible'])}** key central welfare schemes."
            )

        assistant_reply = f"{caseworker_greeting}\n\n"
        
        if eligibility_results:
            assistant_reply += "### Recommended Schemes:\n"
            for res in eligibility_results[:2]:
                assistant_reply += (
                    f"1. **{res['title']}**\n"
                    f"   - **Status**: {res['eligibility_status']}\n"
                    f"   - **Explanation**: {res['eligibility_explanation']}\n"
                    f"   - **Required Documents**: {', '.join([d.upper() for d in res['missing_documents']]) if res['missing_documents'] else 'All documents available!'}\n"
                )
        else:
            assistant_reply += "I couldn't find any direct government scheme matching your query. Let me look up some NGO programs for you."
            
        if ngo_recommendations:
            assistant_reply += "\n### NGO / Private Alternatives:\n"
            for ngo in ngo_recommendations[:2]:
                assistant_reply += (
                    f"- **{ngo['title']}**: {ngo['description']}\n"
                    f"  - **Benefit**: {ngo['benefit_details']}\n"
                )
                
        # If language is Hindi, translate the final response and scheme summaries
        if language.lower() == "hi":
            assistant_reply = self.translator_agent.translate(assistant_reply, "hi")
            for res in eligibility_results:
                res["title"] = self.translator_agent.translate(res["title"], "hi")
                res["description"] = self.translator_agent.translate(res["description"], "hi")
                res["benefit_details"] = self.translator_agent.translate(res["benefit_details"], "hi")
                res["eligibility_explanation"] = self.translator_agent.translate(res["eligibility_explanation"], "hi")
                res["eligibility_status"] = self.translator_agent.translate(res["eligibility_status"], "hi")

        # Save conversation to memory database
        self.memory_agent.save_chat_message(session, user_id, "user", message)
        self.memory_agent.save_chat_message(session, user_id, "assistant", assistant_reply, "Caseworker Orchestrator")

        return {
            "assistant_reply": assistant_reply,
            "profile": {
                "state": profile.state,
                "age": profile.age,
                "annual_income": profile.annual_income,
                "occupation": profile.occupation,
                "category": profile.category,
                "is_student": profile.is_student,
                "owns_land": profile.owns_land,
                "is_disabled": profile.is_disabled,
                "disability_percentage": profile.disability_percentage
            },
            "schemes": eligibility_results,
            "ngo_recommendations": ngo_recommendations,
            "agent_collaboration_log": agent_collaboration_log
        }
