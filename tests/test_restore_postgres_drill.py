import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "restore_postgres_drill.sh"


def _base_env(tmp_path, target_url, allowed_url):
    backup = tmp_path / "backup.dump.age"
    identity = tmp_path / "age-identity.txt"
    backup.write_text("placeholder", encoding="utf-8")
    identity.write_text("placeholder", encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "BACKUP_FILE": str(backup),
        "AGE_IDENTITY_FILE": str(identity),
        "NEXUS_RESTORE_DATABASE_URL": target_url,
        "NEXUS_RESTORE_ALLOWED_DATABASE_URL": allowed_url,
        "NEXUS_RESTORE_CONFIRM": "YES",
    })
    return env


def test_restore_refuses_url_not_matching_explicit_allowlist(tmp_path):
    env = _base_env(
        tmp_path,
        "postgresql://restore@staging.example/nexus_restore_drill",
        "postgresql://restore@production.example/nexus_restore_drill",
    )
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "does not match the explicitly approved" in result.stderr


def test_restore_refuses_non_isolated_database_even_when_url_is_allowlisted(tmp_path):
    url = "postgresql://restore@staging.example/application"
    env = _base_env(tmp_path, url, url)
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "must start with nexus_restore_" in result.stderr
