import os
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, Document, UserScheme
from app.services.ocr import extract_text_from_pdf, classify_and_extract_local, run_multimodal_ocr
from app.core.config import settings

router = APIRouter(prefix="/vault", tags=["vault"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("", response_model=List[Document])
def get_vault_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return session.exec(select(Document).where(Document.user_id == current_user.id)).all()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category_override: str = Form("other"), # User can specify category or let OCR detect
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Read file content
    contents = await file.read()
    
    # Generate file hash to check duplicates
    file_hash = hashlib.sha256(contents).hexdigest()
    existing_doc = session.exec(
        select(Document).where(Document.user_id == current_user.id, Document.file_hash == file_hash)
    ).first()
    
    if existing_doc:
        raise HTTPException(status_code=400, detail="This file is already uploaded to your vault.")
        
    # Write to local uploads directory
    file_extension = file.filename.split(".")[-1].lower()
    file_name = file.filename
    storage_filename = f"{current_user.id}_{file_hash[:10]}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, storage_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
        
    # Hybrid OCR logic
    ocr_results = {}
    ocr_error = None
    
    # 1. Check if Gemini API key exists to perform Multimodal OCR
    if settings.GEMINI_API_KEY:
        try:
            ocr_results = run_multimodal_ocr(contents, file_extension, file_name)
        except Exception as e:
            ocr_error = str(e)
            
    # 2. Fall back to local structural/regex scan
    if not ocr_results:
        extracted_text = ""
        if file_extension == "pdf":
            extracted_text = extract_text_from_pdf(contents)
        ocr_results = classify_and_extract_local(file_name, extracted_text)
        
    # If category override is provided, we can respect it if it is not "other"
    category = ocr_results.get("category", "other")
    if category_override != "other":
        category = category_override

    # Create Document record
    doc = Document(
        user_id=current_user.id,
        file_name=file_name,
        file_path=file_path,
        file_type=file_extension,
        category=category,
        file_hash=file_hash,
        document_id_number=ocr_results.get("document_id_number"),
        owner_name=ocr_results.get("owner_name"),
        expiry_date=ocr_results.get("expiry_date"),
        is_valid=ocr_results.get("is_valid", True),
        extracted_metadata={
            "ocr_method": ocr_results.get("ocr_method"),
            "summary": ocr_results.get("summary", "File successfully parsed locally."),
            "ocr_error": ocr_error
        }
    )
    
    session.add(doc)
    session.commit()
    session.refresh(doc)
    
    # Update checklist status in all user schemes matching this category
    user_schemes = session.exec(select(UserScheme).where(UserScheme.user_id == current_user.id)).all()
    for us in user_schemes:
        if category in us.missing_documents:
            # Recheck and remove from missing documents list
            updated_missing = [d for d in us.missing_documents if d != category]
            us.missing_documents = updated_missing
            session.add(us)
            
    session.commit()
    
    return {
        "message": "Document successfully uploaded and analyzed.",
        "document": doc,
        "ocr_info": ocr_results
    }

@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    doc = session.exec(select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete from filesystem
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
            
    category = doc.category
    session.delete(doc)
    session.commit()
    
    # Recalculate missing documents lists for user schemes
    # Re-fetch all documents of the user in this category to see if another valid one exists
    other_docs = session.exec(
        select(Document).where(
            Document.user_id == current_user.id,
            Document.category == category,
            Document.is_valid == True
        )
    ).all()
    
    if not other_docs:
        # None left, so mark as missing in active schemes
        user_schemes = session.exec(select(UserScheme).where(UserScheme.user_id == current_user.id)).all()
        for us in user_schemes:
            sch = us.scheme
            if category in sch.required_documents and category not in us.missing_documents:
                updated_missing = us.missing_documents + [category]
                us.missing_documents = updated_missing
                session.add(us)
        session.commit()
        
    return {"message": "Document deleted successfully."}
