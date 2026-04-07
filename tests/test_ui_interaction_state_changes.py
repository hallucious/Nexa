from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.interaction_state_changes import read_interaction_state_change_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_interaction_state_changes_project_workspace_panel_and_lifecycle_changes() -> None:
    vm = read_interaction_state_change_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.enabled_change_count >= 1
    run_change = next((item for item in vm.changes if item.action_id == "run_current"), None)
    assert run_change is not None
    assert run_change.target_stage_id == "execution"
    assert run_change.target_workspace_id == "runtime_monitoring"
