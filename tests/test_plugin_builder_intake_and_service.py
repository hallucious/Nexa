from __future__ import annotations

from src.plugins.builder.intake_gate import evaluate_designer_plugin_proposal
from src.plugins.builder.modes import validate_builder_request_mode
from src.plugins.builder.normalize import normalize_designer_proposal_to_builder_request
from src.plugins.builder.service import PluginBuilderService
from src.plugins.contracts.common_enums import BUILDER_STATUS_INTAKE_REJECTED, BUILDER_STATUS_NORMALIZED_PREVIEW_READY
from src.plugins.contracts.intake_types import (
    DesignerPluginBuildProposal,
    DesignerPluginSourceContext,
    PluginBuilderSpecDraft,
)


def _draft(**overrides):
    data = {
        "draft_version": "draft.v1",
        "plugin_purpose": "Review contract clauses.",
        "plugin_name_hint": "contract_review_helper",
        "plugin_category": "document_analysis",
        "capability_summary": "Find risky clauses and explain them.",
        "input_contract_draft": {"document_text": {"type": "string"}, "summary": "Document text"},
        "output_contract_draft": {"clauses": {"type": "list"}, "summary": "Risky clauses"},
        "namespace_policy_request_draft": {
            "requested_read_scopes": ("working_context.input.text",),
            "policy_sensitivity": "medium",
        },
    }
    data.update(overrides)
    return PluginBuilderSpecDraft(**data)


def _proposal(**overrides):
    data = {
        "proposal_id": "proposal-001",
        "proposal_version": "v1",
        "proposal_status": "draft",
        "originating_request_text": "Build a plugin that reviews contracts.",
        "designer_session_ref": "designer-session-001",
        "source_context": DesignerPluginSourceContext(
            source_type="designer_request",
            workspace_ref="workspace-001",
            circuit_ref="circuit-001",
            node_ref="node-001",
            target_usage_summary="Use inside a document-analysis node.",
        ),
        "plugin_builder_spec_draft": _draft(),
    }
    data.update(overrides)
    return DesignerPluginBuildProposal(**data)


def test_intake_gate_rejects_proposal_without_source_anchor() -> None:
    proposal = _proposal(
        source_context=DesignerPluginSourceContext(source_type="designer_request"),
    )

    findings = evaluate_designer_plugin_proposal(proposal)

    assert any(finding.code == "missing_source_anchor" for finding in findings)
    assert any(finding.blocking for finding in findings)


def test_intake_gate_rejects_proposal_claiming_trusted_runtime_space() -> None:
    proposal = _proposal(
        source_context=DesignerPluginSourceContext(
            source_type="trusted_plugin_runtime",
            workspace_ref="workspace-001",
        )
    )

    findings = evaluate_designer_plugin_proposal(proposal)

    assert any(finding.code == "proposal_space_cannot_claim_trusted_runtime" for finding in findings)
    assert any(finding.blocking for finding in findings)


def test_normalize_designer_proposal_preserves_unresolved_fields_and_namespace_request() -> None:
    proposal = _proposal(
        plugin_builder_spec_draft=_draft(
            unresolved_fields=("output schema details",),
            assumptions=("The node has document text in working context.",),
        )
    )

    request = normalize_designer_proposal_to_builder_request(proposal, request_id="pb_req_test")

    assert request.request_id == "pb_req_test"
    assert request.caller_context.workspace_ref == "workspace-001"
    assert request.caller_context.proposal_ref == "proposal-001"
    assert request.builder_spec is not None
    assert request.builder_spec.namespace_policy.requested_read_scopes == ("working_context.input.text",)
    assert request.builder_spec.safety_constraints.unresolved_fields == ("output schema details",)
    assert "assumptions=" in (request.builder_spec.notes or "")
    validate_builder_request_mode(request)


def test_builder_service_returns_preview_ready_result_for_valid_proposal() -> None:
    service = PluginBuilderService(request_id_prefix="req", build_id_prefix="build")

    result = service.preview_from_designer_proposal(_proposal())

    assert result.final_status == BUILDER_STATUS_NORMALIZED_PREVIEW_READY
    assert result.normalized_spec is not None
    assert result.normalized_spec.plugin_name_hint == "contract_review_helper"
    assert result.blocking_findings == ()
    assert result.stage_reports[0].stage == "intake"


def test_builder_service_returns_intake_rejected_result_for_blocking_proposal() -> None:
    service = PluginBuilderService(request_id_prefix="req", build_id_prefix="build")
    proposal = _proposal(
        source_context=DesignerPluginSourceContext(source_type="designer_request"),
    )

    result = service.preview_from_designer_proposal(proposal)

    assert result.final_status == BUILDER_STATUS_INTAKE_REJECTED
    assert result.normalized_spec is None
    assert result.blocking_findings
    assert result.recommended_next_action is not None
