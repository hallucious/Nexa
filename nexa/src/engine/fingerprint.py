from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict

from .model import EngineStructure


@dataclass(frozen=True)
class StructuralFingerprint:
    """Deterministic structural identity for EngineStructure."""
    value: str


def compute_fingerprint(structure: EngineStructure) -> StructuralFingerprint:
    """Compute a deterministic fingerprint from structural data only.

    Rules (v1):
    - Derived solely from Nodes + Channels + Flow + Entry + explicit mappings
    - Excludes runtime/execution data
    """
    payload: Dict[str, Any] = {
        "entry": structure.entry_node_id,
        "nodes": list(structure.node_ids),
        "channels": [
            {
                "channel_id": c.channel_id,
                "src": c.src_node_id,
                "dst": c.dst_node_id,
                "mapping": c.mapping,
            }
            for c in structure.channels
        ],
        "flow": [
            {
                "rule_id": r.rule_id,
                "payload": r.payload,
            }
            for r in structure.flow
        ],
        "meta": structure.meta,
    }

    # Stable JSON
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return StructuralFingerprint(value=h)
