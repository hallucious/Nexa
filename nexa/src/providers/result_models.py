from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional


@dataclass
class BaseResult(Mapping[str, Any]):
    """
    Hybrid result object:
    - Typed attributes for maintainability
    - Dict-like interface for backwards compatibility (Gate code can use .get / ["key"])
    """
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    # --- Mapping / dict-like compatibility ---
    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    def get(self, key: str, default: Any = None) -> Any:  # noqa: A003
        return self.to_dict().get(key, default)

    def keys(self) -> Iterable[str]:
        return self.to_dict().keys()

    def items(self) -> Iterable[tuple[str, Any]]:
        return self.to_dict().items()

    def values(self) -> Iterable[Any]:
        return self.to_dict().values()


@dataclass
class PerplexityVerifyResult(BaseResult):
    verdict: str = "UNKNOWN"      # PASS | FAIL | WARN | ERROR/UNKNOWN (Gate may map)
    confidence: Optional[float] = None
    citations: Optional[list[str]] = None
    summary: Optional[str] = None
