import httpx
import pytest

from app.services.model_router import (
    ModelConfig,
    ModelNotConfigured,
    ModelProviderError,
    ModelRouter,
)


def test_missing_model_configuration_fails_closed():
    with pytest.raises(ModelNotConfigured):
        ModelRouter().generate("system", "hello")


def test_openai_compatible_request_uses_server_side_bearer_key():
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert request.read()
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "  Ready.  "}}]
        })

    config = ModelConfig(
        provider="test",
        base_url="https://model.example/v1",
        model_name="test-model",
        api_key="test-secret",
    )
    router = ModelRouter(config, transport=httpx.MockTransport(handler))
    assert router.generate("system", "hello") == "Ready."


def test_provider_failure_does_not_leak_response_body():
    def handler(request):
        return httpx.Response(401, text="secret-token-invalid")

    config = ModelConfig(
        provider="test",
        base_url="https://model.example/v1",
        model_name="test-model",
        api_key="test-secret",
    )
    router = ModelRouter(config, transport=httpx.MockTransport(handler))
    with pytest.raises(ModelProviderError) as error:
        router.generate("system", "hello")
    assert "secret-token-invalid" not in str(error.value)
    assert "test-secret" not in str(error.value)
