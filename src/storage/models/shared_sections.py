from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.contracts.nex_contract import StorageRole


@dataclass(frozen=True)
class MetaBase:
    format_version: str
    storage_role: StorageRole
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class CircuitModel:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    entry: Optional[str] = None
    outputs: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ResourcesModel:
    prompts: dict[str, Any] = field(default_factory=dict)
    providers: dict[str, Any] = field(default_factory=dict)
    plugins: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateModel:
    input: dict[str, Any] = field(default_factory=dict)
    working: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
