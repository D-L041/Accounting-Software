# PostgreSQL backup and restore runbook

## Status

This is an operational runbook, not evidence that backups are configured. The hosting provider, database instance, backup destination, retention policy, encryption keys and alert recipients must be recorded by the production administrator before live school data is loaded.

## Minimum production configuration

- Managed PostgreSQL with automated daily backups and point-in-time recovery (PITR) enabled.
- Encrypted backups at rest and encrypted transport.
- A separate, access-controlled backup destination/account where supported.
- Documented retention approved by the school/data controller and service owner.
- Alerts for backup failures, low storage, failed jobs and recovery-point objective breaches.
- No production credentials or database URLs committed to Git or pasted into chat.

## Manual logical backup

Run from a trusted administration environment with PostgreSQL client tools installed. Supply DATABASE_URL through the environment or a protected secret manager; do not put it in command history.

```bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL must be supplied securely}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/precious-schoolbooks-$STAMP.dump"
umask 077
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" --file "$FILE"
pg_restore --list "$FILE" >/dev/null
sha256sum "$FILE" > "$FILE.sha256"
printf 'Backup created and archive listing verified: %s\n' "$FILE"
```

Move the archive to the approved encrypted backup destination immediately. A local dump alone is not a disaster-recovery plan.

## Restore drill (isolated database only)

1. Provision an empty isolated PostgreSQL database matching the supported PostgreSQL major version.
2. Verify the backup checksum and archive listing.
3. Restore into the isolated database using a protected RESTORE_DATABASE_URL.
4. Run Django migrations/checks and application-level integrity checks.
5. Verify representative counts and relationships without exporting personal data into the report.
6. Run the backend test suite and smoke-test authentication, school isolation, billing, ledger reports, payroll drafts and audit log.
7. Record restore start/end times, backup timestamp, recovery point, errors and approver.
8. Destroy the isolated restore environment securely after approval.

Example restore command for the isolated target only:

```bash
set -euo pipefail
: "${RESTORE_DATABASE_URL:?Set an isolated restore database URL}"
: "${BACKUP_FILE:?Set the verified backup file}"
: "${CONFIRM_ISOLATED_RESTORE:?Set to YES only after confirming the target is isolated}"
test "$CONFIRM_ISOLATED_RESTORE" = "YES"
pg_restore --exit-on-error --no-owner --no-privileges --dbname="$RESTORE_DATABASE_URL" "$BACKUP_FILE"
```

Never point this command at production as a shortcut. A production recovery requires an approved incident procedure, a verified snapshot/PITR point, a change freeze and explicit service-owner sign-off.

## Recovery acceptance

A backup is not accepted until an actual restore has completed and the restored application passes integrity checks. Record:
- Backup identifier and UTC timestamp.
- Database version and restored schema/migration state.
- Restore duration and recovery point.
- Trial balance totals and balanced status for test-period data.
- Invoice/payment allocation consistency.
- Audit-log continuity.
- Test results, operator and independent reviewer.

## Current release blocker

No managed database or backup provider has been provisioned through this repository workflow, and no real restore drill has been performed. Keep the production backup/restore checklist item open until the hosting owner supplies access and the drill is witnessed.
