# Nexa CODING PLAN

Version: 2.3.0

---

## Completed Steps

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

* Circuit serialization format
* Includes:

  * node structure
  * execution config bindings
  * plugin references
* Deterministic and reproducible

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
827 passed, 3 skipped
```

---

### Step191: ComparableUnit Model Introduction (CRITICAL)

Goal:

* Introduce ComparableUnit as universal comparison abstraction
* Define unit structure:
  - unit_id
  - unit_kind
  - canonical_label
  - payload
  - metadata

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

### Step197: CLI Regression Gating

Goal:

* Integrate regression policy into CLI exit codes

---

### Step198: Configuration-Driven Policy

Goal:

* External policy config
* Severity override
* Policy registry

---

### Step199: Bundle Integrity & Security (Recommended)

Goal:

* Bundle signature / hash verification
* tamper detection

---

### Step200: Demo Preparation (GitHub MVP)

Goal:

* developer demo (.nexb)
* user demo (.nexb)
* README + usage

---

End of Coding Plan
