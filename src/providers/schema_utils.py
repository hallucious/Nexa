from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def extract_json_object(text: str) -> Optional[str]:
    """
    Best-effort extraction of the first valid JSON object in `text`.
    Compatible with Python 3.8.
    Handles:
      - ```json ... ```
      - leading/trailing prose
      - multiple objects (returns first parseable balanced object)
    """
    if not text:
        return None
    t = text.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()

    first = t.find("{")
    if first == -1:
        return None

    depth = 0
    start = None
    for i, ch in enumerate(t[first:], start=first):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                cand = t[start:i + 1].strip()
                try:
                    json.loads(cand)
                    return cand
                except Exception:
                    start = None
                    continue

    last = t.rfind("}")
    if last != -1 and last > first:
        cand = t[first:last + 1].strip()
        try:
            json.loads(cand)
            return cand
        except Exception:
            return None
    return None


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    j = extract_json_object(text)
    if not j:
        return None
    try:
        v = json.loads(j)
        return v if isinstance(v, dict) else None
    except Exception:
        return None
