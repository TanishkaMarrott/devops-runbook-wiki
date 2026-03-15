# Service Down / No Response

## Symptom
Health check failing, alert `ServiceDown` firing, or 100% error rate on all endpoints.

## Affected services
Any

## Likely causes

| Cause | Signal |
|---|---|
| OOM killed | Pod/container restarting, OOMKilled in logs |
| Config error after deploy | Crash on startup, config parse error in logs |
| Dependency unavailable | Service starts but all requests fail immediately |
| Infrastructure failure | Multiple services down, cloud provider alerts |
| Disk full | Write errors in logs, disk usage > 95% |

## Immediate checks

1. **Is it just this service or multiple?** — if multiple, check cloud provider status page first
2. **Check pod/process status** — is it crashing and restarting, or just not responding?
3. **Check logs from the last 5 minutes** — look for startup errors, OOM, or config failures

## Resolution paths

**If OOMKilled** → increase memory limit; check for memory leak if this is recurring

**If config error** → revert the last config change; do not redeploy until config is fixed

**If dependency down** → check that dependency's incident page; implement circuit breaker if not already present

**If infrastructure failure** → escalate immediately; follow [escalation.md](../playbooks/escalation.md)

## Runbook
[wiki/runbooks/service-recovery.md](../runbooks/service-recovery.md)
