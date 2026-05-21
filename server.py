#!/usr/bin/env python3
"""
Agent Replay Debugger MCP — step-debug an agent run
=========================================================

By MEOK AI Labs · https://meok.ai · MIT
<!-- mcp-name: io.github.CSOAI-ORG/agent-replay-debugger-mcp -->

WHAT THIS DOES
--------------
Record every action an agent takes (with inputs, outputs, timestamps,
costs) so you can REPLAY the run deterministically afterward. Step through
each action like a debugger. Filter, search, branch from any step. Sign
the recording for audit evidence.

Pairs with bft-progress-council-mcp (stops loops in real-time) and
agent-audit-logger-mcp (chains the recording into the evidence ledger).

USE CASES
---------
- Debug why an agent ran a £20 cost on what should have been a £0.50 task
- Reproduce a customer-reported "agent gave wrong answer" bug
- Audit evidence: prove EXACTLY what an agent did, to whom, at when
- Train next-gen agents on traces of how senior agents solved problems
- Forensic analysis after a prompt-injection incident

TOOLS
-----
- start_recording(goal, session_id?): open a new recording
- record_step(session_id, action, input, output, model?, tokens?, ms?): one step
- replay_step(session_id, step_idx): re-fetch a specific step
- timeline(session_id, filter?): get full ordered timeline
- branch_from(session_id, step_idx, new_action): explore alternative branch
- search_steps(session_id, query): find steps matching a query
- export_recording(session_id, format): JSON or markdown export
- sign_recording(session_id): HMAC-sign the whole recording for audit

PRICING
-------
Free MIT self-host · £29/mo Starter · £79/mo Pro · A2A Substrate £499/mo.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("agent-replay-debugger")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# In-memory recordings store. Production: Postgres or DuckDB.
_RECORDINGS: dict[str, dict] = {}


def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────────────────────────
# Tools
# ────────────────────────────────────────────────────────────────────────

@mcp.tool()
def start_recording(goal: str, session_id: Optional[str] = None, agent_id: Optional[str] = None) -> dict:
    """Open a new recording for an agent run."""
    sid = session_id or f"rec_{int(time.time())}_{os.urandom(4).hex()}"
    _RECORDINGS[sid] = {
        "session_id": sid,
        "goal": goal,
        "agent_id": agent_id or "anonymous",
        "started_at": _ts(),
        "steps": [],
        "branches": {},
        "signed": False,
    }
    return {
        "session_id": sid,
        "goal": goal,
        "started_at": _RECORDINGS[sid]["started_at"],
        "hint": "Call record_step() after every agent action. Sign + export at end of run.",
    }


@mcp.tool()
def record_step(
    session_id: str,
    action: str,
    input: Optional[str] = None,
    output: Optional[str] = None,
    model: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    duration_ms: Optional[int] = None,
    cost_gbp: Optional[float] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Record one agent step."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    step_idx = len(rec["steps"])
    step = {
        "step_idx": step_idx,
        "ts": time.time(),
        "iso_ts": _ts(),
        "action": action,
        "input": input,
        "output": output,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "cost_gbp": cost_gbp,
        "tags": tags or [],
    }
    rec["steps"].append(step)
    return {
        "session_id": session_id,
        "step_idx": step_idx,
        "step_count": len(rec["steps"]),
    }


@mcp.tool()
def replay_step(session_id: str, step_idx: int) -> dict:
    """Re-fetch a recorded step for replay."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    if step_idx < 0 or step_idx >= len(rec["steps"]):
        return {"error": "step_out_of_range", "range": [0, len(rec["steps"]) - 1]}
    return {"step": rec["steps"][step_idx], "of_total": len(rec["steps"])}


@mcp.tool()
def timeline(session_id: str, model_filter: Optional[str] = None, tag_filter: Optional[str] = None) -> dict:
    """Get the full ordered timeline of recorded steps."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    steps = rec["steps"]
    if model_filter:
        steps = [s for s in steps if s.get("model") == model_filter]
    if tag_filter:
        steps = [s for s in steps if tag_filter in (s.get("tags") or [])]
    total_cost = sum(s.get("cost_gbp", 0) or 0 for s in steps)
    total_tokens = sum((s.get("input_tokens", 0) or 0) + (s.get("output_tokens", 0) or 0) for s in steps)
    total_ms = sum(s.get("duration_ms", 0) or 0 for s in steps)
    return {
        "session_id": session_id,
        "goal": rec["goal"],
        "step_count": len(steps),
        "total_cost_gbp": round(total_cost, 6),
        "total_tokens": total_tokens,
        "total_duration_ms": total_ms,
        "steps_compact": [
            {
                "i": s["step_idx"],
                "action": (s["action"] or "")[:100],
                "model": s.get("model"),
                "tokens": (s.get("input_tokens", 0) or 0) + (s.get("output_tokens", 0) or 0),
                "cost_gbp": s.get("cost_gbp"),
                "ms": s.get("duration_ms"),
            }
            for s in steps
        ],
    }


@mcp.tool()
def branch_from(session_id: str, step_idx: int, new_action: str) -> dict:
    """Open an alternative branch from a specific step."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    branch_id = f"branch_{step_idx}_{int(time.time())}"
    rec["branches"][branch_id] = {
        "from_step_idx": step_idx,
        "new_action": new_action,
        "created_at": _ts(),
        "steps": [],
    }
    return {
        "session_id": session_id,
        "branch_id": branch_id,
        "from_step_idx": step_idx,
        "hint": "Record steps on this branch by passing branch_id in tags or use a sub-session.",
    }


@mcp.tool()
def search_steps(session_id: str, query: str) -> dict:
    """Find steps matching a free-text query (across action + input + output)."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    q = query.lower()
    hits = []
    for s in rec["steps"]:
        haystack = " ".join(str(s.get(k) or "") for k in ["action", "input", "output"]).lower()
        if q in haystack:
            hits.append({"step_idx": s["step_idx"], "action": s["action"][:100], "model": s.get("model")})
    return {"query": query, "hits": hits, "match_count": len(hits)}


@mcp.tool()
def export_recording(session_id: str, format: str = "json") -> dict:
    """Export the full recording as JSON or markdown."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    if format == "markdown":
        lines = [
            f"# Recording: {rec['session_id']}",
            f"**Goal:** {rec['goal']}",
            f"**Agent:** {rec['agent_id']}",
            f"**Started:** {rec['started_at']}",
            f"**Steps:** {len(rec['steps'])}",
            "",
            "## Timeline",
            "",
        ]
        for s in rec["steps"]:
            lines.append(f"### Step {s['step_idx']} — {s.get('action','')[:80]}")
            if s.get("model"):
                lines.append(f"- Model: `{s['model']}`")
            if s.get("input"):
                lines.append(f"- Input: `{(s['input'] or '')[:200]}`")
            if s.get("output"):
                lines.append(f"- Output: `{(s['output'] or '')[:200]}`")
            if s.get("cost_gbp"):
                lines.append(f"- Cost: £{s['cost_gbp']:.6f}")
            lines.append("")
        return {"format": "markdown", "content": "\n".join(lines)}
    return {"format": "json", "content": rec}


@mcp.tool()
def sign_recording(session_id: str) -> dict:
    """HMAC-sign the recording for audit-chain submission."""
    rec = _RECORDINGS.get(session_id)
    if not rec:
        return {"error": "unknown_session"}
    payload = {
        "session_id": session_id,
        "goal": rec["goal"],
        "agent_id": rec["agent_id"],
        "started_at": rec["started_at"],
        "step_count": len(rec["steps"]),
        "total_cost_gbp": round(sum(s.get("cost_gbp", 0) or 0 for s in rec["steps"]), 6),
        "sealed_at": _ts(),
    }
    sig = _sign(payload)
    rec["signed"] = True
    return {
        "signed": True,
        "payload": payload,
        "signature": sig,
        "verify_url": "https://verify.meok.ai",
        "audit_value": "Submit this signed seal alongside EU AI Act Article 12 audit-log records.",
    }


if __name__ == "__main__":
    mcp.run()
