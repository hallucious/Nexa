from __future__ import annotations

from tests.test_ui_product_flow_role_aware import _commit, _run
from src.ui.product_flow_handoff import read_product_flow_handoff_view_model
from src.ui.product_flow_readiness import read_product_flow_readiness_view_model
from src.ui.product_flow_runbook import read_product_flow_runbook_view_model


def test_product_flow_runbook_does_not_expose_followthrough_compare_for_commit_snapshot_before_run() -> None:
    vm = read_product_flow_runbook_view_model(_commit())
    compare_entry = next(entry for entry in vm.entries if entry.entry_id == "compare_results")

    assert compare_entry.enabled is False
    assert compare_entry.action_id is None


def test_product_flow_readiness_prefers_run_boundary_for_commit_snapshot_source() -> None:
    vm = read_product_flow_readiness_view_model(_commit())

    assert vm.source_role == "commit_snapshot"
    assert vm.current_boundary_id == "run"
    assert vm.readiness_status == "ready"


def test_product_flow_handoff_does_not_offer_followthrough_for_commit_snapshot_before_run() -> None:
    vm = read_product_flow_handoff_view_model(_commit())

    assert vm.primary_entry_id == "run_current"
    assert vm.primary_action_id == "run_from_commit"
    assert vm.followthrough_available is False
    assert vm.followthrough_entry_id is None


def test_product_flow_runbook_exposes_trace_and_artifact_actions_for_execution_record_source() -> None:
    vm = read_product_flow_runbook_view_model(_run("completed"))
    trace_entry = next(entry for entry in vm.entries if entry.entry_id == "inspect_trace")
    artifact_entry = next(entry for entry in vm.entries if entry.entry_id == "inspect_artifacts")

    assert vm.runbook_status == "terminal_review"
    assert vm.current_entry_id == "inspect_trace"
    assert vm.recommended_entry_id == "inspect_trace"
    assert trace_entry.enabled is True
    assert trace_entry.action_id == "open_trace"
    assert artifact_entry.enabled is True
    assert artifact_entry.action_id == "open_artifacts"


def test_product_flow_readiness_is_terminal_for_execution_record_source() -> None:
    vm = read_product_flow_readiness_view_model(_run("completed"))

    assert vm.source_role == "execution_record"
    assert vm.current_boundary_id == "followthrough"
    assert vm.readiness_status == "terminal"
    assert vm.blocked_boundary_count == 0
