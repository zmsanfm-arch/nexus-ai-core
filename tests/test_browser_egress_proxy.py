import asyncio
import socket

import pytest

from app.services.browser_egress_proxy import (
    EgressProxy,
    host_allowed,
    load_allowlist,
    resolve_public,
)


def test_egress_allowlist_is_strict_and_supports_subdomains():
    allowed = load_allowlist("example.com,shop.example.net")
    assert host_allowed("example.com", allowed)
    assert host_allowed("www.example.com", allowed)
    assert not host_allowed("evil-example.com", allowed)
    assert not host_allowed("example.net", allowed)


@pytest.mark.parametrize("value", ["", ",", "example.com,,example.net", "https://example.com", "bad..domain"])
def test_egress_allowlist_rejects_invalid_entries(value):
    with pytest.raises(ValueError):
        load_allowlist(value)


def test_egress_proxy_rejects_dns_answers_with_private_ip(monkeypatch):
    async def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    async def run():
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(ValueError, match="non-public"):
            await resolve_public("attacker.example")
    asyncio.run(run())


def test_egress_proxy_accepts_only_configured_domain_suffixes():
    proxy = EgressProxy(frozenset({"example.com"}))
    assert proxy.allowed_domains == frozenset({"example.com"})
