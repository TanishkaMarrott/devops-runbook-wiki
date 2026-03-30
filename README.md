# DevOps Runbook Wiki

A self-improving runbook knowledge base for on-call engineers. Query it during incidents, and it learns from every session — gaps in coverage get proposed as wiki improvements after each query.

![Claude](https://img.shields.io/badge/Claude-Agent_Skills-6B4FBB?logo=anthropic&logoColor=white)
![Wiki](https://img.shields.io/badge/Pattern-Self--Improving_Wiki-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![CI](https://github.com/TanishkaMarrott/devops-runbook-wiki/actions/workflows/ci.yml/badge.svg)

---

## The Problem

Runbooks go stale. Engineers write them once, incidents evolve, and the wiki slowly drifts from reality. The next on-call engineer searches for "connection pool exhausted" and finds a page last updated 18 months ago.

This system closes that loop: every session where the wiki couldn't answer a question becomes a proposal to fix it.

---

## How It Works

```mermaid
flowchart LR
    Q["On-call engineer\naskes a question"]
    W["runbook-wiki skill\nanswers from wiki only"]
    T["Session transcript\nsaved automatically"]
    R["runbook-wiki-reflect\nanalyses transcript"]
    P["Improvement proposal\nshown to admin"]
    A{"Approve?"}
    UP["Wiki updated"]
    LOG["Session logged\nwiki unchanged"]

    Q --> W --> T --> R --> P --> A
    A -->|yes| UP
    A -->|no| LOG
    UP -->|"next session\nhas better answers"| Q
```

**Three skills, one loop:**

| Skill | When it runs | What it does |
|---|---|---|
| `/runbook-wiki` | During an incident | Answers from compiled wiki — no live tool calls, no raw configs |
| `/runbook-wiki-reflect` | After every session | Reads transcript, detects gaps, proposes improvements |
| `/runbook-wiki-ingest` | When configs change | Compiles SLO configs + service manifests into wiki pages |

---

## Wiki Structure

```
wiki/
├── incidents/
│   ├── _index.md          ← symptom triage — start here
│   ├── high-latency.md
│   ├── service-down.md
│   └── db-connection-failure.md
├── services/
│   ├── api-gateway.md     ← SLOs, alerts, common incidents per service
│   └── user-service.md
├── playbooks/
│   ├── _index.md
│   ├── rollback.md
│   ├── escalation.md
│   └── db-failover.md
├── runbooks/
│   └── latency-investigation.md
├── resolutions/           ← past resolved incidents (added over time)
└── learnings.md           ← what the reflect skill has learned and applied
```

---

## Using the Orchestrator

The orchestrator is the CLI that ties everything together. It manages the session lifecycle end-to-end: query → save transcript → reflect → propose → approve/reject → apply.

```bash
pip install rich

# Start an incident query session
python orchestrator.py query

# Re-run reflect on a saved session
python orchestrator.py reflect 20260501T143022Z-demo

# List recent sessions
python orchestrator.py sessions
```

### What a session looks like

```
╭──────────────────────────────────────────────╮
│  DevOps Runbook Wiki                         │
│  Answers from compiled wiki only.            │
╰──────────────────────────────────────────────╯

Session: 20260502T091423Z-a4f2b1

Incident query: api-gateway is returning high latency, p99 > 800ms

╭─ Wiki Answer — confidence high ──────────────╮
│  ## High Latency                             │
│  1. Check distributed traces ...             │
│  2. Check database pool wait time ...        │
│  Sources: wiki/incidents/high-latency.md     │
│           wiki/services/api-gateway.md       │
╰──────────────────────────────────────────────╯

Follow-up question? [y/N]: N
Transcript saved → 20260502T091423Z-a4f2b1-transcript.json

Run reflect analysis on this session? [Y/n]: Y

Loop C — Session went well.
Wiki answered the query confidently. No changes proposed.
```

When a gap is detected:

```
╭─ Reflect Analysis ────────────────────────────╮
│  Loop B — Wiki Gap Detected                  │
│  No wiki page matched query: 'redis cache    │
│  timeout under load'. New page needed.       │
╰───────────────────────────────────────────────╯

  ACTION    FILE                                DESCRIPTION
  CREATE    wiki/incidents/redis-cache-...md   New incident page covering: redis cache timeout

Approve and apply these changes? [y/N]: y
  Created wiki/incidents/redis-cache-timeout-under-load.md
Changes applied. learnings.md updated.
```

## Using the Skills (Claude Code)

### Query during an incident

```
/runbook-wiki api-gateway is returning high latency, p99 > 800ms
```

The skill reads `wiki/incidents/_index.md`, finds the matching incident page, reads the service page for SLO context, and returns a grounded answer with runbook link. It does not run commands.

### After the incident — run reflect

```
/runbook-wiki-reflect <session-id>
```

The reflect skill reads the session transcript, classifies what happened (protocol failure, wiki gap, or session went well), and proposes specific wiki improvements. You approve or reject before anything changes.

### When configs change — ingest

```
/runbook-wiki-ingest services
/runbook-wiki-ingest playbooks
```

Reads from `_git_snapshot/configs/` and `_git_snapshot/manifests/`, compiles structured wiki pages, updates `wiki/incidents/_index.md`.

---

## The Reflect Loop — Three Outcomes

After every session, reflect classifies it into one of three loops:

**Loop A — Protocol fix**: Claude read raw config files or called live tools. The wiki was fine — the skill made a mistake. Proposes a prompt correction, not a wiki change.

**Loop B — Wiki gap**: Claude followed the protocol correctly but the wiki didn't have the answer. Engineer rephrased the question 2+ times, or Claude expressed uncertainty. Proposes specific content to add.

**Loop C — No action**: Session went well. Logs what worked so the pattern isn't changed accidentally.

---

## Key Design Decisions

**Why no live tool calls during queries?** On-call is already high-stress. An assistant that calls kubectl or queries the DB during an incident adds blast radius risk and slows down the query. The wiki is the source of truth — the engineer runs commands, not the assistant.

**Why approve/reject before applying changes?** A reflect agent that auto-applies changes to a runbook wiki is dangerous. Bad proposals get applied at 3am before anyone notices. Every change goes through a human gate.

**Why ingest from raw configs rather than hand-writing wiki pages?** Service SLOs, alert thresholds, and escalation paths live in config files — not in wikis. If you hand-write the wiki, it drifts. Ingest compiles the config into the wiki on demand, keeping them in sync.

---

## Project Structure

```
devops-runbook-wiki/
├── .claude/skills/
│   ├── runbook-wiki/          # query skill
│   ├── runbook-wiki-reflect/  # improvement loop skill
│   └── runbook-wiki-ingest/   # config compiler skill
├── orchestrator.py            # CLI — manages session lifecycle end-to-end
├── tests/
│   └── test_orchestrator.py   # 14 tests covering wiki reading, reflect loop, session management
├── wiki/                      # compiled knowledge base
├── sessions/                  # session transcripts (auto-saved, gitignored)
└── _git_snapshot/             # raw configs (host-managed, read-only, gitignored)
```

---

## Author

Built by [Tanishka Marrott](https://github.com/TanishkaMarrott) — AI Agent Systems Engineer
