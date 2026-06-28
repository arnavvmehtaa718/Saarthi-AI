import json
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, select
from app.core.config import settings
from app.models import Scheme

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

def init_db():
    SQLModel.metadata.create_all(engine)
    seed_schemes()

def get_session():
    with Session(engine) as session:
        yield session

def seed_schemes():
    with Session(engine) as session:
        # Check if we already have schemes
        statement = select(Scheme)
        results = session.exec(statement).all()
        if results:
            return  # Schemes already seeded
        
        schemes = [
            Scheme(
                title="PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
                description="A Central Sector scheme to provide income support to all landholding farmer families in the country to enable them to take care of agricultural expenses and domestic needs.",
                department="Department of Agriculture and Farmers Welfare",
                ministry="Ministry of Agriculture and Farmers Welfare",
                benefit_type="Financial Support",
                benefit_details="Direct benefit transfer of ₹6,000 per year, paid in three equal installments of ₹2,000 directly into the bank accounts of the beneficiary farmers.",
                eligibility_rules={
                    "min_age": 18,
                    "occupation_whitelist": ["Farmer"],
                    "owns_land_required": True,
                    "max_annual_income": None, # No strict income limit, but excludes taxpayers
                    "excludes_taxpayers": True,
                    "excludes_institutional_landholders": True,
                    "excludes_government_employees": True
                },
                required_documents=["aadhaar", "land", "bank", "mobile"],
                state="Central",
                application_url="https://pmkisan.gov.in/",
                steps=[
                    "Visit the official PM-KISAN portal.",
                    "Click on 'New Farmer Registration' under the Farmers Corner.",
                    "Enter Aadhaar number and captcha, choose rural/urban, select state, and search.",
                    "Fill in personal details, land details (Survey/Khata No, Khasra No, Area), and upload land certificate.",
                    "Submit the form and save the registration ID for tracking."
                ],
                deadlines={"end_date": None, "urgency": "Medium"},
                complexity="Low",
                tags=["Farmer", "Income Support", "Agriculture", "Direct Benefit Transfer"],
                eli15_explanation="If you are a farmer who owns farming land, the government will send you ₹6,000 every year in three payments of ₹2,000 directly to your bank account to help you buy seeds, fertilizer, and support your family."
            ),
            Scheme(
                title="Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
                description="The largest health assurance scheme in the world, aiming to provide free health cover up to ₹5 Lakh per family per year for secondary and tertiary care hospitalization.",
                department="National Health Authority",
                ministry="Ministry of Health and Family Welfare",
                benefit_type="Insurance",
                benefit_details="Cashless and paperless access to healthcare services up to ₹5,00,000 per family per year for over 1,300 medical procedures at empanelled public and private hospitals.",
                eligibility_rules={
                    "max_annual_income": 250000.0,
                    "category_whitelist": ["SC", "ST", "OBC", "General", "EWS"],
                    "is_disabled_preferred": True,
                    "excludes_government_employees": True,
                    "is_household_rural_vulnerable": True
                },
                required_documents=["aadhaar", "ration", "income"],
                state="Central",
                application_url="https://dashboard.pmjay.gov.in/",
                steps=[
                    "Check eligibility on the 'Am I Eligible' portal using mobile number or ration card number.",
                    "Locate the nearest Ayushman Mitra or empanelled hospital.",
                    "Present Aadhaar card, Ration card, or PM-JAY letter to verify identity.",
                    "An Ayushman card will be printed for your family, which can be presented at empanelled hospitals for free medical treatment."
                ],
                deadlines={"end_date": None, "urgency": "High"},
                complexity="Medium",
                tags=["Health", "Insurance", "Low Income", "Medical Care"],
                eli15_explanation="This scheme gives low-income families a special health card. If someone in the family falls very sick and needs to stay in a hospital, this card pays for their bills up to ₹5 lakh per year, so they do not have to pay anything out of their own pocket."
            ),
            Scheme(
                title="Pradhan Mantri Mudra Yojana (PMMY)",
                description="A flagship scheme to provide loans up to ₹10 Lakh to non-corporate, non-farm small/micro enterprises to help them start or expand their businesses.",
                department="SIDBI",
                ministry="Ministry of Finance",
                benefit_type="Loan",
                benefit_details="Collateral-free business loans divided into three categories: Shishu (loans up to ₹50,000), Kishor (loans from ₹50,000 to ₹5 Lakh), and Tarun (loans from ₹5 Lakh to ₹10 Lakh).",
                eligibility_rules={
                    "min_age": 18,
                    "max_age": 65,
                    "occupation_whitelist": ["Business Owner", "Artisan", "Farmer", "Street Vendor", "Unemployed"],
                    "is_student": False,
                    "requires_business_plan": True
                },
                required_documents=["aadhaar", "pan", "bank", "residence", "business_proof"],
                state="Central",
                application_url="https://www.udyamimitra.in/",
                steps=[
                    "Identify the category of loan needed: Shishu, Kishor, or Tarun.",
                    "Prepare a business proposal/project report showing business viability.",
                    "Visit any commercial bank, cooperative bank, or MFI, or apply online on the Udyamimitra portal.",
                    "Submit the application form, identity proofs, business proofs, and project report.",
                    "Bank processes application and disburses loan without demanding collateral security."
                ],
                deadlines={"end_date": None, "urgency": "Low"},
                complexity="High",
                tags=["Business", "Loan", "Finance", "Entrepreneurs"],
                eli15_explanation="If you want to start a shop or small business, or grow an existing one, you can get a loan from the bank up to ₹10 lakh without giving the bank any security (like gold or property). The loan amount is divided into three tiers based on how much money you need."
            ),
            Scheme(
                title="Post-Matric Scholarship Scheme for SC/ST/OBC Students",
                description="A Centrally Sponsored Scheme to provide financial assistance to students belonging to Scheduled Castes, Scheduled Tribes, and Other Backward Classes to pursue post-matric or post-secondary courses.",
                department="Department of Social Justice and Empowerment",
                ministry="Ministry of Social Justice and Empowerment",
                benefit_type="Scholarship",
                benefit_details="Full reimbursement of tuition fees and non-refundable compulsory fees charged by the educational institution, plus a monthly maintenance allowance.",
                eligibility_rules={
                    "is_student": True,
                    "category_whitelist": ["SC", "ST", "OBC"],
                    "max_annual_income": 250000.0,
                    "min_education_completed": "Metric"
                },
                required_documents=["aadhaar", "caste", "income", "education", "bank"],
                state="Central",
                application_url="https://scholarships.gov.in/",
                steps=[
                    "Register as a new user on the National Scholarship Portal (NSP).",
                    "Log in using the Application ID received and fill out the detailed scholarship form.",
                    "Upload caste, income, and educational certificates, plus bank details and fee receipts.",
                    "Submit the application for verification by the School/College Node Officer.",
                    "After institute and district approval, the scholarship amount is transferred directly to the student's bank account."
                ],
                deadlines={"end_date": "2026-10-31", "urgency": "High"},
                complexity="Medium",
                tags=["Education", "Scholarship", "Students", "SC/ST/OBC"],
                eli15_explanation="If you are from an SC, ST, or OBC family with an annual income under ₹2.5 lakh, the government will pay back your college tuition fees and give you a monthly stipend to help you cover books, food, and accommodation."
            ),
            Scheme(
                title="Pradhan Mantri Awas Yojana - Gramin (PMAY-G)",
                description="A social welfare program to provide clean, safe, and permanent housing with basic amenities to homeless families and those living in dilapidated houses in rural India.",
                department="Department of Rural Development",
                ministry="Ministry of Rural Development",
                benefit_type="Subsidy",
                benefit_details="Direct financial assistance of ₹1,20,000 (in plains) and ₹1,30,000 (in hilly/difficult areas) for house construction, along with supplementary funds for toilets via Swachh Bharat Mission.",
                eligibility_rules={
                    "max_annual_income": 150000.0,
                    "owns_house": False,
                    "is_rural": True
                },
                required_documents=["aadhaar", "bank", "residence", "income"],
                state="Central",
                application_url=None,
                steps=[
                    "Beneficiaries are identified and ranked by Gram Sabha using Socio-Economic Caste Census (SECC) data.",
                    "The local administration verifies the housing status and constructs a priority list.",
                    "The selected beneficiary is registered, bank details are mapped, and geo-tagged photos of the current house are taken.",
                    "Funds are transferred in installments directly to the bank account upon verification of different construction stages."
                ],
                deadlines={"end_date": None, "urgency": "Medium"},
                complexity="Medium",
                tags=["Housing", "Rural Development", "Low Income", "Subsidy"],
                eli15_explanation="If you live in a village, don't own a concrete house, and have low income, this scheme gives you up to ₹1.3 lakh directly in your bank account in parts to build your own brick house, plus extra money for a toilet."
            ),
            Scheme(
                title="Pradhan Mantri SVANidhi",
                description="A Special Micro-Credit Facility Scheme for Street Vendors to provide affordable working capital loans to resume their livelihoods post-pandemic.",
                department="Urban Development Department",
                ministry="Ministry of Housing and Urban Affairs",
                benefit_type="Loan",
                benefit_details="Collateral-free working capital loan of up to ₹10,000 for a 1-year tenure. On timely repayment, vendors are eligible for a second loan of ₹20,000, and a third loan of ₹50,000, along with a 7% interest subsidy.",
                eligibility_rules={
                    "occupation_whitelist": ["Street Vendor"],
                    "min_age": 18,
                    "is_urban": True
                },
                required_documents=["aadhaar", "voter_id", "bank", "vendor_cert"],
                state="Central",
                application_url="https://pmsvanidhi.mohua.gov.in/",
                steps=[
                    "Ensure you have a Certificate of Vending (CoV) or Letter of Recommendation from the local municipality.",
                    "Visit the PM SVANidhi portal or apply through a Common Service Centre (CSC) or local lending bank.",
                    "Submit Aadhaar, mobile number linked with Aadhaar, bank details, and vending proof.",
                    "The bank will process the loan, which is usually approved and disbursed within 15-30 days."
                ],
                deadlines={"end_date": None, "urgency": "Low"},
                complexity="Low",
                tags=["Street Vendor", "Loan", "Microfinance", "Livelihood"],
                eli15_explanation="If you sell things on the street (a vendor) in a town or city, you can get a loan of ₹10,000 to buy stock. If you pay it back on time, you can get bigger loans up to ₹50,000 with a lower interest rate, and cashback for using digital payments."
            ),
            Scheme(
                title="PM Vishwakarma Scheme",
                description="A scheme to provide end-to-end support to traditional artisans and craftspeople who work with their hands and tools, enhancing the quality and reach of their products.",
                department="Ministry of Micro, Small and Medium Enterprises",
                ministry="Ministry of MSME",
                benefit_type="Skill Development",
                benefit_details="Artisans get a PM Vishwakarma Certificate & ID, basic training (5-7 days) & advanced training (15 days) with ₹500/day stipend, a toolkit incentive of ₹15,000, and collateral-free loans up to ₹3,00,000 at 5% interest.",
                eligibility_rules={
                    "occupation_whitelist": ["Artisan", "Business Owner"],
                    "min_age": 18,
                    "excludes_government_employees": True,
                    "max_family_beneficiary_count": 1
                },
                required_documents=["aadhaar", "bank", "ration", "mobile"],
                state="Central",
                application_url="https://pmvishwakarma.gov.in/",
                steps=[
                    "Register online at a Common Service Centre (CSC) using biometric Aadhaar authentication.",
                    "Submit details of your traditional trade (e.g. carpenter, goldsmith, potter, tailor).",
                    "Get verified at three levels: Gram Panchayat/ULB, District Committee, and State/Central Screen.",
                    "Once verified, undergo skill training, receive the ₹15,000 toolkit voucher, and apply for interest-subsidized credit."
                ],
                deadlines={"end_date": None, "urgency": "High"},
                complexity="Medium",
                tags=["Artisans", "Skill Development", "Financial Aid", "Traditional Crafts"],
                eli15_explanation="If you work with your hands as a traditional craftsman (like a tailor, carpenter, potter, or barber), the government will give you a certificate, train you to improve your skills (paying you ₹500 a day while you learn), give you ₹15,000 to buy new tools, and offer low-interest loans up to ₹3 lakh to grow your work."
            ),
            Scheme(
                title="Pradhan Mantri Garib Kalyan Anna Yojana (PMGKAY)",
                description="A food security welfare scheme designed to provide free food grains to the poorest citizens of India under the National Food Security Act (NFSA).",
                department="Department of Food and Public Distribution",
                ministry="Ministry of Consumer Affairs, Food and Public Distribution",
                benefit_type="Subsidy",
                benefit_details="5 kg of free foodgrains (rice, wheat, or coarse grains) per person per month to Priority Households (PHH) and Antyodaya Anna Yojana (AAY) beneficiaries, in addition to their regular subsidized NFSA quota.",
                eligibility_rules={
                    "max_annual_income": 120000.0,
                    "category_whitelist": ["SC", "ST", "OBC", "General", "EWS"],
                    "has_ration_card": True
                },
                required_documents=["aadhaar", "ration"],
                state="Central",
                application_url="https://nfsa.gov.in/",
                steps=[
                    "Ensure your family has an active Ration Card linked to Aadhaar.",
                    "Visit the nearest Fair Price Shop (Ration Shop) in your locality.",
                    "Undergo biometric (fingerprint/iris) authentication at the electronic Point of Sale (ePoS) machine.",
                    "Collect your free quota of 5 kg foodgrains per family member along with your standard monthly food ration."
                ],
                deadlines={"end_date": "2028-12-31", "urgency": "High"},
                complexity="Low",
                tags=["Food Security", "Ration", "Low Income", "Subsidy"],
                eli15_explanation="This scheme helps low-income families get free food. Every member of the family listed on your Ration Card gets 5 kilograms of free rice, wheat, or grains every month from the local ration shop, so nobody goes hungry."
            )
        ]
        
        session.add_all(schemes)
        session.commit()
