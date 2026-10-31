import logging
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.agents.base import get_ai_client
from app.agents.deadline_agent import DeadlineMonitoringAgent
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.document_agent import DocumentIntelligenceAgent
from app.agents.legal_agent import LegalPolicyAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.prep_agent import ApplicationPreparationAgent
from app.agents.profile_agent import CitizenProfileAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.translator_agent import AITranslatorAgent
from app.models import Scheme, UserProfile

logger = logging.getLogger("saarthi.orchestrator")


class MultiAgentOrchestrator:
    def __init__(self):
        self.profile_agent = CitizenProfileAgent()
        self.discovery_agent = SchemeDiscoveryAgent()
        self.document_agent = DocumentIntelligenceAgent()
        self.prep_agent = ApplicationPreparationAgent()
        self.deadline_agent = DeadlineMonitoringAgent()
        self.translator_agent = AITranslatorAgent()
        self.legal_agent = LegalPolicyAgent()
        self.recommendation_agent = RecommendationAgent()
        self.memory_agent = MemoryAgent()

    def _profile_payload(self, profile: UserProfile) -> Dict[str, Any]:
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
            "disability_type",
            "has_ration_card",
            "is_rural",
            "owns_house",
            "family_beneficiary_count",
            "has_business_plan",
            "is_government_employee",
        ]
        return {field: getattr(profile, field, None) for field in fields}

    def process_chat_message(
        self,
        session: Session,
        user_id: int,
        message: str,
        language: str = "en",
        eli15_mode: bool = False,
    ) -> Dict[str, Any]:
        agents = (
            self.profile_agent,
            self.discovery_agent,
            self.document_agent,
            self.prep_agent,
            self.deadline_agent,
            self.translator_agent,
            self.legal_agent,
            self.recommendation_agent,
            self.memory_agent,
        )
        for agent in agents:
            agent.last_fallback = None

        profile = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            session.add(profile)
            session.commit()
            session.refresh(profile)

        profile_data = self.memory_agent.load_profile_data(session, user_id)
        user_docs = self.memory_agent.load_user_documents(session, user_id)
        chat_context = self.memory_agent.load_chat_context(session, user_id, limit=8)

        updated_profile_data = self.profile_agent.extract_profile_from_text(
            message, profile_data, chat_context
        )
        for key, value in updated_profile_data.items():
            if key in {"id", "user_id", "created_at", "updated_at", "explanation"}:
                continue
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        schemes = session.exec(select(Scheme)).all()
        searched_schemes = self.discovery_agent.search_schemes(message, schemes)
        candidate_schemes = searched_schemes or schemes
        ranked = self.discovery_agent.rank_schemes_for_profile(profile, candidate_schemes)
        top_matches = ranked[:3]

        eligibility_results: List[Dict[str, Any]] = []
        for match in top_matches:
            scheme = match["scheme"]
            document_result = self.document_agent.analyze_documents(user_docs, scheme)
            prep = self.prep_agent.prepare_application_kit(profile, scheme, document_result)

            summary = {
                "id": scheme.id,
                "title": scheme.title,
                "description": scheme.description,
                "benefit_type": scheme.benefit_type,
                "benefit_details": scheme.benefit_details,
                "department": scheme.department,
                "eligibility_status": match["eligibility_status"],
                "eligibility_score": match["eligibility_score"],
                "eligibility_explanation": match["eligibility_explanation"],
                "eligibility_checks": match.get("checks", []),
                "missing_information": match.get("missing_information", []),
                "warnings": match.get("warnings", []),
                "decision_source": match.get("decision_source", "deterministic_rules"),
                "readiness_score": document_result["readiness_score"],
                "required_documents": scheme.required_documents,
                "missing_documents": document_result["missing"],
                "checklist": document_result["checklist"],
                "timeline": prep["timeline"],
                "cover_letter": prep["cover_letter"],
                "steps": prep["steps"],
                "complexity": scheme.complexity,
                "application_url": scheme.application_url,
                "source_url": scheme.source_url or scheme.application_url,
                "source_note": scheme.source_note,
                "state": scheme.state,
                "tags": scheme.tags,
                "deadlines": scheme.deadlines,
                "eli15_explanation": scheme.eli15_explanation,
            }
            if eli15_mode:
                summary["eligibility_explanation"] = scheme.eli15_explanation
            eligibility_results.append(summary)

        ngo_recommendations = self.recommendation_agent.recommend_alternatives(
            profile, eligibility_results
        )

        status_counts = {
            status: sum(1 for item in top_matches if item["eligibility_status"] == status)
            for status in [
                "Eligible",
                "Potentially Eligible",
                "Insufficient Information",
                "Not Eligible",
            ]
        }
        profile_note = updated_profile_data.get("explanation", "")
        if profile_note.startswith("No new profile fields"):
            intro = "I reviewed your profile and checked the schemes that best match this conversation."
        else:
            intro = f"I updated your profile: {profile_note}"

        reply_parts = [intro, ""]
        if eligibility_results:
            reply_parts.append(
                f"I found **{status_counts['Eligible']} eligible**, "
                f"**{status_counts['Potentially Eligible']} potentially eligible**, "
                f"**{status_counts['Insufficient Information']} needing information**, and "
                f"**{status_counts['Not Eligible']} not eligible** schemes in this result."
            )
            reply_parts.append("")
            reply_parts.append("### Schemes checked for you")
            for item in eligibility_results:
                reply_parts.append(f"**{item['title']}** — {item['eligibility_status']}")
                reply_parts.append(item["eligibility_explanation"])
                if item["missing_documents"]:
                    labels = ", ".join(doc.replace("_", " ").upper() for doc in item["missing_documents"])
                    reply_parts.append(f"Documents still needed: {labels}.")
                else:
                    reply_parts.append("All documents required by this scheme are currently in your vault.")
                reply_parts.append("")
            reply_parts.append(
                "Open a scheme in the explorer to see the full checklist, source link, and draft cover letter."
            )
        else:
            reply_parts.append(
                "I could not match a scheme to that message. Try describing your occupation, income, state, or the benefit you need."
            )

        if ngo_recommendations:
            reply_parts.append("")
            reply_parts.append("### Non-government alternatives")
            for ngo in ngo_recommendations[:2]:
                reply_parts.append(
                    f"- **{ngo['title']}**: {ngo['description']} ({ngo['url']})"
                )

        reply_parts.append("")
        fallback_notes = [
            agent.last_fallback for agent in agents if agent.last_fallback
        ]
        if fallback_notes:
            reply_parts.append(
                "Live AI was unavailable for part of this response, so those steps "
                "used labelled deterministic rules or templates instead."
            )
            reply_parts.append("")
        reply_parts.append(
            "This is a preliminary assessment based on the information you provided. "
            "The concerned department makes the final eligibility decision."
        )
        assistant_reply = "\n".join(reply_parts)

        translation_note = None
        if language.lower() == "hi":
            assistant_reply = self.translator_agent.translate(assistant_reply, "hi")
            for item in eligibility_results:
                for field in ("title", "description", "benefit_details", "eligibility_explanation", "eligibility_status"):
                    item[field] = self.translator_agent.translate(item[field], "hi")
            if not self.translator_agent.use_real_ai or self.translator_agent.last_fallback:
                translation_note = (
                    "Offline Hindi glossary is active. Some longer text may remain in English."
                )

        fallback_notes = [
            agent.last_fallback for agent in agents if agent.last_fallback
        ]

        self.memory_agent.save_chat_message(session, user_id, "user", message)
        self.memory_agent.save_chat_message(
            session, user_id, "assistant", assistant_reply, "Caseworker Orchestrator"
        )

        return {
            "assistant_reply": assistant_reply,
            "profile": self._profile_payload(profile),
            "schemes": eligibility_results,
            "ngo_recommendations": ngo_recommendations,
            "status_counts": status_counts,
            "translation_note": translation_note,
            "ai_fallback_notes": fallback_notes,
            "agent_collaboration_log": (
                "Profile extraction, deterministic eligibility checks, document readiness, "
                "application preparation, and recommendation steps completed."
            ),
            "ai": get_ai_client().status(),
        }
