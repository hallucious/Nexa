"""
execution_diff_engine.py

Diff engine that computes RunDiff between two execution run snapshots.

This module is a pure comparison layer.

Invariants:
- No file I/O
- No engine mutation
- No runtime imports
- Deterministic output
- Side-effect free
- No pipeline concepts

Input contract (run snapshot dict):
  {
    "run_id": str,
    "nodes": {
      "<node_id>": {
        "status": str,                         # optional
        "output": any,                         # optional
        "output_ref": str,                     # optional
        "artifacts": {                         # optional
          "<artifact_id>": {
            "hash": str | None,
            "kind": str | None,
          }
        },
        "dependencies": list[str],             # optional
        "metadata": dict,                      # optional
      }
    },
    "artifacts": {                             # optional top-level artifact map
      "<artifact_id>": {
        "hash": str | None,
        "kind": str | None,
      }
    },
    "context": {                               # optional working context snapshot
      "<context_key>": any,
    }
  }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    CHANGE_TYPE_UNCHANGED,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_IDENTICAL,
    ArtifactDiff,
    ContextDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
    TraceDiff,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_nodes(run: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return dict(run.get("nodes") or {})


def _get_artifacts(run: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return dict(run.get("artifacts") or {})


def _get_context(run: Dict[str, Any]) -> Dict[str, Any]:
    return dict(run.get("context") or {})


def _get_node_artifacts(node: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return dict(node.get("artifacts") or {})


def _diff_artifact_maps(
    left_artifacts: Dict[str, Dict[str, Any]],
    right_artifacts: Dict[str, Dict[str, Any]],
) -> List[ArtifactDiff]:
    """Compare two artifact maps and return a list of ArtifactDiff."""
    diffs: List[ArtifactDiff] = []
    all_ids = sorted(set(left_artifacts) | set(right_artifacts))

    for art_id in all_ids:
        in_left = art_id in left_artifacts
        in_right = art_id in right_artifacts

        if in_left and not in_right:
            la = left_artifacts[art_id]
            diffs.append(ArtifactDiff(
                artifact_id=art_id,
                change_type=CHANGE_TYPE_REMOVED,
                left_hash=la.get("hash"),
                left_kind=la.get("kind"),
            ))
        elif in_right and not in_left:
            ra = right_artifacts[art_id]
            diffs.append(ArtifactDiff(
                artifact_id=art_id,
                change_type=CHANGE_TYPE_ADDED,
                right_hash=ra.get("hash"),
                right_kind=ra.get("kind"),
            ))
        else:
            la = left_artifacts[art_id]
            ra = right_artifacts[art_id]
            lh = la.get("hash")
            rh = ra.get("hash")
            lk = la.get("kind")
            rk = ra.get("kind")
            if lh != rh or lk != rk:
                diffs.append(ArtifactDiff(
                    artifact_id=art_id,
                    change_type=CHANGE_TYPE_MODIFIED,
                    left_hash=lh,
                    right_hash=rh,
                    left_kind=lk,
                    right_kind=rk,
                ))

    return diffs


def _diff_node(
    node_id: str,
    left_node: Dict[str, Any],
    right_node: Dict[str, Any],
) -> Optional[NodeDiff]:
    """Compare two node snapshots. Returns NodeDiff if changed, else None."""
    left_status = left_node.get("status")
    right_status = right_node.get("status")
    left_output = left_node.get("output")
    right_output = right_node.get("output")
    left_deps = left_node.get("dependencies", [])
    right_deps = right_node.get("dependencies", [])
    left_meta = left_node.get("metadata", {})
    right_meta = right_node.get("metadata", {})

    left_art = _get_node_artifacts(left_node)
    right_art = _get_node_artifacts(right_node)

    artifact_diffs = _diff_artifact_maps(left_art, right_art)

    status_changed = left_status != right_status
    output_changed = left_output != right_output
    output_ref_changed = left_node.get("output_ref") != right_node.get("output_ref")
    dep_changed = sorted(left_deps or []) != sorted(right_deps or [])
    meta_changed = (left_meta or {}) != (right_meta or {})

    if not (status_changed or output_changed or output_ref_changed or dep_changed or meta_changed or artifact_diffs):
        return None  # unchanged

    art_added = [d.artifact_id for d in artifact_diffs if d.change_type == CHANGE_TYPE_ADDED]
    art_removed = [d.artifact_id for d in artifact_diffs if d.change_type == CHANGE_TYPE_REMOVED]
    art_changed = [d.artifact_id for d in artifact_diffs if d.change_type == CHANGE_TYPE_MODIFIED]

    return NodeDiff(
        node_id=node_id,
        change_type=CHANGE_TYPE_MODIFIED,
        left_status=left_status,
        right_status=right_status,
        left_output_ref=left_node.get("output_ref"),
        right_output_ref=right_node.get("output_ref"),
        artifact_ids_added=art_added,
        artifact_ids_removed=art_removed,
        artifact_ids_changed=art_changed,
    )


def _diff_context(
    left_ctx: Dict[str, Any],
    right_ctx: Dict[str, Any],
) -> List[ContextDiff]:
    """Compare two Working Context snapshots."""
    diffs: List[ContextDiff] = []
    all_keys = sorted(set(left_ctx) | set(right_ctx))

    for key in all_keys:
        in_left = key in left_ctx
        in_right = key in right_ctx

        if in_left and not in_right:
            diffs.append(ContextDiff(
                context_key=key,
                change_type=CHANGE_TYPE_REMOVED,
                left_value=left_ctx[key],
            ))
        elif in_right and not in_left:
            diffs.append(ContextDiff(
                context_key=key,
                change_type=CHANGE_TYPE_ADDED,
                right_value=right_ctx[key],
            ))
        elif left_ctx[key] != right_ctx[key]:
            diffs.append(ContextDiff(
                context_key=key,
                change_type=CHANGE_TYPE_MODIFIED,
                left_value=left_ctx[key],
                right_value=right_ctx[key],
            ))

    return diffs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare_runs(
    left_run: Dict[str, Any],
    right_run: Dict[str, Any],
) -> RunDiff:
    """Compare two execution run snapshots and return a RunDiff.

    Both arguments must be dicts conforming to the run snapshot schema
    documented in this module's docstring.

    Returns:
        RunDiff with status "identical" or "changed".

    Raises:
        TypeError if either argument is not a dict.
    """
    if not isinstance(left_run, dict):
        raise TypeError(f"left_run must be a dict, got {type(left_run).__name__}")
    if not isinstance(right_run, dict):
        raise TypeError(f"right_run must be a dict, got {type(right_run).__name__}")

    left_run_id: str = str(left_run.get("run_id") or "left")
    right_run_id: str = str(right_run.get("run_id") or "right")

    left_nodes = _get_nodes(left_run)
    right_nodes = _get_nodes(right_run)

    set_left = set(left_nodes)
    set_right = set(right_nodes)

    added_node_ids = sorted(set_right - set_left)
    removed_node_ids = sorted(set_left - set_right)
    common_ids = sorted(set_left & set_right)

    # Per-node diffs
    node_diffs: List[NodeDiff] = []

    for nid in added_node_ids:
        rn = right_nodes[nid]
        node_diffs.append(NodeDiff(
            node_id=nid,
            change_type=CHANGE_TYPE_ADDED,
            right_status=rn.get("status"),
            right_output_ref=rn.get("output_ref"),
        ))

    for nid in removed_node_ids:
        ln = left_nodes[nid]
        node_diffs.append(NodeDiff(
            node_id=nid,
            change_type=CHANGE_TYPE_REMOVED,
            left_status=ln.get("status"),
            left_output_ref=ln.get("output_ref"),
        ))

    nodes_changed = 0
    for nid in common_ids:
        nd = _diff_node(nid, left_nodes[nid], right_nodes[nid])
        if nd is not None:
            node_diffs.append(nd)
            nodes_changed += 1

    # Top-level artifact diffs
    left_arts = _get_artifacts(left_run)
    right_arts = _get_artifacts(right_run)
    artifact_diffs = _diff_artifact_maps(left_arts, right_arts)

    # Context diffs
    left_ctx = _get_context(left_run)
    right_ctx = _get_context(right_run)
    context_diffs = _diff_context(left_ctx, right_ctx)

    # Summary
    summary = DiffSummary(
        nodes_added=len(added_node_ids),
        nodes_removed=len(removed_node_ids),
        nodes_changed=nodes_changed,
        artifacts_added=sum(1 for a in artifact_diffs if a.change_type == CHANGE_TYPE_ADDED),
        artifacts_removed=sum(1 for a in artifact_diffs if a.change_type == CHANGE_TYPE_REMOVED),
        artifacts_changed=sum(1 for a in artifact_diffs if a.change_type == CHANGE_TYPE_MODIFIED),
        context_keys_changed=len(context_diffs),
    )

    any_change = bool(
        node_diffs or artifact_diffs or context_diffs
    )
    status = RUN_DIFF_STATUS_CHANGED if any_change else RUN_DIFF_STATUS_IDENTICAL

    return RunDiff(
        left_run_id=left_run_id,
        right_run_id=right_run_id,
        status=status,
        node_diffs=node_diffs,
        artifact_diffs=artifact_diffs,
        context_diffs=context_diffs,
        summary=summary,
    )
