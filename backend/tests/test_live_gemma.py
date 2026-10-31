import os
import struct
import zlib

import pytest
from pydantic import BaseModel

from app.agents.base import AIClient, extract_json, reset_ai_client
from app.core.config import settings

RUN_LIVE = os.getenv("RUN_LIVE_GEMMA") == "1"
CONFIGURED = bool(settings.GEMMA_BASE_URL or settings.GEMINI_API_KEY)

pytestmark = [
    pytest.mark.skipif(
        not RUN_LIVE,
        reason="Set RUN_LIVE_GEMMA=1 to run live Gemma 4 inference tests.",
    ),
    pytest.mark.skipif(
        not CONFIGURED,
        reason="Set GEMMA_BASE_URL or GEMINI_API_KEY to run live Gemma 4 tests.",
    ),
]


class LiveAnswer(BaseModel):
    status: str
    language: str


class LiveColor(BaseModel):
    dominant_color: str


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


@pytest.fixture(scope="module")
def gemma_client():
    saved = {
        name: getattr(settings, name)
        for name in (
            "AI_PROVIDER",
            "GEMMA_BASE_URL",
            "GEMMA_API_KEY",
            "GEMMA_MODEL",
            "GEMINI_API_KEY",
            "GEMMA_GEMINI_MODEL",
        )
    }
    settings.AI_PROVIDER = "gemma"
    if settings.GEMMA_BASE_URL:
        settings.GEMMA_API_KEY = settings.GEMMA_API_KEY or "local-gemma"
        settings.GEMMA_MODEL = settings.GEMMA_MODEL or "google/gemma-4-12B-it"
    reset_ai_client()

    client = AIClient()
    assert client.ready, client.error
    assert client.is_gemma is True
    try:
        yield client
    finally:
        reset_ai_client()
        for name, value in saved.items():
            setattr(settings, name, value)


def test_live_gemma_text(gemma_client):
    result = gemma_client.complete(
        "Reply with exactly SAARTHI_GEMMA_OK and nothing else."
    )

    assert result.is_mock is False
    assert "SAARTHI_GEMMA_OK" in result.text


def test_live_gemma_structured_json(gemma_client):
    result = gemma_client.complete(
        "Return a JSON object with status set to 'ok' and language set to 'en'.",
        response_schema=LiveAnswer,
    )

    payload = extract_json(result.text)
    assert payload["status"].lower() == "ok"
    assert payload["language"].lower().startswith("en")


def test_live_gemma_vision(gemma_client):
    png = _solid_png(64, 64, (220, 20, 20))

    result = gemma_client.vision(
        png,
        "image/png",
        "Return a JSON object with the dominant color as an English color name.",
        response_schema=LiveColor,
    )

    payload = extract_json(result.text)
    assert "red" in payload["dominant_color"].lower()


def test_live_gemma_multilingual(gemma_client):
    hindi = gemma_client.complete(
        "केवल हिंदी में उत्तर दें: भारत की राजधानी क्या है?"
    )
    assert any("\u0900" <= char <= "\u097F" for char in hindi.text)

    english = gemma_client.complete(
        "Answer in English: What is the capital of India?"
    )
    assert "delhi" in english.text.lower()
