from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.server.first_success_blockers import FirstSuccessBlocker, FirstSuccessPreflightSummary, ProviderCostEstimate
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model


def _beginner_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="First Success Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "n1", "kind": "provider", "label": "Summarize document"}],
            edges=[],
            entry="n1",
            outputs=[{"name": "result", "source": "node.n1.output.result"}],
        ),
        resources=ResourcesModel(prompts={}, providers={"openai": {"provider_family": "openai"}}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en"}),
    )


def _clean_validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[],
        blocking_count=0,
        warning_count=0,
        result="passed",
    )


def test_builder_shell_surfaces_first_success_provider_blocker_as_run_bottleneck() -> None:
    preflight = FirstSuccessPreflightSummary(
        ready=False,
        blockers=(
            FirstSuccessBlocker(
                family="provider",
                reason_code="provider_model_access.plan_not_allowed",
                message="Selected AI model is not available on this plan.",
                next_action="Choose an AI model allowed by this plan before running.",
                source_ref="openai:gpt-4o",
            ),
        ),
        provider_cost_estimates=(
            ProviderCostEstimate(
                provider_key="openai",
                model_ref="gpt-4o",
                cost_ratio=3.0,
                pricing_unit="relative_unit",
            ),
        ),
        estimated_total_cost_ratio=3.0,
    )

    vm = read_builder_shell_view_model(
        _beginner_working_save(),
        validation_report=_clean_validation_report(),
        session_keys={"gpt": "sk-test"},
        first_success_preflight=preflight,
    )

    assert vm.first_success_preflight.visible is True
    assert vm.first_success_preflight.ready is False
    assert vm.first_success_preflight.blocker_count == 1
    assert vm.first_success_preflight.top_family == "provider"

    run_stage = next(stage for stage in vm.product_readiness.stages if stage.stage_id == "first_success_run")
    assert run_stage.stage_state == "fix_before_run"
    assert run_stage.blocker_count == 1
    assert run_stage.summary.startswith("Selected AI model is not available on this plan.")
    assert run_stage.recommended_action_id == "open_provider_setup"
    assert run_stage.recommended_action_label == "Choose an AI model allowed by this plan before running."
    assert vm.product_readiness.next_bottleneck_stage == "first_success_run"


def test_builder_shell_surfaces_first_success_file_blocker_without_raw_details() -> None:
    preflight = {
        "ready": False,
        "blockers": [
            {
                "family": "file_extraction",
                "reason_code": "file_extraction.not_ready.failed",
                "message": "Document text extraction failed.",
                "next_action": "Upload a new document or retry extraction before running.",
                "source_ref": "fex-1",
                "details": {"text": "RAW TEXT MUST NOT APPEAR"},
            }
        ],
        "estimated_total_cost_ratio": 1.0,
    }

    vm = read_builder_shell_view_model(
        _beginner_working_save(),
        validation_report=_clean_validation_report(),
        session_keys={"gpt": "sk-test"},
        first_success_preflight=preflight,
    )

    assert vm.first_success_preflight.top_family == "file_extraction"
    assert "RAW TEXT MUST NOT APPEAR" not in str(vm.first_success_preflight)
    run_stage = next(stage for stage in vm.product_readiness.stages if stage.stage_id == "first_success_run")
    assert run_stage.recommended_action_id == "open_file_input"
    assert run_stage.summary.startswith("Document text extraction failed.")


def test_builder_shell_surfaces_ready_first_success_cost_estimate() -> None:
    preflight = FirstSuccessPreflightSummary(
        ready=True,
        blockers=(),
        provider_cost_estimates=(
            ProviderCostEstimate(
                provider_key="anthropic",
                model_ref="claude-haiku-3",
                cost_ratio=1.0,
                pricing_unit="relative_unit",
            ),
        ),
        estimated_total_cost_ratio=1.0,
    )

    vm = read_builder_shell_view_model(
        _beginner_working_save(),
        validation_report=_clean_validation_report(),
        session_keys={"gpt": "sk-test"},
        first_success_preflight=preflight,
    )

    assert vm.first_success_preflight.visible is True
    assert vm.first_success_preflight.ready is True
    assert vm.first_success_preflight.estimated_total_cost_ratio == 1.0
