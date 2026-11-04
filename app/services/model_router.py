import os
from dataclasses import dataclass
from urllib.parse import urlparse

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


def _validate_model_config(config: ModelConfig) -> None:
    parsed = urlparse(config.base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise ValueError("Model provider URL must use HTTPS (HTTP is allowed only for localhost).")
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Model provider URL is invalid.")
    if not config.api_key.strip() or not config.model_name.strip():
        raise ValueError("Model API key and model name are required.")
    if not 0.1 <= config.timeout_seconds <= 120:
        raise ValueError("Model timeout must be between 0.1 and 120 seconds.")


class ModelRouter:
    """OpenAI-compatible adapter; credentials remain server-side and require TLS."""

    def __init__(self, primary: ModelConfig | None = None, transport=None):
        self.primary = primary
        self.transport = transport
        if primary is not None:
            _validate_model_config(primary)

    @classmethod
    def from_env(cls):
        api_key = os.getenv("MODEL_API_KEY", "").strip()
        base_url = os.getenv("MODEL_BASE_URL", "").strip().rstrip("/")
        model_name = os.getenv("MODEL_NAME", "").strip()
        if not (api_key and base_url and model_name):
            return cls()
        try:
            timeout_seconds = float(os.getenv("MODEL_TIMEOUT_SECONDS", "45"))
            config = ModelConfig(
                provider=os.getenv("MODEL_PROVIDER", "openai-compatible"),
                base_url=base_url,
                model_name=model_name,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            )
            return cls(config)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid model provider configuration: {exc}") from None

    def select(self, task_type: str) -> ModelConfig | None:
        return self.primary

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        config = self.select("general")
        if config is None:
            raise ModelNotConfigured(
                "Model is not configured. Set MODEL_BASE_URL, MODEL_NAME and MODEL_API_KEY."
            )
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
            raise ModelProviderError(
                f"Model provider request failed ({type(exc).__name__})."
            ) from None
