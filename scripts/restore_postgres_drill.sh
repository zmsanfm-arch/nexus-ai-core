#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${AGE_IDENTITY_FILE:?AGE_IDENTITY_FILE is required}"
: "${NEXUS_RESTORE_DATABASE_URL:?Use a dedicated isolated restore database URL}"
: "${NEXUS_RESTORE_ALLOWED_DATABASE_URL:?Set the exact approved disposable restore URL separately}"
: "${NEXUS_RESTORE_CONFIRM:?Set NEXUS_RESTORE_CONFIRM=YES after verifying the target is disposable}"
[[ "$NEXUS_RESTORE_CONFIRM" == "YES" ]] || { echo "Restore confirmation rejected." >&2; exit 2; }
# Require an exact, separately supplied destination allowlist. A database-name
# prefix alone is not isolation: it could still point at a production server.
[[ "$NEXUS_RESTORE_DATABASE_URL" == "$NEXUS_RESTORE_ALLOWED_DATABASE_URL" ]] || {
  echo "Restore target does not match the explicitly approved isolated database URL." >&2
  exit 2
}
db_path="${NEXUS_RESTORE_DATABASE_URL##*/}"
db_name="${db_path%%\?*}"
[[ "$db_name" == nexus_restore_* ]] || { echo "Restore target database name must start with nexus_restore_." >&2; exit 2; }
test -r "$BACKUP_FILE"
test -r "$AGE_IDENTITY_FILE"
test -r "$BACKUP_FILE.sha256" || {
  echo "Backup checksum sidecar is required." >&2
  exit 2
}
(cd "$(dirname "$BACKUP_FILE")" && sha256sum --check "$(basename "$BACKUP_FILE").sha256")

command -v age >/dev/null
command -v pg_restore >/dev/null

age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_FILE" |
  pg_restore --exit-on-error --clean --if-exists --no-owner --no-acl --dbname="$NEXUS_RESTORE_DATABASE_URL"
echo "Restore drill completed against explicitly approved isolated database: $db_name"
