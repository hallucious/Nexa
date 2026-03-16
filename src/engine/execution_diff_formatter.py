"""
execution_diff_formatter.py

Renders RunDiff objects into human-readable text.

Responsibilities:
- accept a RunDiff instance
- return formatted text strings
- contain no engine logic (diff computation is done by execution_diff_engine.py)
- contain no file I/O

Public API:
    format_diff_summary(diff: RunDiff) -> str
"""
from __future__ import annotations

from src.engine.execution_diff_model import RunDiff


def format_diff_summary(diff: RunDiff) -> str:
    """Return a minimal human-readable summary of a RunDiff.

    Output format:
        Execution Diff
        status: <status>
        nodes: added=<n> removed=<n> changed=<n>
        artifacts: added=<n> removed=<n> changed=<n>
        context_keys_changed: <n>
    """
    s = diff.summary
    lines = [
        "Execution Diff",
        f"status: {diff.status}",
        f"nodes: added={s.nodes_added} removed={s.nodes_removed} changed={s.nodes_changed}",
        f"artifacts: added={s.artifacts_added} removed={s.artifacts_removed} changed={s.artifacts_changed}",
        f"context_keys_changed: {s.context_keys_changed}",
    ]
    return "\n".join(lines)
