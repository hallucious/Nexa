from __future__ import annotations

from src.engine.diff_types import DiffOp, DiffResult, UnitDiff


_STATUS_TO_OP = {
    "unchanged": "equal",
    "removed": "delete",
    "added": "insert",
}


def _separator_for(unit_diff: UnitDiff) -> str:
    if unit_diff.unit_kind == "char":
        return ""
    return " "


def render_diff_ops(diff_result: DiffResult) -> list[DiffOp]:
    rendered: list[DiffOp] = []

    for unit_diff in diff_result.unit_diffs:
        op_type = _STATUS_TO_OP.get(unit_diff.status)
        if op_type is None:
            raise ValueError(f"Unsupported unit diff status: {unit_diff.status}")

        text = str(unit_diff.unit.payload)
        if not text:
            continue

        if rendered and rendered[-1].op_type == op_type:
            separator = _separator_for(unit_diff)
            previous = rendered[-1]
            rendered[-1] = DiffOp(previous.op_type, previous.text + separator + text)
        else:
            rendered.append(DiffOp(op_type, text))

    return rendered
