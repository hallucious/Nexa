"""
representation_model.py

Core data structures for the universal artifact diff architecture.

This module introduces the two foundational models used by the new
media-agnostic diff pipeline:

    Artifact -> Representation -> ComparableUnit[] -> Alignment -> Diff

This file is intentionally limited to deterministic, serializer-friendly
models only. It must not depend on formatter logic or comparison logic.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ComparableUnit:
    """Smallest comparable building block across artifact types."""

    unit_id: str
    unit_kind: str
    canonical_label: Optional[str]
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class Representation:
    """Deterministic, comparison-ready transformation of an artifact."""

    representation_id: str
    artifact_type: str
    units: list[ComparableUnit]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
