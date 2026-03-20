"""
execution_diff_formatter.py

Renders RunDiff objects into human-readable text.

Public API:
    format_diff_summary(diff: RunDiff) -> str   — minimal summary (unchanged)
    format_diff_details(diff: RunDiff) -> str   — per-item detail sections
    format_diff(diff: RunDiff) -> str           — summary + details
"""
from __future__ import annotations

from pathlib import Path
from pprint import pformat
from typing import Any
import difflib

from src.engine.execution_diff_model import RunDiff


def format_diff_summary(diff: RunDiff) -> str:
    """Return a minimal human-readable summary of a RunDiff."""
    s = diff.summary
    lines = [
        "Execution Diff",
        f"status: {diff.status}",
        f"nodes: added={s.nodes_added} removed={s.nodes_removed} changed={s.nodes_changed}",
        f"artifacts: added={s.artifacts_added} removed={s.artifacts_removed} changed={s.artifacts_changed}",
        f"context_keys_changed: {s.context_keys_changed}",
    ]
    return "\n".join(lines)


def _basename(path: str | None) -> str:
    if not path:
        return "<unknown>"
    return Path(path).name


def _indent_block(text: str, prefix: str = "      ") -> str:
    lines = text.splitlines() or [text]
    return "\n".join(f"{prefix}{line}" for line in lines)


def _compact_raw_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return repr(value)

    raw = value.get("raw")
    if not isinstance(raw, dict):
        text_block = value.get("text")
        if isinstance(text_block, dict):
            raw = text_block.get("raw")

    if not isinstance(raw, dict):
        return repr(value)

    raw_id = raw.get("id", "?")
    model = raw.get("model", "?")
    status = raw.get("status", "?")
    return f"id={raw_id}, model={model}, status={status}"


def _extract_metrics(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None

    metrics = value.get("metrics")
    if not isinstance(metrics, dict):
        text_block = value.get("text")
        if isinstance(text_block, dict):
            metrics = text_block.get("metrics")

    if not isinstance(metrics, dict):
        return None

    latency_ms = metrics.get("latency_ms")
    tokens_used = metrics.get("tokens_used")
    if latency_ms is None and tokens_used is None:
        return None
    return f"latency_ms={latency_ms}, tokens_used={tokens_used}"


def _extract_text(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    text_block = value.get("text")
    if isinstance(text_block, dict):
        text_value = text_block.get("text")
        if isinstance(text_value, str):
            return text_value
    if isinstance(value.get("text"), str):
        return value["text"]
    return None


def _render_text_diff(a_text: str, b_text: str, max_lines: int = 200, max_chars: int = 5000) -> str | None:
    if len(a_text) > max_chars or len(b_text) > max_chars:
        return None

    a_lines = a_text.splitlines()
    b_lines = b_text.splitlines()

    if len(a_lines) > max_lines or len(b_lines) > max_lines:
        return None

    matcher = difflib.SequenceMatcher(a=a_lines, b=b_lines)
    rendered: list[str] = ["    text diff:", ""]

    label_width = len("[A only]")

    def add_line(label: str, line: str) -> None:
        if line.strip() == "":
            return
        rendered.append(f"      {label:<{label_width}}  {line}")

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in a_lines[i1:i2]:
                add_line("[same]", line)
        elif tag == "delete":
            for line in a_lines[i1:i2]:
                add_line("[A only]", line)
        elif tag == "insert":
            for line in b_lines[j1:j2]:
                add_line("[B only]", line)
        elif tag == "replace":
            for line in a_lines[i1:i2]:
                add_line("[A only]", line)
            for line in b_lines[j1:j2]:
                add_line("[B only]", line)

    if len(rendered) == 2:
        return None

    return "\n".join(rendered)


def format_context_value_pair(label: str, a_value: Any, b_value: Any) -> str:
    lines = [f"  [modified] {label}"]

    a_text = _extract_text(a_value)
    b_text = _extract_text(b_value)

    if a_text is not None or b_text is not None:
        lines.append("")
        lines.append("    text (A):")
        lines.append(_indent_block(a_text or "<none>"))
        lines.append("")
        lines.append("    text (B):")
        lines.append(_indent_block(b_text or "<none>"))

        if a_text is not None and b_text is not None:
            text_diff_rendered = _render_text_diff(a_text, b_text)
            if text_diff_rendered:
                lines.append("")
                lines.append(text_diff_rendered)

    a_metrics = _extract_metrics(a_value)
    b_metrics = _extract_metrics(b_value)
    if a_metrics or b_metrics:
        lines.append("")
        lines.append("    metrics:")
        lines.append(f"      A: {a_metrics or '<none>'}")
        lines.append(f"      B: {b_metrics or '<none>'}")

    lines.append("")
    lines.append("    raw summary:")
    lines.append(f"      A: {_compact_raw_summary(a_value)}")
    lines.append(f"      B: {_compact_raw_summary(b_value)}")

    if a_text is None and b_text is None and not (a_metrics or b_metrics):
        lines.append("")
        lines.append("    value (A):")
        lines.append(_indent_block(pformat(a_value)))
        lines.append("")
        lines.append("    value (B):")
        lines.append(_indent_block(pformat(b_value)))

    return "\n".join(lines)


def format_execution_diff_header(a_path: str | None, b_path: str | None) -> str:
    return "\n".join(
        [
            "Execution Diff",
            "--------------",
            f"A: {_basename(a_path)}",
            f"B: {_basename(b_path)}",
        ]
    )


def format_diff_details(diff: RunDiff) -> str:
    """Return per-item detail sections for nodes, artifacts, and context."""
    sections: list[str] = []

    if diff.node_diffs:
        lines = ["Node Changes", "-" * 12]
        for nd in diff.node_diffs:
            lines.append(f"  [{nd.change_type}] {nd.node_id}")
            if nd.left_status or nd.right_status:
                lines.append(f"    status: {nd.left_status} -> {nd.right_status}")
            if nd.left_output_ref or nd.right_output_ref:
                lines.append(f"    output_ref: {nd.left_output_ref} -> {nd.right_output_ref}")
            if nd.artifact_ids_added:
                lines.append(f"    artifacts added: {', '.join(nd.artifact_ids_added)}")
            if nd.artifact_ids_removed:
                lines.append(f"    artifacts removed: {', '.join(nd.artifact_ids_removed)}")
            if nd.artifact_ids_changed:
                lines.append(f"    artifacts changed: {', '.join(nd.artifact_ids_changed)}")
        sections.append("\n".join(lines))

    if diff.artifact_diffs:
        lines = ["Artifact Changes", "-" * 16]
        for ad in diff.artifact_diffs:
            lines.append(f"  [{ad.change_type}] {ad.artifact_id}")
            if ad.left_hash or ad.right_hash:
                lines.append(f"    hash: {ad.left_hash} -> {ad.right_hash}")
            if ad.left_kind or ad.right_kind:
                lines.append(f"    kind: {ad.left_kind} -> {ad.right_kind}")
        sections.append("\n".join(lines))

    if diff.context_diffs:
        lines = ["Context Changes", "-" * 15]
        for cd in diff.context_diffs:
            lines.append(format_context_value_pair(cd.context_key, cd.left_value, cd.right_value))
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_diff(diff: RunDiff) -> str:
    """Return complete diff output: summary + detail sections."""
    summary = format_diff_summary(diff)
    details = format_diff_details(diff)
    if details:
        return summary + "\n\n" + details
    return summary


def format_diff_json(diff: RunDiff) -> dict:
    """Return a machine-readable dict representation of a RunDiff."""
    s = diff.summary

    return {
        "status": diff.status,
        "summary": {
            "nodes_added":           s.nodes_added,
            "nodes_removed":         s.nodes_removed,
            "nodes_changed":         s.nodes_changed,
            "artifacts_added":       s.artifacts_added,
            "artifacts_removed":     s.artifacts_removed,
            "artifacts_changed":     s.artifacts_changed,
            "trace_keys_changed":    s.trace_keys_changed,
            "context_keys_changed":  s.context_keys_changed,
        },
        "nodes": [
            {
                "node_id":               nd.node_id,
                "change_type":           nd.change_type,
                "left_status":           nd.left_status,
                "right_status":          nd.right_status,
                "left_output_ref":       nd.left_output_ref,
                "right_output_ref":      nd.right_output_ref,
                "artifact_ids_added":    nd.artifact_ids_added,
                "artifact_ids_removed":  nd.artifact_ids_removed,
                "artifact_ids_changed":  nd.artifact_ids_changed,
            }
            for nd in diff.node_diffs
        ],
        "artifacts": [
            {
                "artifact_id":  ad.artifact_id,
                "change_type":  ad.change_type,
                "left_hash":    ad.left_hash,
                "right_hash":   ad.right_hash,
                "left_kind":    ad.left_kind,
                "right_kind":   ad.right_kind,
            }
            for ad in diff.artifact_diffs
        ],
        "context": [
            {
                "context_key": cd.context_key,
                "change_type": cd.change_type,
                "left_value":  cd.left_value,
                "right_value": cd.right_value,
            }
            for cd in diff.context_diffs
        ],
    }
