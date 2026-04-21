from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Protocol, Tuple

from src.providers.provider_adapter_contract import ProviderRequest, ProviderResult


StreamChunk = Dict[str, Any]


class ProviderAdapter(Protocol):
    """Vendor translation layer.

    Adapters are pure: they must not touch Engine/Worker state, registries, or trace.
    """

    name: str

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]: ...
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...
    def stream(self, payload: Dict[str, Any]) -> Iterator[StreamChunk]: ...
    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]: ...
    def fingerprint_components(self) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class AdapterConfig:
    api_key: str
    model: str
    endpoint: str
    timeout_sec: int = 60
    # Optional extra headers for OpenAI-compatible proxies.
    extra_headers: Optional[Dict[str, str]] = None
