from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.designer_panel import read_designer_panel_view_model


def _working_save(*, metadata: dict | None = None, last_run: dict | None = None, empty: bool = False) -> WorkingSaveModel:
    nodes = [] if empty else [{"id": "n1", "label": "Draft Generator"}]
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Draft",
        ),
        circuit=CircuitModel(nodes=nodes, edges=[], entry=(None if empty else "n1"), outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run=dict(last_run or {}), errors=[]),
        ui=UIModel(layout={}, metadata=dict(metadata or {})),
    )


def test_builder_shell_result_history_onboarding_does_not_infer_first_success_from_completed_last_run() -> None:
    source = _working_save(last_run={"run_id": "run-local", "status": "completed", "output_preview": "hello"})

    vm = read_builder_shell_view_model(source)

    assert vm.result_history is not None
    assert vm.result_history.onboarding_incomplete is True
    assert vm.result_history.onboarding_step_id == "enter_goal"


def test_builder_shell_result_history_onboarding_uses_explicit_first_success_metadata() -> None:
    source = _working_save(
        metadata={"beginner_first_success_achieved": True},
        last_run={"run_id": "run-local", "status": "completed", "output_preview": "hello"},
    )

    vm = read_builder_shell_view_model(source)

    assert vm.result_history is not None
    assert vm.result_history.onboarding_incomplete is False


def test_designer_empty_workspace_placeholder_uses_central_beginner_milestone_policy() -> None:
    source = _working_save(empty=True, last_run={"run_id": "run-local", "status": "completed"})

    vm = read_designer_panel_view_model(source)

    assert vm.request_state.input_placeholder == "What would you like to build? Describe your goal."


def test_designer_empty_workspace_placeholder_respects_explicit_advanced_unlock() -> None:
    source = _working_save(empty=True, metadata={"advanced_mode_requested": True})

    vm = read_designer_panel_view_model(source)

    assert vm.request_state.input_placeholder == "Describe the circuit change you want to make."
