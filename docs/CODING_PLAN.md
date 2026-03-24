# Nexa CODING PLAN

Version: 2.5.1

---

## Completed Steps

## Release Snapshot (d7cbcf0 baseline)

The current repository state includes the following implemented surface:

### 1. Core Execution Engine

* dependency-based circuit runtime
* node execution phases (pre / core / post)
* ExecutionConfig registry, hashing, validation, and loading
* savefile-based `.nex` execution
* observability and runtime metrics

### 2. Provider Layer

* OpenAI / GPT provider support
* Codex provider support
* Claude provider support
* Gemini provider support
* Perplexity provider support
* provider routing / cooldown / fingerprint contracts
* explicit environment guidance for:
  * missing `.env`
  * missing `python-dotenv`
  * missing provider API key

### 3. Diff / Replay / Audit Tooling

* run comparison
* execution diff formatting
* regression detection + policy decision
* audit pack export
* audit replay
* determinism / provenance tooling
* alignment-based diff contracts present in tests

### 4. Public Demo Baseline

* only `examples/real_ai_bug_autopsy_multinode/` remains as the official demo
* obsolete demo-coupled tests were removed to keep the suite aligned with the retained demo set

### 5. Current Public Baseline

```text
947 passed, 3 skipped
```

* root `README.md` and `docs/CONTRIBUTING.md` were polished for GitHub release readiness in the current baseline

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

### Step188–190: Savefile & Bundle System (NEW)

#### Step188: Savefile (.nex)

* Primary executable savefile format
* Includes:

  * `meta`
  * `circuit`
  * `resources`
  * `state`
  * `ui`
* Deterministic and reproducible
* Savefile is not circuit-only; it includes both structure and state

---

#### Step189: Plugin Integration (Strict)

* plugin.json metadata enforcement
* strict version validation
* plugin resolver + integration layer
* validation BEFORE execution

---

#### Step190: Bundle (.nexb) + CLI Integration

* `.nexb` bundle format
* zip-based packaging
* contains:

  * circuit (.nex)
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

### Current Status

```text
947 passed, 3 skipped
```

---

### Step191: Core Diff Data Model Introduction (CRITICAL)

Goal:

* Introduce core diff data structures:
  - ComparableUnit
  - Representation

Representation:

Representation {
    representation_id: str
    artifact_type: str
    units: List[ComparableUnit]
    metadata: dict
}

ComparableUnit:

ComparableUnit {
    unit_id: str
    unit_kind: str
    canonical_label
    payload
    metadata
}

Outcome:

* foundation for media-agnostic diff engine

---

### Step192: Representation Layer (Text Extractor)

Goal:

* Replace section-based parsing with representation extraction
* Implement:

  extract_text_representation(text) -> Representation

* Convert text into ComparableUnit list

Outcome:

* text is no longer treated as raw string
* section summary logic removed from formatter

---

### Step193: Alignment Engine

Goal:

* Implement unit alignment logic:

  align_units(units_a, units_b)

* Matching priority:
  - canonical_label
  - structure
  - metadata

Outcome:

* stable unit matching across artifacts

---

### Step194: Unit-Based Diff Engine

Goal:

* Replace line-based diff with unit-based comparison
* Implement:

  compare_units(alignment) -> DiffResult

Outcome:

* diff becomes structure-aware
* enables cross-media comparison

---

### Step195: Formatter Simplification

Goal:

* Remove semantic logic from formatter
* Formatter becomes output-only

Outcome:

* strict layer separation
* improved extensibility

---

### Step196: CLI Integration for New Diff Model

Goal:

* integrate new DiffResult into CLI output

---

## Next Steps

### Step197: Release Documentation Hardening

Goal:

* keep README / BLUEPRINT / DEVELOPMENT / provider docs synchronized with current code
* remove stale references to deleted demos
* keep public-facing setup instructions aligned with actual provider behavior

---

### Step198: CLI Regression Gating

Goal:

* integrate regression policy into CLI exit codes more directly for CI/CD use

---

### Step199: Configuration-Driven Policy

Goal:

* external policy config
* severity override
* policy registry

---

### Step200: Release Polish for the Official Demo

Goal:

* finalize `real_ai_bug_autopsy_multinode` as the public GitHub demo
* keep demo instructions, run outputs, and docs aligned

---

End of Coding Plan
