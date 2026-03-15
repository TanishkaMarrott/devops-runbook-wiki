# Database Connection Failure

## Symptom
Services returning "connection refused" or "connection pool exhausted" errors. Alert `DBConnectionFailure` firing.

## Affected services
user-service, payments-service

## Likely causes

| Cause | Signal |
|---|---|
| Connection pool exhausted | Pool wait time > 0, active connections at max |
| DB instance restarting | DB unavailable for < 2 minutes, then recovers |
| Max connections reached | DB error: "too many connections" |
| Network partition | Connections timing out, not refused |
| Credentials rotated | Auth errors in service logs |

## Immediate checks

1. **Check active connections** — are we at the connection limit?
2. **Check DB instance status** — is it up, restarting, or failing over?
3. **Check service logs** — "connection refused" vs "auth failed" vs "pool exhausted" — different causes

## Connection limits

| Service | Pool size | DB max_connections |
|---|---|---|
| user-service | 20 | 100 |
| payments-service | 10 | 100 |

## Resolution paths

**If pool exhausted** → check for connection leaks (transactions not closed); temporarily increase pool size as mitigation

**If DB restarting** → wait 2 minutes; if not recovered, follow [db-failover.md](../playbooks/db-failover.md)

**If credentials rotated** → check secret manager; redeploy service to pick up new credentials

## Runbook
[wiki/runbooks/db-recovery.md](../runbooks/db-recovery.md)
