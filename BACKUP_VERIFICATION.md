# Backup & Disaster Recovery

## Backup Strategy

The Rizz platform uses the bundled `scripts/backup.sh` to perform
nightly full backups of all persistent state:

| Component | Tool | Output | Frequency |
|-----------|------|--------|-----------|
| Postgres | `pg_dump` | Plain SQL | nightly |
| MongoDB | `mongodump` | BSON archive | nightly |
| Redis | `BGSAVE` + `docker cp` | RDB file | nightly |
| Uploaded files | `tar` (volume mount) | tar.gz | nightly |

Backups are tar'd together, optionally GPG-encrypted to a configured
recipient, and stored under `backups/` or pushed to S3 (Standard-IA
storage class). Retention is 14 days by default.

## Cron Setup

Add to `/etc/cron.d/rizz`:

```cron
# Rizz nightly backup at 02:30 UTC
30 2 * * * root /opt/rizz/scripts/backup.sh >> /var/log/rizz/backup.log 2>&1

# Pre-restore: stop writes
0 3 * * * root systemctl stop rizz-nginx rizz-api || true
# Post-backup: keep service up
```

## Verification

Backups should be **restored** regularly (at least monthly) to confirm
they are usable. A broken backup is worse than no backup.

### Automated verification (recommended)

Run weekly, restores to a separate test database, runs integrity
checks, then drops:

```bash
# In CI / on a staging host:
./scripts/verify-backup.sh /backups/rizz-backup-20260101T020000Z.tar.gz
```

The verification script:
  1. Decrypts & untars the archive
  2. Loads into a test database
  3. Runs `pg_dump --schema-only` to confirm schema
  4. Spot-checks a few rows from each table
  5. Counts documents in mongo collections
  6. Verifies redis RDB can be parsed
  7. Prints a pass/fail summary

### Manual verification (quarterly)

```bash
# 1. Pick the most recent backup
LATEST=$(ls -t /backups/rizz-backup-*.tar.gz* | head -1)
echo "Verifying: $LATEST"

# 2. Decrypt
gpg --decrypt "$LATEST" > /tmp/restore.tar.gz

# 3. Extract
mkdir -p /tmp/restore && tar -xzf /tmp/restore.tar.gz -C /tmp/restore

# 4. Restore to a SEPARATE test database
psql -h test-db -U rizz_admin -d rizz_test < /tmp/restore/postgres-*.sql

# 5. Count rows
psql -h test-db -U rizz_admin -d rizz_test -c "
    SELECT 'users' AS t, COUNT(*) FROM users
    UNION ALL SELECT 'posts', COUNT(*) FROM posts;
"

# 6. Compare with source (optional)
psql -h prod-db -U rizz_admin -d rizz_api -c "
    SELECT 'users' AS t, COUNT(*) FROM users
    UNION ALL SELECT 'posts', COUNT(*) FROM posts;
"
```

If row counts differ significantly, the backup is broken. Escalate.

## Recovery Time Objectives

| Tier | RTO (downtime) | RPO (data loss) |
|------|----------------|------------------|
| Critical (API, Auth) | 15 min | 1 hour (last successful backup) |
| Standard (Web, Posts) | 1 hour | 4 hours |
| Archive (logs, analytics) | 24 hours | 24 hours |

With nightly backups at 02:30 UTC and a 15-minute RTO, you have at
most 23h45m of potential data loss in the worst case. To tighten RPO
to <5min, enable WAL archiving on Postgres (continuous archiving).

## Off-site Backup

For production, set `BACKUP_S3_BUCKET` to push encrypted backups
to an S3 bucket in a **different region** than the primary
deployment. Test restore from S3 quarterly.

## Monitoring

The backup script logs to `/var/log/rizz/backup.log` (and stdout in
foreground mode). To alert on backup failure, add a Prometheus
blackbox check or a cron-level email alert:

```cron
# Email if backup.log was NOT updated today
5 4 * * * root test $(find /var/log/rizz/backup.log -mtime -1 | wc -l) -eq 0 && \
    mail -s "Rizz backup stale" ops@rizz.dev < /dev/null
```

## Disaster Recovery Runbook

For a real incident, follow [`docs/DR_RUNBOOK.md`](docs/DR_RUNBOOK.md).
The runbook covers:
  1. Detection & triage
  2. Service isolation
  3. Restore from backup
  4. Failover (if multi-region)
  5. Post-mortem template
