#!/usr/bin/env python3
"""Generate fresh API/admin tokens into a new mode-0600 env file; never prints secrets."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="New env file path; existing files are never overwritten")
    args = parser.parse_args()
    path = Path(args.output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    values = (
        f"NEXUS_API_TOKEN={secrets.token_urlsafe(48)}\n"
        f"NEXUS_ADMIN_TOKEN={secrets.token_urlsafe(48)}\n"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(values)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print(f"Created new secret file with restrictive permissions: {path}")
    print("Install via the host secret-management process, restart services, verify access, then revoke the previous tokens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
