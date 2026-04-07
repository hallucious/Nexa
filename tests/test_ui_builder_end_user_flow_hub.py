from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_end_user_flow_hub import read_builder_end_user_flow_hub_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def test_builder_end_user_flow_hub_unifies_user_flows_and_lifecycle_closure() -> None:
    vm = read_builder_end_user_flow_hub_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.end_user_flows is not None
    assert vm.lifecycle_closure is not None
    assert vm.executable_flow_count == vm.end_user_flows.enabled_flow_count
    assert vm.hub_status_label == "주의 필요"
