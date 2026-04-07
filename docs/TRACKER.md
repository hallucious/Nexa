# Nexa TRACKER

Version: 3.0.0

---

## Completed Steps

## Release Snapshot (runtime convergence baseline)

The current repository state includes the following implemented surface:

### 1. Core Execution Engine

* dependency-based circuit runtime
* node execution phases (pre / core / post)
* ExecutionConfig registry, hashing, validation, and loading
* savefile-based `.nex` execution
* observability and runtime metrics
* execution event stream foundation (started/completed/failed/warning/progress/artifact preview/review_required)
* execution resume contract foundation for paused review-gated runs
* graph-only runtime execution in `NodeExecutionRuntime`

### 2. Prompt / Provider Runtime

* PromptRegistry / PromptSpec integration in the node runtime
* provider execution through ProviderExecutor / ProviderRegistry
* provider result canonicalization in the runtime path
* explicit environment guidance for:
  * missing `.env`
  * missing `python-dotenv`
  * missing provider API key

### 3. Plugin Runtime

* plugin auto-loader for savefile entry-path execution
* versioned plugin registry for registry-based capability resolution
* plugin result normalization and runtime event emission
* legacy plugin loader removal
* legacy plugin registry shell removal
* savefile-aligned plugin execution convergence onto the auto-loader bridge
* savefile executor plugin-node path validated by regression coverage
* legacy `.nex` execution compatibility is now split cleanly: `src/engine/cli.py` is a bounded compatibility shim, `src/cli/savefile_runtime.py` owns execution dispatch, summary generation, payload emission, and baseline-policy wrapping, and `src/circuit/runtime_adapter.py` owns preparation/adaptation logic
* deletion of legacy nex contract leaves (`nex_loader`, `nex_engine_adapter`, `nex_bundle_loader`)
* deletion of remaining legacy nex contract support files (`nex_format`, `nex_serializer`, `nex_validator`)
* deletion of legacy `.nex` reverse-conversion / writer surface (`build_nex_from_engine`, `serialize_nex`, `save_nex_file`)

### 4. Diff / Replay / Audit Tooling

* run comparison
* execution diff formatting
* regression detection + policy decision
* audit pack export
* audit replay
* determinism / provenance tooling
* alignment-based diff contracts present in tests

### 5. Public Demo Baseline

* only `examples/real_ai_bug_autopsy_multinode/` remains as the official demo

### 6. Designer Control Plane

* explicit reopened-from-redirect continuity origin is now preserved across active recent-history reuse rather than flattened into ordinary recent continuity
* if a reopened older thread is later replaced by a newer active revision thread, reopened-origin continuity is now cleared and reduced into low-priority replacement context instead of continuing to control nearby continuity as if the older reopened thread were still active
* obsolete demo-coupled tests were removed to keep the suite aligned with the retained demo set

### 6. Current Verified Baseline

```text
1354 passed, 3 skipped
```

* authoritative storage/runtime durability baseline commit: `8fef812`
* root `README.md` and `docs/CONTRIBUTING.md` were polished for GitHub release readiness
* canonical savefile lifecycle entry points exist across create / serialize / load / validate
* bounded CLI savefile surface remains intact
* role-aware `.nex` storage is now part of the active storage architecture, with `working_save` and `commit_snapshot` treated as official `.nex` roles and Execution Record treated as the run-history layer
* storage semantics are owned by storage/lifecycle APIs rather than CLI/export/replay path-local interpretation
* current storage-sector state is final hardening + spec ↔ implementation sync, not future-only foundation work
* mixed referential rollback+edit requests now surface explicit confirmation reasons through Designer precheck/preview instead of living only inside request normalization
* repeated referential confirmation loops now raise a persisted control-governance policy tier, and that tier is surfaced back through Designer precheck/preview as explicit anchor-required guidance rather than remaining notes-only state
* pending governance anchor-carryover is now cleared once a later referential retry satisfies the stronger-anchor requirement, instead of lingering indefinitely as stale continuity pressure
* explicit scope redirects now archive older approval/revision thread continuity out of the active continuity store; redirected history remains only as low-priority background context for nearby mutation follow-up, can be restored into active continuity if the user explicitly reopens that older scope, and is cleared once a new revision thread is formed
* when a redirected older scope is explicitly reopened, rebuilt session cards and request normalization now mark that thread as a restored multi-step continuity path rather than treating it like ordinary nearby recent history
* cleared governance carryover is now reusable as low-priority recent-resolution context for later referential follow-up requests, while non-referential follow-up hides it and any new unresolved governance revision clears the old resolution history
* low-priority recent-resolution governance context now expires after one nearby follow-up cycle; once consumed, it should be dropped rather than lingering indefinitely as stale low-priority history

---

### Step67–84: Engine/Circuit Stabilization + Core Contract Freeze

* Circuit Runtime Adapter
* Node execution phases (pre / core / post)
* Provider contract
* Plugin contract
* Prompt contract
* Observability
* Plugin registry

---

### Step100–108: Provider/Artifact/Node Observability Contracts

* Provider observability
* Node execution runtime contract
* Artifact schema contract

---

### Step114–120: Node Spec + Graph Runtime + Engine Integration

* NodeSpec contract
* GraphExecutionRuntime
* Engine delegation

---

### Step121–125: ExecutionConfig Architecture

* ExecutionConfig hash identity
* ExecutionConfig registry
* NodeExecutionRuntime stages
* NodeSpec → ExecutionConfig resolution
* ExecutionConfig schema validation

---

### Step126–142: Circuit System + CLI

* ExecutionConfig version negotiation
* Graph scheduler
* Circuit validation / loader
* CLI parser

---

### Step143–170: CLI + Observability + Determinism + Regression

* CLI execution & output
* Plugin auto-loader
* Runtime observability
* Execution replay / diff / debugger
* Determinism validation
* Regression detection

---

### Step179: Context Key Schema Contract

---

### Step186–187.1: Regression Policy Engine

* Typed reason codes
* PolicyDecision (PASS / WARN / FAIL)
* Trigger line formatting

---

### Step188–190: Savefile & Bundle System

#### Step188: Savefile (.nex)

* Primary executable savefile format
* Includes:
  * `meta`
  * `circuit`
  * `resources`
  * `state`
  * `ui`
* deterministic and reproducible
* savefile is not circuit-only; it includes both structure and state

---

#### Step189: Plugin Integration (Strict)

* plugin metadata validation for bundle/plugin resolution flows
* strict version validation
* plugin resolver + integration layer
* validation before execution

---

#### Step190: Bundle (.nexb) + CLI Integration

* `.nexb` bundle format
* zip-based packaging
* contains:
  * circuit (`.nex`)
  * plugins

Execution flow:

```text
CLI
→ detect extension
→ .nex → direct execution
→ .nexb → bundle extract
→ plugin validation
→ engine execution
→ cleanup
```

* temp directory lifecycle handling
* CLI contract preserved
* backward compatibility maintained

---

### Step191–194: Runtime Convergence Line

* governance migration refinement accepted
* node runtime prompt registry integration accepted
* provider runtime canonicalization accepted
* plugin reporting converged away from the legacy registry shell
* `src/engine/plugin_loader.py` removed
* `src/platform/plugin_registry.py` removed
* savefile-aligned plugin loading converged onto `src/platform/plugin_auto_loader.py`
* savefile executor plugin node path now delegates into `src/platform/plugin_executor.py`, preserving plugin artifacts/trace through the converged auto-loader path
* runtime graph plugin metrics count one execution per plugin call rather than double-counting the compiled-graph path

---

### Current Runtime Interpretation

#### Prompt side

* `NodeExecutionRuntime` is the practical prompt execution caller
* prompt resolution is handled through `PromptRegistry` / `PromptSpec`
* No standalone legacy prompt package remains in the repository; the canonical runtime prompt path is the `src/platform/prompt_*` line.

#### Provider side

* provider execution is routed through `ProviderExecutor`
* provider lookup is handled through `ProviderRegistry`
* provider result normalization is concentrated in the runtime path

#### Plugin side

* practical runtime execution side:
  * `src/engine/node_execution_runtime.py`
  * `src/platform/plugin_executor.py`
* `src/platform/plugin_result.py`
* runtime bridge loader for savefile/plugin-entry execution:
  * `src/platform/plugin_auto_loader.py`
* canonical versioned registry side:
  * `src/platform/plugin_version_registry.py`
* execution contract / safe execution side:
  * `src/platform/plugin.py`
* bundle/savefile compatibility side:
  * `src/engine/cli.py` (pure bounded compatibility wrapper for the legacy engine CLI surface)
  * `src/contracts/savefile_executor_aligned.py`

---

### Current Status

```text
1761 passed, 9 skipped
```

* authoritative implementation baseline commit: `46b4df3`
* SubcircuitNode Batch 1 is closed across the practical lifecycle:
  parse -> validate -> execute -> preserve -> load/write API -> official example lock
* Subcircuit Batch 2 core observability / inspectability is now implemented at a practical level
* the line is no longer exploratory; it is closure-quality, regression-backed, and operator-facing enough to stop treating Batch 1 as active unfinished work
* Review Bundle remains an executable regression target rather than a docs-only reference
* Designer Session State Card now has a real code foundation:
  typed model -> session-state-card builder -> request normalizer integration -> proposal-flow integration
* Designer proposal control now persists into session-state semantics:
  control result -> updated session state card -> persisted working-save designer snapshot -> builder restore path
* approval-boundary continuation is now partially connected to the same persistence line:
  approval decision -> session-state evolution -> persisted clarification / revision context -> next proposal rebuild
* current project position is best described as:
  Phase 1 closure complete enough -> formal Phase 2 entry
* next work should avoid reopening Batch 1 fundamentals unless a real regression is found

---

### Next Priority

* formally treat SubcircuitNode Batch 1 as closed unless a new concrete regression is found
* formally treat Subcircuit Batch 2 core observability as implemented, not as speculative future work
* sync top-level status docs to the current `5d16172` reality before opening new implementation
* Phase 2 now includes a real Designer control line rather than only a handoff target:
  - retry / fallback control foundation
  - session-state persistence for control results
  - approval-boundary continuation into persisted clarification / revision context
* the next control-plane line should deepen:
  - approval re-entry after interpretation choice
  - approval re-entry after revision request
  - longer multi-step revision histories
  - richer policy semantics around continuation
* if attention returns to Subcircuit later, it should be from the current stable closure point, not by reopening Batch 1 or pretending Batch 2 core observability is still missing

### Step161: Artifact Preview Event Safety Alignment

* runtime artifact preview emission now builds explicit preview-safe payloads
* `artifact_preview` events now declare non-final semantics (`is_final_artifact = false`)
* lightweight `preview_kind` / `preview_summary` metadata added for preview consumers
* full artifact truth remains separate from preview observability payloads
* focused execution-event / timeline tests passed after the alignment

### Step162: Review-Required Event Foundation

* runtime can now emit `review_required` as a first-class execution event
* explicit runtime review-gate pause foundation now exists (`execution_paused` + `ReviewRequiredPause`)
* plugin trace metadata may request review through a bounded runtime-owned event surface
* minimal payload defaults include `reason` and non-blocking semantics
* review-required signaling remains separate from structural truth and does not yet force runtime pause/block behavior by itself
* focused execution-event tests passed after the alignment


### Latest Increment

* Subcircuit validator hardening now covers child output source validity
* Subcircuit Batch 1 closure coverage is now locked by explicit regression tests
* official Review Bundle example is executable, validated, and preserved across storage lifecycle
* `.nex` load/write paths now preserve `subcircuits` through typed-model and serializer/factory boundaries

### Phase 1 Closure Judgment

* SubcircuitNode Batch 1 is now a credible closure point:
  - parser/model support exists
  - validator hardening is in place
  - runtime propagation and node execution paths are aligned
  - Review Bundle is regression-backed
  - load/write lifecycle preservation is covered
* Subcircuit Batch 2 core observability is now also implemented at a practical level:
  - parent-visible child trace linkage
  - child artifact linkage visibility
  - child node status inspectability
  - child output provenance visibility
  - wrapper-level execution summary improvement
* Designer Session State Card is no longer spec-only; it now exists as a code-backed foundation
* further work should now be treated as formal Phase 2 control-plane work, not as unfinished Phase 1 closure work

* successful commit now reduces stale ready-for-commit continuation state into post-commit summary semantics
* a new Designer request after commit now starts a fresh proposal cycle from the committed baseline instead of inheriting consumed continuation state
* committed-summary history now has explicit exposure/priority semantics: latest summary is primary, older retained summaries are history-only, and referential requests bias toward latest-only interpretation
* the next rational implementation move is continued Phase 2 control-plane maturation, especially longer-horizon control governance and repeated-cycle interpretation safety


- repeat-cycle housekeeping semantics now rotate stale fresh-cycle markers and reduce them back into compact committed-summary notes after successful commit


- Phase 2 update: Designer committed-summary retention history is now bounded and rotated during post-commit cleanup.

- reference_resolution_policy: latest committed summary may auto-resolve generic last/previous references; second-latest and exact commit-id references are allowed when explicit; non-latest older references without a precise anchor must remain explicit ambiguities.

* mixed referential reason-style codes are now centralized in `src/designer/reason_codes.py` and remain Designer-bounded instead of being promoted prematurely into the shared global reason-code catalog

* approval-resolution revision flow now preserves Designer-bounded mixed referential reason codes in `revision_state.retry_reason` and `notes.last_revision_reason_code` instead of collapsing back to a generic approval revision marker

* mixed referential reason retention is now lifecycle-bounded: live cycles use active session-note markers, post-commit cleanup demotes them into compact history-only notes, and fresh unrelated cycles clear transient mixed-reason markers so stale rollback/edit ambiguity does not bleed into new requests
* repeated confirmation cycles now produce explicit control-governance notes summarizing recent attempt history, repeat counts, and whether referential auto-resolution should be temporarily tightened
* referential interpretation safety now escalates after repeated confirmation loops: unanchored rollback/undo language stops auto-resolving until the request includes an explicit commit anchor, explicit node target, or explicit non-latest selector
* governance-tier surfacing is now policy-backed instead of notes-only: precheck/preview only surface elevated/strict referential governance when it is actually applicable to the current request, and already-anchored requests downgrade to warning-level surfacing instead of repeating full confirmation pressure
* governance policy is now reused across approval/revision safety: governance decision points carry explicit next-step guidance, and governance-triggered revision requests persist anchor guidance back into session continuity notes/unresolved questions
* governance transition rules now use anchor-aware hysteresis: elevated/strict tiers are held until an explicit anchored referential resolution occurs, and anchored success relaxes the tier one step at a time instead of dropping immediately to standard; safe non-referential cycles now contribute explicit decay progress, and after enough consecutive safe cycles governance can deescalate one tier even without a new referential anchor event
* governance notes now also track an explicit ambiguity-pressure score/band so long-horizon escalation, partial relief, and safe-cycle decay remain numerically inspectable instead of being inferred only from tier labels
* ambiguity-pressure scoring is now surfaced back through precheck/preview/approval guidance instead of remaining notes-only: strict/elevated governance can explain whether pressure is still building, merely held, or already easing while the tier remains active

* revision-request continuity now persists structured governance guidance, including anchor requirement mode, pressure summary/score/band, and next-safe-action hints so the next cycle inherits pressure-aware anchor guidance instead of only a generic note
* persisted governance revision-guidance carryover is now request-applicability-aware in rebuilt session cards: non-referential follow-up requests stay visually cleaner, while anchored referential retries downgrade carryover from unresolved-risk surfacing to warning-level context instead of repeating full pending-anchor pressure

* approval-boundary continuation now keeps a compact recent revision history (bounded) so rebuilt session cards and the normalizer can recognize longer multi-step revision threads and preserve the latest clarified direction unless the user explicitly redirects scope

* compact recent approval/revision continuity is now redirect-aware: if a new mutation request explicitly redirects scope away from the latest clarified interpretation, rebuilt session cards and normalization retain the old thread only as background history instead of surfacing it as active continuity pressure; if the user later explicitly returns to that older scope, the archived thread is restored as active continuity again
* active compact approval/revision continuity history now also has a short-lived retention window: if no new revision thread reinforces it, it expires after a nearby follow-up cycle instead of lingering indefinitely as stale active continuity


- Redirected recent revision threads are archived out of active continuity using `approval_revision_redirect_archived_*` notes and are cleared when a new active revision thread forms.


## Precision convergence snapshot

- broad precision foundations were added in the correct existing sectors
- confidence + budget-aware routing + safety gate are now connected to the real provider execution boundary
- execution record can now project routing / safety / confidence summaries from runtime trace
- standalone `docs/specs/precision/` documents were transitional and have been merged into existing docs
- branch/merge convergence: formal branch candidates are now emitted from verifier follow-up paths and projected into execution-record observability

- outcome memory now provides bounded runtime route-tier hints and post-run success/failure pattern recording at the node boundary
- review-gate resume can now consume explicit human decision metadata, register it append-only, and project a summarized view into execution-record observability
- explicit human merge choices at review-gate resume can now be materialized as bounded merge-result declarations and projected into execution-record observability
- execution record now projects a trace-intelligence summary when trace carries enough node-level evidence
- designer proposal precheck now surfaces designer-constraint lint / critique findings in the actual proposal flow
- precision closeout status: branch/merge now both have bounded downstream consumers; remaining work is cleanup of duplicated semantics / stale helpers, not new precision feature expansion
