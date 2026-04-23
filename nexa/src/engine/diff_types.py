from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DiffOp:
    op_type: str
    text: str


@dataclass(frozen=True)
class UnitDiff:
    unit_kind: str
    label: Optional[str]
    status: str  # added | removed | changed | unchanged
    delta: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiffResult:
    unit_diffs: list[UnitDiff] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
