# Designer-to-Plugin-Builder Intake Contract v1.0

## Recommended save path
`docs/specs/plugins/designer_to_plugin_builder_intake_contract.md`

## 1. Purpose

This document defines the canonical intake contract between Designer AI and the Plugin Builder in Nexa.

Its purpose is to make the following boundary explicit:

- what Designer AI is allowed to send
- what Designer AI is not allowed to claim
- what the Plugin Builder must treat as proposal-space input
- what must remain unresolved until builder-governed validation and verification occur

This document exists because the Plugin Builder is the official conversion boundary between proposal-space and trusted plugin-space.

Therefore, Designer AI must not send:
- implicit trust
- implicit installability
- implicit registry-worthiness
- implicit runtime authorization

Designer AI may only send a structured intake object that is clear enough for the Plugin Builder to process safely.

## 2. Core Decision

The official flow is:

User Request
-> Designer AI
-> DesignerPluginBuildProposal
-> Plugin Builder intake
-> builder normalization / generation / validation / verification / registration
-> PluginBuilderResult

In short:

Designer AI proposes.
Plugin Builder decides build progression.
Builder-governed stages determine trust and registration readiness.

## 3. Non-Negotiable Boundary

### 3.1 Designer AI is a proposal layer
Designer AI may:
- interpret user need
- infer likely plugin purpose
- propose input/output contracts
- propose side-effect expectations
- propose verification needs
- propose registration intent
- explain uncertainty
- ask for clarification
- produce multiple proposal candidates

Designer AI must not:
- silently install plugins
- silently register plugins
- mark a plugin as trusted
- claim builder validation passed unless it actually did
- claim verification passed unless it actually did
- invent registry publication success
- bypass builder or registry policy

### 3.2 Builder is the trust boundary
The Plugin Builder remains the sole official stage owner for:
- canonical normalization
- scaffold/candidate generation
- contract/policy validation
- verification/test execution
- registration publication
- final builder status emission

### 3.3 Intake is not runtime truth
The intake object is not:
- a registered plugin
- a trusted plugin
- a runtime-usable plugin
- a canonical plugin manifest

It is a proposal-space handoff object.

## 4. Why This Contract Exists Separately from Plugin Builder Spec Contract

The Plugin Builder Spec Contract defines the builder-facing orchestration system and its internal stage model.

This document is narrower and earlier.

It defines the intake boundary from Designer AI into that builder system.

That separation is necessary because:
1. Designer-side ambiguity handling is different from builder-side validation.
2. Proposal semantics are different from trusted candidate semantics.
3. A future reader must be able to distinguish:
   - what Designer AI believed
   - what Builder normalized
   - what Builder validated
   - what Builder ultimately accepted or rejected

Without this distinction, debugging and governance become ambiguous.

## 5. Design Goals

This contract must optimize for:
- clarity
- extensibility
- efficiency
- safe ambiguity handling
- future AI interoperability

## 6. Canonical Intake Object

The official Designer-to-Builder handoff object is:

DesignerPluginBuildProposal
- proposal_id: string
- proposal_version: string
- proposal_status: enum(
    "draft",
    "ready_for_builder_preview",
    "ready_for_builder_build",
    "clarification_required",
    "blocked"
  )
- originating_request_text: string
- designer_session_ref: string | null
- source_context: DesignerPluginSourceContext
- requested_builder_mode: enum(
    "preview_only",
    "scaffold_only",
    "validate_candidate",
    "verify_candidate",
    "build_unregistered",
    "build_and_register"
  )
- plugin_builder_spec_draft: PluginBuilderSpecDraft | null
- ambiguity_report: PluginProposalAmbiguityReport
- risk_report: PluginProposalRiskReport
- clarification_questions: list[ClarificationQuestion]
- explanation: string
- recommended_next_action: string | null

## 7. Proposal Status Semantics

- draft
- ready_for_builder_preview
- ready_for_builder_build
- clarification_required
- blocked

`ready_for_builder_build` means the handoff is sufficiently complete for the builder to attempt work. It does not mean the plugin is valid or trusted.

## 8. Source Context

DesignerPluginSourceContext
- source_type: enum(
    "natural_language_request",
    "workspace_edit_request",
    "plugin_gap_detected_from_circuit_design",
    "manual_admin_request",
    "other"
  )
- workspace_ref: string | null
- savefile_ref: string | null
- circuit_ref: string | null
- node_ref: string | null
- existing_plugin_ref: string | null
- target_usage_summary: string | null

## 9. Canonical Draft Spec Object

PluginBuilderSpecDraft
- draft_version: string
- plugin_purpose: string
- plugin_name_hint: string | null
- plugin_category: enum(
    "transform",
    "ingest",
    "delivery",
    "lookup",
    "formatting",
    "evaluation",
    "control",
    "other",
    "unknown"
  )
- capability_summary: string
- intended_user_value: string
- expected_usage_context: string | null
- input_contract_draft: PluginInputContractDraft
- output_contract_draft: PluginOutputContractDraft
- side_effect_profile_draft: SideEffectProfileDraft
- namespace_policy_request_draft: NamespacePolicyRequestDraft
- runtime_constraint_request_draft: RuntimeConstraintRequestDraft
- dependency_requirement_draft: DependencyRequirementDraft
- template_preference_draft: TemplatePreferenceDraft
- safety_constraint_draft: SafetyConstraintDraft
- verification_requirement_draft: VerificationRequirementDraft
- registration_intent_draft: RegistrationIntentDraft
- unresolved_fields: list[UnresolvedField]
- assumptions: list[DesignerAssumption]
- notes: string | null

Draft naming is mandatory. Designer AI emits a draft for builder normalization, not final trusted builder truth.

## 10. Required Intake Fields

At minimum:
- proposal_id
- proposal_version
- originating_request_text
- requested_builder_mode
- plugin_purpose
- capability_summary
- intended_user_value
- ambiguity_report
- risk_report

## 11. Draft Section Families

The intake must support draft sections for:
- input contract
- output contract
- side effects
- namespace policy request
- runtime constraints
- dependencies
- template preference
- safety constraints
- verification requirements
- registration intent

Each section must support unresolved questions when Designer AI cannot safely determine final truth.

## 12. Ambiguity, Risk, and Assumptions

The intake must explicitly expose:
- unresolved fields
- assumptions
- ambiguity level
- risk level
- clarification questions

A future AI or human reader must be able to see exactly what Designer AI did not know.

## 13. Intake Acceptance Rules

The Plugin Builder should accept intake only when:
1. the proposal status is builder-eligible
2. required core fields are present
3. ambiguity is not blocking without corresponding clarification handling
4. the requested builder mode is compatible with the available draft content
5. the intake does not contain impossible or contradictory claims

Otherwise the builder should reject or downgrade the request with explicit findings.

## 14. Explicitly Forbidden Intake Patterns

The following must be rejected or downgraded:
- hidden trust claims
- hidden installation claims
- hidden registration claims
- unbounded namespace claims
- ambiguity suppression

## 15. Extensibility and Efficiency Rules

The contract must support:
- new draft sections
- new builder modes
- new risk/ambiguity dimensions
- new governance fields

One intake object should support both:
- human-readable preview
- machine-readable builder handoff

## 16. Canonical Summary

The official Nexa position is:
- Designer AI may propose plugin creation through a structured intake object.
- The intake object must remain explicitly draft-level.
- The intake object must expose ambiguity, risk, assumptions, and unresolved fields.
- The Plugin Builder is responsible for trust-bearing progression beyond intake.

## 17. Final Statement

Designer AI does not hand the Builder a trusted plugin.

Designer AI hands the Builder a structured, explicit, uncertainty-aware proposal.

That is the canonical meaning of Designer-to-Plugin-Builder intake in Nexa.
