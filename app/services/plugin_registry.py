"""Fail-closed plugin manifest discovery and permission policy.

This module deliberately discovers metadata only. It never imports plugin code,
loads entrypoints, reads plugin credentials, or activates external side effects.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class PluginManifestError(ValueError):
    """Raised when plugin metadata is invalid."""


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plugin_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    kind: Literal["tool", "provider", "channel", "hook", "skill"]
    status: Literal["disabled", "registered"]
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    requested_permissions: tuple[str, ...] = ()


def load_plugin_manifest(path: str | Path) -> PluginManifest:
    """Parse a strict metadata-only manifest; malformed input fails closed."""
    manifest_path = Path(path)
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise PluginManifestError("Plugin manifest root must be a mapping.")
        return PluginManifest.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise PluginManifestError(f"Invalid plugin manifest: {manifest_path}") from exc


class PluginRegistry:
    """Read-only catalog. Registration does not imply activation or trust."""

    def __init__(self, manifest_dirs: list[str | Path] | None = None):
        self._plugins: dict[str, PluginManifest] = {}
        roots = manifest_dirs or [Path(__file__).resolve().parents[2] / "plugins"]
        for directory in roots:
            root = Path(directory)
            if not root.exists():
                continue
            for path in sorted(root.glob("*/plugin.yaml")):
                manifest = load_plugin_manifest(path)
                if manifest.plugin_id in self._plugins:
                    raise PluginManifestError(f"Duplicate plugin id: {manifest.plugin_id}")
                self._plugins[manifest.plugin_id] = manifest

    def list_plugins(self) -> list[dict]:
        return [manifest.model_dump(mode="json") for _, manifest in sorted(self._plugins.items())]

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)


class PluginPermissionDenied(RuntimeError):
    """Raised when central policy does not authorize a plugin permission."""


class PluginPermissionPolicy:
    """Requires an explicit core allowlist and a matching manifest grant."""

    def __init__(self, allowed_permissions: frozenset[str] = frozenset()):
        self.allowed_permissions = frozenset(allowed_permissions)

    def authorize(self, manifest: PluginManifest, permission: str) -> None:
        if manifest.status != "registered":
            raise PluginPermissionDenied("Plugin is not registered as enabled.")
        if permission not in self.allowed_permissions:
            raise PluginPermissionDenied("Plugin permission is not allowed by central policy.")
        if permission not in manifest.permissions:
            raise PluginPermissionDenied("Plugin manifest does not declare the required permission.")