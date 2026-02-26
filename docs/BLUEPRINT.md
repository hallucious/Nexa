# HYPER-AI BLUEPRINT

Version: 3.1.0  
Status: Contract-driven extensible core (Plugin System + Capability Negotiation)  
Last Updated: 2026-02-26  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step41

---

## Architectural Phases Overview

- Step36: Policy trace (reason_trace)
- Step37: Policy isolation layer
- Step38: Baseline-aware policy diff
- Step39: Baseline Drift Detector + Hard Drift Block
- Step40: Plugin System v1 (Formal Manifest Contract)
- Step41: Capability Negotiation v1 (Contract for Selecting Plugins)

---

## Step36: Policy trace (reason_trace)

### Decision
Every policy decision MUST include a human-readable trace of the evaluation path.

### Location
- `PolicyDecision.reason_trace: list[str]` (always present; may be empty)
- Propagated into:
  - `GateResult.meta["reason_trace"]` (where applicable)
  - `runs/<run_id>/OBSERVABILITY.jsonl` events

---

## Step37: Policy isolation layer

### Decision
Policy logic must be isolated from orchestration and IO.

- Gates evaluate and return decisions.
- Runner orchestrates gates and writes artifacts.
- Plugins provide optional capabilities; gates must not hard-depend on external providers.

---

## Step38: Baseline-aware policy diff

### Decision
Provide a baseline-aware comparison tool between runs using policy decision snapshots.

Constraints:
- Deterministic output ordering
- Trace-only changes are represented, not treated as hard drift by default

---

## Step39: Baseline drift detection + hard drift block

### Phase1 — Baseline selection
- CLI supports `--baseline <run_id>`
- Persist into `RunMeta.baseline_version_id`

### Phase2 — Drift detector (post-run)
After `runner.run()`:
- Resolve baseline dir `runs/<baseline_id>` (if exists)
- Compare baseline vs current via policy diff core
- Write `runs/<current_run_id>/DRIFT_REPORT.json` (deterministic)
- Append `DRIFT_DETECTED` event to `OBSERVABILITY.jsonl`

### Hard vs Soft drift
- Hard drift: `decision` changed OR `reason_code` changed
- Soft drift: decision/reason_code unchanged; trace-only or meta-only change

### Hard drift block
- CLI option `--fail-on-hard-drift`:
  - if hard_count > 0 → exit code 2

---

# Step40: Plugin System v1 (Formal Manifest Contract)

## Objective
Elevate the existing key-based injection mechanism into a formal, versioned, validated plugin contract layer.

Formalizes:
- Injection keys
- Plugin types (extension points)
- Determinism requirements
- Compatibility validation
- Registry enforcement (allowlist)

## Extension Points
- `provider`
- `tool`
- `gate_plugin`
- `postprocessor`

## Injection Targets
Plugins declare where they attach:
- `ctx.providers[<key>]`
- `ctx.plugins[<key>]`
- `ctx.context["plugins"][<key>]`

## Manifest Contract (Required)
Each in-tree plugin file (`src/platform/*_plugin.py`) MUST expose `PLUGIN_MANIFEST` (dict) with at least:
- `manifest_version: "1.0"`
- `id`
- `type`
- `entrypoint: "module_path:symbol"`
- `inject: {target, key}`
- `requires.platform_api` range
- `determinism.required: true` for policy-affecting plugins

## Registry Enforcement
`plugin_registry.py` is authoritative allowlist.

Rule:
- `discovered_plugin_ids == registry_plugin_ids`

No orphan plugins. No implicit activation.

## Compatibility Policy
Platform exposes:
- `PLATFORM_API_VERSION`
- `PIPELINE_CONTRACT_VERSION`

Loader MUST reject plugins if constraints fail.

## Conflict Policy
Two plugins claiming the same `(target, key)` is invalid (reject).

## Scope (v1)
In-tree plugins only. No external package loading.

---

# Step41: Capability Negotiation v1 (Contract for Selecting Plugins)

## Objective
Make plugin selection predictable and testable by formalizing:
- what each gate needs (capabilities)
- how the system chooses among available plugins/providers
- what happens when capabilities are missing (fail vs skip)
- how selection/missing is recorded (reason_code + meta + observability)

This step centralizes scattered fallback logic into a single deterministic rule set.

## Core Concepts

### Capability
A named feature a plugin/provider can supply.
Examples:
- `text_generation`
- `continuity_check`
- `fact_check`
- `counterfactual_generation`
- `final_review`
- `exec_tool`

### Requirement Level
- `required`: if missing → safe failure / stop condition
- `optional`: if missing → continue with missing recorded

### Negotiation
Deterministic priority chain resolution:
- explicit overrides > dedicated keys > general fallbacks
- conflicts rejected by Step40
- selection outcome logged

## Canonical Injection Keys (Normative)
### ctx.providers
- `gpt`
- `gemini`
- `perplexity`
- `g6_counterfactual`
- `g7_final_review`

### ctx.plugins
- `exec`

### ctx.context["plugins"]
- `fact_check` (highest priority override)

## Gate → Capability Requirements (Normative)
- G1: `text_generation` (optional), order: `providers.gpt`
- G2: `continuity_check` (optional), order: `providers.gpt`
- G3: `fact_check` (optional), order:
  1) `context.plugins.fact_check`
  2) `providers.perplexity`
  3) missing → skip (record missing)
- G4: `self_check` (optional), order: `providers.gpt`
- G5: `exec_tool` (optional), order:
  1) `plugins.exec`
  2) fallback to built-in subprocess path
- G6: `counterfactual_generation` (optional by default), order:
  1) `providers.g6_counterfactual`
  2) `providers.gemini`
  3) `providers.gpt`
  4) missing → skip (record missing)
- G7: `final_review` (optional), order:
  1) `providers.g7_final_review`
  2) `providers.gpt`
  3) missing → skip

## Missing Capability Policy (Normative)
### Optional
- Continue safely
- Record:
  - `reason_code`: `CAPABILITY_MISSING`
  - `meta`: includes `missing_capability`, `requested_order`

### Required (future upgrade)
- Fail safely
- Record:
  - `reason_code`: `CAPABILITY_REQUIRED_MISSING`

## Observability (Normative)
Every negotiation MUST append to `OBSERVABILITY.jsonl`:
- `event`: `CAPABILITY_NEGOTIATED`
- `gate_id`, `capability`
- `selected` (or null)
- `missing` (bool)
- `priority_chain` (attempted keys)

## Determinism
Negotiation must be deterministic:
- stable priority order
- stable serialization
- no timestamps in negotiation artifacts
