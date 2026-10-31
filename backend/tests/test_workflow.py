import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.agents.base import reset_ai_client
from app.agents.orchestrator import MultiAgentOrchestrator
from app.core.config import settings
from app.core.db import get_session
from app.main import app
from app.models import Scheme
from app.routes import chat as chat_routes

OCR_PAYLOAD = {
    "category": "aadhaar",
    "document_id_number": "1234 5678 9012",
    "owner_name": "Asha Devi",
    "expiry_date_str": None,
    "is_valid": True,
    "confidence": 0.95,
    "review_required": False,
    "summary": "Aadhaar card for Asha Devi.",
}


def make_text_pdf(text: str) -> bytes:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content = f"BT /F1 12 Tf 72 720 Td ({escape(text)}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode()
    )
    return bytes(output)


class _GemmaStub(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = json.dumps(body.get("messages", []))
        if "Draft letter" in prompt:
            content = "Dear Sir/Madam,\n\nPlease accept my application.\n\nSincerely,\nAsha Devi"
        else:
            content = json.dumps(OCR_PAYLOAD)

        payload = {
            "id": "chatcmpl-workflow",
            "object": "chat.completion",
            "created": 0,
            "model": body.get("model", "gemma"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_upload_extraction_review_and_deterministic_eligibility(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _GemmaStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'workflow.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemma")
    monkeypatch.setattr(
        settings, "GEMMA_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1"
    )
    monkeypatch.setattr(settings, "GEMMA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMMA_MODEL", "google/gemma-4-12B-it")
    reset_ai_client()

    with Session(engine) as session:
        scheme = Scheme(
            title="Test Aadhaar Benefit",
            description="Test scheme for the document workflow.",
            department="Test Department",
            ministry="Test Ministry",
            benefit_type="Financial Support",
            benefit_details="Test benefit.",
            eligibility_rules={"min_age": 18, "max_annual_income": 200000.0},
            required_documents=["aadhaar"],
            state="Central",
            steps=["Upload Aadhaar.", "Submit the application."],
            deadlines={"end_date": None, "urgency": "Low"},
            complexity="Low",
            tags=["Test"],
            eli15_explanation="A simple test benefit.",
        )
        session.add(scheme)
        session.commit()
        session.refresh(scheme)
        scheme_id = scheme.id

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        guest = client.post("/auth/guest")
        assert guest.status_code == 200
        headers = {"Authorization": f"Bearer {guest.json()['access_token']}"}

        profile = client.put(
            "/profile",
            headers=headers,
            json={
                "full_name": "Asha Devi",
                "state": "Bihar",
                "age": 30,
                "annual_income": 100000,
                "category": "General",
                "occupation": "Farmer",
            },
        )
        assert profile.status_code == 200

        pdf = make_text_pdf("Aadhaar 1234 5678 9012 Name: Asha Devi")
        upload = client.post(
            "/vault/upload",
            headers=headers,
            files={"file": ("aadhaar.pdf", pdf, "application/pdf")},
            data={"category_override": "aadhaar"},
        )
        assert upload.status_code == 200
        body = upload.json()
        document = body["document"]
        assert document["category"] == "aadhaar"
        assert document["document_id_number"] == "XXXX XXXX 9012"
        assert document["owner_name"] == "Asha Devi"
        assert document["confidence"] == 0.95
        assert document["review_required"] is False
        assert body["ocr_info"]["ocr_error"] is None
        assert "PDF text extraction" in body["ocr_info"]["method"]

        vault = client.get("/vault", headers=headers)
        assert vault.status_code == 200
        assert len(vault.json()) == 1

        detail = client.get(f"/schemes/{scheme_id}", headers=headers)
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["eligibility_code"] == "Eligible"
        assert detail_body["decision_source"] == "deterministic_rules"
        assert detail_body["missing_documents"] == []
        assert detail_body["checklist"][0]["category"] == "aadhaar"
        assert detail_body["checklist"][0]["status"] == "Verified"

        saved = client.post(
            "/schemes/status",
            headers=headers,
            json={"scheme_id": scheme_id, "status": "saved"},
        )
        assert saved.status_code == 200
        assert saved.json()["missing_documents"] == []
    finally:
        app.dependency_overrides.clear()
        reset_ai_client()
        engine.dispose()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_chat_surfaces_live_ai_failure_instead_of_silent_fallback(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'fallback.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemma")
    monkeypatch.setattr(settings, "GEMMA_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setattr(settings, "GEMMA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMMA_MODEL", "google/gemma-4-12B-it")
    monkeypatch.setattr(settings, "AI_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 0)
    reset_ai_client()
    monkeypatch.setattr(chat_routes, "orchestrator", MultiAgentOrchestrator())

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        guest = client.post("/auth/guest")
        assert guest.status_code == 200
        headers = {"Authorization": f"Bearer {guest.json()['access_token']}"}

        response = client.post(
            "/chat/message",
            headers=headers,
            json={
                "message": "I am a farmer from Bihar earning 2 lakh per year.",
                "language": "en",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ai"]["mode"] == "live"
        assert body["ai_fallback_notes"]
        assert "Live AI was unavailable" in body["assistant_reply"]
    finally:
        app.dependency_overrides.clear()
        reset_ai_client()
        engine.dispose()

