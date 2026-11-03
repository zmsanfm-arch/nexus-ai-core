from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ManifestError(ValueError):
    pass


class AgentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: Literal["registered", "disabled"]
    mode: Literal["advisory"]
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


def load_manifest(path: str | Path) -> AgentManifest:
    """Load and validate a specialist manifest; malformed manifests fail closed."""
    manifest_path = Path(path)
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ManifestError("Manifest root must be a mapping.")
        return AgentManifest.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ManifestError(f"Invalid agent manifest: {manifest_path}") from exc
