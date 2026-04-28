# Nexa Global Remaining Implementation Master Plan

## Recommended save path
`docs/implementation/master/nexa_global_remaining_implementation_master_plan.md`

## 1. Purpose

This document defines the global implementation order for the remaining Nexa work across all currently uploaded implementation plans.

It is written so that another AI can use this document as the single primary execution blueprint for finishing the remaining work without needing to infer sequencing from scattered planning documents.

This document is not a high-level roadmap only.
It is a concrete implementation master plan that answers all of the following:

- what order to implement the remaining plan files in
- which parts must be implemented now versus later
- which workstreams are blocking others
- where Plugin Builder must be pulled forward relative to UI completion
- what each phase must produce
- what must not be done in a given phase
- what completion means before moving to the next phase
- how to avoid rework across UI, SaaS, plugin, and operations layers

This document supersedes any earlier simplistic interpretation such as:
- finish all UI first, then plugin builder
- finish plugin builder first, then return to product UX

Both of those are incorrect.

The correct strategy is:

1. finish the minimum first-success product loop
2. implement Plugin Builder core early enough that UI can integrate it properly
3. finish plugin-aware UI completion
4. harden platform, security, operations, and expansion after the product and plugin surface are structurally real

---

## 2. Authoritative source set

This master plan is derived from the currently uploaded implementation and specification materials.

### 2.1 Control / orchestration plans

- `saas/nexa_saas_backend_foundation_impl_brief.md`
- `saas/saas_implementation_plan_index.md`
- `saas/nexa_saas_completion_plan.md`
- `saas/nexa_saas_completion_plan_practical_execution_order.md`

### 2.2 Remaining UI execution plan

- `ui/nexa_remaining_ui_implementation_plan.md`

### 2.3 SaaS execution plans

- `saas/foundation_and_platform_implementation_plan.md`
- `saas/async_execution_and_worker_implementation_plan.md`
- `saas/provider_billing_and_quota_implementation_plan.md`
- `saas/file_ingestion_and_document_safety_implementation_plan.md`
- `saas/contract_review_vertical_slice_implementation_plan.md`
- `saas/web_application_implementation_plan.md`
- `saas/observability_security_and_privacy_implementation_plan.md`
- `saas/operations_recovery_and_admin_surface_implementation_plan.md`
- `saas/capability_activation_and_expansion_implementation_plan.md`

### 2.4 Operations plan

- `ops/ai_assisted_operations_implementation_plan.md`

### 2.5 Plugin Builder implementation plan

- `pulgin/plugin_builder_full_implementation_plan.md`

### 2.6 Plugin Builder specification family

- `plugin_builder_spec_contract.md`
- `designer_to_plugin_builder_intake_contract.md`
- `plugin_namespace_policy_contract.md`
- `plugin_runtime_artifact_manifest_contract.md`
- `plugin_registry_contract.md`
- `plugin_verification_test_policy_contract.md`
- `plugin_runtime_loading_installation_contract.md`
- `plugin_runtime_execution_binding_contract.md`
- `plugin_context_io_contract.md`
- `plugin_failure_recovery_contract.md`
- `plugin_runtime_observability_contract.md`
- `plugin_runtime_governance_contract.md`
- `plugin_lifecycle_state_machine_contract.md`
- `plugin_classification_mcp_compatibility_contract.md`
- `plugin_contract_family_index.md`

---

## 3. Current truth and corrected planning decision

### 3.1 Current core-product truth

Nexa is not at a "start UI from scratch" stage.
The core product is already past UI foundation creation and is in productization-first loop closure.
At minimum, server-backed first-success surfaces already exist in the current core/UI baseline, and the product is in the territory of making setup, run, and review paths actually operable.

### 3.2 Current SaaS implementation truth

The existence of core-product first-success surfaces does **not** mean SaaS P0 is implemented.
P0 must be treated as **not yet complete** until the approved P0 brief is implemented and green.
Do not assume the following already exist just because the planning documents describe them:
- `asgi.py`
- `src/server/pg/`
- `alembic/`
- `engine_bridge.py`
- `p0_configuration.py`

Any phase that depends on the public SaaS substrate must therefore treat **P0 implementation complete + tests green** as a hard gate.

### 3.3 Current UI truth

The UI already has a shell/module foundation.
The remaining UI work is not greenfield UI architecture.
It is product completion work.

### 3.4 Scope reconciliation rule

`nexa_saas_completion_plan_practical_execution_order.md` remains authoritative for the **SaaS-only track**.
This master plan is authoritative for the **cross-family global sequence** across SaaS, UI, Plugin Builder, and Ops plans.

This means:
- if the question is "what is the correct SaaS MVP order inside the SaaS family?" → follow `practical_execution_order.md`
- if the question is "when must Plugin Builder enter the overall remaining-work sequence relative to UI and SaaS?" → follow this master plan

The difference is scope, not contradiction.

### 3.5 Corrected planning decision

Do **not** postpone Plugin Builder until after all remaining UI work.
That sequencing is irrational because Plugin Builder is already specified as a real product surface with explicit UI caller contexts such as:
- `designer_flow`
- `manual_builder_ui`
- `automation_flow`
- `admin_flow`

Plugin Builder must therefore be implemented early enough that the remaining UI can be completed *around* it rather than being reworked later.

### 3.6 Final sequencing principle

The correct global sequence is:

1. orchestration truth reconciliation
2. P0 implementation and green
3. minimum first-success product loop, real-input/browser minimum, and SaaS-basic observability/security floor
4. Plugin Builder core
5. plugin-aware UI completion
6. broader web/product polish
7. advanced trust, support, and operations maturity
8. operations AI
9. capability expansion
10. deferred/community-style work

---

## 4. Non-negotiable global invariants

These rules apply to every phase.

### 4.1 Product reality beats document literalism
If a legacy plan implies a sequence that would cause rework, use the corrected dependency order in this document.
Do not follow older sequencing literally when it conflicts with actual product dependencies.

### 4.2 First-success loop remains mandatory
A general user must be able to:
- start
- understand
- run
- read the result

This remains the baseline product filter for early phases.

### 4.3 Plugin Builder is an external product surface
Plugin Builder is not a background helper.
It is an explicit surface that must be architected early enough for UI integration.

### 4.4 Proposal-space and trusted plugin-space remain distinct
Designer-originated intent must never be treated as trusted plugin runtime truth.

### 4.5 Working Context remains canonical runtime I/O truth
Plugin execution, provider execution, and runtime execution must continue to honor Working Context boundaries.

### 4.6 UI remains a shell above engine truth
UI may guide, compress, and visualize.
UI must not redefine structural truth, approval truth, execution truth, or storage truth.

### 4.7 Data-governance invariants are global, not phase-local
The data-governance decisions in `nexa_saas_completion_plan.md` are mandatory global constraints.
At minimum, all implementing AIs must preserve the following:
- **Category A append-only is absolute.** `execution_record` and other Category A tables are never updated and never hard-deleted.
- **Category B is the GDPR mutation/deletion zone.** Identity-bearing mutable tables may be updated or deleted during GDPR/user-deletion flows.
- **No direct PII may appear in immutable Category A rows.** Immutable execution/audit rows may store only opaque `user_ref`-style linkage, not raw user ID, email, display name, IP address, or similar direct identity.
- **GDPR deletion must not mutate `execution_record`.** GDPR/user-deletion flows operate by clearing mutable identity tables, not by rewriting immutable execution history.
- **`provider_cost_catalog` is canonical.** Provider pricing and cost resolution must converge on the DB-backed provider catalog defined in the SaaS completion plan.
- **BYOK is explicitly deferred.** No phase may casually reintroduce bring-your-own-key product scope unless the explicit re-evaluation gates in the SaaS completion plan are satisfied.

### 4.8 Operations AI comes after operational truth exists
Do not build AI-assisted operations before the project has a structured operational substrate, admin boundary, and audit/diagnostic sources.
Where Ops documents mention "multi-agent coordination," read that strictly as ops-layer assistant coordination and not as permission to alter the engine execution constitution.

### 4.9 "Multi-agent" in ops does not alter the Nexa execution constitution
If an Ops document refers to `ops_multi_agent_coordination_spec.md` or to "multi-agent coordination," interpret that as coordination among operational assistant agents inside the ops layer.
It does **not** authorize any change to Nexa's constitutional execution model.
Node remains the sole execution unit, and ops-agent coordination must not be misread as engine-level multi-agent orchestration.


### 4.10 AI-assisted operations is internal-only
AI-assisted operations is an owner/operator/admin-only operational system.
It must not be exposed to general users through product UI, workspace APIs, public-share routes, user-facing run APIs, or customer-facing tokens.

Implementation rule:
- every AI-assisted operations route must be under an internal/admin route namespace or equivalent guarded surface,
- every route must enforce backend `ops.*` permissions before source lookup or model invocation,
- UI hiding is required but never sufficient,
- general users, workspace owners, and project collaborators receive no operations AI access unless they also possess an explicit operations role,
- unauthorized attempts must be denied before evidence bundle construction and audited with redacted metadata only.

This rule overrides any ambiguous wording such as "operator-facing" or "admin surface" if a future implementer could misread it as a general product capability.

### 4.10 Expansion comes after usability and operability
Do not move to broad capability expansion before the core product and its operational support are structurally credible.

---

## 5. Global order of implementation files

This is the final global order.
Read these in this order and implement in this order unless a later phase explicitly says that a subset may be parallelized safely.

### Phase 0 — orchestration spine (read-first, not direct build target)
1. `saas/nexa_saas_backend_foundation_impl_brief.md`
2. `saas/saas_implementation_plan_index.md`
3. `saas/nexa_saas_completion_plan.md`
4. `saas/nexa_saas_completion_plan_practical_execution_order.md`

### Phase 1 — P0 implementation and green gate
5. `saas/nexa_saas_backend_foundation_impl_brief.md` (active implementation target)
6. `saas/foundation_and_platform_implementation_plan.md` (supporting decomposition for P0 only where consistent with the approved brief)

### Phase 2 — async spine, real-input/browser minimum, and SaaS-basic observability/security floor
7. `saas/async_execution_and_worker_implementation_plan.md`
8. `saas/provider_billing_and_quota_implementation_plan.md` (provider core only)
9. `saas/file_ingestion_and_document_safety_implementation_plan.md`
10. `ui/nexa_remaining_ui_implementation_plan.md` (UI-A only)
11. `saas/web_application_implementation_plan.md` (skeleton only)
12. `saas/contract_review_vertical_slice_implementation_plan.md`
13. `saas/observability_security_and_privacy_implementation_plan.md` (S7 basic + S8 core only)

### Phase 3 — Plugin Builder core pulled forward
14. `pulgin/plugin_builder_full_implementation_plan.md` (core-first implementation)

### Phase 4 — plugin-aware product completion
15. `ui/nexa_remaining_ui_implementation_plan.md` (UI-B and UI-C)
16. `saas/web_application_implementation_plan.md` (plugin-aware polish stage)

### Phase 5 — advanced trust, support, and operations maturity
17. `saas/observability_security_and_privacy_implementation_plan.md` (remaining advanced/privacy-support remainder only)
18. `saas/operations_recovery_and_admin_surface_implementation_plan.md`
19. `ops/ai_assisted_operations_implementation_plan.md`

### Phase 6 — controlled expansion
20. `saas/capability_activation_and_expansion_implementation_plan.md`

### Phase 7 — explicitly late / deferred work
- UI Class D work from the UI remaining plan
- marketplace/community/account-growth surfaces
- pending/deferred higher-order engine/platform proposals not required for the product core

---

## 6. Detailed phase plan

# Phase 0 — orchestration spine

## 6.1 Goal
Establish one planning truth source before code changes.

## 6.2 Why this phase exists
The uploaded plans overlap.
Without a control spine, an implementing AI may follow one file literally and cause downstream rework.

## 6.3 What to do
- read all four control/orchestration files fully
- extract any contradictions
- adopt this master plan as the final sequencing layer when conflicts arise
- create an internal execution checklist for the current session

## 6.4 Outputs
- one local execution checklist
- one current-phase marker
- one migration note list for conflicts between old sequence and corrected sequence
- one explicit scope note stating that `practical_execution_order.md` is SaaS-local while this master plan is cross-family global

## 6.5 Completion criteria
- no ambiguous interpretation remains about what comes before what
- the implementing AI can state the current phase and why it precedes the next one

## 6.6 Do not do
- do not code from Phase 0 alone
- do not treat orchestration docs as feature implementation specs

---

# Phase 1 — P0 implementation and green gate

## 7.1 Files
- `saas/nexa_saas_backend_foundation_impl_brief.md`
- `saas/foundation_and_platform_implementation_plan.md` (supporting only where it does not conflict with the approved brief)

## 7.2 Goal
Implement P0 exactly enough to satisfy the approved brief and produce a green public-SaaS substrate before any later SaaS-dependent phase begins.

## 7.3 Why this must come first
`practical_execution_order.md` is explicit: P0 implementation complete and green is the first real implementation gate.
Without this substrate, later SaaS-facing phases would be built on imagined files and routes rather than on a real baseline.

## 7.4 Required outcomes

### A. P0 brief implementation
Must establish at minimum:
- the exact route set and route boundaries required by the approved P0 brief
- real app bootstrap / ASGI wiring
- real DB integration and migration baseline
- auth boundary implementation consistent with the approved decision
- public API execution gate behavior consistent with the approved P0 brief
- all route-level and invariant-level tests required by the brief

### B. Foundation decomposition support
`foundation_and_platform_implementation_plan.md` may be used only as a decomposition aid for P0 implementation.
If it conflicts with the approved brief, the approved brief wins.

### C. Green gate semantics
Before leaving this phase, the implementation must satisfy the P0 brief's own success conditions:
- P0 files exist in reality, not only in planning text
- the mandated route slice is implemented
- the required test baseline is green
- no later phase is being propped up by placeholder SaaS infrastructure

## 7.5 Code categories likely created or changed
- app bootstrap / ASGI entrypoint
- config and service wiring
- DB and migration foundations
- auth boundary and request-context infrastructure
- route handlers and public execution gate surfaces
- bridge files required by the approved P0 brief

## 7.6 Tests required before Phase 2
- all P0 brief route tests
- app boot smoke tests
- DB migration/app startup tests
- invariant/contract tests required by the brief
- no placeholder route or scaffold remains in the critical path

## 7.7 Completion criteria
- P0 is implemented in reality, not only described in docs
- the P0 test set is green
- the SaaS public substrate is now real enough that later phases can depend on it honestly

## 7.8 Do not do
- do not skip this phase by pretending core-product surfaces substitute for SaaS P0
- do not start async/provider/file/plugin/web work on top of imagined SaaS files
- do not widen scope beyond the approved brief just because adjacent plans mention later concerns

---

# Phase 2 — async spine and real-input/browser minimum

## 8.1 Files
- `saas/async_execution_and_worker_implementation_plan.md`
- `saas/provider_billing_and_quota_implementation_plan.md` (provider core only)
- `saas/file_ingestion_and_document_safety_implementation_plan.md`
- `ui/nexa_remaining_ui_implementation_plan.md` (UI-A only)
- `saas/web_application_implementation_plan.md` (skeleton only)
- `saas/contract_review_vertical_slice_implementation_plan.md`
- `saas/observability_security_and_privacy_implementation_plan.md` (S7 basic + S8 core only)

## 8.2 Goal
After P0 is real and green, add the minimum async/provider/input/UI/browser capabilities required for a credible first-success loop using real inputs and a minimal browser surface, and establish the SaaS-basic observability/security floor required before that browser surface can be treated as publicly credible.

## 8.3 Why this phase comes before Plugin Builder core
Plugin Builder must not displace the core requirement that a general user can start, run, and read a result.
That minimum loop still comes first.

## 8.4 Subphase 2A — async spine

### Implement now
- non-blocking job submission
- queue/worker execution boundary
- run identity and persisted job state
- retry-safe infrastructure behavior
- status polling or equivalent progress path

### Completion criteria
- a real request can submit work without blocking the request thread
- canonical job state survives process boundaries and restarts

## 8.5 Subphase 2B — provider core only

### Implement now
- canonical provider catalog
- server-managed provider credential path
- provider availability/diagnostic surface for product use
- pricing/cost resolver primitives needed later for user-facing estimates

### Explicitly delay
- full billing UX
- full quota account surface
- monetization polish

### Completion criteria
- the product can offer a provider-backed run path without raw env-var-centric user friction
- provider absence or misconfiguration can be represented in beginner-safe product language

## 8.6 Subphase 2C — real input path

### Implement now
- file upload path
- URL ingestion path where planned
- ingestion safety checks
- quarantine/block semantics where needed
- file/URL -> workflow entry continuity

### Completion criteria
- a real external document path exists
- unsafe or invalid inputs fail with explicit and product-safe messages

## 8.7 Subphase 2D — UI-A only

UI-A means only the immediately blocking UI items.

### Implement now
- beginner shell enforcement minimum
- designer-first empty-state entry
- first-success setup/run/review operability
- direct goal path clarity
- starter template path clarity
- file/URL path clarity
- provider path clarity
- stronger beginner-safe result display minimum
- friendly error message minimum across blocking first-success states

### Do not implement yet
- broad advanced shell closure
- community/share/account growth surfaces
- plugin-aware builder UI

### Completion criteria
- a beginner can tell what path they are in
- the primary next action is obvious
- file/provider/result blockers no longer feel structurally ambiguous

## 8.8 Subphase 2E — web skeleton only

### Implement now
- sign-in or minimal access path if already chosen
- workspace shell container
- upload entry
- submit/run entry
- result screen minimum

### Do not implement yet
- full advanced shell
- deep product polish
- plugin discovery/builder surfaces

## 8.9 Subphase 2F — contract review vertical slice

### Implement now
- one end-to-end PMF candidate path
- upload -> analyze -> return structured result -> allow next action
- enough result quality and visibility for user validation

### Why this must happen here
This is where the project proves a concrete product path before broader platform expansion.

## 8.10 Subphase 2G — SaaS-basic observability/security floor

### Implement now
- S7 basic observability such as Sentry or equivalent crash/error capture
- S8 core security guardrails such as security headers, explicit CORS policy, and rate limiting or equivalent protection
- minimal privacy-safe logging/redaction boundaries for externally facing request paths
- enough event visibility to diagnose upload, run, and browser-surface failures before Phase 3 begins

### Why now
`practical_execution_order.md` places S7 basic and S8 core before the SaaS MVP line.
The cross-family master plan must preserve that SaaS-local timing even though the broader Phase 5 still contains the advanced trust/support remainder.

## 8.11 Tests required before Phase 3
- provider setup and failure-state tests
- file ingestion and safety tests
- first-success route/surface tests
- minimal browser flow tests
- contract review E2E tests
- Sentry/error capture smoke tests
- security-header/CORS/rate-limit tests
- privacy-safe logging/redaction boundary tests

## 8.12 Completion criteria
- a real user can upload a real input, run a real path, and read a real result in a minimal browser flow

---

# Phase 3 — Plugin Builder core pulled forward

## 9.1 File
- `pulgin/plugin_builder_full_implementation_plan.md`

## 9.2 Goal
Implement Plugin Builder early enough that the remaining UI can integrate it correctly.

## 9.3 Why Plugin Builder is here
Plugin Builder is already a product surface, not just a later internal utility.
Its placement here does not invalidate `practical_execution_order.md`; it extends beyond the SaaS-only track because the global remaining-work set includes a Plugin Builder family that the SaaS-local practical order does not attempt to sequence.
It has explicit caller contexts including `designer_flow` and `manual_builder_ui`.
Therefore it must exist before remaining UI completion, otherwise later UI work will be structurally incomplete and will need rework.

## 9.4 Scope of this phase
Implement the Plugin Builder **core-first**, not the entire deepest runtime/governance stack all at once.

## 9.5 Core-first Plugin Builder layers to implement now

### Layer A — Proposal / intake / normalization
Must implement at minimum:
- `DesignerPluginBuildProposal`
- `PluginBuilderRequest`
- `PluginBuilderSpec`
- caller context
- governance context
- build options
- intake gate
- normalization stage
- explicit findings model

### Layer B — namespace and classification
Must implement at minimum:
- requested vs approved namespace split
- explicit namespace policy model
- classification request/result model
- MCP compatibility mapping boundary

### Layer C — generation / artifact / manifest
Must implement at minimum:
- scaffold generation path
- canonical runtime artifact family
- canonical manifest family
- packaging skeleton if configured
- generated file references

### Layer D — validation / verification
Must implement at minimum:
- builder validation report
- verification report
- stage reports
- blocking vs warning findings
- pass/fail stage semantics

### Layer E — registry publication minimum
Must implement at minimum:
- canonical registry entry family
- publication scope model
- artifact_ref / manifest_ref linkage
- readiness posture visibility
- search/discovery minimum semantics

### Layer F — thin server/public surface
Must implement at minimum:
- builder models
- builder runtime service bridge
- builder routes
- public plugin surface updates required for builder discovery/result exposure

## 9.6 Internal code ordering inside this phase

Implement these groups in this order.

### Group 1 — new contracts package spine
1. `src/plugins/contracts/common_enums.py`
2. `src/plugins/contracts/serialization.py`
3. package `__init__.py` files
4. `src/contracts/spec_versions.py` updates

### Group 2 — intake and builder core types
5. `src/plugins/contracts/intake_types.py`
6. `src/plugins/contracts/builder_types.py`

### Group 3 — builder orchestration minimum
7. `src/plugins/builder/findings.py`
8. `src/plugins/builder/modes.py`
9. `src/plugins/builder/intake_gate.py`
10. `src/plugins/builder/normalize.py`
11. `src/plugins/builder/service.py`

### Group 4 — namespace and classification
12. `src/plugins/contracts/namespace_types.py`
13. `src/plugins/contracts/classification_types.py`
14. `src/plugins/builder/classification.py`
15. `src/plugins/adapters/mcp_bridge.py`

### Group 5 — artifact and manifest
16. `src/plugins/contracts/artifact_types.py`
17. `src/plugins/builder/template_resolver.py`
18. `src/plugins/builder/generator.py`
19. `src/plugins/builder/storage.py`
20. `src/plugins/adapters/legacy_platform_bridge.py`

### Group 6 — validation and verification
21. `src/plugins/builder/validator.py`
22. `src/plugins/contracts/verification_types.py`
23. `src/plugins/builder/verifier.py`

### Group 7 — registry minimum
24. `src/plugins/contracts/registry_types.py`
25. `src/plugins/registry/catalog.py`
26. `src/plugins/registry/persistence.py`
27. `src/plugins/registry/search.py`
28. `src/plugins/registry/fingerprint.py`
29. `src/plugins/builder/registrar.py`

### Group 8 — thin server/public surface
30. `src/server/plugin_builder_models.py`
31. `src/server/plugin_builder_runtime.py`
32. `src/server/plugin_builder_routes.py`
33. required updates to `src/server/public_plugin_models.py`
34. required updates to `src/server/public_plugin_runtime.py`

## 9.7 Existing files to bridge during this phase
- `src/platform/plugin_auto_loader.py`
- `src/platform/plugin_executor.py`
- `src/platform/plugin_version_registry.py`
- `src/platform/plugin_definition.py`
- `src/platform/plugin_result.py`
- `src/platform/plugin_discovery.py`
- `src/engine/plugin_registry_fingerprint.py`

These should be bridged, not blindly replaced.

## 9.8 Tests required before Phase 4
- intake normalization tests
- namespace request/approved split tests
- builder stage sequencing tests
- artifact/manifest creation tests
- validation and verification failure-mode tests
- registry entry discovery tests
- thin server route tests for builder surface

## 9.9 Completion criteria
- a Designer or manual builder caller can submit a builder request
- the builder can normalize, generate, validate, verify, and optionally register
- the result is exposed as one coherent builder result object
- a minimal registry/discovery surface exists
- the remaining UI can now integrate against a real builder surface instead of placeholders

## 9.10 Do not do yet
- do not fully finish runtime governance/lifecycle depth in this phase
- do not build every future registry scope
- do not overbuild marketplace/recommendation surfaces

---

# Phase 4 — plugin-aware product completion

## 10.1 Files
- `ui/nexa_remaining_ui_implementation_plan.md` (UI-B and UI-C)
- `saas/web_application_implementation_plan.md` (plugin-aware polish stage)

## 10.2 Goal
Complete the remaining product UI now that Plugin Builder exists as a real surface.

## 10.3 Why this phase must come after Phase 3
Without a real builder, manual builder UI, registry UI, and builder-aware Designer flows would be speculative and would require rework.

## 10.4 UI work to implement now

### A. Plugin-aware Designer Panel
Must support:
- plugin proposal initiation
- clarification prompts for plugin build ambiguity
- preview/build action handoff
- display of builder findings and builder result states

### B. Manual Builder UI
Must support:
- advanced/manual entry into builder flow
- form-driven builder spec editing
- build mode selection where permitted
- validation/verification result inspection
- registration request surface where permitted

### C. Registry and discovery UI
Must support:
- plugin search and browse
- canonical registry entry display
- readiness posture and scope display
- artifact/manifest identity linkage without exposing raw internals unnecessarily

### D. Remaining productization work from UI-B and UI-C
Must finish:
- cost visibility
- waiting-state feedback
- contextual help
- result/history/reentry hardening
- feedback continuity hardening
- product-surface review hardening
- plugin-builder-aware continuity where rational

### E. Web shell polish for the now-expanded product
Must add:
- builder entry points
- discovery links
- richer result surfaces
- clearer advanced/beginner transitions
- deeper browser navigation coherence

## 10.5 Tests required before Phase 5
- UI tests for builder-aware Designer flow
- manual builder UI tests
- registry/discovery UI tests
- result/history/reentry tests
- waiting-state/cost/help tests
- browser integration tests crossing normal product flow and builder flow

## 10.6 Completion criteria
- the product UI can integrate a real Plugin Builder surface without stubbing
- advanced users can discover and use builder functionality
- builder and core product flows coexist coherently inside the product shell

---

# Phase 5 — trust, support, and operations maturity

## 11.1 Files
- `saas/observability_security_and_privacy_implementation_plan.md` (remaining advanced/privacy-support remainder only)
- `saas/operations_recovery_and_admin_surface_implementation_plan.md`
- `ops/ai_assisted_operations_implementation_plan.md`

## 11.2 Goal
Make the product operable, diagnosable, and supportable once the user-facing and builder-facing surfaces are real, building on top of the SaaS-basic observability/security floor already established in Phase 2.

## 11.3 Subphase 5A — advanced observability, privacy, and supportability remainder

### Implement now
- deeper operational observability for runs, uploads, builder jobs, and failures
- privacy/data transparency product support that goes beyond the Phase 2 minimum floor
- richer audit/event support for later admin and ops-AI use
- any remaining trust/support work from the observability/security/privacy plan that is not already required as the Phase 2 SaaS-basic floor

### Why now
By this point the public surface is large enough that advanced supportability and privacy clarity become structural requirements, but the minimum SaaS security floor should already exist from Phase 2.

## 11.4 Subphase 5B — operations recovery and admin surface

### Implement now
- admin visibility for jobs, failures, stuck states, quarantines, and recovery actions
- operational recovery pathways
- support-friendly diagnostics
- storage cleanup and lifecycle maintenance where specified

### Why now
Once users, files, and builder artifacts exist in live flows, the product must be operable without direct low-level intervention.

## 11.5 Subphase 5C — AI-assisted operations

### Implement in explicit internal order
1. read-only insight
2. recommendation and decision structuring
3. approval-gated actions
4. narrow autonomous housekeeping

### Why AI-assisted operations is after admin surface
Operational AI must consume structured operational truth and role boundaries.
Without that, it is unsafe and difficult to audit.


### Required internal-access boundary
Before Stage A is considered implemented, the project must have:

- explicit `ops.*` backend permissions,
- a server-side operations actor context,
- route guards for every AI-assisted operations endpoint,
- denial tests for general users and workspace owners without operations role,
- proof that denied requests do not query operational sources or invoke models,
- redacted audit records for unauthorized attempts.

AI-assisted operations must never be mounted into the general product route tree without these guards.

## 11.6 Tests required before Phase 6
- observability event and log tests
- privacy/redaction tests
- admin action/recovery tests
- AI-assisted ops stage tests with read-only/recommendation/approval separation

## 11.7 Completion criteria
- failures and stuck states are visible and actionable
- privacy/security boundaries are explicit and testable
- operations AI can safely reason over operational truth without bypassing human/operator gates

---

# Phase 6 — controlled expansion

## 12.1 File
- `saas/capability_activation_and_expansion_implementation_plan.md`

## 12.2 Goal
Expand capability only after the product, plugin, and operations layers are coherent.

## 12.3 Implement now
- activation logic for additional capability families
- gated rollout patterns
- modular expansion that preserves current truth boundaries
- capability exposure only when support and operations can sustain it

## 12.4 Do not do
- do not open broad feature families without supportability
- do not let capability breadth outrun product clarity and runtime trust

## 12.5 Completion criteria
- new capability families can be activated without breaking usability, governance, or operational support

---

# Phase 7 — explicitly late work

## 13.1 Includes
- UI Class D work
- community or marketplace growth surfaces
- broader account-growth surfaces
- deferred higher-order engine/platform proposals not required for current product completion

## 13.2 Reason for lateness
These are not current blockers for:
- first success
- plugin-builder-aware product completion
- operability
- trust/support maturity

---

## 14. Cross-phase dependency rules

These rules are mandatory.

### 14.1 Plugin Builder depends on minimal product and platform reality
Do not start Plugin Builder core before:
- Phase 1 P0 implementation is complete and green
- Phase 2 first-success core is minimally credible

### 14.2 Remaining UI completion depends on Plugin Builder existence
Do not attempt full advanced/manual builder UI completion before:
- Plugin Builder core surface exists
- registry/discovery minimum exists
- builder result posture is real

### 14.3 Operations AI depends on admin surface and observability
Do not implement autonomous or semi-autonomous operational AI before:
- admin recovery surface exists
- observability/security/privacy baseline exists

### 14.4 Capability expansion depends on product and ops maturity
Do not broaden capability surface before:
- usability is credible
- plugin surface is integrated
- supportability exists

---

## 15. Parallelization rules

Only the following limited parallelization is allowed.

### Safe parallelization
- Phase 1 is not parallelizable. P0 implementation must be complete and green before any Phase 2 work begins.
- Phase 2 provider core and file ingestion may overlap if the credential model and storage boundaries are already fixed.
- Phase 2 SaaS-basic observability/security floor work may overlap with web skeleton work only after route/access boundaries are already fixed and the security work does not depend on imagined frontend contracts.
- During Phase 3, server/public surface work may begin slightly before registry minimum is finished only if the route contracts are explicitly marked provisional and are rewritten before UI integration.
- During Phase 5, privacy-support remainder work and admin surface work may run in parallel if they do not duplicate audit/event schemas.

### Unsafe parallelization
- any async/provider/file/plugin/web work during Phase 1 before P0 is complete and green
- full UI completion and Plugin Builder core in parallel without a shared builder contract surface
- operations AI and admin/observability foundations in parallel as if they were independent
- capability expansion before security/privacy/admin completion

---

## 16. Migration and truth-reconciliation rule

Before every phase begins, the implementing AI must perform a short reconciliation pass:

1. compare current repository HEAD to the assumptions in the phase documents
2. mark which parts are already landed
3. remove already-completed items from the active batch
4. keep this master sequence unchanged unless a hard dependency has objectively changed

This is mandatory because some documents may lag behind code reality.

---

## 17. Global completion definition

The remaining work is complete only when all of the following are true.

### 17.1 Product completion
- first-success loop is genuinely operable
- returning-use loop is credible
- real file/provider/result paths are product-grade

### 17.2 Plugin integration completion
- Plugin Builder core exists
- Plugin Builder is exposed as a real product surface
- remaining UI is builder-aware and discovery-aware

### 17.3 Platform and web completion
- browser shell is credible for real use
- contract review vertical slice is operational
- async execution and provider/file foundations are stable

### 17.4 Trust and operations completion
- observability/security/privacy baseline is real
- admin recovery surface is usable
- AI-assisted operations is staged safely on top of operational truth

### 17.5 Expansion readiness
- capability activation can proceed without undermining product clarity or supportability

---

## 18. Final decision statement

The global remaining Nexa implementation order is therefore:

1. control/orchestration spine
2. Phase 1 P0 implementation and green gate
3. first-success and real-input blockers
4. minimal web + PMF vertical slice
5. Plugin Builder core
6. plugin-aware UI and web completion
7. observability, security, privacy, admin, and operations AI
8. controlled capability expansion
9. explicitly late/deferred growth work

This is the most rational sequence because it satisfies both of the following simultaneously:

- the product still prioritizes first-success and usability
- Plugin Builder is implemented early enough that the remaining UI can be completed around a real builder surface rather than a placeholder
