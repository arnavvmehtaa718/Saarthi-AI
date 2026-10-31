import re
from urllib.parse import urlparse


AADHAAR_RE = re.compile(r"\b(\d{4})\s?(\d{4})\s?(\d{4})\b")
PAN_RE = re.compile(r"\b([A-Za-z]{5})(\d{4})([A-Za-z])\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")


def mask_aadhaar(value: str) -> str:
    """Mask an Aadhaar number, retaining only the last four digits."""
    compact = re.sub(r"\s", "", value)
    if re.fullmatch(r"\d{12}", compact):
        return f"XXXX XXXX {compact[-4:]}"
    return value


def mask_pan(value: str) -> str:
    """Mask PAN digits while retaining the alphabetic structure."""
    match = PAN_RE.fullmatch(value.strip())
    if match:
        return f"{match.group(1).upper()}****{match.group(3).upper()}"
    return value


def mask_sensitive_id(value: str | None, category: str | None = None) -> str | None:
    if not value:
        return value
    category = (category or "").lower()
    if category == "aadhaar":
        return mask_aadhaar(value)
    if category == "pan":
        return mask_pan(value)
    if AADHAAR_RE.fullmatch(value.replace(" ", "")):
        return mask_aadhaar(value)
    if PAN_RE.fullmatch(value.strip()):
        return mask_pan(value)
    return value


def redact_pii(text: str) -> str:
    """Redact identity numbers before text is sent to any external AI service."""
    if not text:
        return text
    redacted = AADHAAR_RE.sub(lambda m: f"XXXX XXXX {m.group(3)[-4:]}", text)
    redacted = PAN_RE.sub(
        lambda m: f"{m.group(1).upper()}****{m.group(3).upper()}", redacted
    )
    redacted = EMAIL_RE.sub("[email redacted]", redacted)
    redacted = PHONE_RE.sub("[phone redacted]", redacted)
    return redacted


def is_private_endpoint(url: str | None) -> bool:
    """Return True for loopback/private-network model endpoints."""
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        return True
    if host.endswith(".local") or host.endswith(".internal"):
        return True
    if host.startswith("10.") or host.startswith("192.168."):
        return True
    if host.startswith("172."):
        try:
            second = int(host.split(".")[1])
            return 16 <= second <= 31
        except (IndexError, ValueError):
            return False
    return False


def safe_display_filename(filename: str | None) -> str:
    """Keep only the base filename and remove control/path characters."""
    name = (filename or "document").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", name).strip()
    return name[:180] or "document"
