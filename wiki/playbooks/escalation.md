# Escalation Playbook

## When to use

- Service is down and rollback did not recover it
- Multiple services are down simultaneously
- Data loss or corruption is suspected
- You have been investigating for > 30 minutes without progress
- The incident is affecting paying customers and growing

**Do not wait 30 minutes to escalate if the blast radius is large. Escalate early.**

## Escalation path

| Severity | Who to contact | How |
|---|---|---|
| P0 — service down, customers affected | Team lead → VP Engineering | Phone call + Slack |
| P1 — degraded, SLO burning fast | Team lead | Slack DM + `#incidents` |
| P2 — degraded, within SLO budget | Post in `#incidents` | Slack |

## Steps

1. **Post in `#incidents` immediately**
   ```
   [P0] <service-name> is down
   Started: <time>
   Impact: <what users are seeing>
   What I've tried: <brief list>
   Escalating to: <name>
   ```

2. **Call the team lead directly** — do not rely on Slack alone for P0

3. **Keep the incident channel updated** every 10 minutes:
   ```
   [Update 10min] Still investigating DB connection issue. Rollback completed, did not resolve.
   ```

4. **Do not go silent** — if you are stuck, say so. "I don't know what's causing this" is useful information.

5. **Hand off cleanly if you are replaced**
   - Write a summary: what you found, what you tried, current state
   - Do not just disappear

## Post-incident

Within 24 hours of resolution:
- Write a brief timeline in `wiki/resolutions/<date>-<service>-<summary>.md`
- Run `/runbook-wiki-reflect` on the session transcript
- The reflect skill will propose wiki improvements based on what happened
