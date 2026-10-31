import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Saarthi AI - Government Benefits Navigator"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./saarthi.db")

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "dev-only-secret-key-change-before-deploying-please"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://saarthi-ai-dev.vercel.app",
    )

    # AI provider selection. Supported: gemma | gemini | openai | mock
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "90"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "1"))

    # Gemma 4. Verified open-weight identifiers:
    # google/gemma-4-E2B-it, google/gemma-4-E4B-it, google/gemma-4-12B-it,
    # google/gemma-4-26B-A4B-it, google/gemma-4-31B-it.
    # Use an OpenAI-compatible vLLM/Ollama endpoint for self-hosted inference.
    GEMMA_MODEL: str = os.getenv("GEMMA_MODEL", "google/gemma-4-12B-it")
    GEMMA_BASE_URL: str | None = os.getenv("GEMMA_BASE_URL")
    GEMMA_API_KEY: str | None = os.getenv("GEMMA_API_KEY")
    # Gemini API hosted Gemma identifier (used only when no GEMMA_BASE_URL is set).
    GEMMA_GEMINI_MODEL: str = os.getenv("GEMMA_GEMINI_MODEL", "gemma-4-31b-it")
    # Raw identity documents must only be sent to a self-hosted endpoint unless
    # an operator explicitly accepts the privacy trade-off.
    GEMMA_ALLOW_DOCUMENT_BYTES: bool = (
        os.getenv("GEMMA_ALLOW_DOCUMENT_BYTES", "false").lower() == "true"
    )

    # Optional alternative providers
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Document handling
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    ALLOWED_UPLOAD_EXTENSIONS: str = os.getenv(
        "ALLOWED_UPLOAD_EXTENSIONS", "pdf,png,jpg,jpeg"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_upload_extensions(self) -> set[str]:
        return {
            ext.strip().lower().lstrip(".")
            for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")
            if ext.strip()
        }

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}


settings = Settings()
