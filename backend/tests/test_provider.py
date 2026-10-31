import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.agents.base import (
    AIClient,
    AIResult,
    BaseAgent,
    _genai_http_options,
    _schema_parameter_rejected,
    reset_ai_client,
)
from app.core.config import Settings, settings
from app.services import ocr
from app.services.ocr import normalize_category, run_multimodal_ocr


def test_normalize_category_aliases():
    assert normalize_category("voter") == "voter_id"
    assert normalize_category("business") == "business_proof"
    assert normalize_category("vendor") == "vendor_cert"
    assert normalize_category("AADHAAR") == "aadhaar"
    assert normalize_category("not-a-category") == "other"
    assert normalize_category(None) == "other"


class _ProviderHTTPError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


def test_schema_fallback_only_for_explicit_schema_rejection():
    assert _schema_parameter_rejected(
        _ProviderHTTPError(400, "response_format unsupported"), "response_format"
    )
    assert _schema_parameter_rejected(
        _ProviderHTTPError(422, "unknown field response_schema"), "response_schema"
    )
    assert not _schema_parameter_rejected(
        _ProviderHTTPError(429, "rate limit exceeded"), "response_format"
    )
    assert not _schema_parameter_rejected(
        _ProviderHTTPError(500, "response_format unsupported"), "response_format"
    )
    assert not _schema_parameter_rejected(
        _ProviderHTTPError(401, "response_format unsupported"), "response_format"
    )
    assert not _schema_parameter_rejected(
        _ProviderHTTPError(400, "bad image payload"), "response_format"
    )


def test_genai_http_options_use_shared_timeout_and_retry(monkeypatch):
    monkeypatch.setattr(settings, "AI_TIMEOUT_SECONDS", 12)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 2)

    options = _genai_http_options()

    assert options.timeout == 12000
    assert options.retry_options is not None
    assert options.retry_options.attempts == 3
    assert options.retry_options.http_status_codes == [429, 500, 502, 503, 504]


def test_hosted_gemma_status_uses_gemini_api_configuration(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemma")
    monkeypatch.setattr(settings, "GEMMA_BASE_URL", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMMA_GEMINI_MODEL", "gemma-4-31b-it")
    monkeypatch.setattr(settings, "AI_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 1)
    try:
        client = AIClient()
        assert client.ready is True
        assert client.transport == "google-genai"
        assert client.model == "gemma-4-31b-it"

        status = client.status()
        assert status["gemma_mode"] == "gemini_api"
        assert status["gemma_gemini_model"] == "gemma-4-31b-it"
        assert status["timeout_seconds"] == 30
        assert status["max_retries"] == 1
    finally:
        reset_ai_client()


def test_default_env_file_is_backend_env():
    configured = Path(Settings.model_config["env_file"])
    assert configured.name == ".env"
    assert configured.parent.name == "backend"


def test_settings_load_values_from_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMMA_GEMINI_MODEL=gemma-4-26b-a4b-it\n", encoding="utf-8")
    monkeypatch.setitem(Settings.model_config, "env_file", str(env_file))

    loaded = Settings()

    assert loaded.GEMMA_GEMINI_MODEL == "gemma-4-26b-a4b-it"


def test_base_agent_records_and_clears_live_ai_fallback():
    class FailingAI:
        def complete(self, *args, **kwargs):
            raise RuntimeError("429 rate limit exceeded")

    class WorkingAI:
        def complete(self, *args, **kwargs):
            return AIResult(text="ok", provider="gemma", model="test", transport="test")

    agent = BaseAgent("Test Agent", "Test")
    agent.ai = FailingAI()
    with pytest.raises(RuntimeError):
        agent.run_llm("hello")
    assert "429 rate limit exceeded" in (agent.last_fallback or "")

    agent.ai = WorkingAI()
    assert agent.run_llm("hello") == "ok"
    assert agent.last_fallback is None


class _FakeGemma:
    provider = "gemma"
    model = "google/gemma-4-12B-it"
    ready = True
    is_mock = False
    is_gemma = True
    gemma_is_private = True
    error = None

    def __init__(self):
        self.complete_calls = []
        self.vision_calls = []

    def complete(self, prompt, system_instruction=None, response_schema=None):
        self.complete_calls.append(prompt)
        return AIResult(
            text=json.dumps(
                {
                    "category": "aadhaar",
                    "document_id_number": "1234 5678 9012",
                    "owner_name": "Asha Devi",
                    "expiry_date_str": None,
                    "is_valid": True,
                    "confidence": 0.92,
                    "review_required": False,
                    "summary": "Aadhaar card for Asha Devi.",
                }
            ),
            provider=self.provider,
            model=self.model,
            transport="test",
        )

    def vision(self, **kwargs):
        self.vision_calls.append(kwargs)
        raise AssertionError("PDFs must use text extraction, not vision")


def test_pdf_uses_redacted_text_not_vision(monkeypatch):
    fake = _FakeGemma()
    monkeypatch.setattr(ocr, "get_ai_client", lambda: fake)
    monkeypatch.setattr(
        ocr,
        "extract_text_from_pdf",
        lambda _: "Government of India Aadhaar 1234 5678 9012 Name: Asha Devi",
    )

    result = run_multimodal_ocr(b"%PDF-1.4", "pdf", "aadhaar.pdf")

    assert result["category"] == "aadhaar"
    assert result["document_id_number"] == "XXXX XXXX 9012"
    assert len(fake.complete_calls) == 1
    assert fake.vision_calls == []
    assert "1234 5678 9012" not in fake.complete_calls[0]


class _ChatHandler(BaseHTTPRequestHandler):
    reject_schema = False
    rate_limit = False
    request_count = 0

    def do_POST(self):
        _ChatHandler.request_count += 1
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if _ChatHandler.rate_limit:
            data = b'{"error":{"message":"rate limit exceeded"}}'
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(data)
            return
        if _ChatHandler.reject_schema and body.get("response_format"):
            data = b'{"error":{"message":"response_format unsupported"}}'
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        payload = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": body.get("model", "gemma"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": '{"ok": true}'},
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


@pytest.fixture(name="gemma_server")
def gemma_server_fixture():
    server = HTTPServer(("127.0.0.1", 0), _ChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        _ChatHandler.reject_schema = False
        _ChatHandler.rate_limit = False
        _ChatHandler.request_count = 0


def test_openai_compatible_gemma_falls_back_when_schema_rejected(
    monkeypatch, gemma_server
):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemma")
    monkeypatch.setattr(settings, "GEMMA_BASE_URL", gemma_server)
    monkeypatch.setattr(settings, "GEMMA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMMA_MODEL", "google/gemma-4-12B-it")
    _ChatHandler.reject_schema = True

    class Schema(BaseModel):
        ok: bool

    try:
        client = AIClient()
        assert client.ready is True
        assert client.is_gemma is True
        assert client.transport == "openai-compatible"

        result = client.complete("Return ok.", response_schema=Schema)
        assert json.loads(result.text) == {"ok": True}

        status = client.status()
        assert status["is_gemma"] is True
        assert status["gemma_base_url_configured"] is True
    finally:
        reset_ai_client()
        _ChatHandler.reject_schema = False


def test_openai_compatible_rate_limit_is_not_retried_as_schema_fallback(
    monkeypatch, gemma_server
):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemma")
    monkeypatch.setattr(settings, "GEMMA_BASE_URL", gemma_server)
    monkeypatch.setattr(settings, "GEMMA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMMA_MODEL", "google/gemma-4-12B-it")
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 0)
    _ChatHandler.rate_limit = True
    _ChatHandler.request_count = 0

    class Schema(BaseModel):
        ok: bool

    try:
        client = AIClient()
        with pytest.raises(Exception) as excinfo:
            client.complete("Return ok.", response_schema=Schema)
        assert "429" in str(excinfo.value) or "rate" in str(excinfo.value).lower()
        assert _ChatHandler.request_count == 1
    finally:
        reset_ai_client()
        _ChatHandler.rate_limit = False
        _ChatHandler.request_count = 0
