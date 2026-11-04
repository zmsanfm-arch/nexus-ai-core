#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${AGE_RECIPIENT:?AGE_RECIPIENT is required (age public recipient)}"
command -v pg_dump >/dev/null
command -v age >/dev/null
command -v sha256sum >/dev/null

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
final="$BACKUP_DIR/nexus-$stamp.dump.age"
tmp="$final.tmp"
trap 'rm -f "$tmp"' EXIT

pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" | age --encrypt --recipient "$AGE_RECIPIENT" --output "$tmp"
test -s "$tmp"
mv -- "$tmp" "$final"
sha256sum "$final" > "$final.sha256"
chmod 600 "$final" "$final.sha256"
printf 'Encrypted backup created: %s\n' "$final"
printf 'SHA-256: '
cut -d ' ' -f 1 "$final.sha256"
