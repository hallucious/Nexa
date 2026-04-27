from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class ProviderCost:
    provider: str
    cost_ratio: float
    source: Literal["external", "cache", "workspace", "canonical_catalog"]
    model_ref: Optional[str] = None
    pricing_unit: str = "relative_unit"
    confidence: Literal["exact", "fallback", "estimated"] = "estimated"

    def __post_init__(self) -> None:
        if not str(self.provider or "").strip():
            raise ValueError("ProviderCost.provider must be non-empty")
        if self.cost_ratio <= 0:
            raise ValueError("ProviderCost.cost_ratio must be positive")
        if self.model_ref is not None and not str(self.model_ref).strip():
            raise ValueError("ProviderCost.model_ref must be non-empty when provided")
        if not str(self.pricing_unit or "").strip():
            raise ValueError("ProviderCost.pricing_unit must be non-empty")
