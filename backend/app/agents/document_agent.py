from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.models import Document, Scheme

class DocumentIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Document Intelligence Agent",
            description="Analyzes required documents, checks user files, highlights missing documents, and validates document validity."
        )

    def analyze_documents(self, user_docs: List[Document], scheme: Scheme) -> Dict[str, Any]:
        """
        Map user documents against scheme requirements.
        Highlights:
        - Available documents
        - Missing documents
        - Expiration alerts
        """
        required = scheme.required_documents  # e.g., ["aadhaar", "bank", "land"]
        available_categories = {doc.category: doc for doc in user_docs if doc.is_valid}
        
        checklist = []
        missing = []
        warnings = []
        
        for req_cat in required:
            is_present = req_cat in available_categories
            matched_doc = available_categories.get(req_cat) if is_present else None
            
            status = "Missing"
            expiry_alert = False
            doc_name = None
            doc_id = None
            
            if matched_doc:
                status = "Verified"
                doc_name = matched_doc.file_name
                doc_id = matched_doc.document_id_number
                
                # Check for expiration
                if matched_doc.expiry_date:
                    from datetime import datetime
                    if matched_doc.expiry_date < datetime.utcnow():
                        status = "Expired"
                        expiry_alert = True
                        warnings.append(f"Your document '{matched_doc.file_name}' ({req_cat.upper()}) has expired.")
            else:
                missing.append(req_cat)
                
            checklist.append({
                "category": req_cat,
                "required_label": req_cat.replace("_", " ").title(),
                "status": status,
                "file_name": doc_name,
                "document_id": doc_id,
                "expiry_alert": expiry_alert
            })
            
        # Determine overall readiness score
        total_req = len(required)
        ready_count = sum(1 for item in checklist if item["status"] == "Verified")
        readiness_score = (ready_count / total_req * 100.0) if total_req > 0 else 100.0

        return {
            "checklist": checklist,
            "missing": missing,
            "warnings": warnings,
            "readiness_score": readiness_score,
            "is_ready": len(missing) == 0 and len(warnings) == 0
        }
