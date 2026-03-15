# Rollback Playbook

## When to use

A deployment caused a regression — latency spike, error spike, or service down — and the fix
is not immediately obvious. Rolling back is faster than debugging under pressure.

**Rule**: if a deployment happened in the last 2 hours and metrics degraded after it, roll back first, debug second.

## Services covered

All services with a CI/CD pipeline.

## Steps

1. **Confirm the deployment caused it**
   - Check deploy timeline vs. metric degradation start time
   - If they align (within 5 minutes), proceed with rollback

2. **Identify the previous stable version**
   ```bash
   # Kubernetes
   kubectl rollout history deployment/<service-name> -n <namespace>

   # Get the previous revision number
   kubectl rollout history deployment/<service-name> -n <namespace> --revision=<N>
   ```

3. **Execute rollback**
   ```bash
   # Kubernetes — roll back to previous revision
   kubectl rollout undo deployment/<service-name> -n <namespace>

   # Verify rollback is in progress
   kubectl rollout status deployment/<service-name> -n <namespace>
   ```

4. **Verify recovery**
   - Check error rate drops within 2 minutes
   - Check latency returns to baseline within 5 minutes
   - Confirm health checks passing

5. **Lock the pipeline**
   - Block further deployments to this service until root cause is identified
   - Post in `#incidents`: "Rolled back `<service>` to `<version>`. Pipeline locked. Investigating."

6. **Open a post-mortem ticket**
   - Do not unlock the pipeline until the regression is understood

## Rollback fails

If `kubectl rollout undo` fails or the previous version is also broken:
→ Escalate immediately via [escalation.md](escalation.md)

## Owner
Platform team — `#oncall-platform`
