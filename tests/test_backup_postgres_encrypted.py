import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup_postgres_encrypted.sh"


def test_backup_writes_portable_checksum_for_relative_backup_directory(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pg_dump = bin_dir / "pg_dump"
    pg_dump.write_text("#!/bin/sh\nprintf 'fake postgres dump bytes'\n", encoding="utf-8")
    pg_dump.chmod(0o755)

    age = bin_dir / "age"
    age.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "args = sys.argv\n"
        "output = pathlib.Path(args[args.index('--output') + 1])\n"
        "output.write_bytes(sys.stdin.buffer.read())\n",
        encoding="utf-8",
    )
    age.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "PATH": str(bin_dir) + os.pathsep + env.get("PATH", ""),
        "DATABASE_URL": "postgresql://test.invalid/nexus",
        "AGE_RECIPIENT": "age1testrecipient",
        "BACKUP_DIR": "./relative-backups",
    })
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    backup_dir = tmp_path / "relative-backups"
    backup_files = list(backup_dir.glob("*.dump.age"))
    assert len(backup_files) == 1
    backup = backup_files[0]
    checksum = backup.with_name(backup.name + ".sha256")
    assert checksum.is_file()
    verified = subprocess.run(
        ["sha256sum", "--check", checksum.name],
        cwd=backup_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert backup.stat().st_mode & 0o777 == 0o600
    assert backup_dir.stat().st_mode & 0o777 == 0o700
