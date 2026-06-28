import re
import io
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from pypdf import PdfReader
from google import genai
from app.core.config import settings

logger = logging.getLogger("saarthi.ocr")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using pypdf."""
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def classify_and_extract_local(filename: str, text: str) -> Dict[str, Any]:
    """
    Local Regex-based matching for Aadhaar, PAN, dates, and classification.
    Runs fast without needing external APIs.
    """
    content = (filename + " " + text).lower()
    
    # Default category mapping
    category = "other"
    if any(k in content for k in ["aadhaar", "adhar", "uidai"]):
        category = "aadhaar"
    elif any(k in content for k in ["pan ", "pancard", "permanent account"]):
        category = "pan"
    elif any(k in content for k in ["income", "salary slip", "form 16", "revenue"]):
        category = "income"
    elif any(k in content for k in ["caste", "jati", "community certificate"]):
        category = "caste"
    elif any(k in content for k in ["residence", "domicile", "address proof", "electricity"]):
        category = "residence"
    elif any(k in content for k in ["passbook", "bank statement", "account detail"]):
        category = "bank"
    elif any(k in content for k in ["land record", "roor", "khasra", "khatauni", "patta"]):
        category = "land"
    elif any(k in content for k in ["disability", "udid", "handicap"]):
        category = "disability"
    elif any(k in content for k in ["mark sheet", "degree", "diploma", "school leaving", "matriculation"]):
        category = "education"

    # Extract ID numbers
    doc_id = None
    if category == "aadhaar":
        # Aadhaar: 12 digits (often formatted as XXXX XXXX XXXX)
        match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if match:
            doc_id = match.group(0)
    elif category == "pan":
        # PAN: 5 letters, 4 digits, 1 letter
        match = re.search(r'\b[a-zA-Z]{5}\d{4}[a-zA-Z]{1}\b', text)
        if match:
            doc_id = match.group(0).upper()
    elif category == "bank":
        # IFSC code or simple account number guess
        ifsc_match = re.search(r'\b[a-zA-Z]{4}0[a-zA-Z0-9]{6}\b', text)
        if ifsc_match:
            doc_id = f"IFSC: {ifsc_match.group(0).upper()}"
            
    # Extract Expiry Date (if any)
    # Search for common date patterns containing "expiry", "expires", "valid upto"
    expiry_date = None
    expiry_match = re.search(
        r'(?:expiry|expires|valid\s+upto|valid\s+until|exp\b)[^\d]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
        content
    )
    if expiry_match:
        date_str = expiry_match.group(1)
        # Try parsing
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                expiry_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

    # Extract Owner Name
    owner_name = None
    name_match = re.search(r'(?:name|holder|citizen\s+name)[^\w]*([a-zA-Z\s]{3,25})', text, re.IGNORECASE)
    if name_match:
        owner_name = name_match.group(1).strip()

    return {
        "category": category,
        "document_id_number": doc_id,
        "owner_name": owner_name,
        "expiry_date": expiry_date,
        "confidence": 0.8,
        "is_valid": True,
        "ocr_method": "Local Regex & Keyword Structural Scan"
    }

def run_multimodal_ocr(file_bytes: bytes, file_type: str, filename: str) -> Dict[str, Any]:
    """
    Multimodal AI OCR using Gemini 2.5.
    Sends raw image or PDF bytes directly to Gemini to extract metadata.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")

    try:
        # Determine mime type
        mime_type = "application/pdf" if file_type.lower() == "pdf" else f"image/{file_type.lower()}"
        if file_type.lower() in ["jpg", "jpeg"]:
            mime_type = "image/jpeg"
        elif file_type.lower() == "png":
            mime_type = "image/png"

        # Initialize client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Prepare instructions
        system_instruction = (
            "You are a professional document scanning agent in India. "
            "Examine the document provided. Classify it into one of these categories: "
            "['aadhaar', 'pan', 'income', 'caste', 'residence', 'bank', 'land', 'disability', 'education', 'other']. "
            "Extract the owner's full name, the official document ID number (e.g. 12-digit Aadhaar, 10-char PAN), "
            "and any expiration/validity dates. Return the data ONLY as a valid JSON object matching the requested schema."
        )

        class GeminiOCRSchema(BaseModel):
            category: str
            document_id_number: str | None
            owner_name: str | None
            expiry_date_str: str | None = Field(description="Format YYYY-MM-DD if found, else null")
            is_valid: bool = Field(description="Check if document seems authentic and not expired")
            summary: str

        from google.genai import types
        # Pass bytes directly
        content_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        )
        
        prompt = f"Analyze this uploaded file: {filename} and extract core metadata."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, content_part],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GeminiOCRSchema
            )
        )
        
        result = json.loads(response.text)
        
        # Parse expiry date string to datetime if available
        expiry_date = None
        if result.get("expiry_date_str"):
            try:
                expiry_date = datetime.strptime(result["expiry_date_str"], "%Y-%m-%d")
            except Exception:
                pass

        return {
            "category": result.get("category", "other"),
            "document_id_number": result.get("document_id_number"),
            "owner_name": result.get("owner_name"),
            "expiry_date": expiry_date,
            "confidence": 0.95,
            "is_valid": result.get("is_valid", True),
            "ocr_method": "Gemini Multimodal Vision API Scan",
            "summary": result.get("summary", "")
        }

    except Exception as e:
        logger.error(f"Gemini OCR processing failed, falling back to local: {e}")
        # Return none or raise to let controller fall back
        raise e
