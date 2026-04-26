from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model


def _working_save(*, nodes: list[dict] | None = None, metadata: dict | None = None) -> WorkingSaveModel:
    node_list = nodes or []
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Draft",
        ),
        circuit=CircuitModel(
            nodes=node_list,
            edges=[],
            entry=(str(node_list[0].get("id")) if node_list else None),
            outputs=[],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata or {"app_language": "en-US"}),
    )


def test_beginner_empty_workspace_surface_policy_starts_from_designer_before_graph() -> None:
    vm = read_builder_shell_view_model(_working_save())

    assert vm.diagnostics.beginner_mode is True
    assert vm.diagnostics.empty_workspace_mode is True
    assert vm.beginner_surface_policy.visible is True
    assert vm.beginner_surface_policy.primary_surface_id == "designer"
    assert vm.beginner_surface_policy.primary_workspace_id == "node_configuration"
    assert vm.beginner_surface_policy.graph_first_allowed is False
    assert "graph_workspace" in vm.beginner_surface_policy.suppressed_surface_ids
    assert "trace_timeline" in vm.beginner_surface_policy.suppressed_surface_ids
    assert vm.beginner_surface_policy.can_open_advanced_surfaces is False
    assert vm.beginner_surface_policy.unlock_condition == "first_success_or_explicit_advanced_request"


def test_beginner_nonempty_workspace_allows_graph_but_keeps_deep_surfaces_locked() -> None:
    vm = read_builder_shell_view_model(_working_save(nodes=[{"id": "draft"}]))

    assert vm.diagnostics.beginner_mode is True
    assert vm.diagnostics.empty_workspace_mode is False
    assert vm.beginner_surface_policy.visible is True
    assert vm.beginner_surface_policy.graph_first_allowed is True
    assert "graph_workspace" not in vm.beginner_surface_policy.suppressed_surface_ids
    assert "trace_timeline" in vm.beginner_surface_policy.suppressed_surface_ids
    assert "diff_viewer" in vm.beginner_surface_policy.suppressed_surface_ids
    assert "artifact_viewer" in vm.beginner_surface_policy.suppressed_surface_ids


def test_advanced_request_disables_beginner_surface_policy_gate() -> None:
    vm = read_builder_shell_view_model(
        _working_save(metadata={"app_language": "en-US", "advanced_mode_requested": True})
    )

    assert vm.diagnostics.beginner_mode is False
    assert vm.beginner_surface_policy.visible is False
    assert vm.beginner_surface_policy.can_open_advanced_surfaces is True
    assert vm.beginner_surface_policy.suppressed_surface_ids == ()
    assert vm.beginner_surface_policy.unlock_condition == "already_unlocked"
