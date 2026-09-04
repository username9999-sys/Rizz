# Disaster Recovery Runbook

This runbook is the **on-call playbook** for responding to a major
incident on the Rizz platform. Use it in conjunction with
`BACKUP_VERIFICATION.md` (recovery procedure) and `SCALING.md`
(capacity planning).

## Severity definitions

  - **SEV-1**: Complete outage. Customers cannot reach the API.
  - **SEV-2**: Degraded service. Some requests failing or slow.
  - **SEV-3**: Bug / minor issue. No customer impact yet.

## SEV-1: Complete outage

### 1. Detect & confirm (5 min)

  - Check Prometheus: `up{job="rizz-api"} == 0` for >1m
  - Check Alertmanager for active `ApiDown` alerts
  - Check nginx access log for traffic patterns
  - **Manually curl** `https://rizz.dev/api/v2` from a different network

### 2. Communicate (5 min)

  - Post in Slack `#rizz-incident`:
    ```
    [SEV-1] Rizz API is down. Investigating. Started at <time>.
    ```
  - Page on-call via PagerDuty
  - Update status page: `https://status.rizz.dev`

### 3. Triage (15 min)

  - SSH into host (or get shell via Termux / QEMU)
  - `docker ps` to see if containers are running
  - Check `docker logs rizz-api --tail=200` for stack traces
  - Check disk space: `df -h`
  - Check memory: `free -h`
  - Check Postgres replication: `psql -c "SELECT * FROM pg_stat_replication"`

### 4. Mitigate (variable)

Pick the first applicable:

  | Symptom | Action |
  |---------|--------|
  | Container crashed | `docker compose restart api` |
  | Postgres down | `docker compose restart postgres`; check `/var/log/postgresql` |
  | Disk full | `docker system prune -a`; check `/var/lib/docker` |
  | Memory pressure | Kill largest memory hog; check for memory leak |
  | Network issue | Check `iptables -L`, security groups, CDN status |
  | Bad deploy | `git revert HEAD` + redeploy previous tag |

### 5. Communicate resolution

  - Update Slack
  - Update status page to "Monitoring"
  - Post in `#rizz-eng`: "API restored. Root cause: <x>. ETA for postmortem: <date>."

## SEV-2: Degraded service

Use the same triage path. The most common causes:

  - **High error rate**: usually a code regression. Roll back.
  - **High latency**: usually database slowness. Check
    `pg_stat_statements` for slow queries.
  - **Cache invalidation storm**: if you just deployed, traffic
    that was hitting cache now hits the DB. Wait it out or warm cache.

## SEV-3: Bug / minor issue

Triage on next business day. File a GitHub issue with the
`bug` label and `severity: sev-3`.

## Restore from backup

See [`BACKUP_VERIFICATION.md`](../BACKUP_VERIFICATION.md) for the
full procedure. Quick summary:

```bash
LATEST=$(ls -t /backups/rizz-backup-*.tar.gz* | head -1)
gpg --decrypt "$LATEST" > /tmp/restore.tar.gz
mkdir -p /tmp/restore && tar -xzf /tmp/restore.tar.gz -C /tmp/restore
PGPASSWORD=$POSTGRES_PASSWORD psql -h prod-db -U rizz_admin -d rizz_api \
    -f /tmp/restore/postgres-*.sql
```

> ⚠️ **This restores the entire database to a previous point in time.
> Run only after consulting the on-call lead.**

## Failover (multi-region)

If the primary region is down for an extended period:

  1. Update DNS: lower TTL 24h in advance, then point to secondary
  2. Verify secondary has fresh data (replication lag < 1 min)
  3. Promote secondary to primary: `pg_ctl promote`
  4. Bring up API in secondary region
  5. Notify customers via status page

## Post-mortem

Within 5 business days of any SEV-1 or SEV-2, file a post-mortem in
`docs/postmortems/YYYY-MM-DD-<slug>.md`. Template:

```markdown
# Post-mortem: <short title>

**Date**: YYYY-MM-DD
**Severity**: SEV-1 / SEV-2
**Duration**: HH:MM (start - resolved)
**On-call lead**: <name>

## What happened

<2-3 paragraph summary>

## Timeline

- HH:MM — <event>
- HH:MM — <event>
- HH:MM — <event>

## Root cause

<What was the actual cause? Not just symptoms.>

## What went well

<Things that worked as expected during the incident.>

## What went poorly

<Things that didn't work or slowed us down.>

## Action items

- [ ] <Action 1> (owner: <name>, due: <date>)
- [ ] <Action 2> (owner: <name>, due: <date>)
```

## Contacts

  - Primary on-call: see PagerDuty schedule
  - Slack: `#rizz-incident` (war room), `#rizz-alerts` (auto)
  - Status page: `https://status.rizz.dev`
  - Customer support: `support@rizz.dev`

## Reference

  - [BACKUP_VERIFICATION.md](../BACKUP_VERIFICATION.md) — restore procedure
  - [SCALING.md](../SCALING.md) — capacity & scaling decisions
  - [SECURITY_POLICY.md](../SECURITY_POLICY.md) — security incident reporting
  - [monitoring/prometheus/alerts.yml](../monitoring/prometheus/alerts.yml) — alert definitions
