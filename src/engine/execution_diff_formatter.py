"""
execution_diff_formatter.py

Renders RunDiff objects into human-readable text.

Public API:
    format_diff_summary(diff: RunDiff) -> str   — minimal summary (unchanged)
    format_diff_details(diff: RunDiff) -> str   — per-item detail sections
    format_diff(diff: RunDiff) -> str           — summary + details
"""
from __future__ import annotations

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


def format_diff_details(diff: RunDiff) -> str:
    """Return per-item detail sections for nodes, artifacts, and context."""
    sections: list[str] = []

    # --- Node Changes ---
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

    # --- Artifact Changes ---
    if diff.artifact_diffs:
        lines = ["Artifact Changes", "-" * 16]
        for ad in diff.artifact_diffs:
            lines.append(f"  [{ad.change_type}] {ad.artifact_id}")
            if ad.left_hash or ad.right_hash:
                lines.append(f"    hash: {ad.left_hash} -> {ad.right_hash}")
            if ad.left_kind or ad.right_kind:
                lines.append(f"    kind: {ad.left_kind} -> {ad.right_kind}")
        sections.append("\n".join(lines))

    # --- Context Changes ---
    if diff.context_diffs:
        lines = ["Context Changes", "-" * 15]
        for cd in diff.context_diffs:
            lines.append(f"  [{cd.change_type}] {cd.context_key}")
            lines.append(f"    {cd.left_value!r} -> {cd.right_value!r}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_diff(diff: RunDiff) -> str:
    """Return complete diff output: summary + detail sections."""
    summary = format_diff_summary(diff)
    details = format_diff_details(diff)
    if details:
        return summary + "\n\n" + details
    return summary
