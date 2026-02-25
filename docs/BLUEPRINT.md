# HYPER-AI BLUEPRINT

Version: 2.1.0  
Status: Stabilized (Post-Step29)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11 (Hybrid registry/discovery contract), Step29 (Unified resolve(ctx) entrypoint), Step30 (Meta contract)

## Core Objective
- Build a framework that structurally minimizes bug probability via AI collaboration.
- Priority order: **Reproducibility > Contract stability > Test evidence > Expandability**.

---

## Platform Plugin Architecture (Step29)

### 1) Single entrypoint
All platform plugins must expose **one** entrypoint:

- `resolve(ctx: GateContext) -> Optional[PluginObject]`

Gates must call platform plugins **only** through `resolve(ctx)`.

> Legacy `resolve_<gate>_plugin(...)` entrypoints are deprecated and must not be used.

### 2) PluginObject contract
`resolve(ctx)` returns `None` or an object that satisfies its gate-specific protocol.

For plugins that return a `meta: dict` (e.g., G4/G6/G7 flows), meta is standardized by Step30.

---

## Hybrid Registry + Discovery (Step11)

### 3) Discovery (scan)
- Discover candidate plugins by scanning:
  - `src/platform/*_plugin.py`

### 4) Registry (official list)
- Maintain a central registry of **official** plugins.
- Only registry-approved plugins are considered “in-system.”

### 5) Hybrid contract
- Any registry entry must be importable.
- Any discovered `*_plugin.py` that is **not** in the registry is treated as **orphan** and should fail CI (stability-first).
- Any plugin missing `resolve(ctx)` fails CI.

---

## Meta contract (Step30)

### Scope
Applies to any platform plugin output that includes a `meta: dict`.

### Required keys
Every such `meta` must include:

- `reason_code` (enum string)
- `provider` (string)
- `source` (string)
- `contract_version` (string)

Additional keys are allowed.

### Allowed `reason_code` values
- `SUCCESS`
- `SKIPPED`
- `PROVIDER_MISSING`
- `PROVIDER_ERROR`
- `CONTRACT_VIOLATION`
- `INTERNAL_ERROR`

### Why it exists
- Makes logs comparable across gates/plugins.
- Enables stable failure cataloging and regression analysis.
- Prevents silent drift in meta payloads.

---

## Gate ↔ Platform boundary

Gates should only do:

1) `plugin = resolve(ctx)`
2) if `plugin is None`: handle gracefully
3) else: call the plugin protocol (gate-specific)

Gates must **not**:
- depend on provider internals
- call alternate plugin entrypoints
- assume plugin file presence implies activation (registry defines activation)

---

## Stabilization goals
- Remove implicit behavior.
- Enforce a single entrypoint.
- Lock contracts via tests.
- Make structural regression immediately fail in `pytest`.
