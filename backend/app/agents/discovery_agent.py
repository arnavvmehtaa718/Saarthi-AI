import re
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent
from app.models import Scheme, UserProfile

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "want",
    "need",
    "help",
    "please",
    "with",
    "scheme",
    "schemes",
    "government",
    "govt",
}

SYNONYMS = {
    "loan": ["loan", "credit", "mudra", "svanidhi", "finance", "business"],
    "health": ["health", "hospital", "medical", "insurance", "ayushman", "illness"],
    "scholarship": ["scholarship", "education", "college", "student", "study", "tuition"],
    "farmer": ["farmer", "kisan", "agriculture", "crop", "land"],
    "food": ["food", "ration", "grain", "hunger", "pds"],
    "housing": ["house", "housing", "awas", "home", "rural"],
    "business": ["business", "entrepreneur", "shop", "artisan", "vendor", "mudra"],
    "disability": ["disability", "disabled", "handicap", "udid"],
}

STATUS_ORDER = {
    "Eligible": 0,
    "Potentially Eligible": 1,
    "Insufficient Information": 2,
    "Not Eligible": 3,
}


class SchemeDiscoveryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Scheme Discovery Agent",
            description="Searches and ranks schemes using the shared deterministic eligibility engine.",
        )
        self.eligibility_agent = EligibilityVerificationAgent()

    def _tokens(self, text: str) -> set[str]:
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        tokens = {word for word in words if word not in STOPWORDS and len(word) > 1}
        for token in list(tokens):
            tokens.update(SYNONYMS.get(token, []))
        return tokens

    def search_schemes(self, query: str, schemes: List[Scheme]) -> List[Scheme]:
        """Keyword search with a small benefit-domain synonym map."""
        if not query or not query.strip():
            return schemes

        query_lower = query.lower().strip()
        query_tokens = self._tokens(query)
        matched: list[tuple[Scheme, int]] = []

        for scheme in schemes:
            title = scheme.title.lower()
            description = scheme.description.lower()
            benefit = (scheme.benefit_details or "").lower()
            tags = " ".join(scheme.tags or []).lower()
            haystack = f"{title} {description} {benefit} {tags}"
            haystack_tokens = self._tokens(haystack)

            score = 0
            if query_lower in title:
                score += 60
            if query_lower in description:
                score += 20
            score += 8 * len(query_tokens & haystack_tokens)
            for token in query_tokens:
                if token in tags:
                    score += 10
                if token in title:
                    score += 6

            if score > 0:
                matched.append((scheme, score))

        matched.sort(key=lambda item: item[1], reverse=True)
        return [scheme for scheme, _ in matched]

    def rank_schemes_for_profile(
        self, profile: UserProfile, schemes: List[Scheme]
    ) -> List[Dict[str, Any]]:
        """Rank schemes by deterministic eligibility, never by additive guessing."""
        ranked: List[Dict[str, Any]] = []
        for scheme in schemes:
            result = self.eligibility_agent.verify(profile, scheme)
            ranked.append(
                {
                    "scheme": scheme,
                    "eligibility_score": result["score"],
                    "eligibility_status": result["status"],
                    "eligibility_explanation": result["explanation"],
                    "checks": result["checks"],
                    "missing_information": result["missing_information"],
                    "warnings": result["warnings"],
                    "decision_source": result["decision_source"],
                    "required_documents": scheme.required_documents,
                }
            )

        ranked.sort(
            key=lambda item: (
                STATUS_ORDER.get(item["eligibility_status"], 4),
                -item["eligibility_score"],
                item["scheme"].title.lower(),
            )
        )
        return ranked
