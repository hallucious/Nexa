from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from src.plugins.builder.findings import split_findings
from src.plugins.builder.intake_gate import evaluate_designer_plugin_proposal, proposal_has_blocking_findings
from src.plugins.builder.normalize import normalize_designer_proposal_to_builder_request
from src.plugins.contracts.builder_types import BuilderStageReport, PluginBuilderResult
from src.plugins.contracts.common_enums import (
    BUILDER_STAGE_INTAKE,
    BUILDER_STAGE_NORMALIZE,
    BUILDER_STATUS_INTAKE_REJECTED,
    BUILDER_STATUS_NORMALIZED_PREVIEW_READY,
)
from src.plugins.contracts.intake_types import DesignerPluginBuildProposal


@dataclass(frozen=True)
class PluginBuilderService:
    """Initial Plugin Builder service.

    This first slice owns intake and normalization only. It deliberately does
    not generate, validate, verify, install, or register plugin code.
    """

    request_id_prefix: str = "pb_req"
    build_id_prefix: str = "pb_build"

    def preview_from_designer_proposal(self, proposal: DesignerPluginBuildProposal) -> PluginBuilderResult:
        findings = evaluate_designer_plugin_proposal(proposal)
        blocking, warnings = split_findings(findings)
        request_id = f"{self.request_id_prefix}_{uuid4().hex}"
        build_id = f"{self.build_id_prefix}_{uuid4().hex}"

        if proposal_has_blocking_findings(findings):
            return PluginBuilderResult(
                build_id=build_id,
                request_id=request_id,
                final_status=BUILDER_STATUS_INTAKE_REJECTED,
                stage_reports=(
                    BuilderStageReport(
                        stage=BUILDER_STAGE_INTAKE,
                        status=BUILDER_STATUS_INTAKE_REJECTED,
                        findings=findings,
                    ),
                ),
                blocking_findings=blocking,
                warning_findings=warnings,
                explanation="Plugin Builder intake was rejected before normalization.",
                recommended_next_action="Resolve blocking intake findings and submit a revised proposal.",
            )

        request = normalize_designer_proposal_to_builder_request(proposal, request_id=request_id)
        return PluginBuilderResult(
            build_id=build_id,
            request_id=request.request_id,
            final_status=BUILDER_STATUS_NORMALIZED_PREVIEW_READY,
            normalized_spec=request.builder_spec,
            stage_reports=(
                BuilderStageReport(stage=BUILDER_STAGE_INTAKE, status="accepted", findings=findings),
                BuilderStageReport(stage=BUILDER_STAGE_NORMALIZE, status=BUILDER_STATUS_NORMALIZED_PREVIEW_READY),
            ),
            blocking_findings=blocking,
            warning_findings=warnings,
            explanation="Plugin Builder proposal was normalized into preview-ready builder request space.",
            recommended_next_action="Review unresolved fields and proceed to validation in the next Builder stage.",
        )


__all__ = ["PluginBuilderService"]
