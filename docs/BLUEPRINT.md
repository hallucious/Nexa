# HYPER-AI BLUEPRINT

Version: 2.0.0  
Status: Stabilized (Post-Step29)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11 (Hybrid registry/discovery contract), Step29 (Unified resolve(ctx) entrypoint)

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
`resolve(ctx)` returns `None` or an object that satisfies:

- `generate(prompt: str) -> tuple[str, dict]`

Rules:
- `text` must be `str`
- `meta` must be `dict`
- For normal operation, it must not raise.
- Errors are expressed via `meta["error"]` (string code).

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
- Any plugin returning an object that violates the `generate()` contract fails CI.

---

## Gate ↔ Platform boundary

Gates should only do:

1) `plugin = resolve(ctx)`
2) if `plugin is None`: handle gracefully
3) else: `text, meta = plugin.generate(prompt)`

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

