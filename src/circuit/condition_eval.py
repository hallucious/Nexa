from typing import Any, Dict


def _get_path(data: Dict[str, Any], path: str):
    parts = path.split(".")
    cur = data
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def evaluate(expr: str, context: Dict[str, Any]) -> bool:
    if expr.startswith("has("):
        key = expr[4:-1].strip().strip('"')
        return _get_path(context, key) is not None

    if expr.startswith("eq("):
        inside = expr[3:-1]
        key, literal = inside.split(",", 1)
        key = key.strip().strip('"')
        literal = literal.strip().strip('"')
        return str(_get_path(context, key)) == literal

    if expr.startswith("neq("):
        inside = expr[4:-1]
        key, literal = inside.split(",", 1)
        key = key.strip().strip('"')
        literal = literal.strip().strip('"')
        return str(_get_path(context, key)) != literal

    raise ValueError("Unsupported condition expression")
