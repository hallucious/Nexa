from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class DiffOp:
    op_type: str
    text: str


@dataclass(frozen=True)
class UnitDiff:
    unit_kind: str
    label: str | None
    status: str  # added | removed | unchanged
    unit: ComparableUnit
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiffResult:
    unit_diffs: list[UnitDiff]
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
