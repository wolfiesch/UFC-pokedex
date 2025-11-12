# Database Backup Handling

All SQL dumps and snapshot archives now live under `data/backups/legacy/` so the repository root stays lean.

## Adding a New Backup

1. Verify the file is compressed or otherwise reasonably sized.
2. Drop it into `data/backups/legacy/` with a timestamped filename (e.g., `ufc_pokedex_backup_YYYYMMDD_HHMMSS.sql.gz`).
3. Update `data/README.md` if the backup captures a notable event (schema migration, data correction, etc.).

## Retention Policy

- Keep the latest two full backups plus any snapshot tied to an incident postmortem.
- Remove anything older than 90 days unless it documents a migration or audit.

## Restoring

1. Copy the desired file from `data/backups/legacy/`.
2. Follow the restoration steps in `docs/runbooks/deployment/DEPLOYMENT.md` (database section).
3. Re-run `make db-upgrade` after restore to catch migrations that landed after the dump.
