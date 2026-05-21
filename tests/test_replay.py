"""Smoke tests for agent-replay-debugger-mcp."""
import sys, os, inspect, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    start_recording,
    record_step,
    replay_step,
    timeline,
    branch_from,
    search_steps,
    export_recording,
    sign_recording,
    _RECORDINGS,
)


def test_start_recording():
    _RECORDINGS.clear()
    r = start_recording("Fix bug X")
    assert r["session_id"].startswith("rec_")


def test_record_steps_increment_idx():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    r1 = record_step(sid, "edit file.py", input="x", output="y", model="claude-opus-4.7", input_tokens=100, output_tokens=50, duration_ms=1500, cost_gbp=0.006)
    r2 = record_step(sid, "run tests", output="fail")
    assert r1["step_idx"] == 0
    assert r2["step_idx"] == 1


def test_replay_step():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "edit", input="aaa")
    r = replay_step(sid, 0)
    assert r["step"]["action"] == "edit"


def test_replay_step_out_of_range():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    r = replay_step(sid, 99)
    assert "error" in r


def test_timeline_totals_cost_tokens_ms():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "a", model="claude-opus-4.7", input_tokens=1000, output_tokens=500, cost_gbp=0.06, duration_ms=2000)
    record_step(sid, "b", model="gpt-5", input_tokens=2000, output_tokens=1000, cost_gbp=0.105, duration_ms=3000)
    t = timeline(sid)
    assert t["step_count"] == 2
    assert abs(t["total_cost_gbp"] - 0.165) < 0.001
    assert t["total_tokens"] == 4500
    assert t["total_duration_ms"] == 5000


def test_timeline_filter_by_model():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "a", model="claude-opus-4.7")
    record_step(sid, "b", model="gpt-5")
    record_step(sid, "c", model="claude-opus-4.7")
    t = timeline(sid, model_filter="claude-opus-4.7")
    assert t["step_count"] == 2


def test_branch_from_creates_branch():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "step1")
    record_step(sid, "step2")
    r = branch_from(sid, 1, "alternative-step2")
    assert r["branch_id"].startswith("branch_1_")


def test_search_steps_finds_match():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "fix EU AI Act bug")
    record_step(sid, "run pytest")
    record_step(sid, "deploy to staging")
    r = search_steps(sid, "AI Act")
    assert r["match_count"] >= 1


def test_export_json():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "x")
    r = export_recording(sid, "json")
    assert r["format"] == "json"


def test_export_markdown():
    _RECORDINGS.clear()
    sid = start_recording("test goal")["session_id"]
    record_step(sid, "step1", model="opus", cost_gbp=0.05)
    r = export_recording(sid, "markdown")
    assert "# Recording:" in r["content"]
    assert "step1" in r["content"]


def test_sign_recording():
    _RECORDINGS.clear()
    sid = start_recording("test")["session_id"]
    record_step(sid, "x", cost_gbp=0.5)
    r = sign_recording(sid)
    assert r["signed"] is True
    assert "signature" in r


if __name__ == "__main__":
    g = dict(globals())
    fns = [v for k, v in g.items() if k.startswith("test_") and inspect.isfunction(v)]
    p = f = 0
    for fn in fns:
        try:
            fn(); print(f"✓ {fn.__name__}"); p += 1
        except Exception as e:
            print(f"✗ {fn.__name__}: {type(e).__name__}: {e}"); traceback.print_exc(); f += 1
    print(f"\n{p} passed, {f} failed")
