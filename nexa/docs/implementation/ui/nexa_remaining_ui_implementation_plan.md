# Nexa Remaining UI Implementation Plan

## Recommended save path
`docs/implementation/ui/nexa_remaining_ui_implementation_plan.md`

## 1. Purpose

This document defines the full remaining UI implementation plan for Nexa based on:
- the current uploaded source baseline `nexa_0014690.Zip`
- the already-landed first-success / returning-user productization batches completed after `0b9cbda2`
- the canonical UI/productization policy documents already present in the repository

This is not a greenfield UI plan.
It assumes that:
- the UI foundation already exists
- major UI contracts already exist
- major UI modules already exist
- the current task is to finish the remaining product-facing UI work without reopening settled architecture boundaries

The document is written so that another AI can execute the remaining UI work from this plan alone.

## 2. Scope

This plan covers only the remaining UI work.

It does **not** cover:
- plugin builder implementation
- SubcircuitNode implementation
- evolution-system implementation
- broad automation platform expansion
- general documentation sync outside what is strictly required for UI implementation
- SaaS-only account/community growth systems before the first-success and early return-use loop are fully closed

## 3. Current Truth Baseline

### 3.1 Source baseline to use
Use the uploaded repository baseline:
- `nexa_0014690.Zip`

Treat that source snapshot as the authoritative starting point for this plan.

### 3.2 Recently landed UI/productization work already reflected in the current direction
The following batches are already conceptually landed and must **not** be re-planned as if they are still missing:

1. `0b9cbda2`
   - first-success setup/run/product review sections became actually rendered in the shell
2. `2e97711`
   - first-success setup surface refinement
3. `6aab581`
   - first-success run surface refinement
4. `925e34e`
   - return-use guidance and result reentry routing refinement
5. `3dcb7fe`
   - feedback continuity and thread reentry refinement
6. `0014690`
   - top-level product surface review and bottleneck routing refinement

### 3.3 Working interpretation of current project state
Current state is:
- UI foundation exists
- Python-side shell/view-model layer exists
- first-success and early returning-user routing surfaces now materially exist
- the main remaining work is to finish the product-facing beginner/general-user path and then selectively complete the next directly connected UI blockers

In short:
- do **not** re-open UI foundation creation
- do **not** create a second competing shell plan
- do **not** switch the primary objective back to graph/editor polishing
- do **not** drift into farther roadmap sectors before the remaining direct UI blockers are closed

## 4. Architectural Invariants That Must Remain Unchanged

All remaining UI work must preserve the following invariants.

### 4.1 Engine truth remains engine-owned
UI must not own:
- structural truth
- approval truth
- execution truth
- storage lifecycle truth

### 4.2 UI is a shell above the engine
Canonical structure remains:

Nexa Engine
-> UI Adapter / View Model Layer
-> UI Module Slots
-> Theme / Layout Layer

### 4.3 UI reads truth and emits intent/action
UI modules must:
- read truth via adapter/view-model boundaries
- emit intent/action/proposal requests
- never directly mutate raw engine state

### 4.4 Designer remains proposal-first
Designer UI must continue to reflect:

Intent -> Patch -> Precheck -> Preview -> Approval -> Commit

UI may compress or simplify how this appears to beginners,
but it must not bypass the underlying governance chain.

### 4.5 Beginner-first exposure policy remains binding
The first-session user must not be forced into:
- graph-first editing
- trace-first observability
- diff-first comparison
- raw validator internals
- engine/internal storage terminology

### 4.6 `.nex.ui` boundary remains unchanged
- UI continuity is Working Save scoped
- Commit Snapshot must not gain canonical `ui`
- UI continuity persistence must never become engine truth

## 5. Canonical Planning Documents To Treat As Higher Authority

When plan details conflict, resolve in this order:

1. Current uploaded source baseline
2. `docs/specs/ui/beginner_shell_compression_policy.md`
3. `docs/specs/ui/general_user_productization_priority.md`
4. `docs/specs/ui/runtime_bootstrap/core_runtime_ui_implementation_plan.md`
5. UI contract documents under `docs/specs/ui/`
6. Older historical discussion documents

## 6. Current Code Inventory: What Already Exists

The following UI modules already exist in the current repository and must be treated as extension/integration targets rather than greenfield work.

### 6.1 Core shell and hub layer
- `src/ui/builder_shell.py`
- `src/ui/product_flow_shell.py`
- `src/ui/builder_workflow_hub.py`
- `src/ui/builder_dispatch_hub.py`
- `src/ui/builder_end_user_flow_hub.py`
- `src/ui/builder_execution_adapter_hub.py`
- `src/ui/builder_interaction_hub.py`

### 6.2 Core module surfaces
- `src/ui/graph_workspace.py`
- `src/ui/inspector_panel.py`
- `src/ui/validation_panel.py`
- `src/ui/execution_panel.py`
- `src/ui/designer_panel.py`
- `src/ui/storage_panel.py`
- `src/ui/top_bar.py`
- `src/ui/panel_coordination.py`

### 6.3 Product-facing beginner/return-use surfaces
- `src/ui/template_gallery.py`
- `src/ui/provider_setup_guidance.py`
- `src/ui/external_input_guidance.py`
- `src/ui/friendly_error_messages.py`
- `src/ui/result_history.py`
- `src/ui/feedback_channel.py`
- `src/ui/circuit_library.py`
- `src/ui/execution_launch_workflow.py`
- `src/ui/execution_anxiety_reduction.py`

### 6.4 Advanced/post-unlock surfaces
- `src/ui/trace_timeline_viewer.py`
- `src/ui/artifact_viewer.py`
- `src/ui/diff_viewer.py`
- `src/ui/runtime_monitoring_workspace.py`
- `src/ui/node_configuration_workspace.py`
- `src/ui/visual_editor_workspace.py`
- `src/ui/command_palette.py`
- `src/ui/command_execution_adapter.py`
- `src/ui/command_routing.py`

### 6.5 Server-side product shell and continuity surfaces
- `src/server/workspace_shell_runtime.py`
- `src/server/result_history_runtime.py`
- `src/server/feedback_runtime.py`
- `src/server/starter_template_runtime.py`
- `src/server/workspace_onboarding_api.py`
- `src/server/run_list_api.py`
- `src/server/provider_health_api.py`
- `src/server/provider_secret_api.py`
- `src/server/artifact_trace_read_api.py`

### 6.6 Current implication
Therefore the remaining UI work is primarily:
- enforcement
- integration
- routing completion
- product-safe copy and continuity improvement
- server/UI linkage closure
- selective missing surface implementation where the module exists but the product path is not yet closed

It is **not** primarily about inventing new UI architecture.

## 7. Remaining UI Work: Canonical Classification

The remaining UI work is divided into four classes.

### Class A — Must finish now (blocking current product readiness)
These are the remaining UI blockers that directly govern whether Nexa can be considered general-user ready for the current beginner-first product loop.

1. Beginner shell enforcement completion
2. API access barrier reduction
3. External data input minimum first-success path
4. Template gallery productization completion
5. Friendly error messaging completion
6. Stronger result display completion

### Class B — Should finish immediately after Class A
These are not the first blocker, but they directly affect execution confidence and real-world usability.

7. Cost visibility
8. Execution waiting-state feedback completion
9. In-app contextual help
10. Mobile first-run minimum support
11. Privacy and data-handling transparency

### Class C — Already materially implemented, but require closure audit/hardening only
These are not greenfield remaining items anymore. They now require closure verification, ranking stabilization, and consistency hardening only if gaps remain after Class A and B.

12. Circuit library / reopen flow hardening
13. Result history / result reentry hardening
14. Onboarding continuity hardening
15. Feedback continuity hardening
16. Product surface review / bottleneck routing hardening

### Class D — Deferred product expansion, not current blockers
These remain future UI work, but must not be implemented before Class A and B are done unless an explicit product-distribution decision changes priority.

17. User accounts/sessions UI
18. Circuit sharing UI
19. Community/marketplace/community-review UI

## 8. Non-Goals During Remaining UI Implementation

While implementing the remaining UI plan, do **not** do the following by default:

1. Reopen raw graph editor polishing as the main task
2. Re-open trace/diff/artifact deepening before beginner surfaces are closed
3. Rebuild the shell from scratch
4. Move the main effort into plugin builder, SubcircuitNode, automation platform, or evolution system
5. Treat advanced observability surfaces as first-session surfaces
6. Drift into SaaS growth systems before general-user first-success and early return-use are genuinely closed

## 9. Execution Strategy

The remaining UI work must be executed with the following strategy.

### 9.1 Prefer convergence over redesign
If a module already exists, extend it.
Do not create a second module with overlapping responsibility unless the current module is structurally unusable.

### 9.2 Prefer server-authoritative routing for product guidance
Beginner-facing product bottleneck surfaces should continue to be driven primarily by server-authoritative readiness/continuity evaluation when that mechanism already exists.

### 9.3 Keep implementation narrow and vertical
Each batch should:
- choose one real user/product bottleneck
- modify the minimum directly connected files
- add/adjust tests
- avoid opportunistic sideways expansion

### 9.4 Close one user path at a time
The correct order is:
- first-success start path
- first-success run/result path
- return-use continuity path
- confidence/transparency path
- advanced/post-unlock path

## 10. Workstream 1 — Beginner Shell Enforcement Completion

## 10.1 Goal
Finish the code-level enforcement of the beginner shell policy across the actual shell, not just as a spec.

## 10.2 Why it is still remaining
The policy is already documented, and recent server-shell work materially improved first-success guidance. However, the repository still treats beginner compression as partially implemented rather than fully enforced.

The remaining issue is not absence of the shell but incomplete enforcement consistency.

## 10.3 Required outcomes
The beginner shell must reliably ensure all of the following:
- empty workspace opens Designer-first
- graph is not the first required primary surface
- engine-facing terms are remapped on beginner-visible surfaces
- advanced surfaces remain hidden/collapsed until first success or explicit request
- proposal flow appears as one confirmation moment to beginners
- validation is compressed into status + cause + next action
- storage/runtime/internal engine vocabulary does not leak into first-session critical surfaces

## 10.4 Primary files
- `src/ui/builder_shell.py`
- `src/ui/panel_coordination.py`
- `src/ui/designer_panel.py`
- `src/ui/proposal_commit_workflow.py`
- `src/ui/execution_panel.py`
- `src/ui/i18n.py`
- `src/ui/product_flow_shell.py`
- `src/server/workspace_shell_runtime.py`

## 10.5 Implementation tasks

### A. Empty-workspace enforcement
- verify that empty beginner workspace opens with Designer request surface as the dominant visible panel
- suppress graph-first requirement in that state
- ensure the first visible primary action aligns with “describe goal” or “choose starter entry path” rather than graph navigation

### B. Terminology remapping enforcement
Enforce beginner display remapping everywhere on critical first-success surfaces:
- Circuit -> Workflow
- Node -> Step
- Provider -> AI model

Audit and close leakage in:
- shell banners
- empty states
- onboarding hints
- validation summaries
- provider setup guidance
- template gallery summaries
- result/history return surfaces

### C. Advanced surface gating
Ensure the following are not beginner-primary before first success:
- trace
- diff
- artifact deep inspection
- graph-heavy editor surface
- raw storage lifecycle internals
- deep validator internals

Implementation should happen primarily through:
- panel visibility gating
- collapsed state defaults
- unlock-state evaluation
- explicit user-mode toggles

### D. Proposal compression
Audit the beginner-facing proposal flow to ensure the user sees:
- what Nexa will build
- what must be confirmed
- one visible approve/revise decision moment

Do not surface the full internal chain unless the user has already unlocked advanced control.

### E. Validation compression
Every beginner-critical validation surface must show:
- a status label
- a one-sentence cause
- one clear next action

Do not surface raw reason-code vocabulary as the first visible copy.

## 10.6 Required tests
Extend or verify:
- `tests/test_ui_builder_shell_view_model.py`
- `tests/test_ui_panel_coordination.py`
- `tests/test_ui_designer_panel_view_model.py`
- `tests/test_ui_execution_panel_view_model.py`
- `tests/test_ui_proposal_commit_workflow.py`
- `tests/test_ui_product_flow_shell.py`
- `tests/test_phase8_surface_i18n_contract.py`
- targeted server-shell route tests if routing depends on server payload

## 10.7 Definition of done
This workstream is done only when:
- a beginner can enter the shell and start without graph-first pressure
- advanced surfaces are not prematurely surfaced
- beginner wording is consistent on the first-success path
- proposal/validation are visibly compressed in beginner mode
- tests prove the gating and wording rules

## 11. Workstream 2 — API Access Barrier Reduction

## 11.1 Goal
Remove raw environment-variable-centric provider friction from the beginner product path.

## 11.2 Why it is still remaining
The current repository has provider health, secret, and binding infrastructure, plus provider setup guidance, but the product path still fundamentally assumes technical familiarity with provider credentials.

This is one of the strongest remaining beginner barriers.

## 11.3 Required outcomes
A beginner must be able to understand and complete provider setup without needing to understand:
- `.env`
- environment variables
- model backend internals
- provider secret storage vocabulary

## 11.4 Primary files
UI:
- `src/ui/provider_setup_guidance.py`
- `src/ui/designer_panel.py`
- `src/ui/friendly_error_messages.py`
- `src/ui/i18n.py`
- `src/ui/action_schema.py`
- `src/ui/command_routing.py`

Server/API:
- `src/server/provider_health_api.py`
- `src/server/provider_secret_api.py`
- `src/server/provider_binding_store.py`
- `src/server/provider_probe_api.py`
- `src/server/provider_health_models.py`
- `src/server/provider_secret_models.py`
- `src/server/workspace_shell_runtime.py`

Provider layer:
- `src/providers/env_diagnostics.py`
- `src/designer/semantic_backend_presets.py`

## 11.5 Implementation tasks

### A. Beginner-safe provider entry UI
Implement or refine a guided provider setup surface that:
- explains why setup is needed in product language
- shows supported providers/models in user-facing terms
- gives a single primary next action
- distinguishes “not configured”, “configured but disabled”, “healthy”, and “failing” states

### B. Secret setup path abstraction
The UI must not expose raw configuration instructions as the primary route.

Preferred order:
1. guided in-app secret entry or connection path
2. explicit health confirmation
3. re-entry to the blocked workflow path

### C. Provider health remediation messaging
Map health failures into beginner-friendly action surfaces:
- missing key
- bad key
- disabled binding
- provider unavailable
- rate limited / quota blocked

### D. Routing integration
The shell must route blocked first-success paths into provider setup when provider setup is truly the bottleneck, not merely one of several valid actions.

### E. Testable provider state machine
Normalize the provider setup UI behavior around canonical user-facing states and ensure it survives refresh/re-entry.

## 11.6 Required tests
- `tests/test_ui_provider_setup_guidance.py`
- `tests/test_phase4_provider_access_path.py`
- `tests/test_provider_env_guidance.py`
- `tests/test_server_provider_secret_routes.py`
- `tests/test_server_provider_health_routes.py`
- `tests/test_server_provider_probe_routes.py`
- `tests/test_server_framework_binding.py`
- `tests/test_server_fastapi_binding.py`

## 11.7 Definition of done
This workstream is done only when:
- a beginner can complete provider setup through the UI path
- missing/invalid/disabled states produce clear next-step copy
- the first-success shell routes to provider setup only when it is the actual bottleneck
- provider setup no longer feels like a developer-only prerequisite

## 12. Workstream 3 — External Data Input Minimum Path

## 12.1 Goal
Allow a beginner to start at least one meaningful workflow from a file or URL, not only pasted text.

## 12.2 Why it is still remaining
The codebase contains external-input guidance, but the productized first-success entry path for file/URL input is still not fully closed.

This remains a major real-world usability gap.

## 12.3 Required outcomes
A beginner must be able to:
- choose file input
- choose URL input
- understand what that choice means
- continue through proposal/review/run with that input path
- avoid confusion with starter-template/direct-goal/provider-only paths

## 12.4 Primary files
UI:
- `src/ui/external_input_guidance.py`
- `src/ui/designer_panel.py`
- `src/ui/builder_shell.py`
- `src/ui/action_schema.py`
- `src/ui/i18n.py`

Server/runtime:
- `src/server/workspace_shell_runtime.py`
- `src/server/starter_template_runtime.py`
- relevant upload/ingestion route surfaces

Platform/plugin boundary:
- `src/platform/plugin_auto_loader.py`
- any existing file/URL reader plugin registration and capability linkage

## 12.5 Implementation tasks

### A. File entry surface
Implement a beginner-safe file entry path with:
- clear upload action
- supported file-type explanation
- state feedback for “uploaded / pending / scanned / ready / rejected” if the ingestion path already supports such states

### B. URL entry surface
Implement a beginner-safe URL entry path with:
- clear URL field
- validation feedback
- explanation that Nexa will read web content through a safe ingestion path

### C. Entry-path separation
Do not let file/URL entry collapse back into generic goal-entry wording.
The shell must visibly distinguish:
- direct goal entry
- starter template entry
- file entry
- URL entry
- provider setup path

### D. Input safety linkage
If input safety blocks or warns on file/URL content, surface it in beginner-safe messaging and route to the correct next action.

### E. Proposal-flow integration
Ensure a file/URL entry leads into the same proposal/review path without bypassing governance.

## 12.6 Required tests
- `tests/test_ui_designer_panel_view_model.py`
- `tests/test_ui_action_schema.py`
- `tests/test_ui_builder_shell_view_model.py`
- file/URL-specific server route tests
- `tests/test_server_http_route_surface.py`
- input safety route tests where relevant

## 12.7 Definition of done
This workstream is done only when:
- file and URL entry paths are visible, understandable, and distinct
- they route through the normal beginner product flow
- their next action is explicit
- first-success can be achieved from at least one real external-data path

## 13. Workstream 4 — Template Gallery Productization Completion

## 13.1 Goal
Turn the starter template gallery from “available examples” into a product-quality first-success accelerator.

## 13.2 Why it is still remaining
The module exists, but the product requirement is not merely to show templates. It is to make the gallery representative, validated, and clearly connected to the beginner flow.

## 13.3 Required outcomes
The template gallery must:
- communicate what Nexa can do
- reduce blank-page anxiety
- provide representative starter workflows
- connect naturally into the Designer/proposal flow
- not collide confusingly with direct goal entry

## 13.4 Primary files
- `src/ui/template_gallery.py`
- `src/ui/designer_panel.py`
- `src/ui/i18n.py`
- `src/ui/action_schema.py`
- `src/server/starter_template_runtime.py`
- `src/server/workspace_shell_runtime.py`
- `src/designer/proposal_flow.py`
- `src/contracts/savefile_factory.py`

## 13.5 Implementation tasks

### A. Representative starter set
Audit and complete starter coverage for at least:
- summarization
- document analysis
- writing assistance
- classification/review analysis
- code review/explanation

### B. Product-facing template descriptions
Each template needs:
- beginner-facing name
- beginner-facing summary
- expected input type
- expected output type
- rough best-use statement

### C. Entry-path integration
Selecting a template must clearly move the user into:
- template-chosen state
- review/proposal creation
- provider setup if needed
- run path if ready

### D. Template continuity
If a starter template path is already selected, the shell must stay on that path instead of collapsing into generic goal-entry logic.

### E. Validated starter registration
Ensure starter templates are not just discoverable but safe, compatible, and stable enough to be part of the first-success loop.

## 13.6 Required tests
- `tests/test_ui_template_gallery.py`
- `tests/test_ui_designer_panel_view_model.py`
- `tests/test_ui_action_schema.py`
- starter-template runtime tests
- targeted server-shell tests for selected-template continuity

## 13.7 Definition of done
This workstream is done only when:
- a beginner can look at the gallery and understand what Nexa can do
- selecting a template reliably advances the product path
- template continuity survives shell refresh/re-entry
- starter templates materially reduce blank-state friction

## 14. Workstream 5 — Friendly Error Messaging Completion

## 14.1 Goal
Make product-facing errors understandable and actionable without engine knowledge.

## 14.2 Why it is still remaining
Friendly error helpers exist, but the product requirement is broader: consistent beginner-safe error handling across the actual first-success and returning-user path.

## 14.3 Required outcomes
Every beginner-visible error on the main product path must show:
- status
- one-sentence cause
- one clear next action

### Examples of families that must be covered
- provider setup/configuration failure
- network failure
- quota/cost denial
- input safety block
- execution timeout/failure
- missing result/empty result
- onboarding/continuity mismatch

## 14.4 Primary files
- `src/ui/friendly_error_messages.py`
- `src/ui/execution_panel.py`
- `src/ui/validation_panel.py`
- `src/ui/designer_panel.py`
- `src/ui/i18n.py`
- `src/server/workspace_shell_runtime.py`
- relevant server route surfaces that emit user-facing errors

## 14.5 Implementation tasks

### A. Error family inventory
Inventory current user-facing error families and map them to product-safe labels/actions.

### B. First-surface prioritization
Ensure the first visible copy is not:
- raw reason code
- internal failure point label
- subsystem-only jargon

### C. Correct routing by family
Errors must route users differently depending on family:
- provider problem -> provider setup
- input safety -> input review/edit
- quota problem -> quota/cost explanation
- network/provider timeout -> retry guidance
- validation block -> exact blocking next action

### D. Cross-surface consistency
Friendly error language must remain consistent across:
- shell cards
- execution panel
- validation panel
- feedback/report route
- mobile/compact surface variants

## 14.6 Required tests
- `tests/test_ui_friendly_error_messaging.py`
- `tests/test_ui_execution_panel_view_model.py`
- `tests/test_ui_validation_panel_view_model.py`
- `tests/test_phase8_surface_i18n_contract.py`
- route tests for user-facing failure surfaces

## 14.7 Definition of done
This workstream is done only when:
- a beginner can understand what went wrong without reading engine jargon
- the next action is obvious
- errors no longer feel like internal diagnostic leakage

## 15. Workstream 6 — Stronger Execution Result Display Completion

## 15.1 Goal
Provide a result surface that lets general users read and use successful output immediately.

## 15.2 Why it is still remaining
The current repository includes result history and artifact-oriented surfaces, but the product requirement is stronger than a preview string. A successful run must end in a readable, usable result screen.

## 15.3 Required outcomes
The result surface must support at least:
- readable rendering
- copy action
- type-aware presentation
- clear distinction between latest result and deeper trace/artifact tooling
- smooth reentry into result history

### Minimum result classes to support
- plain text result
- list-like textual result
- lightweight structured result (key-value sections)

## 15.4 Primary files
- `src/ui/execution_panel.py`
- `src/ui/result_history.py`
- `src/ui/artifact_viewer.py`
- `src/ui/i18n.py`
- `src/server/result_history_runtime.py`
- `src/server/run_read_api.py`
- `src/server/artifact_trace_read_api.py`

## 15.5 Implementation tasks

### A. Result-surface hierarchy
Define and enforce:
- beginner result screen
- recent result history screen
- advanced artifact/trace screen

The beginner result screen must be the default post-success endpoint.

### B. Copy/reuse affordances
Add or refine:
- copy output
- reopen latest result
- continue workflow from result context
- report issue from result surface

### C. Type-aware rendering
Avoid treating every result as one preview string.
Render based on simple detected shape.

### D. Linkage with recent-result continuity
Return-use routing should reopen the result surface directly when that is the best continuity path.

### E. Distinguish result from trace
A beginner reopening a result must not be forced into trace literacy.
Trace is deeper evidence, not the first result surface.

## 15.6 Required tests
- `tests/test_ui_execution_panel_view_model.py`
- `tests/test_ui_artifact_viewer_view_model.py`
- `tests/test_ui_runtime_monitoring_workspace.py`
- `tests/test_server_execution_artifact_trace_consistency.py`
- `tests/test_server_result_history_*` or equivalent result route tests

## 15.7 Definition of done
This workstream is done only when:
- a successful run ends in a readable result surface
- copy/reuse is available
- beginners are not pushed into trace/artifact complexity by default

## 16. Workstream 7 — Cost Visibility

## 16.1 Goal
Reduce hesitation before running by surfacing cost expectations and actual usage in product language.

## 16.2 Why it is still remaining
Internal cost/usage estimation exists, but user-facing cost visibility is not yet sufficiently closed on the beginner path.

## 16.3 Required outcomes
Show both:
- pre-run estimated usage/cost
- post-run actual usage/cost summary

In beginner language, relative labels may be shown first if exact billing language is not yet stable.

## 16.4 Primary files
- `src/ui/execution_panel.py`
- `src/ui/designer_panel.py`
- `src/ui/i18n.py`
- `src/designer/precheck_builder.py`
- engine/trace usage source modules
- `src/server/workspace_shell_runtime.py`

## 16.5 Implementation tasks
- surface pre-run cost visibility near the run decision
- surface post-run actual usage near result/monitoring surfaces
- clearly separate estimate from actual
- tie quota/cost issues into friendly error messaging

## 16.6 Required tests
- `tests/test_ui_execution_panel_view_model.py`
- `tests/test_phase4_ui_flow_connection.py`
- quota/cost surface tests where available

## 16.7 Definition of done
A beginner can tell:
- whether a run is likely cheap/moderate/expensive
- what was actually used after the run

## 17. Workstream 8 — Execution Waiting-State Feedback Completion

## 17.1 Goal
Remove the “dead screen” feeling during long or quiet execution.

## 17.2 Why it is still remaining
The repository has runtime-monitoring and execution-anxiety-reduction modules, but the Stage 2 product requirement is stronger: the user must reliably feel that the product is still alive and progressing.

## 17.3 Required outcomes
During execution, the product must surface:
- visible running state
- progress/checkpoint hints when available
- recent event visibility
- a stable “still working” explanation
- safe next actions while waiting

## 17.4 Primary files
- `src/ui/execution_panel.py`
- `src/ui/runtime_monitoring_workspace.py`
- `src/ui/execution_anxiety_reduction.py`
- `src/ui/notification/toast/banner` related code if present
- `src/ui/i18n.py`
- server execution status surfaces and run list/read routes

## 17.5 Implementation tasks
- unify quiet-running fallback copy
- ensure waiting-state actions exist (stay here, review recent events, reopen result history when appropriate)
- keep graph/runtime focus aligned where relevant
- avoid silent state regressions when progress details are sparse

## 17.6 Required tests
- `tests/test_ui_runtime_monitoring_workspace.py`
- `tests/test_phase6_execution_anxiety_reduction.py`
- `tests/test_server_run_list_api.py`
- execution route tests that validate running-state surfaces

## 17.7 Definition of done
This workstream is done only when the user can clearly tell that Nexa is still working and has not frozen.

## 18. Workstream 9 — In-App Contextual Help

## 18.1 Goal
Give blocked users an in-product explanation and next-step path without requiring external docs.

## 18.2 Why it is still remaining
Guided-disclosure specs exist and multiple product-flow shells exist, but contextual help still needs stronger state-aware product integration.

## 18.3 Required outcomes
Users must be able to get contextual help for:
- why execution is blocked
- why this action is disabled
- what this screen is for
- what to do next in the current stage
- how to interpret a current failure

## 18.4 Primary files
- `src/ui/execution_anxiety_reduction.py`
- `src/ui/product_flow_runbook.py`
- `src/ui/product_flow_readiness.py`
- `src/ui/product_flow_handoff.py`
- `src/ui/validation_panel.py`
- `src/ui/designer_panel.py`
- `src/ui/i18n.py`

## 18.5 Implementation tasks
- connect blocked states to contextual help cards
- ensure help is stage-aware, not global/static
- add “why am I here / what next?” support on key bottleneck surfaces
- tie help entries to the same current path / next step model used by first-success and continuity cards

## 18.6 Required tests
- `tests/test_ui_product_flow_runbook.py`
- `tests/test_ui_product_flow_readiness.py`
- `tests/test_ui_product_flow_handoff.py`
- `tests/test_ui_validation_panel_view_model.py`

## 18.7 Definition of done
A blocked beginner can understand the current obstacle and next step without leaving the product flow.

## 19. Workstream 10 — Mobile First-Run Minimum Support

## 19.1 Goal
Make the minimum first-success loop work on a mobile-sized surface.

## 19.2 Why it is still remaining
Responsive/mobile policy exists, but the product path still needs explicit implementation for the minimum beginner loop.

## 19.3 Required outcomes
On mobile-sized layouts, the user must be able to:
1. enter goal
2. review preview
3. approve
4. run
5. read result

Graph editing, trace, diff, deep inspection, and advanced monitoring may remain reduced or deferred.

## 19.4 Primary files
- `src/ui/builder_shell.py`
- `src/ui/designer_panel.py`
- `src/ui/execution_panel.py`
- `src/ui/result_history.py`
- `src/ui/panel_coordination.py`
- `src/ui/i18n.py`

## 19.5 Implementation tasks
- define a mobile-first surface stack
- ensure one-primary-surface-at-a-time behavior where needed
- keep the first-success path operable without requiring simultaneous desktop-like panel visibility
- avoid exposing advanced surfaces as substitutes for missing mobile product flow

## 19.6 Required tests
- viewport/responsive shell tests if available
- `tests/test_ui_builder_shell_view_model.py`
- `tests/test_ui_panel_coordination.py`
- any mobile-specific rendering/state tests present or newly added

## 19.7 Definition of done
A beginner can complete the minimum first-success loop on mobile without needing the full desktop panel layout.

## 20. Workstream 11 — Privacy and Data-Handling Transparency

## 20.1 Goal
Show users where their data goes and what Nexa stores/does not store on the critical beginner path.

## 20.2 Why it is still remaining
Transparency is a trust and compliance requirement, and it remains one of the Stage 2 gaps.

## 20.3 Required outcomes
The product must clearly communicate:
- when external provider calls happen
- what inputs are sent outward
- what local persistence exists
- what is not retained or not shared

## 20.4 Primary files
- `src/ui/execution_anxiety_reduction.py`
- `src/ui/designer_panel.py`
- `src/ui/provider_setup_guidance.py`
- `src/ui/external_input_guidance.py`
- `src/ui/i18n.py`
- server/provider route surfaces that expose current state

## 20.5 Implementation tasks
- add privacy/data-path fact surfaces to first-success and input/provider paths
- explain provider invocation timing in beginner language
- show local persistence role in user-facing terms without exposing internal storage jargon too early
- ensure transparency copy survives mobile and compact surfaces

## 20.6 Required tests
- product-surface tests validating privacy fact rendering
- `tests/test_phase4_ui_flow_connection.py`
- `tests/test_ui_designer_panel_view_model.py`
- `tests/test_ui_provider_setup_guidance.py`

## 20.7 Definition of done
A user can understand the basic data path of their workflow without reading engine code or external docs.

## 21. Workstream 12 — Continuity Surface Hardening Audit (Non-Greenfield)

## 21.1 Goal
Audit already-implemented continuity surfaces and fix only real remaining gaps.

## 21.2 Why this is not a greenfield workstream
Current direction already includes implemented work for:
- return-use routing
- result reentry
- feedback continuity
- product-surface review routing

Therefore this workstream is a hardening/audit pass only.

## 21.3 Surfaces to audit
- `src/ui/circuit_library.py`
- `src/ui/result_history.py`
- `src/ui/feedback_channel.py`
- `src/server/workspace_shell_runtime.py`
- `src/server/result_history_runtime.py`
- `src/server/feedback_runtime.py`
- `src/server/workspace_onboarding_api.py`

## 21.4 Audit questions
- does the best continuity path win consistently?
- are thread/result/workflow reopen priorities stable?
- do server-authoritative bottleneck sections agree with lower continuity sections?
- do return-use surfaces remain beginner-facing instead of collapsing into advanced history/trace paths?

## 21.5 Required tests
- `tests/test_server_framework_binding.py`
- `tests/test_server_fastapi_binding.py`
- `tests/test_server_http_route_surface.py`
- `tests/test_server_continuity_summary_consistency.py`
- `tests/test_server_workspace_onboarding_routes.py`
- `tests/test_ui_circuit_library.py`
- `tests/test_ui_result_history*` if present
- `tests/test_ui_feedback_channel.py`

## 21.6 Definition of done
This workstream is done only when continuity surfaces no longer fight each other and the best direct return path wins consistently.

## 22. Workstream 13 — Advanced/Post-Unlock Surface Integration (After Class A and B)

## 22.1 Goal
Connect already-existing advanced surfaces into a coherent post-first-success/advanced shell without promoting them prematurely into beginner-critical scope.

## 22.2 Scope
- graph-heavy visual editor workflows
- trace/timeline surface linkage
- artifact inspection linkage
- diff comparison linkage
- command palette deepening
- runtime monitoring workspace integration

## 22.3 Primary files
- `src/ui/graph_workspace.py`
- `src/ui/visual_editor_workspace.py`
- `src/ui/runtime_monitoring_workspace.py`
- `src/ui/trace_timeline_viewer.py`
- `src/ui/artifact_viewer.py`
- `src/ui/diff_viewer.py`
- `src/ui/command_palette.py`
- `src/ui/panel_coordination.py`
- `src/ui/product_flow_shell.py`

## 22.4 Important boundary
Do not start this workstream until:
- Class A is materially complete
- Class B is materially complete
- the beginner first-success path is genuinely product-grade

## 22.5 Definition of done
Advanced surfaces feel like a coherent unlocked expansion of the shell,
not a competing first-session product path.

## 23. Workstream 14 — Deferred Product Expansion UI (Do Not Implement Yet)

These remain future UI tasks only after the current plan is complete and product-distribution decisions justify them.

### 23.1 Accounts / sessions UI
Only after deployment strategy requires it.

### 23.2 Circuit sharing UI
Only after first-success and early return-use are stable.

### 23.3 Community ecosystem UI
Only after the product has a stable personal use loop and enough user value to justify growth systems.

## 24. Canonical Execution Order

Implement the remaining UI in the following order.

### Phase A — Enforce beginner shell completely
1. Workstream 1 — Beginner Shell Enforcement Completion

### Phase B — Close the remaining first-success blockers
2. Workstream 2 — API Access Barrier Reduction
3. Workstream 3 — External Data Input Minimum Path
4. Workstream 4 — Template Gallery Productization Completion
5. Workstream 5 — Friendly Error Messaging Completion
6. Workstream 6 — Stronger Execution Result Display Completion

### Phase C — Reduce hesitation and increase trust
7. Workstream 7 — Cost Visibility
8. Workstream 8 — Execution Waiting-State Feedback Completion
9. Workstream 9 — In-App Contextual Help
10. Workstream 10 — Mobile First-Run Minimum Support
11. Workstream 11 — Privacy and Data-Handling Transparency

### Phase D — Audit and harden continuity already implemented
12. Workstream 12 — Continuity Surface Hardening Audit

### Phase E — Only after A-D are materially stable
13. Workstream 13 — Advanced/Post-Unlock Surface Integration

### Phase F — Future only
14. Workstream 14 — Deferred Product Expansion UI

## 25. Batch Design Rules For Another AI

If another AI implements this plan, follow these batch rules.

### Rule 1
One batch should remove one real user/product bottleneck.
Do not mix unrelated sectors.

### Rule 2
Prefer batches that modify:
- one primary surface file
- one or two linked UI helpers
- the smallest directly connected server/runtime routes
- the relevant tests

### Rule 3
Do not claim completion from module presence alone.
A module existing is not the same as the product path being closed.

### Rule 4
When a workstream already has a module, default to:
- extend
- wire
- re-rank
- re-route
- test
not rewrite.

### Rule 5
Use current bottleneck logic rather than aesthetic preference.
If multiple possible improvements exist, implement the one that removes the strongest real user barrier first.

## 26. Repository-Wide Regression Expectations

Every remaining UI batch must preserve:
- engine-owned truth boundaries
- role-aware storage behavior
- no Commit Snapshot canonical `ui`
- no fake execution history
- beginner-mode compression rules
- post-first-success unlock rules
- server-authoritative product bottleneck guidance where already established

## 27. Minimum Regression Suite To Re-run After Every UI Batch

At minimum, re-run the tests directly connected to the changed workstream.
Additionally, after every product-surface-affecting batch, re-run:
- `tests/test_server_framework_binding.py`
- `tests/test_server_fastapi_binding.py`
- `tests/test_server_http_route_surface.py`
- `tests/test_ui_builder_shell_view_model.py`
- `tests/test_ui_panel_coordination.py`
- `tests/test_phase8_surface_i18n_contract.py`

If the batch touches continuity, also re-run:
- `tests/test_server_continuity_summary_consistency.py`
- `tests/test_server_workspace_onboarding_routes.py`
- `tests/test_ui_feedback_channel.py`
- `tests/test_ui_circuit_library.py`

If the batch touches provider access, also re-run:
- `tests/test_ui_provider_setup_guidance.py`
- `tests/test_phase4_provider_access_path.py`
- provider secret/health route tests

If the batch touches result display or execution anxiety, also re-run:
- `tests/test_ui_execution_panel_view_model.py`
- `tests/test_ui_runtime_monitoring_workspace.py`
- `tests/test_phase6_execution_anxiety_reduction.py`
- relevant run/result server route tests

## 28. Final Definition of Success

This plan is complete only when all of the following are true.

### Beginner first-success
A beginner can:
- open Nexa
- understand what to do first
- start from goal/template/file/URL
- complete provider setup without developer knowledge
- review/approve in product language
- run
- read a useful result

### Confidence and trust
A beginner can:
- understand waiting state
- understand cost posture
- understand basic data path
- understand errors and next steps

### Returning-user continuity
A returning user can:
- reopen the right workflow/result/feedback path
- continue from onboarding/product continuity without confusion

### Advanced surfaces
Advanced users can unlock deeper surfaces after first success without collapsing the beginner experience.

## 29. Final Statement

The remaining UI work in Nexa is no longer “design the UI.”
It is:

**finish the beginner-safe product loop, reduce real-world setup and run friction, then selectively unlock the already-built advanced shell.**

That is the correct meaning of “remaining UI implementation” for the current baseline.
