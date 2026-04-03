# Nexa CODING PLAN

Version: 2.8.0

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
* execution event stream foundation (started/completed/failed/warning/progress/artifact preview)
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
1212 passed, 3 skipped
```

* authoritative storage hardening baseline commit: `15031be`
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
1117 passed, 3 skipped
```

* storage-sector architecture work is no longer in foundation-building mode
* current storage-sector stage: late-stage hardening / near-closure
* Working Save -> Commit Snapshot -> Execution Record -> Updated Working Save summary is the intended active lifecycle
* recent work progressively removed stale replay, stale contract, thin native, thin nested, top-level thin, and write-boundary over-trust paths
* next storage work should prioritize spec ↔ implementation sync and completion judgment rather than broad storage refactoring

---

### Next Priority

* runtime-completion work should continue from the converged plugin baseline, not from deleted legacy paths
* documentation is synchronized to the accepted runtime direction through this tracker update
* future plugin work should target boundary clarification or deeper unification only when it can be done without reopening removed legacy paths


* legacy `.nex` plugin validation is owned by `src/platform/external_loader.py`; CLI keeps only branching, savefile fallback, and policy/output handling


- Legacy engine CLI compatibility is now wrapper-oriented: `src/engine/cli.py` is a bounded shim, `src/cli/savefile_runtime.py` owns execution dispatch, summary generation, payload emission, and baseline-policy wrapping, and `src/circuit/runtime_adapter.py` owns legacy preparation/adaptation logic.


- Execution record foundation implemented in code: contract, model, serialization, and working-save summary integration.


* Storage lifecycle linkage started: Working Save → Commit Snapshot creation and Execution Record → Working Save last-run summary update APIs


* Storage runtime linkage implemented in code: Commit Snapshot–anchored Execution Record creation and Working Save last-run update can now be driven from one lifecycle path


### Step161: Artifact Preview Event Safety Alignment

* runtime artifact preview emission now builds explicit preview-safe payloads
* `artifact_preview` events now declare non-final semantics (`is_final_artifact = false`)
* lightweight `preview_kind` / `preview_summary` metadata added for preview consumers
* full artifact truth remains separate from preview observability payloads
* focused execution-event / timeline tests passed after the alignment
