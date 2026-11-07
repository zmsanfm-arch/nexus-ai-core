import pytest

from app.services.plugin_registry import (
    PluginManifestError, PluginPermissionDenied, PluginPermissionPolicy,
    PluginRegistry, load_plugin_manifest,
)


def _manifest(tmp_path, *, status="registered", permissions=("message.send",)):
    path = tmp_path / "plugin.yaml"
    permission_values = ", ".join(permissions)
    path.write_text(
        "plugin_id: telegram_bridge\n"
        "name: Telegram Bridge\n"
        "version: 1.0.0\n"
        "kind: channel\n"
        f"status: {status}\n"
        "capabilities: [channel.telegram]\n"
        f"permissions: [{permission_values}]\n"
        f"requested_permissions: [{permission_values}]\n"
        , encoding="utf-8"
    )
    return path


def test_plugin_manifest_is_strict(tmp_path):
    manifest = load_plugin_manifest(_manifest(tmp_path))
    assert manifest.plugin_id == "telegram_bridge"
    assert manifest.kind == "channel"


def test_unknown_manifest_fields_fail_closed(tmp_path):
    path = _manifest(tmp_path)
    path.write_text(path.read_text() + "entrypoint: package.module:run\n")
    with pytest.raises(PluginManifestError):
        load_plugin_manifest(path)


def test_plugin_registry_discovers_metadata_only(tmp_path):
    plugin_dir = tmp_path / "telegram_bridge"
    plugin_dir.mkdir()
    _manifest(plugin_dir)
    registry = PluginRegistry([tmp_path])
    assert [item["plugin_id"] for item in registry.list_plugins()] == ["telegram_bridge"]


def test_duplicate_plugin_ids_fail_closed(tmp_path):
    for folder in ("one", "two"):
        plugin_dir = tmp_path / folder
        plugin_dir.mkdir()
        path = _manifest(plugin_dir)
        path.write_text(path.read_text().replace("telegram_bridge", "same_plugin"))
    with pytest.raises(PluginManifestError, match="Duplicate"):
        PluginRegistry([tmp_path])


def test_plugin_permission_requires_core_allowlist_and_manifest_grant(tmp_path):
    manifest = load_plugin_manifest(_manifest(tmp_path))
    PluginPermissionPolicy(frozenset({"message.send"})).authorize(manifest, "message.send")
    with pytest.raises(PluginPermissionDenied):
        PluginPermissionPolicy().authorize(manifest, "message.send")


def test_disabled_plugin_cannot_be_authorized(tmp_path):
    manifest = load_plugin_manifest(_manifest(tmp_path, status="disabled"))
    with pytest.raises(PluginPermissionDenied, match="not registered"):
        PluginPermissionPolicy(frozenset({"message.send"})).authorize(manifest, "message.send")


def test_manifest_grant_cannot_expand_core_allowlist(tmp_path):
    manifest = load_plugin_manifest(_manifest(tmp_path))
    with pytest.raises(PluginPermissionDenied, match="central policy"):
        PluginPermissionPolicy(frozenset({"knowledge.retrieve"})).authorize(manifest, "message.send")