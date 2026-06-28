import pytest
from sqlmodel import SQLModel, create_engine, Session
from app.models import UserProfile, Scheme
from app.agents.profile_agent import CitizenProfileAgent
from app.agents.discovery_agent import SchemeDiscoveryAgent
from app.agents.eligibility_agent import EligibilityVerificationAgent

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
