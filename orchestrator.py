"""
Runbook wiki orchestrator — manages session lifecycle end-to-end.

Flow:
  query → answer from wiki → save transcript → (optional) reflect → propose → approve/reject → apply
"""

from __future__ import annotations

import json
import re
import sys
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

WIKI_DIR = Path(__file__).parent / "wiki"
SESSIONS_DIR = Path(__file__).parent / "sessions"
LEARNINGS_FILE = WIKI_DIR / "learnings.md"
SESSIONS_DIR.mkdir(exist_ok=True)

console = Console()


# ---------------------------------------------------------------------------
# Wiki reading helpers
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _index_symptoms() -> dict[str, str]:
    """Parse wiki/incidents/_index.md symptom → page mapping."""
    index = _read_file(WIKI_DIR / "incidents" / "_index.md")
    mapping: dict[str, str] = {}
    for line in index.splitlines():
        # Markdown table row: | symptom | page |
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 2 and not parts[0].startswith("-") and parts[0].lower() != "symptom":
            symptom = parts[0].lower()
            page_ref = parts[1].lower().replace(" ", "-").strip("`[]()")
            mapping[symptom] = page_ref
    return mapping


def _find_incident_page(query: str) -> str | None:
    """Return incident page path that best matches the query, or None."""
    query_lower = query.lower()
    candidates = list((WIKI_DIR / "incidents").glob("*.md"))
    candidates = [c for c in candidates if c.name != "_index.md"]

    # Score by keyword overlap with filename and file content
    scored: list[tuple[float, Path]] = []
    for page in candidates:
        text = page.read_text().lower()
        name_score = sum(1 for word in re.findall(r"\w+", query_lower) if word in page.stem)
        content_score = sum(1 for word in re.findall(r"\w+", query_lower) if word in text)
        scored.append((name_score * 2 + content_score, page))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0:
        return str(scored[0][1])
    return None


def _find_service_page(query: str) -> str | None:
    query_lower = query.lower()
    for page in (WIKI_DIR / "services").glob("*.md"):
        if page.stem.replace("-", " ") in query_lower or any(
            w in query_lower for w in page.stem.split("-")
        ):
            return str(page)
    return None


def answer_from_wiki(query: str) -> dict:
    """
    Answer the query using only wiki content — no live tool calls.
    Returns dict with answer text, sources used, confidence.
    """
    sources: list[str] = []
    sections: list[str] = []

    # Always read the symptom index
    index_path = WIKI_DIR / "incidents" / "_index.md"
    index_text = _read_file(index_path)
    if index_text:
        sources.append("wiki/incidents/_index.md")

    # Find the best matching incident page
    incident_path = _find_incident_page(query)
    if incident_path:
        incident_text = _read_file(Path(incident_path))
        sections.append(incident_text)
        sources.append(incident_path.replace(str(WIKI_DIR.parent) + "/", ""))

    # Find service page if mentioned
    service_path = _find_service_page(query)
    if service_path:
        service_text = _read_file(Path(service_path))
        sections.append(service_text)
        sources.append(service_path.replace(str(WIKI_DIR.parent) + "/", ""))

    # Only include playbook index if we already have a matching incident or service page
    if incident_path or service_path:
        playbook_dir = WIKI_DIR / "playbooks"
        playbook_index = _read_file(playbook_dir / "_index.md")
        if playbook_index:
            sections.append(playbook_index)
            sources.append("wiki/playbooks/_index.md")

    if not sections:
        return {
            "answer": (
                "No matching wiki page found for this query. "
                "The wiki may not cover this incident type yet. "
                "Consider running `/runbook-wiki-reflect` after this session to propose new content."
            ),
            "sources": sources,
            "confidence": "low",
            "gap_detected": True,
        }

    combined = "\n\n---\n\n".join(sections)

    # Extract the most relevant excerpt (first matching section)
    answer_lines: list[str] = []
    in_relevant = False
    query_keywords = set(re.findall(r"\w{4,}", query.lower()))

    for line in combined.splitlines():
        line_lower = line.lower()
        if any(kw in line_lower for kw in query_keywords):
            in_relevant = True
        if in_relevant:
            answer_lines.append(line)
        if len(answer_lines) > 60:
            break

    answer = "\n".join(answer_lines) if answer_lines else combined[:2000]

    return {
        "answer": answer.strip(),
        "sources": list(dict.fromkeys(sources)),  # deduplicate preserving order
        "confidence": "high" if incident_path else "medium",
        "gap_detected": False,
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def new_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = uuid.uuid4().hex[:6]
    return f"{ts}-{short}"


def save_transcript(session_id: str, query: str, result: dict, follow_ups: list[dict]) -> Path:
    transcript = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "response": result,
        "follow_ups": follow_ups,
        "gap_detected": result.get("gap_detected", False) or len(follow_ups) >= 2,
    }
    path = SESSIONS_DIR / f"{session_id}-transcript.json"
    path.write_text(json.dumps(transcript, indent=2))
    return path


# ---------------------------------------------------------------------------
# Reflect — gap analysis
# ---------------------------------------------------------------------------

def reflect_on_session(transcript_path: Path) -> dict | None:
    """
    Analyse session transcript and return a proposal dict, or None if no action needed.
    Implements Loop A/B/C classification.
    """
    data = json.loads(transcript_path.read_text())
    gap = data.get("gap_detected", False)
    confidence = data.get("response", {}).get("confidence", "high")
    follow_up_count = len(data.get("follow_ups", []))
    query = data.get("query", "")

    # Loop C — session went well
    if not gap and confidence == "high" and follow_up_count == 0:
        return None

    # Loop A — protocol failure (answer came from outside wiki — not possible in this impl)
    # Loop B — wiki gap
    proposal: dict = {
        "loop": "B",
        "session_id": data["session_id"],
        "query": query,
        "finding": "",
        "proposed_changes": [],
    }

    if not data.get("response", {}).get("sources"):
        proposal["finding"] = f"No wiki page matched query: '{query}'. New incident page needed."
        # Infer page slug from query
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower())[:40].strip("-")
        proposal["proposed_changes"].append({
            "action": "create",
            "path": f"wiki/incidents/{slug}.md",
            "description": f"New incident page covering: {query}",
            "draft": _draft_incident_page(query),
        })
    elif follow_up_count >= 2 or confidence == "medium":
        proposal["finding"] = (
            f"Engineer asked {follow_up_count + 1} questions before getting a useful answer. "
            f"Existing pages matched but may lack depth."
        )
        sources = data.get("response", {}).get("sources", [])
        for src in sources:
            if "incidents/" in src and "_index" not in src:
                proposal["proposed_changes"].append({
                    "action": "augment",
                    "path": src,
                    "description": f"Add more detail to cover: {query}",
                    "draft": None,
                })

    return proposal if proposal["proposed_changes"] else None


def _draft_incident_page(query: str) -> str:
    title = query.strip().rstrip("?.").title()
    return textwrap.dedent(f"""\
        # {title}

        ## Symptoms

        <!-- Describe observable symptoms here -->

        ## Immediate checks

        ```bash
        # Add diagnostic commands here
        ```

        ## Root causes

        | Cause | How to identify | Fix |
        |---|---|---|
        | <!-- cause --> | <!-- signal --> | <!-- action --> |

        ## Resolution

        <!-- Step-by-step resolution -->

        ## Escalation

        If not resolved in 15 minutes → [escalation playbook](../playbooks/escalation.md)
    """)


# ---------------------------------------------------------------------------
# Apply approved changes
# ---------------------------------------------------------------------------

def apply_change(change: dict) -> None:
    path = Path(__file__).parent / change["path"]
    path.parent.mkdir(parents=True, exist_ok=True)

    if change["action"] == "create":
        if path.exists():
            console.print(f"[yellow]  Skipped — {change['path']} already exists[/yellow]")
        else:
            path.write_text(change["draft"])
            console.print(f"[green]  Created {change['path']}[/green]")

    elif change["action"] == "augment":
        console.print(
            f"[cyan]  Flagged for augmentation: {change['path']}[/cyan]\n"
            f"  Open the file and add detail covering: {change['description']}"
        )


def append_to_learnings(proposal: dict, approved: bool) -> None:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sid = proposal["session_id"]
    loop = proposal["loop"]
    finding = proposal["finding"]

    if approved:
        changes = "; ".join(
            f"{c['action']} {c['path']}" for c in proposal["proposed_changes"]
        )
        entry = (
            f"\n## {date} — Session {sid}\n"
            f"**Loop**: {loop}\n"
            f"**Finding**: {finding}\n"
            f"**Applied**: {changes}\n"
        )
    else:
        entry = (
            f"\n## {date} — Session {sid}\n"
            f"**Loop**: {loop}\n"
            f"**Finding**: {finding}\n"
            f"**Applied**: rejected — wiki unchanged\n"
        )

    content = LEARNINGS_FILE.read_text()
    LEARNINGS_FILE.write_text(content + entry)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def show_answer(result: dict, query: str) -> None:
    confidence_color = {"high": "green", "medium": "yellow", "low": "red"}.get(
        result["confidence"], "white"
    )
    console.print(
        Panel(
            Markdown(result["answer"]),
            title=f"[bold]Wiki Answer[/bold] — confidence [{confidence_color}]{result['confidence']}[/{confidence_color}]",
            border_style="blue",
        )
    )
    if result["sources"]:
        console.print("[dim]Sources:[/dim]")
        for src in result["sources"]:
            console.print(f"  [dim]• {src}[/dim]")
    console.print()


def show_proposal(proposal: dict) -> None:
    console.print(
        Panel(
            f"[bold]Loop {proposal['loop']} — Wiki Gap Detected[/bold]\n\n"
            f"[yellow]{proposal['finding']}[/yellow]",
            border_style="yellow",
            title="Reflect Analysis",
        )
    )
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("File")
    table.add_column("Description")
    for change in proposal["proposed_changes"]:
        table.add_row(change["action"].upper(), change["path"], change["description"])
    console.print(table)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def run_query_session() -> None:
    """Interactive session: query → answer → optional reflect loop."""
    console.print(
        Panel(
            "[bold blue]DevOps Runbook Wiki[/bold blue]\n"
            "Answers from compiled wiki only. No live tool calls.",
            border_style="blue",
        )
    )

    session_id = new_session_id()
    console.print(f"[dim]Session: {session_id}[/dim]\n")

    query = Prompt.ask("[bold]Incident query[/bold]")
    if not query.strip():
        console.print("[red]Empty query — exiting.[/red]")
        return

    # Answer from wiki
    result = answer_from_wiki(query)
    show_answer(result, query)

    # Collect follow-up questions in same session
    follow_ups: list[dict] = []
    while True:
        more = Confirm.ask("Follow-up question?", default=False)
        if not more:
            break
        fq = Prompt.ask("[bold]Follow-up[/bold]")
        fr = answer_from_wiki(fq)
        show_answer(fr, fq)
        follow_ups.append({"query": fq, "response": fr})

    # Save transcript
    transcript_path = save_transcript(session_id, query, result, follow_ups)
    console.print(f"[dim]Transcript saved → {transcript_path.name}[/dim]\n")

    # Offer reflect
    run_reflect = Confirm.ask("Run reflect analysis on this session?", default=True)
    if not run_reflect:
        console.print("[dim]Session closed. Run /runbook-wiki-reflect later if needed.[/dim]")
        return

    proposal = reflect_on_session(transcript_path)

    if proposal is None:
        console.print(
            Panel(
                "[green]Loop C — Session went well.[/green]\n"
                "Wiki answered the query confidently with no follow-ups. No changes proposed.",
                border_style="green",
                title="Reflect",
            )
        )
        append_to_learnings(
            {
                "loop": "C",
                "session_id": session_id,
                "finding": "Session resolved cleanly — no wiki gap detected.",
                "proposed_changes": [],
            },
            approved=True,
        )
        return

    show_proposal(proposal)

    approved = Confirm.ask("\nApprove and apply these changes?", default=False)

    if approved:
        console.print("\n[bold]Applying changes…[/bold]")
        for change in proposal["proposed_changes"]:
            apply_change(change)
        append_to_learnings(proposal, approved=True)
        console.print("\n[green]Changes applied. learnings.md updated.[/green]")
    else:
        append_to_learnings(proposal, approved=False)
        console.print("[dim]Proposal rejected. Logged to learnings.md.[/dim]")


def run_reflect_only(session_id: str) -> None:
    """Re-run reflect on a saved transcript by session ID."""
    pattern = f"{session_id}-transcript.json"
    matches = list(SESSIONS_DIR.glob(pattern))
    if not matches:
        # Try partial match
        matches = [p for p in SESSIONS_DIR.glob("*-transcript.json") if session_id in p.name]

    if not matches:
        console.print(f"[red]No transcript found for session: {session_id}[/red]")
        console.print("Available sessions:")
        for p in sorted(SESSIONS_DIR.glob("*-transcript.json")):
            console.print(f"  {p.stem}")
        return

    transcript_path = matches[0]
    console.print(f"[dim]Reading transcript: {transcript_path.name}[/dim]\n")

    proposal = reflect_on_session(transcript_path)

    if proposal is None:
        console.print("[green]No action needed — session resolved cleanly.[/green]")
        return

    show_proposal(proposal)
    approved = Confirm.ask("\nApprove and apply these changes?", default=False)

    if approved:
        for change in proposal["proposed_changes"]:
            apply_change(change)
        append_to_learnings(proposal, approved=True)
        console.print("[green]Changes applied.[/green]")
    else:
        append_to_learnings(proposal, approved=False)
        console.print("[dim]Proposal rejected.[/dim]")


def list_sessions() -> None:
    transcripts = sorted(SESSIONS_DIR.glob("*-transcript.json"), reverse=True)
    if not transcripts:
        console.print("[dim]No sessions yet.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Session ID")
    table.add_column("Query")
    table.add_column("Confidence")
    table.add_column("Gap")
    table.add_column("Follow-ups")

    for tp in transcripts[:20]:
        data = json.loads(tp.read_text())
        sid = data.get("session_id", tp.stem)
        query = data.get("query", "")[:60]
        conf = data.get("response", {}).get("confidence", "?")
        gap = "yes" if data.get("gap_detected") else "no"
        fups = str(len(data.get("follow_ups", [])))
        table.add_row(sid, query, conf, gap, fups)

    console.print(table)


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("query", "q"):
        run_query_session()

    elif args[0] in ("reflect", "r"):
        if len(args) < 2:
            console.print("[red]Usage: python orchestrator.py reflect <session-id>[/red]")
            sys.exit(1)
        run_reflect_only(args[1])

    elif args[0] in ("sessions", "ls"):
        list_sessions()

    else:
        console.print(
            "[bold]DevOps Runbook Wiki Orchestrator[/bold]\n\n"
            "Commands:\n"
            "  python orchestrator.py query            — start an incident query session\n"
            "  python orchestrator.py reflect <id>     — re-run reflect on a saved session\n"
            "  python orchestrator.py sessions         — list recent sessions\n"
        )


if __name__ == "__main__":
    main()
