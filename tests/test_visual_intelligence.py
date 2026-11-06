from pathlib import Path

import pytest

from app.services.visual_intelligence import (
    TenantAccessError,
    VisualInputError,
    VisualIntelligenceStore,
    canonical_instagram_url,
)


def test_canonical_instagram_post_url():
    assert canonical_instagram_url(
        "https://www.instagram.com/p/AbC_123/?igsh=tracking"
    ) == "https://www.instagram.com/p/AbC_123/"


@pytest.mark.parametrize("url", [
    "http://www.instagram.com/p/abc/",
    "https://instagram.com/accounts/login/",
    "https://evil.example/p/abc/",
    "https://user:pass@instagram.com/p/abc/",
    "https://instagram.com/p/abc/?next=https://evil.example",
])
def test_rejects_unsafe_or_non_post_urls(url):
    with pytest.raises(VisualInputError):
        canonical_instagram_url(url)


def test_capture_url_is_scoped_and_deduplicated(tmp_path):
    store = VisualIntelligenceStore(tmp_path)
    first = store.capture_url("tenant-a", "user-a", "https://instagram.com/reel/XYZ/")
    second = store.capture_url("tenant-a", "user-a", "https://www.instagram.com/reel/XYZ/")
    assert first.id == second.id
    assert len(store.list_sources("tenant-a", "user-a")) == 1
    assert store.list_sources("tenant-b", "user-a") == []


def test_upload_media_and_prevent_cross_tenant_asset_access(tmp_path):
    store = VisualIntelligenceStore(tmp_path)
    # Minimal PNG signature plus a small payload; content is type-sniffed, not filename-trusted.
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    source = store.capture_media(
        "tenant-a", "user-a", png, filename="../../payload.exe",
        caption="steel chain", labels=["NEXUS", "chain"],
    )
    path, mime = store.get_asset("tenant-a", "user-a", source.id)
    assert path.is_file()
    assert mime == "image/png"
    with pytest.raises(TenantAccessError):
        store.get_asset("tenant-b", "user-a", source.id)


def test_search_is_scoped_and_uses_caption_and_labels(tmp_path):
    store = VisualIntelligenceStore(tmp_path)
    store.capture_url("tenant-a", "user-a", "https://instagram.com/p/one/",
                      caption="stainless steel necklace", labels=["NEXUS"])
    store.capture_url("tenant-b", "user-b", "https://instagram.com/p/two/",
                      caption="stainless steel necklace", labels=["NEXUS"])
    results = store.search("tenant-a", "user-a", "steel necklace")
    assert len(results) == 1
    assert results[0].tenant_id == "tenant-a"


def test_rejects_oversized_and_unknown_media(tmp_path):
    store = VisualIntelligenceStore(tmp_path)
    with pytest.raises(VisualInputError):
        store.capture_media("t", "u", b"not a media file")
    with pytest.raises(VisualInputError):
        store.capture_media("t", "u", b"\x89PNG\r\n\x1a\n" + b"x" * (25 * 1024 * 1024))
