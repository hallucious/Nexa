from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_execution_adapter_hub import read_builder_execution_adapter_hub_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def test_builder_execution_adapter_hub_integrates_dispatch_adapters_and_state_changes() -> None:
    vm = read_builder_execution_adapter_hub_view_model(_working_save())

    assert vm.dispatch_hub is not None
    assert vm.execution_adapters is not None
    assert vm.state_changes is not None
    assert vm.executable_action_count >= 1
    assert vm.hub_status_label == "주의 필요"
