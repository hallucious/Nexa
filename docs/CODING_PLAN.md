# Nexa CODING PLAN

Version: 2.2.0

---

## Completed Steps

### Step67–84: Engine/Circuit Stabilization + Core Contract Freeze

- Circuit Runtime Adapter: conditional edge + trace wiring + node resource execution
- Node execution phases: pre / core / post (AI in core only; node-internal contract)
- Provider contract: ProviderResult + reason_code normalization
- Plugin contract: PluginResult envelope + stage-aware + reason_code normalization
- Prompt contract: PromptSpec hash/render + PromptRegistry
- Observability: opt-in node/stage/prompt event recording
- Plugin registry: version registry + safe resolve

### Step100–108: Provider/Artifact/Node Observability Contracts

- Provider observability, trace, result, execution contracts
- Node execution runtime contract
- Artifact schema contract

### Step114–120: Node Spec + Graph Runtime + Engine Integration

- NodeSpec contract, GraphExecutionRuntime contract, Engine delegation

### Step121–125: ExecutionConfig Architecture

- **Step121**: ExecutionConfig canonical hash identity (`src/engine/execution_config_hash.py`)
- **Step122**: ExecutionConfig registry (`src/platform/execution_config_registry.py`)
- **Step123**: NodeExecutionRuntime resource execution stages (pre_plugins → prompt_render → provider_execute → post_plugins → validation → output_mapping)
- **Step124**: NodeSpec → ExecutionConfig resolution (`src/engine/node_spec_resolver.py`)
- **Step125**: ExecutionConfig schema validation (`src/platform/execution_config_schema.py`)

### Step126–142: Circuit System + CLI

- ExecutionConfig version negotiation, bridge, compiled resource graph
- Graph wave scheduler, final output resolver
- Circuit validation, I/O, loader
- CLI parser

### Step143–170: CLI + Observability + Determinism + Regression

- CLI: state injection, output export, summary, error handling
- Plugin auto-loader, runtime metrics, observability export
- Execution event stream, timeline, replay
- Execution determinism validator, artifact hashing
- Execution snapshot and diff, diff visualizer
- Regression detector (typed reason codes, severity)
- Audit pack, provenance graph, run comparator, execution debugger

### Step179: Context Key Schema Contract

- `src/contracts/context_key_schema.py`
- `docs/specs/contracts/context_key_schema_contract.md`

### Step186–186.3: Regression Reason Code System

- Typed reason codes with severity modeling
- Reason code constants extracted to `src/contracts/regression_reason_codes.py` (single source of truth)

### Step187–187.1: Regression Policy Engine

- `src/engine/execution_regression_policy.py`
- PolicyDecision (PASS / WARN / FAIL)
- HIGH → FAIL, MEDIUM → WARN, LOW → PASS
- Detailed trigger lines: `Trigger: node n1 (NODE_SUCCESS_TO_FAILURE, HIGH)`

**Current baseline: 688 passed, 3 skipped**

---

## Next Steps

### Step188: CLI Regression Gating

Goal: Integrate policy engine into CLI for CI/CD.

- `--baseline` flag for comparison run
- Exit code driven by PolicyDecision status (0=PASS, 1=WARN, 2=FAIL)
- Structured output for FAIL/WARN cases

### Step189: Configuration-Driven Policy

Goal: Allow policy rules to be configured per-circuit or per-run.

- Policy config schema
- Per-reason-code severity override
- Policy config registry

---

End of Coding Plan
