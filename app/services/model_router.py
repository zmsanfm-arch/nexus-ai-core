import os
from dataclasses import dataclass

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
        return cls(ModelConfig(
            provider=os.getenv("MODEL_PROVIDER", "openai-compatible"),
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "45")),
        ))

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
            # Do not expose provider response bodies, credentials, or request headers.
            raise ModelProviderError(
                f"Model provider request failed ({type(exc).__name__})."
            ) from None
