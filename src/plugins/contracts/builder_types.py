from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.plugins.builder.findings import BuilderFinding
from src.plugins.contracts.common_enums import (
    BUILDER_MODE_CREATE_NEW,
    BUILDER_STATUS_NORMALIZED_PREVIEW_READY,
    CALLER_TYPE_DESIGNER_FLOW,
    REGISTRATION_SCOPE_WORKSPACE,
    SOURCE_TYPE_DESIGNER_PROPOSAL,
)
from src.plugins.contracts.serialization import JsonPayloadMixin


@dataclass(frozen=True)
class PluginInputContract(JsonPayloadMixin):
    fields: Mapping[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass(frozen=True)
class PluginOutputContract(JsonPayloadMixin):
    fields: Mapping[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass(frozen=True)
class SideEffectProfile(JsonPayloadMixin):
    side_effects_allowed: bool = False
    external_targets: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class NamespacePolicyRequest(JsonPayloadMixin):
    requested_read_scopes: tuple[str, ...] = ()
    requested_write_scopes: tuple[str, ...] = ()
    requested_external_read_targets: tuple[str, ...] = ()
    requested_external_write_targets: tuple[str, ...] = ()
    policy_sensitivity: str = "low"
    rationale: str | None = None
    unresolved_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeConstraintRequest(JsonPayloadMixin):
    timeout_ms: int | None = None
    memory_limit_mb: int | None = None
    network_access: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class DependencyRequirementSet(JsonPayloadMixin):
    python_packages: tuple[str, ...] = ()
    system_packages: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class TemplatePreference(JsonPayloadMixin):
    preferred_template: str | None = None
    allow_fallback: bool = True


@dataclass(frozen=True)
class SafetyConstraintSet(JsonPayloadMixin):
    constraints: tuple[str, ...] = ()
    unresolved_fields: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationRequirementSet(JsonPayloadMixin):
    required_profile: str = "light"
    require_static_load_check: bool = True
    require_smoke_execution: bool = False
    require_io_contract_check: bool = True
    additional_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegistrationIntent(JsonPayloadMixin):
    requested: bool = False
    target_registry_scope: str = REGISTRATION_SCOPE_WORKSPACE
    publish_label: str | None = None


@dataclass(frozen=True)
class ClassificationRequest(JsonPayloadMixin):
    requested_class: str = "internal_native"
    mcp_compatibility_requested: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class BuilderCallerContext(JsonPayloadMixin):
    caller_type: str = CALLER_TYPE_DESIGNER_FLOW
    caller_ref: str | None = None
    workspace_ref: str | None = None
    savefile_ref: str | None = None
    proposal_ref: str | None = None
    user_ref: str | None = None


@dataclass(frozen=True)
class BuilderGovernanceContext(JsonPayloadMixin):
    approval_required: bool = True
    human_review_required: bool = True
    allowed_registration_scope: str = REGISTRATION_SCOPE_WORKSPACE
    risk_tier: str = "low"
    policy_profile: str = "default"


@dataclass(frozen=True)
class BuilderBuildOptions(JsonPayloadMixin):
    generate_tests: bool = True
    strict_validation: bool = True
    strict_verification: bool = False
    prefer_templates: bool = True
    allow_partial_preview_defaults: bool = True
    fail_on_warning: bool = False
    include_scaffold_comments: bool = True
    package_candidate: bool = False


@dataclass(frozen=True)
class RegistrationRequest(JsonPayloadMixin):
    requested: bool = False
    target_registry_scope: str = REGISTRATION_SCOPE_WORKSPACE
    publish_label: str | None = None
    install_after_register: bool = False
    activation_request: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginBuilderSpec(JsonPayloadMixin):
    spec_version: str
    plugin_purpose: str
    plugin_name_hint: str | None
    plugin_category: str
    capability_summary: str
    input_contract: PluginInputContract = field(default_factory=PluginInputContract)
    output_contract: PluginOutputContract = field(default_factory=PluginOutputContract)
    side_effect_profile: SideEffectProfile = field(default_factory=SideEffectProfile)
    namespace_policy: NamespacePolicyRequest = field(default_factory=NamespacePolicyRequest)
    runtime_constraints: RuntimeConstraintRequest = field(default_factory=RuntimeConstraintRequest)
    dependency_requirements: DependencyRequirementSet = field(default_factory=DependencyRequirementSet)
    template_preference: TemplatePreference = field(default_factory=TemplatePreference)
    safety_constraints: SafetyConstraintSet = field(default_factory=SafetyConstraintSet)
    verification_requirements: VerificationRequirementSet = field(default_factory=VerificationRequirementSet)
    registration_intent: RegistrationIntent = field(default_factory=RegistrationIntent)
    classification_request: ClassificationRequest | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not str(self.spec_version or "").strip():
            raise ValueError("PluginBuilderSpec.spec_version must be non-empty")
        if not str(self.plugin_purpose or "").strip():
            raise ValueError("PluginBuilderSpec.plugin_purpose must be non-empty")
        if not str(self.plugin_category or "").strip():
            raise ValueError("PluginBuilderSpec.plugin_category must be non-empty")


@dataclass(frozen=True)
class BuilderStageReport(JsonPayloadMixin):
    stage: str
    status: str
    findings: tuple[BuilderFinding, ...] = ()


@dataclass(frozen=True)
class PluginBuilderRequest(JsonPayloadMixin):
    request_id: str
    mode: str = BUILDER_MODE_CREATE_NEW
    source_type: str = SOURCE_TYPE_DESIGNER_PROPOSAL
    builder_spec: PluginBuilderSpec | None = None
    existing_candidate_ref: str | None = None
    existing_registry_ref: str | None = None
    caller_context: BuilderCallerContext = field(default_factory=BuilderCallerContext)
    governance_context: BuilderGovernanceContext = field(default_factory=BuilderGovernanceContext)
    build_options: BuilderBuildOptions = field(default_factory=BuilderBuildOptions)
    registration_request: RegistrationRequest | None = None

    def __post_init__(self) -> None:
        if not str(self.request_id or "").strip():
            raise ValueError("PluginBuilderRequest.request_id must be non-empty")


@dataclass(frozen=True)
class PluginBuilderResult(JsonPayloadMixin):
    build_id: str
    request_id: str
    final_status: str = BUILDER_STATUS_NORMALIZED_PREVIEW_READY
    normalized_spec: PluginBuilderSpec | None = None
    generated_candidate_ref: str | None = None
    generated_files: tuple[str, ...] = ()
    validation_report: Mapping[str, Any] = field(default_factory=dict)
    verification_report: Mapping[str, Any] = field(default_factory=dict)
    registry_record: Mapping[str, Any] | None = None
    stage_reports: tuple[BuilderStageReport, ...] = ()
    blocking_findings: tuple[BuilderFinding, ...] = ()
    warning_findings: tuple[BuilderFinding, ...] = ()
    explanation: str | None = None
    recommended_next_action: str | None = None


__all__ = [
    "BuilderBuildOptions",
    "BuilderCallerContext",
    "BuilderGovernanceContext",
    "BuilderStageReport",
    "ClassificationRequest",
    "DependencyRequirementSet",
    "NamespacePolicyRequest",
    "PluginBuilderRequest",
    "PluginBuilderResult",
    "PluginBuilderSpec",
    "PluginInputContract",
    "PluginOutputContract",
    "RegistrationIntent",
    "RegistrationRequest",
    "RuntimeConstraintRequest",
    "SafetyConstraintSet",
    "SideEffectProfile",
    "TemplatePreference",
    "VerificationRequirementSet",
]
