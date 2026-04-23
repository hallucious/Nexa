# Plugin Builder Spec Contract v1.1-c

## Recommended save path
`docs/specs/plugins/plugin_builder_spec_contract.md`

## 1. Purpose

This document defines the canonical Plugin Builder contract for Nexa.

Its purpose is to establish one official builder-facing contract for converting a Designer-originated plugin proposal into a validated, testable, registrable plugin candidate that Nexa can use safely.

This document is intentionally broader than a simple plugin format contract.

It does not define only:
- plugin file shape
- plugin input/output schema
- plugin metadata fields

Instead, it defines the full builder-facing lifecycle and contract boundary for:

- plugin proposal intake
- plugin builder specification normalization
- scaffold/code generation
- contract/policy validation
- verification/test execution
- registry publication
- final builder result reporting

This document exists because the correct architectural role is not:

Designer AI -> directly create trusted plugin -> immediate runtime use

but rather:

User Request
-> Designer AI
-> Plugin Builder Spec Proposal
-> Plugin Builder
-> Internal validation / verification / registration flow
-> Approved plugin candidate
-> Nexa runtime usage

The builder is the canonical conversion and governance boundary between proposal-space and trusted plugin-space.

## 2. Core Decision

The official Nexa direction is:

1. Designer AI may propose plugin creation intent and plugin builder specification.
2. The Plugin Builder is the single external system surface for plugin construction.
3. The Plugin Builder must internally separate generation, validation, verification, and registration responsibilities.
4. Plugin trust must never be inferred from AI authorship alone.
5. No plugin may become runtime-usable until builder-governed checks complete successfully.

In short:

The Plugin Builder is one external product concept, but internally it is a structured multi-stage process.

## 3. Non-Negotiable Boundaries

The following boundaries must remain unchanged:

### 3.1 Designer AI boundary
Designer AI is a proposal-producing design layer, not a direct runtime mutation layer.
Designer AI may produce:
- plugin creation proposal
- plugin builder spec draft
- clarification prompts
- safe preview/explanation

Designer AI must not:
- silently install plugins
- silently register plugins
- bypass builder validation
- bypass verification
- grant runtime trust by itself

### 3.2 Savefile boundary
Plugin code must remain external to `.nex` savefile truth.
A savefile may reference a plugin.
A savefile must not become the canonical container for plugin source code.

### 3.3 Runtime boundary
Runtime may execute only plugins that have passed the required builder-governed gates.

### 3.4 Trust boundary
AI-generated code is not trusted merely because it was generated.
Trust emerges only after builder-governed validation and verification.

### 3.5 Registration boundary
Registration is not equivalent to proposal generation and is not equivalent to code scaffold generation.
Registration is a later controlled stage.

## 4. Why This Contract Uses “Builder” Instead of “Plugin Spec” as the Primary Name

The name of this document is intentionally:

Plugin Builder Spec Contract

rather than:

Plugin Spec Contract

because the scope of this contract is not limited to describing a plugin object in isolation.

This document defines the full contract family needed for a builder-facing plugin lifecycle:
- what the builder receives
- how it interprets input
- how it separates internal stages
- what it must validate
- what it may generate
- what it may register
- what result object it must emit

A narrower “Plugin Spec Contract” may exist later for describing the plugin artifact itself.
That would be a subordinate or related document.
This document is the broader orchestration contract.

## 5. Design Goals

This contract must optimize for all of the following:

### 5.1 Extensibility
The builder must support future growth without redesigning the public concept each time.

Examples:
- more plugin templates
- more validation rules
- richer verification modes
- more registry targets
- future packaging modes
- future policy tiers

### 5.2 Efficiency
The builder must avoid redundant orchestration complexity at the outer layer.
Upper layers should not need to coordinate multiple separate systems manually.

### 5.3 Clarity
A future reader, including another AI system, must be able to determine:
- what the builder is
- what the builder is not
- what enters it
- what leaves it
- what stages exist internally
- which stage owns which responsibility

### 5.4 Composability inside Nexa
The builder must be usable in multiple contexts:
- Designer-driven creation flow
- advanced manual builder flow
- future automation flow
- future governance/review flow
- future internal “build preview only” or “validate only” workflows

### 5.5 Deterministic governance
Even if generation includes non-deterministic AI assistance earlier in the flow, the builder-governed trust gates must be explicit and inspectable.

## 6. Product Surface vs Internal Structure

### 6.1 Product surface principle
Externally, Nexa should expose one concept:

Plugin Builder

This is the official external entry point.

Upper layers should not need to think in terms of separately orchestrating:
- builder
- validator
- verifier
- registry

as independent product surfaces.

### 6.2 Internal structure principle
Internally, the builder must not collapse all responsibilities into one undifferentiated blob.

The builder must preserve clear internal stage ownership.

In short:

Externally unified
Internally structured

This distinction is mandatory.

## 7. Canonical External Concept

The canonical external concept is:

PluginBuilder

The canonical external responsibilities of PluginBuilder are:

- accept a builder spec proposal
- normalize and enrich it
- generate a plugin scaffold/candidate
- validate it against contract and policy rules
- verify it through required checks/tests
- register/publish it when requested and allowed
- emit one structured build result

The PluginBuilder is therefore a stage-sequence owner, not merely a code generator.

## 8. Canonical Internal Stage Model

The builder must internally distinguish at least the following stage families.

### 8.1 Spec Intake Stage
Purpose:
- receive plugin builder spec input
- establish build mode
- assign build identity
- resolve requested operation scope

Primary outputs:
- normalized builder request
- build id
- resolved mode
- initial findings if input is malformed

### 8.2 Spec Normalization Stage
Purpose:
- normalize the incoming builder spec
- fill safe defaults where allowed
- resolve template/classification/category
- convert ambiguous shape into a canonical internal form

Primary outputs:
- normalized plugin builder spec
- explicit unresolved ambiguity list
- normalized capability request set

### 8.3 Generation Stage
Purpose:
- generate plugin scaffold and candidate assets
- create code/module skeleton
- create manifest/metadata
- create test scaffold if configured
- generate packaging skeleton if applicable

Primary outputs:
- generated plugin candidate
- generated source files
- generated metadata files
- generated test files
- generation log

### 8.4 Validation Stage
Purpose:
- enforce contract and policy boundaries
- verify namespace write restrictions
- verify I/O schema compatibility
- verify manifest completeness
- verify forbidden patterns
- verify required metadata presence
- evaluate and approve/revise/reject requested classification

Primary outputs:
- validation report
- blocking findings
- warning findings
- policy findings
- approved classification outcome

### 8.5 Verification Stage
Purpose:
- run verification checks required for trust elevation
- execute static checks
- run test suites
- run smoke checks
- run template-specific checks if needed

Primary outputs:
- verification report
- pass/fail state
- failure reasons
- coverage of required checks

### 8.6 Registration Stage
Purpose:
- publish the plugin candidate into the registry layer when explicitly requested and allowed
- produce final registry metadata
- bind stable registry reference

Primary outputs:
- registry record
- installable reference
- publication status

### 8.7 Result Emission Stage
Purpose:
- emit one structured final builder result
- make the entire stage history visible and explainable

Primary outputs:
- PluginBuilderResult

## 9. Canonical Build Modes

The builder must support explicit modes rather than one monolithic action.

### 9.1 preview_only
Meaning:
- normalize request
- possibly classify template fit
- possibly generate high-level scaffold preview
- do not create trusted build artifacts
- do not register

### 9.2 scaffold_only
Meaning:
- generate candidate scaffold/assets
- do not claim trust
- do not register

### 9.3 validate_candidate
Meaning:
- validate a generated or supplied candidate
- may include policy checks
- does not register by default

### 9.4 verify_candidate
Meaning:
- run verification/test layer
- does not register by default

### 9.5 build_unregistered
Meaning:
- complete generation + validation + verification
- candidate is build-complete
- not yet registered

### 9.6 build_and_register
Meaning:
- complete all required stages
- publish to registry if gates pass

### 9.7 revalidate_existing
Meaning:
- re-run validation/verification on an existing registered or unregistered candidate

The mode must always be explicit in the request.

## 10. Canonical Input Object

The official builder-facing input object is:

PluginBuilderRequest

PluginBuilderRequest
- request_id: string
- mode: enum(
    "preview_only",
    "scaffold_only",
    "validate_candidate",
    "verify_candidate",
    "build_unregistered",
    "build_and_register",
    "revalidate_existing"
  )
- source_type: enum(
    "designer_proposal",
    "manual_spec",
    "existing_candidate",
    "existing_registry_plugin"
  )
- builder_spec: PluginBuilderSpec | null
- existing_candidate_ref: string | null
- existing_registry_ref: string | null
- caller_context: BuilderCallerContext
- governance_context: BuilderGovernanceContext
- build_options: BuilderBuildOptions
- registration_request: RegistrationRequest | null

Rules:
1. At least one source path must be resolvable.
2. `builder_spec` is required for proposal-originated new builds.
3. Existing references must be explicit for revalidation/reverification flows.
4. The builder must reject ambiguous source requests.

## 11. Canonical Builder Spec Object

The official input specification object is:

PluginBuilderSpec

This is the payload that Designer AI or an advanced user provides to the builder.

PluginBuilderSpec
- spec_version: string
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
    "other"
  )
- capability_summary: string
- input_contract: PluginInputContract
- output_contract: PluginOutputContract
- side_effect_profile: SideEffectProfile
- namespace_policy: NamespacePolicyRequest
- runtime_constraints: RuntimeConstraintRequest
- dependency_requirements: DependencyRequirementSet
- template_preference: TemplatePreference
- safety_constraints: SafetyConstraintSet
- verification_requirements: VerificationRequirementSet
- registration_intent: RegistrationIntent
- classification_request: ClassificationRequest | null
- notes: string | null

This object must be canonical enough that another AI, another human, or a later Nexa component can understand exactly what was intended.

## 12. Builder Spec Section Semantics

### 12.1 plugin_purpose
Human-readable purpose statement.
Must explain what real job the plugin performs.

### 12.2 plugin_category
High-level category for template selection and policy routing.

### 12.3 capability_summary
Concise explanation of the plugin’s capability in builder terms.

### 12.4 input_contract
Defines accepted input structure.
Must be explicit enough for generation and validation.

### 12.5 output_contract
Defines emitted output structure.
Must be explicit enough for runtime and downstream compatibility.

### 12.6 side_effect_profile
Defines whether the plugin is:
- pure/read-transform
- external-read
- external-write
- mixed

This is critical for governance.

### 12.7 namespace_policy
Defines requested or allowed write targets.
The builder must never assume unrestricted write authority.

### 12.8 runtime_constraints
Defines expected limits such as:
- latency expectation
- timeout preference
- retry compatibility
- determinism preference
- memory/size limits if needed

### 12.9 dependency_requirements
Defines required external libraries, APIs, or platform assumptions.

### 12.10 template_preference
Allows the builder to prefer a known internal scaffold path rather than free-form generation when possible.

### 12.11 safety_constraints
Defines prohibited behaviors, sensitive data restrictions, allowed external targets, and dangerous pattern exclusions.

### 12.12 verification_requirements
Defines what level of verification is required before the candidate can be treated as build-complete or registry-eligible.

### 12.13 registration_intent
Defines whether the target is:
- local temporary candidate
- local private registry
- shared internal registry
- future public registry
or another governed target

## 13. Caller Context

The builder must know who is calling and from what context.

BuilderCallerContext
- caller_type: enum(
    "designer_flow",
    "manual_builder_ui",
    "automation_flow",
    "admin_flow",
    "unknown"
  )
- caller_ref: string | null
- workspace_ref: string | null
- savefile_ref: string | null
- proposal_ref: string | null
- user_ref: string | null

Purpose:
- auditing
- policy routing
- trace linkage
- future multi-actor governance

## 14. Governance Context

BuilderGovernanceContext
- approval_required: bool
- human_review_required: bool
- allowed_registration_scope: enum(
    "none",
    "local_private_only",
    "shared_internal_allowed",
    "full_allowed"
  )
- risk_tier: enum("low", "medium", "high", "restricted")
- policy_profile: string | null

The builder must not decide trust in a governance vacuum.

## 15. Build Options

BuilderBuildOptions
- generate_tests: bool
- strict_validation: bool
- strict_verification: bool
- prefer_templates: bool
- allow_partial_preview_defaults: bool
- fail_on_warning: bool
- include_scaffold_comments: bool
- package_candidate: bool

These options may tune the process, but must not override core policy prohibitions.

## 16. Registration Request

RegistrationRequest
- requested: bool
- target_registry_scope: enum(
    "none",
    "local_private",
    "workspace_shared",
    "internal_shared",
    "other"
  )
- publish_label: string | null
- install_after_register: bool
- activation_request: bool

Registration must always be explicit.
It must not be inferred simply because build succeeded.

## 17. Canonical Output Object

The official builder output object is:

PluginBuilderResult

PluginBuilderResult
- build_id: string
- request_id: string
- final_status: enum(
    "preview_ready",
    "scaffold_generated",
    "validation_failed",
    "verification_failed",
    "build_complete_unregistered",
    "registered",
    "rejected"
  )
- normalized_spec: PluginBuilderSpec | null
- generated_candidate_ref: string | null
- generated_files: list[GeneratedFileRef]
- validation_report: ValidationReport | null
- verification_report: VerificationReport | null
- registry_record: RegistryRecord | null
- stage_reports: list[BuilderStageReport]
- blocking_findings: list[BuilderFinding]
- warning_findings: list[BuilderFinding]
- explanation: string
- recommended_next_action: string | null

This object must tell a later reader exactly:
- what happened
- what stage succeeded
- what stage failed
- whether runtime trust was granted
- whether registration occurred

## 18. Canonical Status Semantics

### 18.1 preview_ready
A preview exists, but no trusted candidate exists.

### 18.2 scaffold_generated
Source scaffold exists, but trust gates are not complete.

### 18.3 validation_failed
Contract/policy rules failed.
The candidate must not progress to trusted runtime use.

### 18.4 verification_failed
Validation may have passed, but verification/test gates failed.
The candidate must not progress to trusted runtime use.

### 18.5 build_complete_unregistered
The candidate passed required internal build gates, but is not registered.

### 18.6 registered
The candidate passed required stages and was published to the permitted registry target.

### 18.7 rejected
The request itself or the candidate path is not acceptable under builder policy.

## 19. Findings Model

The builder must expose findings explicitly.

BuilderFinding
- finding_id: string
- severity: enum("info", "warning", "blocking")
- stage: enum(
    "intake",
    "normalization",
    "generation",
    "validation",
    "verification",
    "registration"
  )
- code: string
- message: string
- target_ref: string | null
- remediation_hint: string | null

This is necessary for both human understanding and future AI-to-AI interoperability.

## 20. Validation Responsibility

The builder must own validation as an internal stage family.

Validation must include at minimum:

### 20.1 Builder spec shape validation
- required field presence
- canonical shape validation
- enum/legal value validation

### 20.2 Plugin contract validation
- input/output contract completeness
- required metadata presence
- category/template compatibility

### 20.3 Namespace policy validation
- requested write targets
- prohibited write areas
- mismatch between purpose and requested authority

### 20.4 Side effect policy validation
- external write/read declarations
- undeclared side-effect detection where possible
- forbidden capability class rejection

### 20.5 Dependency validation
- unsupported dependency flags
- forbidden dependency patterns
- unresolved required dependency declarations

Validation must remain a distinct internal stage even though the external product concept is one builder.



Recommended classification-related categories include:
- CLASSIFICATION_REQUEST_AMBIGUOUS
- CLASSIFICATION_MCP_COMPATIBILITY_UNCLEAR
- CLASSIFICATION_RUNTIME_AUTHORITY_UNCLEAR
- CLASSIFICATION_ADAPTER_RECURSION_DETECTED
- CLASSIFICATION_APPROVAL_REQUIRED

## 21. Verification Responsibility

The builder must own verification as an internal stage family.

Verification must include at minimum:

### 21.1 Static verification
- syntactic validity
- import/module load validity
- manifest coherence

### 21.2 Test verification
- generated or required tests
- smoke execution
- failure reason capture

### 21.3 Template integrity verification
- template completeness
- placeholder resolution
- category-template consistency

### 21.4 Optional policy verification
- output sample conformity
- declared I/O contract smoke check
- restricted behavior checks

Verification is not optional if the candidate is to become trusted.

## 22. Registration Responsibility

Registration must remain an internal builder stage family, not an unrelated external manual concept.

Registration must include at minimum:

### 22.1 Registry target resolution
- where publication is allowed
- whether caller is permitted

### 22.2 Metadata publication
- stable name/reference
- version or revision marker if used
- category/capability metadata

### 22.3 Installability state
- whether the candidate is merely recorded
- whether it is installable
- whether it is activated

### 22.4 Registration result emission
- success/failure record
- registry reference
- registry findings if any

## 23. Why Registration Remains Inside Builder Instead of as a Separate Product Surface

Registration remains part of the builder’s internal stage model because:

1. Upper layers should not need to orchestrate extra trust transitions manually.
2. Registration is downstream of generation/validation/verification.
3. The user/product concept should stay simple:
   “build this plugin”
   rather than
   “generate this, then validate that, then register elsewhere.”

This does not mean registration is conceptually unimportant.
It means its role is internally explicit but externally unified.

## 24. Why Validation and Verification Remain Inside Builder Instead of as Separate External Systems

For the same reason:

- external simplicity
- internal rigor
- easier future composition

Upper layers such as Designer UI, automation, or future orchestration circuits should be able to call one system surface and choose mode/stage depth, rather than manually coordinating multiple unrelated surfaces.

## 25. Extensibility Rules

This contract must evolve under the following rules:

### 25.1 New internal stages may be added
if they do not break the external unified builder concept.

### 25.2 New validation and verification rules may be added
if findings remain explicit and machine-readable.

### 25.3 New plugin categories/templates may be added
without redesigning the entire builder contract.

### 25.4 New registry scopes may be added
if governance rules remain explicit.

### 25.5 New build modes may be added
only if their semantics are clearly distinguishable from existing modes.

## 26. Efficiency Rules

The builder should optimize for:

### 26.1 Minimal upper-layer orchestration burden
Upper layers should call one builder surface.

### 26.2 Reusable internal reports
Validation and verification outputs should be reusable rather than recomputed unnecessarily.

### 26.3 Stage-selective execution
Preview-only and validate-only flows should avoid doing irrelevant later work.

### 26.4 Template-first preference where practical
When a safe template exists, the builder should prefer template-driven scaffold generation over unnecessarily open-ended generation.

## 27. Clarity Rules for Future Readers and Future AI Systems

This contract must be readable by:
- a human maintainer months later
- another AI system operating on the project later
- a debugging workflow that needs precise stage responsibility

Therefore:

### 27.1 Every externally visible status must map to clear internal stage meaning.
### 27.2 Every finding must identify stage and severity.
### 27.3 The distinction between proposal, candidate, trusted candidate, and registered plugin must remain explicit.
### 27.4 “Builder” must never be interpreted as “mere code generator.”
### 27.5 “Unified external concept” must never be interpreted as “internally unstructured blob.”

## 28. Relationship to Current Plugin Vocabulary

This contract introduces `plugin_category` as a builder/spec/purpose classification axis.

It must not be silently confused with existing current-code terms such as `plugin_type`.

Canonical distinction:
- `plugin_category` answers: what functional purpose-class is this plugin being built for?
- `plugin_type` answers: what current runtime/platform/plugin-role class does this plugin belong to in existing code?

These two axes may later be mapped, but they are not synonyms and one must not replace the other by assumption.

## 29. Relationship to Current Codebase Alignment

This document primarily describes the target builder-facing contract family, not a claim that the full structure already exists in current code.

Current-state interpretation:
- some related concepts already exist in loader/discovery/executor/platform code
- the unified Builder surface described here is a target contract direction
- migration/bridge work is required before this document can be treated as a direct one-to-one code map

At implementation time, this contract must be read alongside current code families such as discovery, auto-loading, executor, and existing plugin contract vocabulary.

## 30. Relationship to Existing PRE / CORE / POST Stage Structure

This contract does not delete or replace the current PRE / CORE / POST stage model used elsewhere in the codebase.

Instead, this document describes a higher-level builder lifecycle around plugin creation, validation, verification, and registration.

Interpretation rule:
- PRE / CORE / POST remains an execution-stage vocabulary
- this Builder contract remains a build/publication-oriented contract vocabulary
- coexistence is mandatory until an explicit migration document says otherwise

## 29. Relationship to Other Documents

This document should be read alongside or followed by related documents such as:

- Designer-side plugin proposal/intake contract
- plugin runtime artifact/manifest contract
- plugin namespace policy contract
- plugin registry contract
- plugin verification/test policy contract

Those may be split later.
This document remains the top-level builder-facing orchestration contract.

## 31. Canonical Summary

The official Nexa position is:

- The correct primary term is Plugin Builder Spec Contract.
- Nexa should expose one external builder concept, not multiple fragmented product surfaces.
- The builder must internally preserve distinct responsibility layers:
  spec intake,
  normalization,
  generation,
  validation,
  verification,
  registration,
  result emission.
- Designer AI may produce the builder spec proposal, but may not grant trust by itself.
- Plugin runtime trust emerges only after builder-governed stages complete successfully.
- This design is preferred because it is more extensible, more efficient, easier to compose inside Nexa, and less confusing for future readers.

## 32. Final Statement

Plugin building in Nexa is not:
AI writes code -> trust assumed

Plugin building in Nexa is:

proposal
-> builder-governed structured stage sequence
-> explicit findings
-> explicit trust gates
-> explicit registration outcome

That is the canonical meaning of Plugin Builder in Nexa.
