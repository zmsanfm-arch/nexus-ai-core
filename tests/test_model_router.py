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
        return httpx.Response(200, json={"choices": [{"message": {"content": "  Ready.  "}}]})

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


@pytest.mark.parametrize(
    "base_url",
    [
        "http://model.example/v1",
        "https://user:password@model.example/v1",
        "https://model.example/v1?token=unsafe",
        "https://model.example:99999/v1",
    ],
)
def test_unsafe_provider_urls_are_rejected(base_url):
    config = ModelConfig(
        provider="test",
        base_url=base_url,
        model_name="test-model",
        api_key="test-secret",
    )
    with pytest.raises(ValueError):
        ModelRouter(config)


@pytest.mark.parametrize("timeout", [0, -1, 121, float("inf"), float("nan")])
def test_invalid_provider_timeouts_are_rejected(timeout):
    config = ModelConfig(
        provider="test",
        base_url="https://model.example/v1",
        model_name="test-model",
        api_key="test-secret",
        timeout_seconds=timeout,
    )
    with pytest.raises(ValueError, match="between 1 and 120"):
        ModelRouter(config)


def test_local_http_provider_is_allowed():
    config = ModelConfig(
        provider="test",
        base_url="http://localhost:8080/v1",
        model_name="test-model",
        api_key="test-secret",
    )
    router = ModelRouter(
        config,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"choices": [{"message": {"content": "Local ready"}}]}
            )
        ),
    )
    assert router.generate("system", "hello") == "Local ready"


def test_provider_redirect_is_not_followed():
    config = ModelConfig(
        provider="test",
        base_url="https://model.example/v1",
        model_name="test-model",
        api_key="test-secret",
    )
    router = ModelRouter(
        config,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302, headers={"Location": "https://other.example/collect"}
            )
        ),
    )
    with pytest.raises(ModelProviderError):
        router.generate("system", "hello")
