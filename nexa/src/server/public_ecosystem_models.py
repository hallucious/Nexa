from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicEcosystemCatalogResponse:
    status: str
    catalog: Mapping[str, Any]
    surfaces: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    public_sdk_entrypoints: Mapping[str, str] = field(default_factory=dict)
    supported_contract_markers: tuple[str, ...] = ()
    supported_runtime_markers: tuple[str, ...] = ()
    supported_transport_kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicEcosystemCatalogResponse.status: {self.status}")
        if not self.catalog:
            raise ValueError("ProductPublicEcosystemCatalogResponse.catalog must be non-empty")
        if not self.surfaces:
            raise ValueError("ProductPublicEcosystemCatalogResponse.surfaces must be non-empty")
