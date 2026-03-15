# Incident Index — Symptom Triage

Use this index first. Map the symptom to an incident page, then read that page for cause + fix.

| Symptom | Incident Page | Likely Service | Playbook |
|---|---|---|---|
| High latency / slow responses | [high-latency.md](high-latency.md) | api-gateway, user-service | [rollback.md](../playbooks/rollback.md) |
| Service returning 5xx errors | [error-spike.md](error-spike.md) | any | [rollback.md](../playbooks/rollback.md) |
| Service completely down / no response | [service-down.md](service-down.md) | any | [escalation.md](../playbooks/escalation.md) |
| Database connection failures | [db-connection-failure.md](db-connection-failure.md) | user-service, payments-service | [db-failover.md](../playbooks/db-failover.md) |
| Deployment broke something | [post-deploy-regression.md](post-deploy-regression.md) | any | [rollback.md](../playbooks/rollback.md) |
| Alert firing but service looks fine | [alert-false-positive.md](alert-false-positive.md) | any | — |
