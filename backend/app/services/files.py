import os
from pathlib import Path


class UploadValidationError(ValueError):
    pass


MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def normalize_extension(filename: str | None) -> str:
    name = (filename or "").strip()
    if "." not in name:
        raise UploadValidationError("File must have a .pdf, .png, .jpg, or .jpeg extension.")
    return name.rsplit(".", 1)[-1].lower()


def detect_mime(file_bytes: bytes, extension: str) -> str:
    if extension == "pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise UploadValidationError("The uploaded file is not a valid PDF.")
        return "application/pdf"
    if extension == "png":
        if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise UploadValidationError("The uploaded file is not a valid PNG image.")
        return "image/png"
    if extension in {"jpg", "jpeg"}:
        if not file_bytes.startswith(b"\xff\xd8\xff"):
            raise UploadValidationError("The uploaded file is not a valid JPEG image.")
        return "image/jpeg"
    raise UploadValidationError("Unsupported file type.")


def validate_upload(
    filename: str | None,
    file_bytes: bytes,
    allowed_extensions: set[str],
    max_bytes: int,
) -> tuple[str, str]:
    extension = normalize_extension(filename)
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise UploadValidationError(f"Unsupported file type. Allowed: {allowed}.")
    if not file_bytes:
        raise UploadValidationError("The uploaded file is empty.")
    if len(file_bytes) > max_bytes:
        raise UploadValidationError(
            f"File is too large. Maximum size is {max_bytes // (1024 * 1024)} MB."
        )
    mime_type = detect_mime(file_bytes, extension)
    return extension, mime_type


def safe_storage_path(upload_dir: str, stored_filename: str) -> str:
    """Resolve a stored filename inside the upload directory, blocking traversal."""
    base = Path(upload_dir).resolve()
    candidate = (base / os.path.basename(stored_filename)).resolve()
    if base != candidate and base not in candidate.parents:
        raise UploadValidationError("Invalid storage path.")
    return str(candidate)
