from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    profile: Optional["UserProfile"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})
    documents: List["Document"] = Relationship(back_populates="user")
    user_schemes: List["UserScheme"] = Relationship(back_populates="user")
    reminders: List["Reminder"] = Relationship(back_populates="user")
    chat_messages: List["ChatMessage"] = Relationship(back_populates="user")

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    
    # Demographics & State
    state: str = Field(default="All")  # e.g., "Uttar Pradesh", "Maharashtra"
    district: Optional[str] = Field(default=None)
    age: int = Field(default=18)
    gender: str = Field(default="General") # "Male", "Female", "Transgender", "Other"
    
    # Socio-economic
    annual_income: float = Field(default=0.0)
    category: str = Field(default="General") # "General", "OBC", "SC", "ST", "EWS"
    occupation: str = Field(default="Unemployed") # "Farmer", "Student", "Artisan", "Business Owner", "Salaried", "Unemployed", "Street Vendor"
    educational_level: str = Field(default="None") # "Illiterate", "Primary", "Metric", "Senior Secondary", "Graduate", "Post Graduate"
    
    # Flags
    is_student: bool = Field(default=False)
    owns_land: bool = Field(default=False)
    land_area_hectares: float = Field(default=0.0)
    employment_status: str = Field(default="Unemployed") # "Employed", "Self-Employed", "Unemployed"
    is_disabled: bool = Field(default=False)
    disability_percentage: float = Field(default=0.0)
    disability_type: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="profile")

class Scheme(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: str
    department: str
    ministry: str
    benefit_type: str  # "Financial Support", "Subsidy", "Insurance", "Scholarship", "Skill Development", "Loan"
    benefit_details: str
    
    # Specific criteria ranges & arrays (JSON)
    eligibility_rules: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    # Required document categories (JSON list)
    required_documents: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    state: str = Field(default="Central")  # "Central" or specific State Name
    application_url: Optional[str] = Field(default=None)
    steps: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    deadlines: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON)) # e.g. {"end_date": "2026-12-31", "urgency": "High"}
    
    complexity: str = Field(default="Medium") # "Low", "Medium", "High"
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    eli15_explanation: str
    
    user_relations: List["UserScheme"] = Relationship(back_populates="scheme")

class UserScheme(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    scheme_id: int = Field(foreign_key="scheme.id", index=True)
    
    status: str = Field(default="discovered")  # "discovered", "saved", "applied", "approved", "rejected"
    eligibility_score: float = Field(default=0.0)  # 0 to 100
    eligibility_status: str = Field(default="Likely Eligible")  # "Eligible", "Likely Eligible", "Missing Information", "Not Eligible"
    eligibility_explanation: str
    
    missing_documents: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    application_draft: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timeline: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="user_schemes")
    scheme: Scheme = Relationship(back_populates="user_relations")

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    file_name: str
    file_path: str
    file_type: str  # "pdf", "png", "jpeg"
    category: str  # "aadhaar", "pan", "income", "caste", "residence", "bank", "land", "disability", "education", "other"
    file_hash: str
    
    # Metadata extracted by OCR
    document_id_number: Optional[str] = Field(default=None) # e.g. Aadhaar number
    owner_name: Optional[str] = Field(default=None)
    expiry_date: Optional[datetime] = Field(default=None)
    is_valid: bool = Field(default=True)
    
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="documents")

class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    scheme_id: Optional[int] = Field(default=None, foreign_key="scheme.id", nullable=True)
    
    title: str
    description: str
    trigger_date: datetime
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="reminders")

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="user")  # "user", "assistant", "system"
    content: str
    agent_name: Optional[str] = Field(default=None) # Which agent produced this content (if role is assistant)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="chat_messages")
