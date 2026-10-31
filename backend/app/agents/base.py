import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional, Type

from pydantic import BaseModel

from app.core.config import settings
from app.services.privacy import is_private_endpoint

logger = logging.getLogger("saarthi.agents")


class AIProviderError(RuntimeError):
    """Raised when the configured AI provider cannot serve a request."""


class AIConfigurationError(AIProviderError):
    """Raised when the selected provider is missing required configuration."""


@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    transport: str
    is_mock: bool = False
    latency_ms: int | None = None


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response, tolerating code fences."""
    if not text:
        raise ValueError("Empty AI response")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        value = json.loads(cleaned[start : end + 1])
        if isinstance(value, dict):
            return value
    raise ValueError("AI response did not contain a JSON object")


def _provider_status_code(exc: Exception) -> int | None:
    for attribute in ("status_code", "code"):
        value = getattr(exc, attribute, None)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _schema_parameter_rejected(exc: Exception, parameter: str) -> bool:
    """True only when an endpoint explicitly rejects a response-schema option.

    Rate limits, timeouts, authentication failures and server errors must never
    trigger a silent retry without the schema.
    """
    if _provider_status_code(exc) not in {400, 422}:
        return False
    message = str(exc).lower()
    markers = (
        parameter.lower(),
        "response_format",
        "response_mime_type",
        "response_schema",
        "schema",
        "not supported",
        "unsupported",
        "unknown field",
    )
    return any(marker in message for marker in markers)


def _genai_http_options():
    """Apply the shared timeout/retry policy to Gemini-hosted models."""
    from google.genai import types

    return types.HttpOptions(
        timeout=max(1, int(settings.AI_TIMEOUT_SECONDS * 1000)),
        retryOptions=types.HttpRetryOptions(
            attempts=max(1, settings.AI_MAX_RETRIES + 1),
            httpStatusCodes=[429, 500, 502, 503, 504],
        ),
    )


class AIClient:
    """Single provider abstraction used by every agent.

    The selected provider is explicit. A failure in the selected provider is
    surfaced to the caller; it is never silently replaced by a different model.
    Deterministic local fallbacks are labelled by the calling agent.
    """

    def __init__(self) -> None:
        self.requested_provider = (settings.AI_PROVIDER or "mock").strip().lower()
        self.provider = self.requested_provider
        self.model = ""
        self.transport = "none"
        self.ready = False
        self.error: str | None = None
        self._genai_client = None
        self._openai_client = None
        self._configure()

    def _configure(self) -> None:
        provider = self.requested_provider
        if provider == "mock":
            self.provider = "mock"
            self.model = "deterministic-rules"
            self.transport = "local"
            self.ready = True
            return

        if provider == "gemma":
            if settings.GEMMA_BASE_URL:
                try:
                    from openai import OpenAI

                    self._openai_client = OpenAI(
                        api_key=settings.GEMMA_API_KEY or "local-gemma",
                        base_url=settings.GEMMA_BASE_URL.rstrip("/"),
                        timeout=settings.AI_TIMEOUT_SECONDS,
                        max_retries=settings.AI_MAX_RETRIES,
                    )
                    self.model = settings.GEMMA_MODEL
                    self.transport = "openai-compatible"
                    self.ready = True
                except Exception as exc:  # pragma: no cover - depends on environment
                    self.error = f"Could not initialise Gemma endpoint client: {exc}"
                return

            if settings.GEMINI_API_KEY:
                try:
                    from google import genai

                    self._genai_client = genai.Client(
                        api_key=settings.GEMINI_API_KEY,
                        http_options=_genai_http_options(),
                    )
                    self.model = settings.GEMMA_GEMINI_MODEL
                    self.transport = "google-genai"
                    self.ready = True
                except Exception as exc:  # pragma: no cover
                    self.error = f"Could not initialise Gemini-hosted Gemma client: {exc}"
                return

            self.error = (
                "AI_PROVIDER=gemma requires GEMMA_BASE_URL (self-hosted vLLM/Ollama) "
                "or GEMINI_API_KEY (Gemini API hosted Gemma)."
            )
            return

        if provider == "gemini":
            if not settings.GEMINI_API_KEY:
                self.error = "AI_PROVIDER=gemini requires GEMINI_API_KEY."
                return
            try:
                from google import genai

                self._genai_client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=_genai_http_options(),
                )
                self.model = settings.GEMINI_MODEL
                self.transport = "google-genai"
                self.ready = True
            except Exception as exc:  # pragma: no cover
                self.error = f"Could not initialise Gemini client: {exc}"
            return

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                self.error = "AI_PROVIDER=openai requires OPENAI_API_KEY."
                return
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=settings.AI_TIMEOUT_SECONDS,
                    max_retries=settings.AI_MAX_RETRIES,
                )
                self.model = settings.OPENAI_MODEL
                self.transport = "openai"
                self.ready = True
            except Exception as exc:  # pragma: no cover
                self.error = f"Could not initialise OpenAI client: {exc}"
            return

        self.error = (
            f"Unsupported AI_PROVIDER='{provider}'. Use gemma, gemini, openai, or mock."
        )

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    @property
    def is_gemma(self) -> bool:
        return self.provider == "gemma" and self.ready

    @property
    def gemma_is_private(self) -> bool:
        return (
            self.is_gemma
            and self.transport == "openai-compatible"
            and is_private_endpoint(settings.GEMMA_BASE_URL)
        )

    def status(self) -> dict[str, Any]:
        if self.ready and self.is_mock:
            mode = "mock"
            privacy = "No citizen data leaves this machine. Responses are rule-based."
        elif self.ready:
            mode = "live"
            if self.is_gemma:
                privacy = (
                    "Gemma 4 is self-hosted on a private endpoint."
                    if self.gemma_is_private
                    else "Gemma 4 is served by a hosted endpoint. Document bytes are blocked unless explicitly enabled."
                )
            else:
                privacy = (
                    "This is an alternative provider, not Gemma. Only redacted text is sent."
                )
        else:
            mode = "unconfigured"
            privacy = "No live AI provider is available. Deterministic fallbacks are labelled."

        return {
            "requested_provider": self.requested_provider,
            "active_provider": self.provider,
            "model": self.model,
            "transport": self.transport,
            "mode": mode,
            "ready": self.ready,
            "is_gemma": self.is_gemma,
            "error": self.error,
            "privacy": privacy,
            "gemma_base_url_configured": bool(settings.GEMMA_BASE_URL),
            "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
            "gemma_mode": (
                "self_hosted"
                if self.is_gemma and self.transport == "openai-compatible"
                else "gemini_api"
                if self.is_gemma and self.transport == "google-genai"
                else None
            ),
            "gemma_gemini_model": (
                settings.GEMMA_GEMINI_MODEL
                if self.is_gemma and self.transport == "google-genai"
                else None
            ),
            "document_bytes_allowed": bool(settings.GEMMA_ALLOW_DOCUMENT_BYTES),
            "timeout_seconds": settings.AI_TIMEOUT_SECONDS,
            "max_retries": settings.AI_MAX_RETRIES,
        }

    def _schema_instruction(self, response_schema: Type[BaseModel]) -> str:
        return (
            "\nReturn only a JSON object matching this schema:\n"
            f"{json.dumps(response_schema.model_json_schema())}"
        )

    def complete(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> AIResult:
        if not self.ready:
            raise AIConfigurationError(self.error or "AI provider is not configured.")
        if self.is_mock:
            raise AIProviderError(
                "AI_PROVIDER=mock. This agent must use its labelled deterministic fallback."
            )

        started = time.perf_counter()
        if self._openai_client is not None:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            user_prompt = prompt
            kwargs: dict[str, Any] = {}
            if response_schema:
                user_prompt += self._schema_instruction(response_schema)
                kwargs["response_format"] = {"type": "json_object"}
            messages.append({"role": "user", "content": user_prompt})
            try:
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    **kwargs,
                )
            except Exception as exc:
                # Some OpenAI-compatible Gemma servers reject response_format.
                if not response_schema or not _schema_parameter_rejected(
                    exc, "response_format"
                ):
                    raise
                kwargs.pop("response_format", None)
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    **kwargs,
                )
            text = response.choices[0].message.content or ""
            return AIResult(
                text=text,
                provider=self.provider,
                model=self.model,
                transport=self.transport,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        if self._genai_client is not None:
            from google.genai import types

            config_args: dict[str, Any] = {}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            if response_schema:
                config_args["response_mime_type"] = "application/json"
                config_args["response_schema"] = response_schema
            try:
                response = self._genai_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args),
                )
            except Exception as exc:
                # Some hosted Gemma deployments do not accept response_schema.
                if not response_schema or not _schema_parameter_rejected(
                    exc, "response_schema"
                ):
                    raise
                config_args.pop("response_schema", None)
                config_args.pop("response_mime_type", None)
                prompt = prompt + self._schema_instruction(response_schema)
                response = self._genai_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args),
                )
            return AIResult(
                text=response.text or "",
                provider=self.provider,
                model=self.model,
                transport=self.transport,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        raise AIProviderError("No AI transport was initialised.")

    def vision(
        self,
        file_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> AIResult:
        if not self.ready:
            raise AIConfigurationError(self.error or "AI provider is not configured.")
        if self.is_mock:
            raise AIProviderError("AI_PROVIDER=mock cannot perform vision extraction.")

        started = time.perf_counter()
        if self._openai_client is not None:
            encoded = base64.b64encode(file_bytes).decode("ascii")
            data_url = f"data:{mime_type};base64,{encoded}"
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            user_text = prompt
            kwargs: dict[str, Any] = {}
            if response_schema:
                user_text += self._schema_instruction(response_schema)
                kwargs["response_format"] = {"type": "json_object"}
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            )
            try:
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1200,
                    **kwargs,
                )
            except Exception as exc:
                # Some OpenAI-compatible Gemma servers reject response_format.
                if not response_schema or not _schema_parameter_rejected(
                    exc, "response_format"
                ):
                    raise
                kwargs.pop("response_format", None)
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1200,
                    **kwargs,
                )
            return AIResult(
                text=response.choices[0].message.content or "",
                provider=self.provider,
                model=self.model,
                transport=self.transport,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        if self._genai_client is not None:
            from google.genai import types

            config_args: dict[str, Any] = {}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            if response_schema:
                config_args["response_mime_type"] = "application/json"
                config_args["response_schema"] = response_schema
            content_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            try:
                response = self._genai_client.models.generate_content(
                    model=self.model,
                    contents=[prompt, content_part],
                    config=types.GenerateContentConfig(**config_args),
                )
            except Exception as exc:
                if not response_schema or not _schema_parameter_rejected(
                    exc, "response_schema"
                ):
                    raise
                config_args.pop("response_schema", None)
                config_args.pop("response_mime_type", None)
                response = self._genai_client.models.generate_content(
                    model=self.model,
                    contents=[prompt + self._schema_instruction(response_schema), content_part],
                    config=types.GenerateContentConfig(**config_args),
                )
            return AIResult(
                text=response.text or "",
                provider=self.provider,
                model=self.model,
                transport=self.transport,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        raise AIProviderError("No AI transport was initialised.")


_ai_client: AIClient | None = None


def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client


def reset_ai_client() -> None:
    """Reset the cached provider, primarily for tests and config reloads."""
    global _ai_client
    _ai_client = None


class BaseAgent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.ai = get_ai_client()
        self.use_real_ai = self.ai.ready and not self.ai.is_mock
        self.last_fallback: str | None = None
        logger.info(
            "Agent %s using provider=%s model=%s ready=%s",
            self.name,
            self.ai.provider,
            self.ai.model,
            self.ai.ready,
        )

    def run_llm(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            result = self.ai.complete(prompt, system_instruction, response_schema)
        except Exception as exc:
            self.last_fallback = f"{self.name}: {exc}"
            logger.warning("Live AI call failed for %s: %s", self.name, exc)
            raise
        self.last_fallback = None
        return result.text

    def run_vision(
        self,
        file_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            result = self.ai.vision(
                file_bytes, mime_type, prompt, system_instruction, response_schema
            )
        except Exception as exc:
            self.last_fallback = f"{self.name}: {exc}"
            logger.warning("Live AI vision call failed for %s: %s", self.name, exc)
            raise
        self.last_fallback = None
        return result.text

    def mock_response(self, fallback_data: Any) -> Any:
        return fallback_data

    def provider_status(self) -> dict[str, Any]:
        return self.ai.status()
