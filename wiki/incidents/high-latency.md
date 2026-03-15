# High Latency / Slow Responses

## Symptom
p99 latency > 500ms or alert `HighLatency` firing. Engineers reporting slow API responses.

## Affected services
api-gateway, user-service, payments-service

## Likely causes

| Cause | Signal |
|---|---|
| Database query slowdown | DB CPU > 80%, slow query log active |
| Downstream service degraded | Dependency latency high in traces |
| Traffic spike above SLO | RPS 2x normal, no infra change |
| Memory pressure / GC pauses | JVM heap > 85%, GC pause > 200ms |
| Recent bad deployment | Latency started at last deploy time |

## Immediate checks

1. **Check traces** — is latency in this service or a downstream dependency?
2. **Check DB** — `SHOW PROCESSLIST` or equivalent; look for long-running queries
3. **Check deploy timeline** — did latency start at a recent deployment?

## Resolution paths

**If downstream service is slow** → check that service's incident page; do not rollback this service yet

**If DB is slow** → read [db-connection-failure.md](db-connection-failure.md); check slow query log

**If recent deployment** → follow [rollback.md](../playbooks/rollback.md)

**If traffic spike** → check if autoscaling triggered; manually scale if not

## Runbook
[wiki/runbooks/latency-investigation.md](../runbooks/latency-investigation.md)
