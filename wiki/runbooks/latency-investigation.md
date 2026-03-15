# Latency Investigation Runbook

## Goal
Identify the root cause of elevated latency and restore p99 to within SLO.

## Steps

### 1. Isolate — this service or upstream?
Check distributed traces. If the slow span is inside this service, continue below.
If the slow span is in a dependency, switch to that service's runbook.

### 2. Check the database
```sql
-- PostgreSQL: find long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '1 second'
ORDER BY duration DESC;
```
If long-running queries found: check for missing indexes, lock contention, or a bad query introduced by the latest deployment.

### 3. Check memory and GC
```bash
# JVM services
kubectl exec -it <pod> -- jcmd <pid> GC.heap_info

# Node services
kubectl exec -it <pod> -- node -e "console.log(process.memoryUsage())"
```
GC pauses > 200ms cause latency spikes. If heap is > 85%: consider restart as mitigation while investigating leak.

### 4. Check connection pool wait time
If pool wait time > 0, the service is queuing requests waiting for a DB connection.
Short-term: increase pool size. Long-term: find and fix connection leaks.

### 5. Check for traffic spike
Compare current RPS to baseline. If > 2x:
- Is it legitimate traffic? (marketing campaign, viral event)
- Is autoscaling triggered? If not, scale manually.

### 6. Confirm resolution
After applying fix: latency p99 should return to baseline within 5 minutes.
If not resolved in 10 minutes → escalate via [escalation playbook](../playbooks/escalation.md).
