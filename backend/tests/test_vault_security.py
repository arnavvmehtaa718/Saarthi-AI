from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Document, User


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_document_download_requires_auth_and_owner(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    stored_file = tmp_path / "aadhaar.png"
    stored_file.write_bytes(b"\x89PNG\r\n\x1a\nstored")
    outside_file = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside_file.write_bytes(b"outside")

    with Session(engine) as session:
        owner = User(email="owner@example.com", hashed_password=get_password_hash("pw"))
        other = User(email="other@example.com", hashed_password=get_password_hash("pw"))
        session.add(owner)
        session.add(other)
        session.commit()
        session.refresh(owner)
        session.refresh(other)

        doc = Document(
            user_id=owner.id,
            file_name="aadhaar.png",
            file_path=str(stored_file),
            file_type="png",
            category="aadhaar",
            file_hash="hash-1",
        )
        outside_doc = Document(
            user_id=owner.id,
            file_name="outside.txt",
            file_path=str(outside_file),
            file_type="txt",
            category="other",
            file_hash="hash-2",
        )
        session.add(doc)
        session.add(outside_doc)
        session.commit()
        session.refresh(doc)
        session.refresh(outside_doc)
        doc_id = doc.id
        outside_doc_id = outside_doc.id
        owner_token = create_access_token(subject=owner.id)
        other_token = create_access_token(subject=other.id)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        unauthenticated = client.get(f"/vault/{doc_id}/file")
        assert unauthenticated.status_code == 401

        other_user = client.get(
            f"/vault/{doc_id}/file", headers=_headers(other_token)
        )
        assert other_user.status_code == 404

        owner_response = client.get(
            f"/vault/{doc_id}/file", headers=_headers(owner_token)
        )
        assert owner_response.status_code == 200
        assert owner_response.content == stored_file.read_bytes()
        assert owner_response.headers["cache-control"] == "private, no-store"
        assert owner_response.headers["x-content-type-options"] == "nosniff"

        escaped_path = client.get(
            f"/vault/{outside_doc_id}/file", headers=_headers(owner_token)
        )
        assert escaped_path.status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        outside_file.unlink(missing_ok=True)
