#!/usr/bin/env bash
set -euo pipefail

: "${BACKUP_FILE:?Set BACKUP_FILE to the encrypted artifact backup}"
: "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the age identity file}"
: "${NEXUS_RESTORE_ARTIFACT_ROOT:?Set NEXUS_RESTORE_ARTIFACT_ROOT to an empty restore directory}"
: "${NEXUS_RESTORE_CONFIRM:?Set NEXUS_RESTORE_CONFIRM=YES to authorize the isolated restore}"

if [[ "$NEXUS_RESTORE_CONFIRM" != "YES" ]]; then
  echo "Artifact restore requires NEXUS_RESTORE_CONFIRM=YES." >&2
  exit 2
fi
if [[ ! -f "$BACKUP_FILE" || -L "$BACKUP_FILE" || ! -f "$AGE_IDENTITY_FILE" || -L "$AGE_IDENTITY_FILE" ]]; then
  echo "Backup and identity must be regular, non-symlink files." >&2
  exit 2
fi
if [[ ! -f "$BACKUP_FILE.sha256" ]]; then
  echo "Artifact backup checksum file is missing." >&2
  exit 2
fi
(cd "$(dirname "$BACKUP_FILE")" && sha256sum -c "$(basename "$BACKUP_FILE").sha256")

target="$NEXUS_RESTORE_ARTIFACT_ROOT"
if [[ -L "$target" ]]; then
  echo "Restore target must not be a symlink." >&2
  exit 2
fi
mkdir -p "$target"
if find "$target" -mindepth 1 -print -quit | grep -q .; then
  echo "Restore target must be empty." >&2
  exit 2
fi
target="$(realpath -e "$target")"
parent="$(dirname "$target")"
staging="$(mktemp -d "$parent/.nexus-artifacts-restore.XXXXXX")"
archive="$(mktemp)"
cleanup() { rm -rf "$staging"; rm -f "$archive"; }
trap cleanup EXIT

age -d -i "$AGE_IDENTITY_FILE" -o "$archive" "$BACKUP_FILE"

python3 - "$archive" "$staging" <<'PY'
import hashlib
import json
import os
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath

archive_path = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve()
max_total = int(os.getenv("NEXUS_ARTIFACT_RESTORE_MAX_BYTES", str(5 * 1024**3)))
max_members = int(os.getenv("NEXUS_ARTIFACT_RESTORE_MAX_MEMBERS", "100000"))
seen = set()
total = 0

with tarfile.open(archive_path, "r:gz") as tar:
    members = tar.getmembers()
    if len(members) > max_members:
        raise SystemExit("Artifact archive contains too many entries.")
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\x00" in name:
            raise SystemExit("Artifact archive contains an unsafe path.")
        normalized = str(path)
        if normalized in seen:
            raise SystemExit("Artifact archive contains duplicate paths.")
        seen.add(normalized)
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            raise SystemExit("Artifact archive contains an unsupported link or special file.")
        if not (member.isdir() or member.isfile()):
            raise SystemExit("Artifact archive contains an unsupported entry.")
        total += member.size
        if total > max_total:
            raise SystemExit("Artifact archive exceeds the configured restore size limit.")
        destination = (root / Path(*path.parts)).resolve()
        if destination != root and root not in destination.parents:
            raise SystemExit("Artifact archive path escapes the restore root.")
        if member.isdir():
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        source = tar.extractfile(member)
        if source is None:
            raise SystemExit("Artifact archive member cannot be read.")
        with source, destination.open("xb") as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        os.chmod(destination, 0o600)

# Validate the Artifact Store's on-disk schema and every content hash.
for directory in root.iterdir():
    if directory.is_symlink() or not directory.is_dir() or not re.fullmatch(r"[a-f0-9]{64}", directory.name):
        raise SystemExit("Artifact archive contains an invalid principal directory.")
    os.chmod(directory, 0o700)
    metadata_ids = set()
    blob_ids = set()
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise SystemExit("Artifact archive contains an unexpected filesystem entry.")
        match = re.fullmatch(r"([a-f0-9]{32})\.(json|blob)", item.name)
        if not match:
            raise SystemExit("Artifact archive contains an invalid artifact filename.")
        artifact_id, suffix = match.groups()
        os.chmod(item, 0o600)
        if suffix == "json":
            metadata_ids.add(artifact_id)
            record = json.loads(item.read_text(encoding="utf-8"))
            if record.get("artifact_id") != artifact_id or record.get("principal_key") != directory.name:
                raise SystemExit("Artifact metadata ownership mismatch.")
            blob = directory / f"{artifact_id}.blob"
            if not blob.is_file() or blob.is_symlink():
                raise SystemExit("Artifact blob is missing.")
            content = blob.read_bytes()
            if len(content) != record.get("size_bytes") or hashlib.sha256(content).hexdigest() != record.get("sha256"):
                raise SystemExit("Artifact content integrity check failed.")
        else:
            blob_ids.add(artifact_id)
    if metadata_ids != blob_ids:
        raise SystemExit("Artifact metadata/blob set is incomplete.")
PY

if find "$target" -mindepth 1 -print -quit | grep -q .; then
  echo "Restore target changed during validation; refusing to overwrite." >&2
  exit 2
fi
cp -a "$staging"/. "$target"/
printf 'Restored and verified mission artifacts into %s\n' "$target"
