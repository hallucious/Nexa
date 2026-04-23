# Nexa All-Phases Execution Batch Table v1.0

## Recommended save path
`docs/implementation/master/nexa_all_phases_execution_batch_table.md`

## 1. Purpose

This document converts the approved global master plan into executable implementation batches across **all active phases**, not only Phase 1.

It exists so that another AI system can move from planning to execution without re-interpreting:
- phase order
- cross-document priority
- batch boundaries
- dependency gates
- test obligations
- “do now” vs “do later” scope

This is an execution companion to the approved master plan.  
It is not a replacement for the master plan.  
The master plan defines the global sequence.  
This document defines the batch-level execution shape.

## 2. Authoritative input set

Use the following as the planning spine behind this document:

1. `docs/implementation/master/nexa_global_remaining_implementation_master_plan.md`
2. `saas/nexa_saas_backend_foundation_impl_brief.md`
3. `saas/saas_implementation_plan_index.md`
4. `saas/nexa_saas_completion_plan.md`
5. `saas/nexa_saas_completion_plan_practical_execution_order.md`
6. `ui/nexa_remaining_ui_implementation_plan.md`
7. `pulgin/plugin_builder_full_implementation_plan.md`
8. `ops/ai_assisted_operations_implementation_plan.md`
9. `docs/specs/ui/beginner_shell_compression_policy.md`
10. `docs/specs/ui/general_user_productization_priority.md`

If any future document conflicts with this batch table, the conflict must be resolved against the master plan first.

## 3. Non-negotiable global execution rules

### 3.1 Phase 1 hard gate
Phase 1 is **not parallelizable**.

No Phase 2 work may begin until:
- P0 implementation exists in code
- P0 tests are green
- repository baseline is stable enough to support later work without imaginary files

### 3.2 First-success priority remains real
Even though Plugin Builder is pulled forward before total UI completion, the project remains in a first-success / productization-first stage.

That means:
- beginner-first path clarity still outranks advanced tooling polish
- graph-first complexity must still remain deferred for beginner-first entry
- provider/file/result blockers still outrank growth surfaces

### 3.3 Plugin Builder is early, but not first
Plugin Builder is not a late afterthought.
It must land before full UI completion because the UI must become plugin-builder-aware.

However:
- Plugin Builder does not come before P0
- Plugin Builder does not come before async/provider/file substrate
- Plugin Builder does not come before minimum first-success surface operability

### 3.4 Data-governance invariants
The following are fixed and must be preserved in all phases:

- Category A execution/audit records are append-only and must not be deleted casually
- Category B user-facing mutable data may carry GDPR-delete semantics
- direct PII must not be placed into Category A execution truth
- `execution_record` truth is not a GDPR-mutation target
- `provider_cost_catalog` is canonical provider-cost reference state
- BYOK remains explicitly deferred unless a later decision changes it

### 3.5 Ops multi-agent boundary
Any “multi-agent coordination” inside AI-assisted operations refers only to **ops-layer assistant coordination**.
It must not be interpreted as changing the Nexa engine execution model.

Node remains the sole execution unit.

### 3.6 What this document intentionally does not do
This document does not define:
- line-by-line code
- final schema details
- endpoint payload definitions in full
- product copy
- design mockups

Those belong to implementation files and lower-level specs.

## 4. Phase map

### Phase 1
P0 implementation and green gate

### Phase 2
Async/provider/file substrate + UI-A + web skeleton + contract-review vertical slice + SaaS-basic observability/security floor

### Phase 3
Plugin Builder core and public surface

### Phase 4
Plugin-builder-aware UI completion + web polish

### Phase 5
Advanced observability/privacy-support remainder + admin/recovery + AI-assisted operations

### Phase 6
Capability activation and expansion

### Late Track
Explicitly deferred or intentionally post-core work

---

# 5. Phase 1 — P0 implementation and green gate

## 5.1 Goal
Create the real server/platform spine that later phases can safely build on.

## 5.2 Entry condition
None. This is the first implementation phase.

## 5.3 Exit gate
Phase 1 is complete only when:
- P0 files exist in code, not only in documents
- app bootstrap exists
- DB/migration baseline exists
- foundational config exists
- engine/server integration bridge exists
- green baseline is established

## 5.4 Batch table

### Batch P0-1 — Bootstrap and configuration spine
**Primary goal**
Create the minimum application/bootstrap/config skeleton.

**Expected file focus**
- `asgi.py`
- `src/server/p0_configuration.py`
- `src/server/config/__init__.py`
- `src/server/config/settings.py`
- `src/server/config/env.py`
- `tests/server/test_bootstrap_smoke.py`

**Must deliver**
- application entrypoint
- deterministic settings loading
- environment/bootstrap validation
- explicit failure on missing required config

**Do not do**
- no feature routes yet
- no fake runtime logic
- no product UI work here

**Batch completion**
- import/bootstrap smoke passes
- app can start under test config

### Batch P0-2 — DB and migration baseline
**Primary goal**
Create the canonical persistence spine.

**Expected file focus**
- `src/server/pg/__init__.py`
- `src/server/pg/session.py`
- `src/server/pg/base.py`
- `src/server/pg/models/`
- `alembic/`
- `alembic.ini`
- `tests/server/test_db_bootstrap.py`
- `tests/server/test_alembic_smoke.py`

**Must deliver**
- SQLAlchemy base/session
- migration environment
- initial migration baseline
- health-checked DB wiring

**Do not do**
- no premature product tables beyond baseline needs
- no billing complexity yet

**Batch completion**
- migration up/down works in test env
- DB session smoke passes

### Batch P0-3 — Engine/server bridge and request spine
**Primary goal**
Create the minimum bridge between server orchestration and core Nexa engine entry.

**Expected file focus**
- `src/server/engine_bridge.py`
- `src/server/runtime/__init__.py`
- `src/server/runtime/service.py`
- `src/server/routes/health.py`
- `tests/server/test_engine_bridge_smoke.py`

**Must deliver**
- one canonical engine integration boundary
- request-safe execution/service wrapper
- health endpoint
- error-safe server-side bridge semantics

**Do not do**
- no full business logic
- no advanced queueing here

**Batch completion**
- bridge smoke test passes
- health route passes

### Batch P0-4 — Governance floor and canonical catalog anchors
**Primary goal**
Anchor the few platform truths later phases depend on.

**Expected file focus**
- provider cost catalog model and seed path
- baseline table classification metadata
- data governance constants or rule module
- tests for Category A / Category B boundaries

**Suggested file focus**
- `src/server/pg/models/provider_cost_catalog.py`
- `src/server/governance/data_classification.py`
- `src/server/governance/pii_rules.py`
- `tests/server/test_data_governance_invariants.py`

**Must deliver**
- `provider_cost_catalog` canonical anchor
- explicit Category A / Category B distinction
- PII placement guardrails

**Do not do**
- no BYOK implementation
- no GDPR delete executor yet

**Batch completion**
- invariant tests pass

### Batch P0-5 — Phase 1 green gate
**Primary goal**
Prove P0 is real and stable enough to unlock Phase 2.

**Required tests**
- bootstrap smoke
- config smoke
- DB smoke
- migration smoke
- engine bridge smoke
- any mandatory baseline suite selected by repository state

**Batch completion**
- all P0 tests pass together
- no missing-file assumptions remain
- Phase 2 may start

---

# 6. Phase 2 — Substrate + UI-A + vertical slice + basic security floor

## 6.1 Goal
Move from mere platform spine to a minimum real product loop.

## 6.2 Entry condition
Phase 1 P0 implementation is complete and green.

## 6.3 Exit gate
Phase 2 is complete only when:
- async execution substrate exists
- provider core exists
- file/document ingestion minimum exists
- UI-A first-success path is materially improved
- web skeleton works end-to-end
- contract-review vertical slice is alive
- S7 basic + S8 core security floor is in place

## 6.4 Batch table

### Batch 2A — Async execution substrate
**Primary goal**
Introduce non-blocking execution/worker substrate.

**Expected file focus**
- queue/worker runtime files
- job persistence or in-memory abstraction if documented
- run state projection files
- test workers / queue smoke tests

**Suggested file focus**
- `src/server/jobs/`
- `src/server/worker/`
- `src/server/runtime/run_queue.py`
- `tests/server/test_async_run_submission.py`
- `tests/server/test_worker_smoke.py`

**Must deliver**
- queued run submission
- worker-side run execution
- status progression beyond synchronous request blocking

**Batch completion**
- async run smoke passes
- status transition test passes

### Batch 2B — Provider core early slice
**Primary goal**
Create the server-managed provider core that reduces raw-env friction.

**Expected file focus**
- provider catalog resolver
- server-managed credential abstraction
- provider pricing lookup
- provider diagnostics surface
- tests for provider resolution

**Suggested file focus**
- `src/providers/env_diagnostics.py`
- `src/designer/semantic_backend_presets.py`
- server-side provider config/registry files
- `tests/providers/test_provider_resolution.py`

**Must deliver**
- canonical provider list
- server-managed provider selection base
- pricing lookup path

**Do not do**
- no full BYOK
- no billing UX

**Batch completion**
- provider resolution tests pass
- pricing lookup works from canonical catalog

### Batch 2C — File ingestion and document safety minimum
**Primary goal**
Make real document input possible safely.

**Expected file focus**
- upload intake
- MIME/type validation
- size/safety checks
- document reference persistence
- tests for valid/invalid uploads

**Suggested file focus**
- `src/server/uploads/`
- `src/server/documents/`
- `tests/server/test_file_ingestion_minimum.py`
- `tests/server/test_document_safety_rules.py`

**Must deliver**
- upload path
- file reference path
- minimum safety checks
- rejection of unsafe/unsupported input

**Batch completion**
- file ingest tests pass

### Batch 2D — UI-A first-success core
**Primary goal**
Close the strongest immediate beginner blockers.

**Expected file focus**
- `src/ui/builder_shell.py`
- `src/ui/i18n.py`
- `src/ui/panel_coordination.py`
- `src/ui/designer_panel.py`
- `src/ui/execution_panel.py`
- `src/ui/proposal_commit_workflow.py`
- current server shell/runtime files if server-authoritative routing is needed
- UI/server shell tests

**Must deliver**
- beginner shell enforcement minimum
- clearer entry-path separation
- provider/file/result blocker reduction
- stronger actionable first-success path

**Batch completion**
- targeted first-success/product surface tests pass
- first-success route ambiguity reduced materially

### Batch 2E — Web skeleton minimum
**Primary goal**
Expose the minimum browser product shell.

**Expected file focus**
- auth/session skeleton if required by chosen approach
- workspace page shell
- upload path integration
- submit/run path
- result screen minimum
- frontend smoke tests

**Must deliver**
- sign-in or equivalent access boundary
- workspace shell
- upload → submit → result path

**Do not do**
- no advanced polish
- no marketplace/growth chrome

**Batch completion**
- browser skeleton smoke passes

### Batch 2F — Contract-review vertical slice
**Primary goal**
Bring up one real PMF-aligned slice using the existing substrate.

**Expected file focus**
- contract/document pipeline logic
- result rendering for review use case
- integration tests across upload → run → result

**Must deliver**
- one usable contract-review flow
- result output meaningful to user
- no dead-end demo-only path

**Batch completion**
- one end-to-end contract-review test passes

### Batch 2G — SaaS-basic observability/security floor
**Primary goal**
Implement the minimum S7 basic + S8 core floor before Phase 3.

**Expected file focus**
- Sentry/basic exception capture
- security headers
- explicit CORS policy
- rate limiting
- minimum redaction/safe logging
- tests for headers and rate limiting

**Suggested file focus**
- `src/server/observability/`
- `src/server/security/`
- `tests/server/test_security_headers.py`
- `tests/server/test_rate_limiting.py`

**Must deliver**
- basic error capture
- core security floor
- no public-facing blind spot before Plugin Builder/UI expansion

**Batch completion**
- header/rate-limit tests pass
- basic observability hook works

### Batch 2H — Phase 2 green gate
**Primary goal**
Prove the first real product loop exists.

**Required tests**
- async substrate tests
- provider core tests
- file ingestion tests
- UI-A targeted tests
- web skeleton smoke
- vertical-slice e2e
- security/observability floor tests

**Batch completion**
- Phase 2 suites pass together
- system supports one real first-success contract-review path

---

# 7. Phase 3 — Plugin Builder core and public surface

## 7.1 Goal
Build the Plugin Builder core before total UI completion so that later UI can become plugin-builder-aware instead of being rebuilt afterward.

## 7.2 Entry condition
Phase 2 is complete and green.

## 7.3 Exit gate
Phase 3 is complete only when:
- Plugin Builder core stages exist
- artifact/manifest/registry minimum exists
- verification posture minimum exists
- manual/designer callable public surface exists

## 7.4 Batch table

### Batch 3A — Common contracts and builder entry types
**Primary goal**
Create the common vocabulary and canonical builder entry/result objects.

**Expected file focus**
- `src/plugins/contracts/common_enums.py`
- `src/plugins/contracts/serialization.py`
- `src/plugins/contracts/intake_types.py`
- `src/plugins/contracts/builder_types.py`
- `src/contracts/spec_versions.py`
- tests for serialization/types

**Must deliver**
- builder request/result canon
- deterministic enums/status vocabulary

### Batch 3B — Intake gate, normalization, service skeleton
**Primary goal**
Create proposal-space → builder-space conversion boundary.

**Expected file focus**
- `src/plugins/builder/findings.py`
- `src/plugins/builder/modes.py`
- `src/plugins/builder/intake_gate.py`
- `src/plugins/builder/normalize.py`
- `src/plugins/builder/service.py`
- tests for intake rejection and normalization

**Must deliver**
- normalized Plugin Builder request flow
- no direct runtime trust leap from intake

### Batch 3C — Namespace, classification, artifact/manifest minimum
**Primary goal**
Ground Builder output in enforceable contracts.

**Expected file focus**
- `src/plugins/contracts/namespace_types.py`
- `src/plugins/contracts/classification_types.py`
- `src/plugins/contracts/artifact_types.py`
- `src/plugins/builder/classification.py`
- `src/plugins/adapters/mcp_bridge.py`
- tests for namespace requested/approved distinction

**Must deliver**
- namespace policy objects
- artifact identity/manifest base
- classification request/approval split

### Batch 3D — Generation, validation, verification minimum
**Primary goal**
Make the Builder actually produce and evaluate candidates.

**Expected file focus**
- `src/plugins/builder/template_resolver.py`
- `src/plugins/builder/generator.py`
- `src/plugins/builder/storage.py`
- `src/plugins/builder/validator.py`
- `src/plugins/contracts/verification_types.py`
- `src/plugins/builder/verifier.py`
- bridge edits in legacy platform files if required
- tests for build/validation/verification

**Must deliver**
- candidate generation
- validation findings
- verification posture minimum

### Batch 3E — Registry and public Builder surface
**Primary goal**
Expose Builder output through a real external surface.

**Expected file focus**
- `src/plugins/contracts/registry_types.py`
- `src/plugins/registry/catalog.py`
- `src/plugins/registry/persistence.py`
- `src/plugins/registry/search.py`
- `src/plugins/registry/fingerprint.py`
- `src/plugins/builder/registrar.py`
- `src/server/plugin_builder_models.py`
- `src/server/plugin_builder_runtime.py`
- `src/server/plugin_builder_routes.py`
- `src/server/public_plugin_models.py`
- `src/server/public_plugin_runtime.py`
- tests for public builder routes and registry output

**Must deliver**
- manual_builder_ui-callable public Builder surface
- designer_flow-callable Builder surface
- canonical registry entry family minimum

### Batch 3F — Phase 3 green gate
**Primary goal**
Prove Plugin Builder core is real enough to wire into UI.

**Required tests**
- intake/normalize tests
- namespace/artifact tests
- build/validation/verification tests
- registry/public route tests

**Batch completion**
- another AI could call Builder via public surface and receive meaningful build posture

---

# 8. Phase 4 — Plugin-builder-aware UI completion + web polish

## 8.1 Goal
Finish the remaining UI in a way that is aware of the now-real Plugin Builder surface.

## 8.2 Entry condition
Phase 3 is complete and green.

## 8.3 Exit gate
Phase 4 is complete only when:
- Designer panel can route into Plugin Builder where appropriate
- manual Builder UI exists
- registry/discovery UI exists
- remaining UI-B/UI-C work is closed to product-grade level
- web shell is polished beyond skeleton status

## 8.4 Batch table

### Batch 4A — Designer-panel Builder integration
**Primary goal**
Teach Designer-panel flows how to create or propose plugin-build work.

**Expected file focus**
- `src/ui/designer_panel.py`
- proposal/preview files
- plugin-builder client adapter files
- tests for designer → builder preview/action linkage

**Must deliver**
- bounded plugin-build intent path from Designer UI
- clear preview/findings exposure

### Batch 4B — Manual Builder UI
**Primary goal**
Expose Plugin Builder as an explicit user-facing advanced tool.

**Expected file focus**
- `src/ui/builder_shell.py`
- builder-specific UI module(s)
- i18n keys
- tests for manual Builder screens

**Must deliver**
- form/preview/build/status surface
- mode-safe entry path

### Batch 4C — Registry/discovery UI
**Primary goal**
Expose the canonical registry entry family to users.

**Expected file focus**
- registry/discovery UI modules
- search/filter UI
- public-plugin runtime adapters
- tests for registry list/detail rendering

**Must deliver**
- registry list
- entry detail
- readiness/policy/verification posture visibility

### Batch 4D — UI-B/UI-C remainder
**Primary goal**
Close the remaining productization and return-use surfaces.

**Expected file focus**
- result/history/library UI
- onboarding continuity surfaces
- contextual help
- waiting-state feedback
- cost visibility
- mobile first-run minimum
- privacy/data transparency
- feedback channel surface

**Must deliver**
- no major beginner/return-user blocker remains in planned active UI scope

### Batch 4E — Web polish and integrated product shell
**Primary goal**
Move browser shell from skeleton to genuinely usable product shell.

**Expected file focus**
- richer shell navigation
- registry/build surfaces in web shell
- result/trace/artifact integration where appropriate
- web e2e tests

**Must deliver**
- polished browser workflow
- plugin-builder-aware UX coherence

### Batch 4F — Phase 4 green gate
**Required tests**
- designer-builder integration tests
- manual builder UI tests
- registry UI tests
- remaining beginner/return-use UI tests
- web e2e tests

**Batch completion**
- Plugin Builder and product UI no longer live in separate conceptual worlds

---

# 9. Phase 5 — Advanced observability/privacy-support remainder + admin/recovery + AI-assisted operations

## 9.1 Goal
Strengthen trust, operability, and internal support after the public/product loop is alive.

## 9.2 Entry condition
Phase 4 is complete and green.

## 9.3 Exit gate
Phase 5 is complete only when:
- advanced observability/privacy remainder is in place
- admin/recovery surfaces exist
- AI-assisted operations has at least Stage A and B safely deployed
- any Stage C execution is approval-gated

## 9.4 Batch table

### Batch 5A — Advanced observability/privacy-support remainder
**Primary goal**
Finish the deeper part of observability and user-facing privacy support not required for the early floor.

**Expected file focus**
- advanced redaction/privacy explanation surfaces
- richer operational telemetry
- deeper run diagnostics
- trace/artifact support surfaces if server/admin scoped
- tests for privacy/support behavior

**Must deliver**
- privacy-support depth
- deeper observability for support and debugging

### Batch 5B — Admin and recovery surface
**Primary goal**
Create the operator-facing surface for recovery and lifecycle management.

**Expected file focus**
- admin routes/modules
- stuck-job inspection
- upload quarantine controls
- subscription/quota/admin status surfaces
- backup/recovery utilities
- admin tests

**Must deliver**
- SQL-free operational recovery path
- admin inspection and bounded repair tools

### Batch 5C — AI-assisted operations Stage A
**Primary goal**
Read-only ops insight.

**Expected file focus**
- ops context ingestion
- read-only summarization/retrieval
- runbook-aware explanation surfaces
- tests for read-only guarantees

**Must deliver**
- AI-assisted ops insight without write authority

### Batch 5D — AI-assisted operations Stage B
**Primary goal**
Recommendation and decision-structuring.

**Expected file focus**
- recommendation logic
- structured recommendation objects
- operator review surface
- tests for “advice only” boundary

**Must deliver**
- concrete recommendations, no autonomous actions

### Batch 5E — AI-assisted operations Stage C
**Primary goal**
Approval-gated safe actions.

**Expected file focus**
- approval workflow integration
- bounded safe-action executor
- audit logging
- tests for approval gate and action bounds

**Must deliver**
- no ungated autonomous mutation
- explicit approval boundary on each action

### Batch 5F — AI-assisted operations Stage D (optional within Phase 5)
**Primary goal**
Very narrow autonomous housekeeping only if prior stages are stable.

**Must deliver**
- bounded, reversible, low-risk autonomy

**Do not do**
- no broad autonomous control plane
- no engine-execution-model mutation

### Batch 5G — Phase 5 green gate
**Required tests**
- privacy-support tests
- admin/recovery tests
- ops AI Stage A/B tests
- Stage C approval-gated action tests if enabled

**Batch completion**
- system is supportable by humans and assistive AI without violating execution constitution

---

# 10. Phase 6 — Capability activation and expansion

## 10.1 Goal
Expand capability only after the core loop, Plugin Builder integration, and operational support are stable.

## 10.2 Entry condition
Phase 5 is complete and green.

## 10.3 Exit gate
Phase 6 is complete only when:
- expansion features are added without destabilizing core user/product loop
- rollout, policy, and quota controls remain intact

## 10.4 Batch table

### Batch 6A — Capability activation core
**Primary goal**
Introduce the first controlled activation path for new capability families.

**Expected file focus**
- feature/capability gating modules
- activation policy files
- rollout/flag tests

**Must deliver**
- explicit activation controls
- no hidden capability exposure

### Batch 6B — Expansion integrations
**Primary goal**
Connect additional engine/platform capability families as planned.

**Possible focus**
- advanced automation connections
- governed delivery integrations
- deeper streaming-linked UX
- richer destination or tool families

**Must deliver**
- expansion without breaking earlier product guarantees

### Batch 6C — Rollout, quota, and policy hardening
**Primary goal**
Ensure expansion remains governable.

**Expected file focus**
- feature flags
- quota gates
- org/user scope rules
- rollout tests

### Batch 6D — Phase 6 green gate
**Required tests**
- capability activation tests
- rollout/policy/quota tests
- regression suite protecting Phase 1-5 flows

**Batch completion**
- expansion is real, but core product loop remains intact

---

# 11. Late Track — Explicitly late or deferred work

The following are not part of the active mainline implementation phases above unless a later explicit decision promotes them.

## 11.1 UI growth surfaces
- user accounts and sessions UI if not required earlier by deployment choice
- sharing UI
- community/marketplace surfaces

## 11.2 Deferred engine proposals
- batch execution
- auto-evaluation/evaluation-node family
- regression alert automation
- conditional branch / loop nodes
- cross-run memory
- interactive / conversational execution

## 11.3 Advanced plugin runtime depth not required by early Builder/UI integration
- full runtime governance/lifecycle depth beyond active phase need
- deep runtime observability layers not required for current product loop
- marketplace-like plugin ecosystem work

## 11.4 Larger future sectors
- SubcircuitNode implementation
- evolution-system work
- broad platform shift work outside current master plan

---

# 12. Cross-phase test discipline

## 12.1 Every phase must end in a green gate
No phase is complete because files were edited.
A phase is complete only when its declared gate passes.

## 12.2 Never trust partial green
A later batch passing does not retroactively make an earlier foundational gap acceptable.

## 12.3 Protect earlier phases with regression suites
Later phases must preserve:
- first-success core
- provider/file/result path
- product UI continuity
- Builder public surface
- admin safety boundaries

## 12.4 Prefer phase-local tests plus one integrated gate
Each phase should have:
- local unit/integration tests per batch
- one phase-wide gate suite

---

# 13. Parallelization rules

## 13.1 Safe parallelization begins only after Phase 1
Phase 1 is not parallelizable.

## 13.2 Safe overlaps after Phase 1
Reasonable overlap is allowed only when contracts and ownership boundaries are already fixed.

Examples:
- UI-A work may overlap lightly with web skeleton work after async/provider/file foundations are real
- some Plugin Builder contract work may overlap with non-conflicting UI preparation work after Phase 2 is green
- admin/privacy remainder may overlap with Stage A read-only ops work if mutation boundaries are already fixed

## 13.3 Unsafe overlap examples
Do not overlap if it would create imagined files or invented authority.

Examples:
- any async/provider/file/plugin/web work during Phase 1 before P0 is complete and green
- UI completion before Plugin Builder public surface exists
- AI-assisted ops actions before admin/recovery and approval boundaries are real
- capability expansion before product loop and operational support are stable

---

# 14. How another AI should use this document

When beginning work:

1. identify the current active phase
2. identify the next incomplete batch inside that phase
3. verify phase entry condition is already satisfied
4. execute only that batch scope
5. run the declared tests
6. update phase status
7. move to the next batch only after the current batch gate is satisfied

Do not skip batches because a later feature sounds more interesting.
Do not pull late-track work forward without a new explicit decision.

---

# 15. Final execution principle

The correct order is not:
- “finish all UI first”
- or “build all plugin/platform depth first”

The correct order is:
- establish the real platform spine
- make one real product loop work
- bring Plugin Builder in before total UI completion
- finish UI in a plugin-aware way
- add support/ops depth
- only then expand capability further

That is the execution order that preserves both product rationality and architectural honesty.
