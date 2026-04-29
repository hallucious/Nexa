from __future__ import annotations

from typing import Mapping

from src.plugins.builder.findings import BuilderFinding, blocking_finding, warning_finding
from src.plugins.contracts.common_enums import BUILDER_STAGE_INTAKE
from src.plugins.contracts.intake_types import DesignerPluginBuildProposal

_TRUSTED_RUNTIME_SOURCE_NAMES = frozenset(
    {
        "trusted_plugin_runtime",
        "installed_plugin_runtime",
        "active_plugin_runtime",
    }
)


def evaluate_designer_plugin_proposal(proposal: DesignerPluginBuildProposal) -> tuple[BuilderFinding, ...]:
    """Evaluate whether a Designer-originated plugin proposal may enter Builder space.

    This gate intentionally does not trust proposal-space objects as runtime
    plugin truth. It only decides whether enough information exists to normalize
    a preview-ready builder request.
    """

    findings: list[BuilderFinding] = []
    source_type = str(proposal.source_context.source_type or "").strip()
    if source_type in _TRUSTED_RUNTIME_SOURCE_NAMES:
        findings.append(
            blocking_finding(
                finding_id="builder.intake.proposal_trust_boundary",
                stage=BUILDER_STAGE_INTAKE,
                code="proposal_space_cannot_claim_trusted_runtime",
                message="Designer proposals cannot claim trusted plugin runtime status.",
                target_ref=source_type,
                remediation_hint="Normalize through Plugin Builder and explicit verification before runtime trust.",
            )
        )
    if not proposal.source_context.has_target_anchor():
        findings.append(
            blocking_finding(
                finding_id="builder.intake.missing_source_anchor",
                stage=BUILDER_STAGE_INTAKE,
                code="missing_source_anchor",
                message="Plugin Builder intake requires a workspace, savefile, circuit, node, or existing plugin reference.",
                remediation_hint="Attach the proposal to a concrete workspace or plugin target before builder normalization.",
            )
        )
    if proposal.plugin_builder_spec_draft is None:
        findings.append(
            blocking_finding(
                finding_id="builder.intake.missing_spec_draft",
                stage=BUILDER_STAGE_INTAKE,
                code="missing_spec_draft",
                message="Plugin Builder intake requires a draft builder specification.",
                remediation_hint="Ask Designer to produce a draft purpose, capability summary, input contract, and output contract.",
            )
        )
    elif proposal.plugin_builder_spec_draft.unresolved_fields:
        findings.append(
            warning_finding(
                finding_id="builder.intake.unresolved_fields",
                stage=BUILDER_STAGE_INTAKE,
                code="unresolved_fields_present",
                message="The proposal contains unresolved fields that must remain visible through normalization.",
                target_ref=",".join(proposal.plugin_builder_spec_draft.unresolved_fields),
                remediation_hint="Carry unresolved fields into the preview result and request clarification if they block validation.",
            )
        )
    if _ambiguity_present(proposal.ambiguity_report):
        findings.append(
            warning_finding(
                finding_id="builder.intake.ambiguity_report_present",
                stage=BUILDER_STAGE_INTAKE,
                code="ambiguity_report_present",
                message="The proposal includes ambiguity that must be preserved for review.",
                remediation_hint="Normalize a preview, but do not silently resolve ambiguity as trusted runtime truth.",
            )
        )
    return tuple(findings)


def proposal_has_blocking_findings(findings: tuple[BuilderFinding, ...]) -> bool:
    return any(finding.blocking for finding in findings)


def _ambiguity_present(report: Mapping[str, object]) -> bool:
    if not isinstance(report, Mapping):
        return False
    if not report:
        return False
    if bool(report.get("present")):
        return True
    unresolved = report.get("unresolved") or report.get("questions") or report.get("items")
    if isinstance(unresolved, (list, tuple, set)):
        return bool(unresolved)
    return bool(unresolved)


__all__ = [
    "evaluate_designer_plugin_proposal",
    "proposal_has_blocking_findings",
]
