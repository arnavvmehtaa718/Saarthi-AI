import hashlib
import os
import secrets
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agents.document_agent import DocumentIntelligenceAgent
from app.core.config import settings
from app.core.db import get_session
from app.models import Document, User, UserScheme
from app.routes.deps import get_current_user
from app.services.files import (
    UploadValidationError,
    safe_storage_path,
    validate_upload,
)
from app.services.ocr import (
    classify_and_extract_local,
    extract_text_from_pdf,
    normalize_category,
    run_multimodal_ocr,
)

router = APIRouter(prefix="/vault", tags=["vault"])
document_agent = DocumentIntelligenceAgent()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


class DocumentOut(BaseModel):
    id: int
    file_name: str
    file_type: str
    category: str
    file_hash: str
    document_id_number: str | None = None
    owner_name: str | None = None
    expiry_date: datetime | None = None
    is_valid: bool
    confidence: float
    review_required: bool
    extracted_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    download_url: str


def serialize_document(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        file_name=doc.file_name,
        file_type=doc.file_type,
        category=doc.category,
        file_hash=doc.file_hash,
        document_id_number=doc.document_id_number,
        owner_name=doc.owner_name,
        expiry_date=doc.expiry_date,
        is_valid=doc.is_valid,
        confidence=doc.confidence,
        review_required=doc.review_required,
        extracted_metadata=doc.extracted_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        download_url=f"/vault/{doc.id}/file",
    )


def recalculate_missing_documents(session: Session, user_id: int) -> None:
    user_docs = session.exec(select(Document).where(Document.user_id == user_id)).all()
    relations = session.exec(select(UserScheme).where(UserScheme.user_id == user_id)).all()
    for relation in relations:
        if not relation.scheme:
            continue
        result = document_agent.analyze_documents(user_docs, relation.scheme)
        relation.missing_documents = result["missing"]
        relation.updated_at = datetime.utcnow()
        session.add(relation)
    session.commit()


@router.get("", response_model=List[DocumentOut])
def get_vault_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    docs = session.exec(select(Document).where(Document.user_id == current_user.id)).all()
    return [serialize_document(doc) for doc in docs]


@router.get("/{doc_id}/file")
def download_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    doc = session.exec(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    base = os.path.abspath(settings.UPLOAD_DIR)
    path = os.path.abspath(doc.file_path)
    try:
        inside_upload_dir = os.path.commonpath([base, path]) == base
    except ValueError:
        inside_upload_dir = False
    if not inside_upload_dir or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Stored file not found")

    media_type = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(doc.file_type.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        filename=doc.file_name,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category_override: str = Form("other"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    raw_category = (category_override or "other").strip().lower()
    category_override = normalize_category(raw_category)
    if raw_category != "other" and category_override == "other":
        raise HTTPException(status_code=400, detail="Unsupported document category.")

    contents = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum size is {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    try:
        file_extension, mime_type = validate_upload(
            file.filename,
            contents,
            settings.allowed_upload_extensions,
            settings.MAX_UPLOAD_BYTES,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_hash = hashlib.sha256(contents).hexdigest()
    existing_doc = session.exec(
        select(Document).where(
            Document.user_id == current_user.id,
            Document.file_hash == file_hash,
        )
    ).first()
    if existing_doc:
        raise HTTPException(status_code=400, detail="This file is already uploaded to your vault.")

    user_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    storage_filename = f"{secrets.token_hex(16)}.{file_extension}"
    file_path = safe_storage_path(user_dir, storage_filename)
    with open(file_path, "wb") as handle:
        handle.write(contents)

    ocr_results: Dict[str, Any] = {}
    ocr_error = None
    try:
        ocr_results = run_multimodal_ocr(
            contents,
            file_extension,
            file.filename or storage_filename,
            category_hint=category_override,
        )
    except Exception as exc:
        ocr_error = str(exc)
        extracted_text = extract_text_from_pdf(contents) if file_extension == "pdf" else ""
        ocr_results = classify_and_extract_local(
            file.filename or storage_filename,
            extracted_text,
            mime_type=mime_type,
        )

    category = normalize_category(ocr_results.get("category"))
    if category_override != "other":
        category = category_override

    doc = Document(
        user_id=current_user.id,
        file_name=os.path.basename(file.filename or storage_filename),
        file_path=file_path,
        file_type=file_extension,
        category=category,
        file_hash=file_hash,
        document_id_number=ocr_results.get("document_id_number"),
        owner_name=ocr_results.get("owner_name"),
        expiry_date=ocr_results.get("expiry_date"),
        is_valid=ocr_results.get("is_valid", True),
        confidence=float(ocr_results.get("confidence", 0.0) or 0.0),
        review_required=bool(ocr_results.get("review_required", True)),
        extracted_metadata={
            "ocr_method": ocr_results.get("ocr_method"),
            "summary": ocr_results.get("summary", ""),
            "provider": ocr_results.get("provider"),
            "model": ocr_results.get("model"),
            "privacy_note": ocr_results.get("privacy_note"),
            "ocr_error": ocr_error,
            "category_source": "uploader" if category_override != "other" else "extraction",
        },
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)
    recalculate_missing_documents(session, current_user.id)

    return {
        "message": "Document stored privately and analysed.",
        "document": serialize_document(doc),
        "ocr_info": {
            "category": category,
            "confidence": doc.confidence,
            "review_required": doc.review_required,
            "method": doc.extracted_metadata.get("ocr_method"),
            "summary": doc.extracted_metadata.get("summary"),
            "ocr_error": ocr_error,
        },
    }


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    doc = session.exec(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    session.delete(doc)
    session.commit()
    recalculate_missing_documents(session, current_user.id)
    return {"message": "Document deleted successfully."}
