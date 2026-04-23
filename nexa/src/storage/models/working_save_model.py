from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.contracts.nex_contract import WORKING_SAVE_ROLE
from src.storage.models.shared_sections import CircuitModel, MetaBase, ResourcesModel, StateModel


@dataclass(frozen=True)
class WorkingSaveMeta(MetaBase):
    working_save_id: str = ""

    def __post_init__(self) -> None:
        if self.storage_role != WORKING_SAVE_ROLE:
            raise ValueError("WorkingSaveMeta.storage_role must be 'working_save'")


@dataclass(frozen=True)
class RuntimeModel:
    status: str = "draft"
    validation_summary: dict[str, Any] = field(default_factory=dict)
    last_run: dict[str, Any] = field(default_factory=dict)
    errors: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class UIModel:
    layout: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DesignerDraftModel:
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkingSaveModel:
    meta: WorkingSaveMeta
    circuit: CircuitModel
    resources: ResourcesModel
    state: StateModel
    runtime: RuntimeModel
    ui: UIModel
    designer: Optional[DesignerDraftModel] = None
