import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "monitor_nexus.py"
SPEC = importlib.util.spec_from_file_location("nexus_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


class Response:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def configure(monkeypatch):
    monkeypatch.setenv("NEXUS_READY_URL", "https://api.example.test/ready")
    monkeypatch.setenv("NEXUS_QUEUE_URL", "https://api.example.test/admin/queue")
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("NEXUS_ALERT_WEBHOOK", "https://hooks.example.test/services/test")
    monkeypatch.setenv("NEXUS_DEAD_TASK_ALERT_THRESHOLD", "1")


def test_monitor_delivers_alert_when_dead_letter_threshold_is_reached(monkeypatch):
    configure(monkeypatch)
    get_calls = []
    post_calls = []

    def fake_get(url, **kwargs):
        get_calls.append((url, kwargs))
        if url.endswith("/ready"):
            return Response({"status": "ready"})
        return Response({"queue": {"dead": 2}})

    def fake_post(url, **kwargs):
        post_calls.append((url, kwargs))
        return Response({"ok": True})

    monkeypatch.setattr(monitor.httpx, "get", fake_get)
    monkeypatch.setattr(monitor.httpx, "post", fake_post)
    assert monitor.main() == 1
    assert len(get_calls) == 2
    assert get_calls[1][1]["headers"]["Authorization"] == "Bearer test-admin-token"
    assert len(post_calls) == 1
    assert "dead-letter queue threshold reached: 2" in post_calls[0][1]["json"]["text"]


def test_monitor_reports_alert_delivery_failure(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(
        monitor.httpx, "get",
        lambda url, **kwargs: Response({"status": "not-ready"}) if url.endswith("/ready")
        else Response({"queue": {"dead": 0}}),
    )
    monkeypatch.setattr(
        monitor.httpx, "post",
        lambda *args, **kwargs: Response(error=RuntimeError("webhook unavailable")),
    )
    assert monitor.main() == 3


def test_monitor_does_not_send_alert_when_all_checks_pass(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(
        monitor.httpx, "get",
        lambda url, **kwargs: Response({"status": "ready"}) if url.endswith("/ready")
        else Response({"queue": {"dead": 0}}),
    )
    calls = []
    monkeypatch.setattr(monitor.httpx, "post", lambda *args, **kwargs: calls.append(args))
    assert monitor.main() == 0
    assert calls == []
