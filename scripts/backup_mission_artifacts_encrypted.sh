#!/usr/bin/env bash
set -euo pipefail

: "${NEXUS_ARTIFACT_ROOT:?Set NEXUS_ARTIFACT_ROOT to the persistent mission artifact volume}"
: "${AGE_RECIPIENT:?Set AGE_RECIPIENT to the backup recipient public key}"
: "${BACKUP_DIR:?Set BACKUP_DIR to the encrypted backup destination}"

root="${NEXUS_ARTIFACT_ROOT}"
if [[ ! -d "$root" || -L "$root" ]]; then
  echo "Artifact root must be an existing, non-symlink directory." >&2
  exit 2
fi
root="$(realpath -e "$root")"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

if find "$root" -type l -print -quit | grep -q .; then
  echo "Artifact root contains a symlink; refusing backup." >&2
  exit 2
fi
if find "$root" \( -type f -o -type d \) -prune -o -print -quit | grep -q .; then
  echo "Artifact root contains an unsupported filesystem entry." >&2
  exit 2
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/nexus-artifacts-$timestamp.tar.gz.age"
archive="$(mktemp)"
trap 'rm -f "$archive"' EXIT

tar -C "$root" --numeric-owner --owner=0 --group=0 -czf "$archive" .
age -r "$AGE_RECIPIENT" -o "$output" "$archive"
chmod 600 "$output"
sha256sum "$output" > "$output.sha256"
chmod 600 "$output.sha256"
printf '%s\n' "$output"
