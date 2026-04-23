from __future__ import annotations

from src.engine.diff_types import DiffOp, DiffResult


def _unit_text(unit_diff) -> str:
    if unit_diff.delta is not None:
        return str(unit_diff.delta)
    if unit_diff.label is not None:
        return str(unit_diff.label)
    return ""


def render_diff_ops(diff_result: DiffResult, *, separator: str = "") -> list[DiffOp]:
    ops: list[DiffOp] = []

    for unit_diff in diff_result.unit_diffs:
        text = _unit_text(unit_diff)
        if not text:
            continue

        if unit_diff.status == "unchanged":
            op_type = "equal"
        elif unit_diff.status == "removed":
            op_type = "delete"
        elif unit_diff.status == "added":
            op_type = "insert"
        elif unit_diff.status == "changed":
            # contract-safe fallback; comparator should normally decompose changed into removed/added
            op_type = "delete"
        else:
            raise ValueError(f"Unsupported unit diff status: {unit_diff.status}")

        if ops and ops[-1].op_type == op_type:
            prev = ops[-1]
            joiner = separator if prev.text and text else ""
            ops[-1] = DiffOp(op_type, f"{prev.text}{joiner}{text}")
        else:
            ops.append(DiffOp(op_type, text))

    return ops
