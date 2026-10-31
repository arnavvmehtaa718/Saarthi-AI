import io
import logging
import re
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field
from pypdf import PdfReader

from app.agents.base import AIProviderError, extract_json, get_ai_client
from app.core.config import settings
from app.services.privacy import mask_sensitive_id, redact_pii

logger = logging.getLogger("saarthi.ocr")

VALID_CATEGORIES = {
    "aadhaar",
    "pan",
    "income",
    "caste",
    "residence",
    "bank",
    "land",
    "disability",
    "education",
    "ration",
    "voter_id",
    "business_proof",
    "vendor_cert",
    "other",
}

CATEGORY_ALIASES = {
    "adhar": "aadhaar",
    "uidai": "aadhaar",
    "voter": "voter_id",
    "voterid": "voter_id",
    "epic": "voter_id",
    "business": "business_proof",
    "vendor": "vendor_cert",
    "caste_certificate": "caste",
    "income_certificate": "income",
    "residence_certificate": "residence",
    "bank_account": "bank",
    "land_record": "land",
}


def normalize_category(value: str | None) -> str:
    """Map uploader aliases onto the canonical category names used by schemes."""
    candidate = (value or "other").strip().lower()
    candidate = CATEGORY_ALIASES.get(candidate, candidate)
    return candidate if candidate in VALID_CATEGORIES else "other"



class DocumentOCRSchema(BaseModel):
    category: str = Field(description="One of the supported document categories")
    document_id_number: str | None = Field(
        description="Official document number, or null if not visible", default=None
    )
    owner_name: str | None = Field(description="Name printed on the document", default=None)
    expiry_date_str: str | None = Field(
        description="Expiry or validity date as YYYY-MM-DD, or null", default=None
    )
    is_valid: bool = Field(
        description="False only when the document is visibly expired or invalid", default=True
    )
    confidence: float = Field(
        description="Confidence between 0 and 1 for the classification and extraction", default=0.0
    )
    review_required: bool = Field(
        description="True when the image is unclear, cropped, or fields are uncertain", default=True
    )
    summary: str = Field(description="Short factual summary without repeating full ID numbers", default="")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as exc:
        logger.error("Error extracting text from PDF: %s", exc)
        return ""


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _category_from_text(content: str) -> str:
    patterns = [
        ("aadhaar", r"\b(aadhaar|adhar|uidai)\b"),
        ("pan", r"\b(pan|pancard|permanent account number)\b"),
        ("income", r"\b(income certificate|salary slip|form 16|revenue certificate)\b"),
        ("caste", r"\b(caste|jati|community certificate)\b"),
        ("residence", r"\b(residence|domicile|address proof|electricity bill)\b"),
        ("bank", r"\b(passbook|bank statement|account details|ifsc)\b"),
        ("land", r"\b(land record|roor|khasra|khatauni|patta)\b"),
        ("disability", r"\b(disability|udid|handicap)\b"),
        ("education", r"\b(mark sheet|marksheet|degree|diploma|school leaving|matriculation)\b"),
        ("ration", r"\b(ration card|pds|antyodaya|priority household)\b"),
        ("voter_id", r"\b(voter|electoral|epic)\b"),
        ("business_proof", r"\b(udyam|gst|business registration|shop act|trade licence)\b"),
        ("vendor_cert", r"\b(certificate of vending|vendor certificate|street vendor)\b"),
    ]
    for category, pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return category
    return "other"


def classify_and_extract_local(
    filename: str,
    text: str,
    mime_type: str | None = None,
) -> Dict[str, Any]:
    """Fast local keyword/regex scan used when vision extraction is unavailable.

    This deliberately does not pretend to read image pixels. Image uploads are
    marked for review unless a vision-capable model is enabled.
    """
    content = f"{filename}\n{text}"
    category = _category_from_text(content)
    doc_id = None
    if category == "aadhaar":
        match = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text)
        if match:
            doc_id = mask_sensitive_id(match.group(0), "aadhaar")
    elif category == "pan":
        match = re.search(r"\b[a-zA-Z]{5}\d{4}[a-zA-Z]\b", text)
        if match:
            doc_id = mask_sensitive_id(match.group(0), "pan")
    elif category == "bank":
        ifsc_match = re.search(r"\b[a-zA-Z]{4}0[a-zA-Z0-9]{6}\b", text)
        if ifsc_match:
            doc_id = f"IFSC: {ifsc_match.group(0).upper()}"

    expiry_date = None
    expiry_match = re.search(
        r"(?:expiry|expires|valid\s+upto|valid\s+until|valid\s+till|exp\b)[^\d]*"
        r"(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})",
        content,
        re.IGNORECASE,
    )
    if expiry_match:
        expiry_date = _parse_expiry(expiry_match.group(1))

    owner_name = None
    name_match = re.search(
        r"(?:name|holder|citizen\s+name)[^\w]*([A-Za-z][A-Za-z\s.]{2,40})",
        text,
        re.IGNORECASE,
    )
    if name_match:
        owner_name = name_match.group(1).strip()

    has_text = bool(text.strip())
    is_image = (mime_type or "").startswith("image/")
    confidence = 0.68 if has_text and category != "other" else (0.35 if category != "other" else 0.2)
    review_required = (not has_text) or is_image or category == "other" or confidence < 0.7
    is_valid = True
    if expiry_date and expiry_date < datetime.utcnow():
        is_valid = False

    if has_text:
        summary = "Local keyword and PDF-text scan completed. Verify extracted fields against the original document."
    else:
        summary = (
            "No readable text was extracted locally. The document is stored for manual review; "
            "enable a vision-capable Gemma 4 endpoint to read image content."
        )

    return {
        "category": category if category in VALID_CATEGORIES else "other",
        "document_id_number": doc_id,
        "owner_name": owner_name,
        "expiry_date": expiry_date,
        "confidence": confidence,
        "is_valid": is_valid,
        "review_required": review_required,
        "ocr_method": "Local filename/PDF-text scan (no image OCR)",
        "summary": summary,
        "provider": "local",
        "model": "regex",
    }


def _can_send_document_bytes() -> tuple[bool, str]:
    ai = get_ai_client()
    if not ai.ready:
        return False, ai.error or "No AI provider is configured."
    if ai.is_mock:
        return False, "AI_PROVIDER=mock; document vision is disabled."
    if not ai.is_gemma:
        return False, "Raw document bytes are only sent to Gemma 4, not alternative providers."
    if ai.gemma_is_private:
        return True, "Self-hosted Gemma 4 endpoint on a private network."
    if settings.GEMMA_ALLOW_DOCUMENT_BYTES:
        return True, "Hosted Gemma endpoint explicitly enabled for document bytes."
    return (
        False,
        "Document bytes are blocked for hosted endpoints. Set GEMMA_ALLOW_DOCUMENT_BYTES=true "
        "only after accepting the privacy trade-off.",
    )


def _can_send_extracted_text() -> tuple[bool, str]:
    ai = get_ai_client()
    if not ai.ready:
        return False, ai.error or "No AI provider is configured."
    if ai.is_mock:
        return False, "AI_PROVIDER=mock; document extraction is disabled."
    return True, "Only redacted extracted text is sent to the configured provider."


def _build_ocr_result(
    ai,
    payload: Dict[str, Any],
    method: str,
    privacy_note: str,
) -> Dict[str, Any]:
    category = normalize_category(payload.get("category"))

    confidence = payload.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    expiry_date = _parse_expiry(payload.get("expiry_date_str"))
    review_required = bool(payload.get("review_required", False)) or confidence < 0.7
    is_valid = bool(payload.get("is_valid", True))
    if expiry_date and expiry_date < datetime.utcnow():
        is_valid = False
        review_required = True

    return {
        "category": category,
        "document_id_number": mask_sensitive_id(
            payload.get("document_id_number"), category
        ),
        "owner_name": payload.get("owner_name"),
        "expiry_date": expiry_date,
        "confidence": confidence,
        "is_valid": is_valid,
        "review_required": review_required,
        "ocr_method": method,
        "summary": redact_pii(str(payload.get("summary") or "")).strip(),
        "provider": ai.provider,
        "model": ai.model,
        "privacy_note": privacy_note,
    }


def run_multimodal_ocr(
    file_bytes: bytes,
    file_type: str,
    filename: str,
    category_hint: str | None = None,
) -> Dict[str, Any]:
    """Read a document with the configured AI provider.

    PDFs are parsed locally and only redacted text is sent to the model. Images
    use Gemma 4 vision, and raw bytes are restricted to self-hosted endpoints.
    Raises AIProviderError/ValueError when extraction is unavailable so the
    caller can fall back to a clearly labelled local scan.
    """
    extension = file_type.lower().lstrip(".")
    system_instruction = (
        "You are a careful Indian government-document extraction assistant. "
        "Read only what is visible. Never guess a number, name, or date. "
        "If a field is unclear, set review_required=true and explain briefly. "
        "Return only JSON matching the schema."
    )
    category_line = (
        "Classify it into one of: aadhaar, pan, income, caste, residence, bank, land, "
        "disability, education, ration, voter_id, business_proof, vendor_cert, other. "
    )
    hint_line = ""
    if category_hint and category_hint != "other":
        hint_line = (
            f"The uploader selected the category '{normalize_category(category_hint)}'; "
            "verify or correct it. "
        )

    if extension == "pdf":
        text = extract_text_from_pdf(file_bytes)
        if not text.strip():
            raise AIProviderError(
                "No selectable text was found in the PDF. Upload a clear image or "
                "enable a vision-capable Gemma 4 endpoint."
            )
        allowed, reason = _can_send_extracted_text()
        if not allowed:
            raise AIProviderError(reason)
        ai = get_ai_client()
        prompt = (
            f"Analyse the text extracted from the PDF named '{filename}'. "
            f"{category_line}{hint_line}"
            "Extract the owner name, document number, and expiry date if present. "
            "Do not include any other personal data in the summary.\n\n"
            f"Document text:\n{redact_pii(text)}"
        )
        try:
            raw = ai.complete(
                prompt,
                system_instruction,
                response_schema=DocumentOCRSchema,
            )
            payload = extract_json(raw.text)
        except Exception as exc:
            logger.warning("Gemma PDF text extraction failed: %s", exc)
            raise AIProviderError(f"Gemma PDF text extraction failed: {exc}") from exc
        return _build_ocr_result(
            ai, payload, f"{ai.model} PDF text extraction", reason
        )

    allowed, reason = _can_send_document_bytes()
    if not allowed:
        raise AIProviderError(reason)

    ai = get_ai_client()
    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(extension)
    if not mime_type:
        raise ValueError("Unsupported file type for vision extraction.")

    prompt = (
        f"Analyse the attached document named '{filename}'. "
        f"{category_line}{hint_line}"
        "Extract the owner name, document number, and expiry date if present. "
        "Do not include any other personal data in the summary."
    )

    try:
        raw = ai.vision(
            file_bytes=file_bytes,
            mime_type=mime_type,
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=DocumentOCRSchema,
        )
        payload = extract_json(raw.text)
    except Exception as exc:
        logger.warning("Gemma document extraction failed: %s", exc)
        raise AIProviderError(f"Gemma document extraction failed: {exc}") from exc

    return _build_ocr_result(
        ai, payload, f"{ai.model} multimodal vision", reason
    )
