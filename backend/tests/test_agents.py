import pytest
from sqlmodel import SQLModel, create_engine, Session
from app.models import UserProfile, Scheme
from app.agents.profile_agent import CitizenProfileAgent
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent
from app.agents.document_agent import DocumentIntelligenceAgent
from app.models import Document
from app.services.ocr import classify_and_extract_local
from app.services.privacy import mask_aadhaar, mask_pan, redact_pii

# Setup inline SQLite memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="db_session")
def db_session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

def test_profile_agent_extraction():
    agent = CitizenProfileAgent()
    
    # Test message from farmer
    profile = {
        "state": "All",
        "age": 18,
        "annual_income": 0.0,
        "occupation": "Unemployed",
        "category": "General",
        "is_student": False,
        "owns_land": False,
        "is_disabled": False
    }
    
    message = "I am a kisan from Uttar Pradesh, earning 1.5 Lakh per year."
    updated = agent.extract_profile_from_text(message, profile)
    
    assert updated["occupation"] == "Farmer"
    assert updated["state"] == "Uttar Pradesh"
    assert updated["annual_income"] == 150000.0
    assert updated["owns_land"] is True

def test_eligibility_agent_rules():
    elig_agent = EligibilityVerificationAgent()
    
    # Scheme details
    scheme = Scheme(
        title="Test Scheme",
        description="Scheme for young students",
        department="Education",
        ministry="HRD",
        benefit_type="Scholarship",
        benefit_details="Reimbursement of college fee",
        eligibility_rules={
            "min_age": 15,
            "max_age": 25,
            "is_student": True,
            "max_annual_income": 200000.0,
            "category_whitelist": ["OBC", "SC", "ST"]
        },
        required_documents=["aadhaar", "income"],
        eli15_explanation="Free tuition fees for minority students."
    )
    
    # 1. Eligible student
    eligible_profile = UserProfile(
        user_id=1,
        state="All",
        age=20,
        annual_income=120000.0,
        occupation="Student",
        category="OBC",
        is_student=True
    )
    
    res = elig_agent.verify(eligible_profile, scheme)
    assert res["status"] == "Eligible"
    assert res["score"] == 100.0
    
    # 2. Ineligible student (over income threshold)
    rich_profile = UserProfile(
        user_id=2,
        state="All",
        age=20,
        annual_income=300000.0,
        occupation="Student",
        category="OBC",
        is_student=True
    )
    res_rich = elig_agent.verify(rich_profile, scheme)
    assert res_rich["status"] == "Not Eligible"
    assert res_rich["score"] == 10.0

def _scheme(**rules):
    return Scheme(
        title="Rule Test Scheme",
        description="Test",
        department="Test",
        ministry="Test",
        benefit_type="Subsidy",
        benefit_details="Test benefit",
        eligibility_rules=rules,
        required_documents=["aadhaar"],
        eli15_explanation="Test",
    )


def test_unknown_optional_facts_produce_insufficient_information():
    agent = EligibilityVerificationAgent()
    scheme = _scheme(has_ration_card=True, is_rural=True)
    profile = UserProfile(user_id=10, state="All", age=30, annual_income=100000)
    result = agent.verify(profile, scheme)
    assert result["status"] == "Insufficient Information"
    assert "ration card status" in result["missing_information"]
    assert "rural residence" in result["missing_information"]


def test_critical_failure_is_not_upgraded_by_other_matches():
    agent = EligibilityVerificationAgent()
    scheme = _scheme(max_annual_income=100000, category_whitelist=["SC"])
    profile = UserProfile(user_id=11, state="All", age=30, annual_income=500000, category="SC")
    result = agent.verify(profile, scheme)
    assert result["status"] == "Not Eligible"
    assert result["score"] == 10.0


def test_discovery_delegates_to_rule_engine():
    agent = SchemeDiscoveryAgent()
    scheme = _scheme(max_annual_income=100000)
    profile = UserProfile(user_id=12, state="All", age=30, annual_income=500000)
    ranked = agent.rank_schemes_for_profile(profile, [scheme])
    assert ranked[0]["eligibility_status"] == "Not Eligible"
    assert ranked[0]["eligibility_score"] == 10.0


def test_profile_sc_does_not_match_school():
    agent = CitizenProfileAgent()
    profile = {"category": "General", "occupation": "Unemployed"}
    updated = agent.extract_profile_from_text("I left school after class 10.", profile)
    assert updated["category"] == "General"
    assert updated["occupation"] == "Unemployed"


def test_sensitive_ids_are_masked():
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_pan("ABCDE1234F") == "ABCDE****F"
    redacted = redact_pii("Aadhaar 123456789012 PAN ABCDE1234F call 9876543210")
    assert "123456789012" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "9876543210" not in redacted


def test_local_ocr_masks_aadhaar():
    result = classify_and_extract_local(
        "aadhaar.pdf",
        "Government of India Aadhaar 1234 5678 9012 Name: Asha Devi",
        mime_type="application/pdf",
    )
    assert result["category"] == "aadhaar"
    assert result["document_id_number"] == "XXXX XXXX 9012"


def test_document_agent_flags_review_and_missing():
    agent = DocumentIntelligenceAgent()
    scheme = _scheme()
    scheme.required_documents = ["aadhaar", "income"]
    docs = [
        Document(
            user_id=1,
            file_name="aadhaar.png",
            file_path="/tmp/aadhaar.png",
            file_type="png",
            category="aadhaar",
            file_hash="x",
            is_valid=True,
            confidence=0.3,
            review_required=True,
        )
    ]
    result = agent.analyze_documents(docs, scheme)
    statuses = {item["category"]: item["status"] for item in result["checklist"]}
    assert statuses["aadhaar"] == "Needs Review"
    assert statuses["income"] == "Missing"
    assert result["readiness_score"] == 0.0
