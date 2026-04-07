from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.interaction_lifecycle_closure import read_interaction_lifecycle_closure_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def test_interaction_lifecycle_closure_tracks_stage_closure_and_requirements() -> None:
    vm = read_interaction_lifecycle_closure_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.current_stage_id in {"drafting", "review", "commit", "execution", "history"}
    assert len(vm.stages) == 5
    assert any(stage.open_requirement is not None or stage.closeable for stage in vm.stages)
    assert vm.closure_status_label in {"주의 필요", "차단됨", "준비됨"}
    assert all(stage.stage_label for stage in vm.stages)
