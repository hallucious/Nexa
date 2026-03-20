from __future__ import annotations

from src.engine.diff_types import DiffOp, DiffResult


def render_diff_ops(diff_result: DiffResult) -> list[DiffOp]:
    ops: list[DiffOp] = []
    for unit_diff in diff_result.unit_diffs:
        text = "" if unit_diff.delta is None else str(unit_diff.delta)
        if unit_diff.status == "unchanged":
            ops.append(DiffOp("equal", text if text else str(unit_diff.label or "")))
        elif unit_diff.status == "removed":
            ops.append(DiffOp("delete", text))
        elif unit_diff.status == "added":
            ops.append(DiffOp("insert", text))
        elif unit_diff.status == "changed":
            # kept for future extensibility; current comparator decomposes into remove/add
            ops.append(DiffOp("delete", text))
        else:
            raise ValueError(f"Unsupported unit diff status: {unit_diff.status}")
    return ops
