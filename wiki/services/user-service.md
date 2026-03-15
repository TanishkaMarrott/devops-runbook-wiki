# user-service

Handles authentication, user profile management, and session management.

## SLO Thresholds

| Metric | Target |
|---|---|
| Availability | 99.95% (22min/month downtime budget) |
| Latency p99 | < 300ms |
| Error rate | < 0.05% |
| Measurement window | 30 days rolling |

## Alerts

| Alert | Condition | Severity |
|---|---|---|
| `AuthFailureSpike` | Auth errors > 5% for 3min | P1 |
| `HighLatency` | p99 > 600ms for 5min | P2 |
| `DBConnectionFailure` | DB connection errors > 0 for 2min | P1 |
| `SessionCacheDown` | Redis connection failures | P2 |

## Common Incidents

- [DB connection failure](../incidents/db-connection-failure.md) — most common
- [High latency](../incidents/high-latency.md) — usually DB query slowdown
- [Service down](../incidents/service-down.md) — check DB and Redis first

## Dependencies

- PostgreSQL (primary datastore)
- Redis (session cache)
- notification-service (async email/push)

## Connection limits

- DB pool size: 20 connections
- Redis pool size: 50 connections

## Owner & Escalation

- Owner: identity-team
- On-call: `#oncall-identity` Slack
- Escalation: identity-team lead → CTO
- Runbooks: [db-recovery](../runbooks/db-recovery.md) · [db-failover](../playbooks/db-failover.md)
