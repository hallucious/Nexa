# Nexa CODING PLAN

Version: 2.9.0

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
* obsolete demo-coupled tests were removed to keep the suite aligned with the retained demo set

### 6. Current Verified Baseline

```text
1283 passed, 3 skipped
```

* authoritative storage/runtime durability baseline commit: `8fef812`
* root `README.md` and `docs/CONTRIBUTING.md` were polished for GitHub release readiness
* canonical savefile lifecycle entry points exist across create / serialize / load / validate
* bounded CLI savefile surface remains intact
* role-aware `.nex` storage is now part of the active storage architecture, with `working_save` and `commit_snapshot` treated as official `.nex` roles and Execution Record treated as the run-history layer
* storage semantics are owned by storage/lifecycle APIs rather than CLI/export/replay path-local interpretation
* current storage-sector state is final hardening + spec ↔ implementation sync, not future-only foundation work

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
1335 passed, 3 skipped
```

* SubcircuitNode Batch 1 is now implemented across the practical lifecycle:
  parse -> validate -> execute -> preserve -> load/write API -> official example lock
* the line is no longer exploratory; it is closure-quality and regression-backed
* Review Bundle is now an executable regression target rather than a docs-only reference
* current Subcircuit state is best described as Batch 1 closed / Batch 2 not started
* next work should avoid reopening Batch 1 fundamentals unless a real regression is found

---

### Next Priority

* formally treat SubcircuitNode Batch 1 as closed unless a new concrete gap is found
* next Subcircuit work should move to Batch 2 quality layers, not back into Batch 1 core enablement
* preferred next Subcircuit directions are:
  - richer trace / artifact semantics
  - stronger observability around child runs
  - deeper parent-child execution inspection
* if attention shifts away from Subcircuit, do so from the current stable closure point rather than from an unfinished Batch 1 baseline

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
* further Subcircuit work should now be treated as post-Batch-1 work, not as unfinished Batch 1 fundamentals
