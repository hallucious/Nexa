from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.validation_panel import read_validation_panel_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Compression Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "draft", "kind": "provider", "label": "Draft"}],
            edges=[],
            entry="draft",
            outputs=[{"name": "result", "source": "node.draft.output.result"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )


def test_beginner_validation_summary_uses_one_sentence_cause() -> None:
    report = ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(
                code="MISSING_MODEL",
                category="provider",
                severity="high",
                blocking=True,
                location="node:draft",
                message="Step 1 has no AI model selected. Internal detail: provider_config missing for node draft.",
                hint="Choose an AI model.",
            )
        ],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_validation_panel_view_model(_working_save(), validation_report=report)

    assert vm.beginner_summary.status_signal == "Cannot run yet."
    assert vm.beginner_summary.cause == "Step 1 has no AI model selected."
    assert vm.beginner_summary.next_action_type == "focus_top_issue"
    assert vm.beginner_summary.next_action_label == "Fix this step"


def test_beginner_validation_summary_flattens_multiline_detail() -> None:
    report = ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(
                code="BAD_INPUT",
                category="input",
                severity="high",
                blocking=True,
                location="node:draft",
                message="Input file is not ready\nraw_trace=file_upload_001 scan_pending",
                hint="Fix input.",
            )
        ],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_validation_panel_view_model(_working_save(), validation_report=report)

    assert vm.beginner_summary.cause == "Input file is not ready raw_trace=file_upload_001 scan_pending"
    assert "\n" not in vm.beginner_summary.cause
