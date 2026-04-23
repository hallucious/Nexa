from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicSdkCatalogResponse:
    status: str
    catalog: Mapping[str, Any]
    tools: tuple[Mapping[str, Any], ...] = ()
    resources: tuple[Mapping[str, Any], ...] = ()
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    public_sdk_entrypoints: Mapping[str, str] = field(default_factory=dict)
    supported_contract_markers: tuple[str, ...] = ()
    supported_runtime_markers: tuple[str, ...] = ()
    supported_transport_kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicSdkCatalogResponse.status: {self.status}")
        if not self.catalog:
            raise ValueError("ProductPublicSdkCatalogResponse.catalog must be non-empty")
