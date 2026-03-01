from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .fingerprint import StructuralFingerprint


@dataclass(frozen=True)
class Revision:
    """Structural revision of an Engine.

    Contract reference: docs/specs/engine_constraints.md, trace_model.md.
    A Revision is immutable once published.
    """
    revision_id: str
    fingerprint: StructuralFingerprint
    meta: Dict[str, Any]
