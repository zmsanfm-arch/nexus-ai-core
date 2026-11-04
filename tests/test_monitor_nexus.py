import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "monitor_nexus.py"


def _env(**overrides):
    env = os.environ.copy()
    env.update({
        "NEXUS_READY_URL": "https://api.example.test/ready",
        "NEXUS_QUEUE_URL": "https://api.example.test/admin/queue",
        "NEXUS_ADMIN_TOKEN": "test-token",
        "NEXUS_ALERT_WEBHOOK": "https://hooks.example.test/services/test",
        "NEXUS_DEAD_TASK_ALERT_THRESHOLD": "1",
    })
    env.update(overrides)
    return env


def _run(**overrides):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=_env(**overrides),
        capture_output=True,
        text=True,
        timeout=5,
    )


def test_monitor_rejects_plain_http_before_network_access():
    result = _run(NEXUS_READY_URL="http://api.example.test/ready")
    assert result.returncode == 2
    assert "must be an HTTPS URL" in result.stderr


def test_monitor_rejects_embedded_credentials():
    result = _run(NEXUS_QUEUE_URL="https://user:password@api.example.test/admin/queue")
    assert result.returncode == 2
    assert "without embedded credentials" in result.stderr


def test_monitor_rejects_url_fragment():
    result = _run(NEXUS_ALERT_WEBHOOK="https://hooks.example.test/services/test#fragment")
    assert result.returncode == 2
    assert "without embedded credentials or a fragment" in result.stderr


def test_monitor_rejects_invalid_dead_letter_threshold():
    result = _run(NEXUS_DEAD_TASK_ALERT_THRESHOLD="not-an-integer")
    assert result.returncode == 2
    assert "Invalid monitor configuration" in result.stderr


def test_monitor_rejects_zero_dead_letter_threshold():
    result = _run(NEXUS_DEAD_TASK_ALERT_THRESHOLD="0")
    assert result.returncode == 2
    assert "must be at least 1" in result.stderr
