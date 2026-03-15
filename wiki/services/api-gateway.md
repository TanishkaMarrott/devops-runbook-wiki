# api-gateway

Entry point for all external traffic. Routes requests to upstream services.

## SLO Thresholds

| Metric | Target |
|---|---|
| Availability | 99.9% (43min/month downtime budget) |
| Latency p99 | < 200ms |
| Error rate | < 0.1% |
| Measurement window | 30 days rolling |

## Alerts

| Alert | Condition | Severity |
|---|---|---|
| `HighLatency` | p99 > 500ms for 5min | P2 |
| `ErrorSpike` | 5xx rate > 1% for 2min | P1 |
| `ServiceDown` | Health check failing for 1min | P0 |
| `TrafficAnomaly` | RPS > 3x baseline for 10min | P3 |

## Common Incidents

- [High latency](../incidents/high-latency.md) — most common; usually downstream service
- [Error spike](../incidents/error-spike.md) — check upstream services first
- [Service down](../incidents/service-down.md) — rare; usually config or infra

## Dependencies

- user-service (auth validation)
- payments-service (payment endpoints)
- notification-service (async, non-blocking)

## Owner & Escalation

- Owner: platform-team
- On-call: `#oncall-platform` Slack
- Escalation: platform-team lead → VP Engineering
- Runbooks: [latency-investigation](../runbooks/latency-investigation.md) · [rollback](../playbooks/rollback.md)
