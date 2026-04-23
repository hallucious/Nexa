import json
from typing import Dict, Any


def canonicalize_definition(data: Dict[str, Any]) -> str:
    cleaned = dict(data)
    meta = cleaned.get("meta")
    if isinstance(meta, dict) and "ui" in meta:
        meta = dict(meta)
        meta.pop("ui", None)
        cleaned["meta"] = meta

    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
