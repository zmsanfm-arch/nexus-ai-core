import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    model_name: str
    api_key: str
    timeout_seconds: float = 45.0


class ModelNotConfigured(RuntimeError):
    pass


class ModelProviderError(RuntimeError):
    pass


class ModelRouter:
    """OpenAI-compatible chat-completions adapter; credentials stay server-side."""

    def __init__(self, primary: ModelConfig | None = None, transport=None):
        self.primary = primary
        self.transport = transport

    @classmethod
    def from_env(cls):
        api_key = os.getenv("MODEL_API_KEY", "").strip()
        base_url = os.getenv("MODEL_BASE_URL", "").strip().rstrip("/")
        model_name = os.getenv("MODEL_NAME", "").strip()
        if not (api_key and base_url and model_name):
            return cls()
        try:
            timeout_seconds = float(os.getenv("MODEL_TIMEOUT_SECONDS", "45"))
        except ValueError:
            raise ModelProviderError("MODEL_TIMEOUT_SECONDS must be a number.") from None
        return cls(ModelConfig(
            provider=os.getenv("MODEL_PROVIDER", "openai-compatible"),
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        ))

    def select(self, task_type: str) -> ModelConfig | None:
        return self.primary

    @staticmethod
    def _validate_config(config: ModelConfig) -> None:
        try:
            parsed = urlsplit(config.base_url)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError:
            raise ModelProviderError("Model provider URL is invalid.") from None

        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if (
            not hostname
            or parsed.scheme not in ({"https", "http"} if hostname in local_hosts else {"https"})
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ModelProviderError(
                "Model provider URL must use HTTPS; HTTP is allowed only for localhost."
            )
        if not math.isfinite(config.timeout_seconds) or not 1 <= config.timeout_seconds <= 120:
            raise ModelProviderError(
                "MODEL_TIMEOUT_SECONDS must be between 1 and 120 seconds."
            )
        if not config.api_key or not config.model_name:
            raise ModelProviderError("Model provider credentials or model name are missing.")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        config = self.select("general")
        if config is None:
            raise ModelNotConfigured(
                "Model is not configured. Set MODEL_BASE_URL, MODEL_NAME and MODEL_API_KEY."
            )
        self._validate_config(config)
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        try:
            with httpx.Client(
                timeout=config.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    f"{config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ModelProviderError("Provider returned an empty response.")
                return content.strip()
        except ModelProviderError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            # Do not expose provider response bodies, credentials, or request headers.
            raise ModelProviderError(
                f"Model provider request failed ({type(exc).__name__})."
            ) from None
