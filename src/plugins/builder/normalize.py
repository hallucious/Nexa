from __future__ import annotations

from uuid import uuid4

from src.plugins.contracts.builder_types import (
    BuilderBuildOptions,
    BuilderCallerContext,
    BuilderGovernanceContext,
    ClassificationRequest,
    DependencyRequirementSet,
    NamespacePolicyRequest,
    PluginBuilderRequest,
    PluginBuilderSpec,
    PluginInputContract,
    PluginOutputContract,
    RegistrationIntent,
    RegistrationRequest,
    RuntimeConstraintRequest,
    SafetyConstraintSet,
    SideEffectProfile,
    TemplatePreference,
    VerificationRequirementSet,
)
from src.plugins.contracts.common_enums import SOURCE_TYPE_DESIGNER_PROPOSAL
from src.plugins.contracts.intake_types import DesignerPluginBuildProposal, PluginBuilderSpecDraft


PLUGIN_BUILDER_SPEC_VERSION = "plugin-builder-spec.v1"


def normalize_designer_proposal_to_builder_request(
    proposal: DesignerPluginBuildProposal,
    *,
    request_id: str | None = None,
) -> PluginBuilderRequest:
    """Convert a Designer proposal into canonical Plugin Builder request space."""

    draft = proposal.plugin_builder_spec_draft
    if draft is None:
        raise ValueError("Cannot normalize Designer proposal without plugin_builder_spec_draft")
    normalized_spec = normalize_spec_draft(draft)
    registration_intent = normalized_spec.registration_intent
    registration_request = RegistrationRequest(
        requested=registration_intent.requested,
        target_registry_scope=registration_intent.target_registry_scope,
        publish_label=registration_intent.publish_label,
    )
    return PluginBuilderRequest(
        request_id=request_id or f"pb_req_{uuid4().hex}",
        mode=proposal.requested_builder_mode,
        source_type=SOURCE_TYPE_DESIGNER_PROPOSAL,
        builder_spec=normalized_spec,
        caller_context=BuilderCallerContext(
            caller_type="designer_flow",
            caller_ref=proposal.designer_session_ref,
            workspace_ref=proposal.source_context.workspace_ref,
            savefile_ref=proposal.source_context.savefile_ref,
            proposal_ref=proposal.proposal_id,
        ),
        governance_context=BuilderGovernanceContext(
            approval_required=True,
            human_review_required=True,
            allowed_registration_scope=registration_intent.target_registry_scope,
            risk_tier=_risk_tier_from_report(proposal.risk_report),
            policy_profile="plugin_builder_default",
        ),
        build_options=BuilderBuildOptions(),
        registration_request=registration_request if registration_request.requested else None,
    )


def normalize_spec_draft(draft: PluginBuilderSpecDraft) -> PluginBuilderSpec:
    """Normalize a draft spec into the canonical builder spec family."""

    return PluginBuilderSpec(
        spec_version=PLUGIN_BUILDER_SPEC_VERSION,
        plugin_purpose=draft.plugin_purpose,
        plugin_name_hint=draft.plugin_name_hint,
        plugin_category=draft.plugin_category,
        capability_summary=draft.capability_summary or draft.intended_user_value or draft.plugin_purpose,
        input_contract=PluginInputContract(
            fields=dict(draft.input_contract_draft),
            summary=str(draft.input_contract_draft.get("summary") or ""),
        ),
        output_contract=PluginOutputContract(
            fields=dict(draft.output_contract_draft),
            summary=str(draft.output_contract_draft.get("summary") or ""),
        ),
        side_effect_profile=SideEffectProfile(
            side_effects_allowed=bool(draft.side_effect_profile_draft.get("side_effects_allowed", False)),
            external_targets=tuple(str(item) for item in draft.side_effect_profile_draft.get("external_targets", ()) or ()),
            notes=str(draft.side_effect_profile_draft.get("notes") or "") or None,
        ),
        namespace_policy=NamespacePolicyRequest(
            requested_read_scopes=tuple(str(item) for item in draft.namespace_policy_request_draft.get("requested_read_scopes", ()) or ()),
            requested_write_scopes=tuple(str(item) for item in draft.namespace_policy_request_draft.get("requested_write_scopes", ()) or ()),
            requested_external_read_targets=tuple(str(item) for item in draft.namespace_policy_request_draft.get("requested_external_read_targets", ()) or ()),
            requested_external_write_targets=tuple(str(item) for item in draft.namespace_policy_request_draft.get("requested_external_write_targets", ()) or ()),
            policy_sensitivity=str(draft.namespace_policy_request_draft.get("policy_sensitivity") or "low"),
            rationale=str(draft.namespace_policy_request_draft.get("rationale") or "") or None,
            unresolved_questions=tuple(str(item) for item in draft.namespace_policy_request_draft.get("unresolved_questions", ()) or ()),
        ),
        runtime_constraints=RuntimeConstraintRequest(
            timeout_ms=_optional_int(draft.runtime_constraint_request_draft.get("timeout_ms")),
            memory_limit_mb=_optional_int(draft.runtime_constraint_request_draft.get("memory_limit_mb")),
            network_access=bool(draft.runtime_constraint_request_draft.get("network_access", False)),
            notes=str(draft.runtime_constraint_request_draft.get("notes") or "") or None,
        ),
        dependency_requirements=DependencyRequirementSet(
            python_packages=tuple(str(item) for item in draft.dependency_requirement_draft.get("python_packages", ()) or ()),
            system_packages=tuple(str(item) for item in draft.dependency_requirement_draft.get("system_packages", ()) or ()),
            notes=str(draft.dependency_requirement_draft.get("notes") or "") or None,
        ),
        template_preference=TemplatePreference(
            preferred_template=str(draft.template_preference_draft.get("preferred_template") or "") or None,
            allow_fallback=bool(draft.template_preference_draft.get("allow_fallback", True)),
        ),
        safety_constraints=SafetyConstraintSet(
            constraints=tuple(str(item) for item in draft.safety_constraint_draft.get("constraints", ()) or ()),
            unresolved_fields=draft.unresolved_fields,
            assumptions=draft.assumptions,
        ),
        verification_requirements=VerificationRequirementSet(
            required_profile=str(draft.verification_requirement_draft.get("required_profile") or "light"),
            require_static_load_check=bool(draft.verification_requirement_draft.get("require_static_load_check", True)),
            require_smoke_execution=bool(draft.verification_requirement_draft.get("require_smoke_execution", False)),
            require_io_contract_check=bool(draft.verification_requirement_draft.get("require_io_contract_check", True)),
            additional_requirements=tuple(str(item) for item in draft.verification_requirement_draft.get("additional_requirements", ()) or ()),
        ),
        registration_intent=RegistrationIntent(
            requested=bool(draft.registration_intent_draft.get("requested", False)),
            target_registry_scope=str(draft.registration_intent_draft.get("target_registry_scope") or "workspace"),
            publish_label=str(draft.registration_intent_draft.get("publish_label") or "") or None,
        ),
        classification_request=ClassificationRequest(
            requested_class=str(draft.classification_request_draft.get("requested_class") or "internal_native"),
            mcp_compatibility_requested=bool(draft.classification_request_draft.get("mcp_compatibility_requested", False)),
            notes=str(draft.classification_request_draft.get("notes") or "") or None,
        ) if draft.classification_request_draft else None,
        notes=_combined_notes(draft),
    )


def _combined_notes(draft: PluginBuilderSpecDraft) -> str | None:
    parts: list[str] = []
    if draft.notes:
        parts.append(str(draft.notes))
    if draft.unresolved_fields:
        parts.append("unresolved_fields=" + ",".join(draft.unresolved_fields))
    if draft.assumptions:
        parts.append("assumptions=" + " | ".join(draft.assumptions))
    return "\n".join(parts) if parts else None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _risk_tier_from_report(report: object) -> str:
    if isinstance(report, dict):
        return str(report.get("risk_tier") or report.get("tier") or "low")
    return "low"


__all__ = [
    "PLUGIN_BUILDER_SPEC_VERSION",
    "normalize_designer_proposal_to_builder_request",
    "normalize_spec_draft",
]
