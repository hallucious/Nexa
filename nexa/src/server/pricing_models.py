from dataclasses import dataclass
from typing import Literal


@dataclass
class ProviderCost:
    provider: str
    cost_ratio: float
    source: Literal["external", "cache", "workspace"]
