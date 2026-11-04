#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${AGE_IDENTITY_FILE:?AGE_IDENTITY_FILE is required}"
: "${NEXUS_RESTORE_DATABASE_URL:?Use a dedicated isolated restore database URL}"
: "${NEXUS_RESTORE_CONFIRM:?Set NEXUS_RESTORE_CONFIRM=YES after verifying the target is disposable}"
[[ "$NEXUS_RESTORE_CONFIRM" == "YES" ]] || { echo "Restore confirmation rejected." >&2; exit 2; }
db_path="${NEXUS_RESTORE_DATABASE_URL##*/}"
db_name="${db_path%%\?*}"
[[ "$db_name" == nexus_restore_* ]] || { echo "Restore target database name must start with nexus_restore_." >&2; exit 2; }
command -v age >/dev/null
command -v pg_restore >/dev/null
test -r "$BACKUP_FILE"
test -r "$AGE_IDENTITY_FILE"

if [[ -f "$BACKUP_FILE.sha256" ]]; then
  (cd "$(dirname "$BACKUP_FILE")" && sha256sum --check "$(basename "$BACKUP_FILE").sha256")
fi

age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_FILE" |
  pg_restore --exit-on-error --clean --if-exists --no-owner --no-acl --dbname="$NEXUS_RESTORE_DATABASE_URL"
echo "Restore drill completed against isolated database: $db_name"
