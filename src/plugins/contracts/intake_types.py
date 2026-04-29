from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.plugins.contracts.common_enums import BUILDER_MODE_CREATE_NEW
from src.plugins.contracts.serialization import JsonPayloadMixin


@dataclass(frozen=True)
class DesignerPluginSourceContext(JsonPayloadMixin):
    source_type: str
    workspace_ref: str | None = None
    savefile_ref: str | None = None
    circuit_ref: str | None = None
    node_ref: str | None = None
    existing_plugin_ref: str | None = None
    target_usage_summary: str | None = None

    def has_target_anchor(self) -> bool:
        return any(
            str(value or "").strip()
            for value in (
                self.workspace_ref,
                self.savefile_ref,
                self.circuit_ref,
                self.node_ref,
                self.existing_plugin_ref,
            )
        )


@dataclass(frozen=True)
class PluginBuilderSpecDraft(JsonPayloadMixin):
    draft_version: str
    plugin_purpose: str
    plugin_name_hint: str | None = None
    plugin_category: str = "general"
    capability_summary: str = ""
    intended_user_value: str = ""
    expected_usage_context: str = ""
    input_contract_draft: Mapping[str, Any] = field(default_factory=dict)
    output_contract_draft: Mapping[str, Any] = field(default_factory=dict)
    side_effect_profile_draft: Mapping[str, Any] = field(default_factory=dict)
    namespace_policy_request_draft: Mapping[str, Any] = field(default_factory=dict)
    runtime_constraint_request_draft: Mapping[str, Any] = field(default_factory=dict)
    dependency_requirement_draft: Mapping[str, Any] = field(default_factory=dict)
    template_preference_draft: Mapping[str, Any] = field(default_factory=dict)
    safety_constraint_draft: Mapping[str, Any] = field(default_factory=dict)
    verification_requirement_draft: Mapping[str, Any] = field(default_factory=dict)
    registration_intent_draft: Mapping[str, Any] = field(default_factory=dict)
    classification_request_draft: Mapping[str, Any] = field(default_factory=dict)
    unresolved_fields: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not str(self.draft_version or "").strip():
            raise ValueError("PluginBuilderSpecDraft.draft_version must be non-empty")
        if not str(self.plugin_purpose or "").strip():
            raise ValueError("PluginBuilderSpecDraft.plugin_purpose must be non-empty")
        object.__setattr__(self, "unresolved_fields", _normalized_tuple(self.unresolved_fields))
        object.__setattr__(self, "assumptions", _normalized_tuple(self.assumptions))


@dataclass(frozen=True)
class DesignerPluginBuildProposal(JsonPayloadMixin):
    proposal_id: str
    proposal_version: str
    proposal_status: str
    originating_request_text: str
    designer_session_ref: str
    source_context: DesignerPluginSourceContext
    requested_builder_mode: str = BUILDER_MODE_CREATE_NEW
    plugin_builder_spec_draft: PluginBuilderSpecDraft | None = None
    ambiguity_report: Mapping[str, Any] = field(default_factory=dict)
    risk_report: Mapping[str, Any] = field(default_factory=dict)
    clarification_questions: tuple[str, ...] = ()
    explanation: str | None = None
    recommended_next_action: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("proposal_id", "proposal_version", "proposal_status", "designer_session_ref"):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"DesignerPluginBuildProposal.{field_name} must be non-empty")
        object.__setattr__(self, "clarification_questions", _normalized_tuple(self.clarification_questions))


def _normalized_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(item for item in (str(value or "").strip() for value in values) if item)


__all__ = [
    "DesignerPluginBuildProposal",
    "DesignerPluginSourceContext",
    "PluginBuilderSpecDraft",
]
