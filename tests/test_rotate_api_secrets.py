from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rotate_api_secrets.py"


def test_rotation_creates_distinct_restrictive_secrets_without_printing_values(tmp_path):
    output = tmp_path / "secrets" / "next.env"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.is_file()
    assert os.stat(output).st_mode & 0o777 == 0o600
    entries = dict(
        line.split("=", 1)
        for line in output.read_text(encoding="utf-8").splitlines()
    )
    assert set(entries) == {"NEXUS_API_TOKEN", "NEXUS_ADMIN_TOKEN"}
    assert len(entries["NEXUS_API_TOKEN"]) >= 32
    assert len(entries["NEXUS_ADMIN_TOKEN"]) >= 32
    assert entries["NEXUS_API_TOKEN"] != entries["NEXUS_ADMIN_TOKEN"]
    assert entries["NEXUS_API_TOKEN"] not in result.stdout
    assert entries["NEXUS_ADMIN_TOKEN"] not in result.stdout
    assert entries["NEXUS_API_TOKEN"] not in result.stderr
    assert entries["NEXUS_ADMIN_TOKEN"] not in result.stderr


def test_rotation_refuses_to_overwrite_existing_secret_file(tmp_path):
    output = tmp_path / "next.env"
    original = "KEEP_THIS_FILE=unchanged\n"
    output.write_text(original, encoding="utf-8")
    os.chmod(output, 0o600)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert output.read_text(encoding="utf-8") == original
    assert "KEEP_THIS_FILE" not in result.stdout
