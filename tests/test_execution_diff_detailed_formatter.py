from src.engine.execution_diff_formatter import (
    format_context_value_pair,
    format_execution_diff_header,
)


def test_header_uses_a_b_and_basenames():
    header = format_execution_diff_header(
        "examples/real_ai_bug_autopsy_multinode/runs/run_a.json",
        "examples/real_ai_bug_autopsy_multinode/runs/run_b.json",
    )
    assert "A: run_a.json" in header
    assert "B: run_b.json" in header
    assert "left" not in header
    assert "right" not in header


def test_context_pair_uses_a_b_and_compact_raw_summary():
    a_value = {
        "text": {"text": "AAA"},
        "metrics": {"latency_ms": 10, "tokens_used": 20},
        "raw": {"id": "resp_a", "model": "gpt-x", "status": "completed"},
    }
    b_value = {
        "text": {"text": "BBB"},
        "metrics": {"latency_ms": 30, "tokens_used": 40},
        "raw": {"id": "resp_b", "model": "gpt-y", "status": "completed"},
    }

    rendered = format_context_value_pair("output.planner_node", a_value, b_value)

    assert "text (A):" in rendered
    assert "text (B):" in rendered
    assert "A: latency_ms=10, tokens_used=20" in rendered
    assert "B: latency_ms=30, tokens_used=40" in rendered
    assert "A: id=resp_a, model=gpt-x, status=completed" in rendered
    assert "B: id=resp_b, model=gpt-y, status=completed" in rendered
    assert "left" not in rendered
    assert "right" not in rendered
