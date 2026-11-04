#!/usr/bin/env python3
"""One-shot readiness/queue monitor; schedule externally (e.g. every minute)."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

import httpx


def validate_https_url(value: str, setting: str) -> str:
    """Reject plaintext URLs and URL forms that can leak credentials or confuse routing."""
    try:
        parsed = urllib.parse.urlsplit(value)
        # Accessing .port also validates malformed/out-of-range port syntax.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{setting} is not a valid URL.") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(f"{setting} must be an HTTPS URL without embedded credentials or a fragment.")
    return value


def request(url: str, token: str | None = None):
    url = validate_https_url(url, "monitor endpoint")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(
        url, headers=headers, timeout=8.0, follow_redirects=False
    )
    response.raise_for_status()
    return response.json()


def notify(webhook: str, message: str) -> None:
    webhook = validate_https_url(webhook, "alert webhook")
    response = httpx.post(
        webhook, json={"text": message}, timeout=8.0, follow_redirects=False
    )
    response.raise_for_status()


def main() -> int:
    health_url = os.environ.get("NEXUS_READY_URL", "").strip()
    queue_url = os.environ.get("NEXUS_QUEUE_URL", "").strip()
    admin_token = os.environ.get("NEXUS_ADMIN_TOKEN", "").strip()
    webhook = os.environ.get("NEXUS_ALERT_WEBHOOK", "").strip()
    if not all((health_url, queue_url, admin_token, webhook)):
        print("Required monitor configuration is missing.", file=sys.stderr)
        return 2

    try:
        health_url = validate_https_url(health_url, "NEXUS_READY_URL")
        queue_url = validate_https_url(queue_url, "NEXUS_QUEUE_URL")
        webhook = validate_https_url(webhook, "NEXUS_ALERT_WEBHOOK")
        dead_limit = int(os.environ.get("NEXUS_DEAD_TASK_ALERT_THRESHOLD", "1"))
        if dead_limit < 1:
            raise ValueError("NEXUS_DEAD_TASK_ALERT_THRESHOLD must be at least 1.")
    except ValueError as exc:
        print(f"Invalid monitor configuration: {exc}", file=sys.stderr)
        return 2

    problems = []
    try:
        readiness = request(health_url)
        if readiness.get("status") != "ready":
            problems.append("NEXUS readiness check is not ready")
    except Exception as exc:
        problems.append(f"NEXUS readiness request failed ({type(exc).__name__})")

    try:
        queue = request(queue_url, admin_token).get("queue", {})
        dead = int(queue.get("dead", 0))
        if dead >= dead_limit:
            problems.append(f"NEXUS dead-letter queue threshold reached: {dead}")
    except Exception as exc:
        problems.append(f"NEXUS admin queue check failed ({type(exc).__name__})")

    if problems:
        try:
            notify(webhook, "NEXUS AI CORE alert: " + "; ".join(problems))
        except Exception as exc:
            print(f"Alert delivery failed ({type(exc).__name__}).", file=sys.stderr)
            return 3
        print(f"Alert delivered ({len(problems)} condition(s)).")
        return 1
    print("NEXUS checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
