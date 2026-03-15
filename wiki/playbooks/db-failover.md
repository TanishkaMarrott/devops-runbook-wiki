# Database Failover Playbook

## When to use

Primary DB instance is down or unrecoverable and automatic failover has not triggered,
or automatic failover triggered but services have not reconnected.

## Steps

1. **Confirm the primary is actually down**
   ```bash
   # Check DB instance status
   # AWS RDS
   aws rds describe-db-instances --db-instance-identifier <name> --query 'DBInstances[0].DBInstanceStatus'

   # Direct connection test
   psql -h <primary-host> -U <user> -c "SELECT 1" 2>&1
   ```

2. **Check if automatic failover triggered**
   - RDS Multi-AZ: check Events in console for "Multi-AZ instance failover completed"
   - If completed: the DNS endpoint now points to the new primary — services should reconnect automatically

3. **If automatic failover did NOT trigger — manual failover**
   ```bash
   # AWS RDS
   aws rds reboot-db-instance --db-instance-identifier <name> --force-failover
   ```

4. **Force service reconnection**
   Services use connection pools that may hold stale connections. After failover:
   ```bash
   kubectl rollout restart deployment/user-service -n production
   kubectl rollout restart deployment/payments-service -n production
   ```

5. **Verify recovery**
   - Services return to normal error rate within 3 minutes
   - No "connection refused" errors in logs
   - DB instance status: `available`

6. **Check replica lag**
   After failover the new primary's replica (old primary) may have lag.
   Monitor for 15 minutes before declaring incident resolved.

## Escalation

If failover does not complete within 10 minutes → escalate via [escalation.md](escalation.md)

## Owner
Infrastructure team — `#oncall-infra`
