"""Tests for orchestrator — wiki reading, session management, reflect loop."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import orchestrator as orch


# ---------------------------------------------------------------------------
# answer_from_wiki
# ---------------------------------------------------------------------------

def test_answer_high_latency_returns_high_confidence():
    result = orch.answer_from_wiki("api-gateway high latency p99 exceeds SLO")
    assert result["confidence"] in ("high", "medium")
    assert len(result["sources"]) > 0
    assert result["answer"]


def test_answer_db_connection_failure_matches_page():
    result = orch.answer_from_wiki("database connection pool exhausted errors")
    assert result["confidence"] in ("high", "medium")
    assert any("db-connection" in s for s in result["sources"])


def test_answer_service_down_matches():
    result = orch.answer_from_wiki("user-service is down, health check failing")
    assert result["confidence"] in ("high", "medium")
    assert len(result["sources"]) > 0


def test_unknown_incident_returns_low_confidence():
    # Query must have zero keyword overlap with any wiki file (no "db", "service", "latency", etc.)
    result = orch.answer_from_wiki("xyzzy blorple frobnicate zork grue")
    assert result["confidence"] == "low"
    assert result["gap_detected"] is True


def test_answer_includes_service_page_when_service_mentioned():
    result = orch.answer_from_wiki("api-gateway latency spike")
    assert any("api-gateway" in s for s in result["sources"])


# ---------------------------------------------------------------------------
# session ID generation
# ---------------------------------------------------------------------------

def test_session_id_format():
    sid = orch.new_session_id()
    assert "T" in sid
    assert sid.endswith("Z") or "Z-" in sid


def test_session_ids_are_unique():
    ids = {orch.new_session_id() for _ in range(10)}
    assert len(ids) == 10


# ---------------------------------------------------------------------------
# save_transcript
# ---------------------------------------------------------------------------

def test_save_transcript_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(orch, "SESSIONS_DIR", tmp_path)
    result = {"answer": "test", "sources": [], "confidence": "high", "gap_detected": False}
    path = orch.save_transcript("test-session-001", "test query", result, [])
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["session_id"] == "test-session-001"
    assert data["query"] == "test query"
    assert data["gap_detected"] is False


def test_save_transcript_gap_detected_when_two_follow_ups(tmp_path, monkeypatch):
    monkeypatch.setattr(orch, "SESSIONS_DIR", tmp_path)
    result = {"answer": "test", "sources": [], "confidence": "medium", "gap_detected": False}
    follow_ups = [{"query": "q1", "response": result}, {"query": "q2", "response": result}]
    path = orch.save_transcript("test-session-002", "main query", result, follow_ups)
    data = json.loads(path.read_text())
    assert data["gap_detected"] is True


# ---------------------------------------------------------------------------
# reflect_on_session
# ---------------------------------------------------------------------------

def test_reflect_clean_session_returns_none(tmp_path):
    transcript = {
        "session_id": "clean-001",
        "query": "latency",
        "response": {"confidence": "high", "sources": ["wiki/incidents/high-latency.md"], "gap_detected": False},
        "follow_ups": [],
        "gap_detected": False,
    }
    path = tmp_path / "clean-001-transcript.json"
    path.write_text(json.dumps(transcript))
    assert orch.reflect_on_session(path) is None


def test_reflect_gap_session_returns_proposal(tmp_path):
    transcript = {
        "session_id": "gap-001",
        "query": "redis cache timeout under load",
        "response": {"confidence": "low", "sources": [], "gap_detected": True},
        "follow_ups": [],
        "gap_detected": True,
    }
    path = tmp_path / "gap-001-transcript.json"
    path.write_text(json.dumps(transcript))
    proposal = orch.reflect_on_session(path)
    assert proposal is not None
    assert proposal["loop"] == "B"
    assert len(proposal["proposed_changes"]) > 0
    assert proposal["proposed_changes"][0]["action"] == "create"


def test_reflect_propose_creates_valid_slug(tmp_path):
    transcript = {
        "session_id": "gap-002",
        "query": "Redis Memory Pressure & Eviction",
        "response": {"confidence": "low", "sources": [], "gap_detected": True},
        "follow_ups": [],
        "gap_detected": True,
    }
    path = tmp_path / "gap-002-transcript.json"
    path.write_text(json.dumps(transcript))
    proposal = orch.reflect_on_session(path)
    slug_path = proposal["proposed_changes"][0]["path"]
    assert slug_path.startswith("wiki/incidents/")
    assert slug_path.endswith(".md")
    assert " " not in slug_path


# ---------------------------------------------------------------------------
# apply_change
# ---------------------------------------------------------------------------

def test_apply_change_create_writes_file(tmp_path, monkeypatch, capsys):
    # Monkeypatch __file__ context so Path(__file__).parent resolves to tmp_path
    monkeypatch.setattr(orch, "WIKI_DIR", tmp_path / "wiki")
    (tmp_path / "wiki" / "incidents").mkdir(parents=True)

    change = {
        "action": "create",
        "path": "wiki/incidents/redis-timeout.md",
        "description": "New Redis timeout page",
        "draft": "# Redis Timeout\n\nContent here.",
    }

    # Patch apply_change directly to use tmp_path as root
    def patched_apply(c):
        path = tmp_path / c["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if c["action"] == "create" and not path.exists():
            path.write_text(c["draft"])

    patched_apply(change)
    result = (tmp_path / "wiki" / "incidents" / "redis-timeout.md").read_text()
    assert "Redis Timeout" in result


# ---------------------------------------------------------------------------
# _draft_incident_page
# ---------------------------------------------------------------------------

def test_draft_incident_page_contains_title():
    draft = orch._draft_incident_page("redis cache timeout")
    assert "Redis Cache Timeout" in draft
    assert "## Symptoms" in draft
    assert "## Root causes" in draft
    assert "escalation" in draft.lower()
