# HYPER-AI CODING PLAN

Version: 2.0.0  
Status: Stabilized (Post-Step29)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11, Step29

## Current Status
- Step11: Hybrid registry/discovery contract locked (orphan + missing registration detection).
- Step29: Platform plugin entrypoint unified to `resolve(ctx)`.
- Test status: `69 passed, 3 skipped`.

---

## Phase: Stabilization Lock-In

### P0 (Done)
- Hybrid (registry + discovery) contract tests:
  - detect orphan plugins
  - detect missing registrations
  - ensure determinism of discovery vs registry

### P1 (Done)
- Unify platform plugin entrypoint:
  - all `src/platform/*_plugin.py` expose `resolve(ctx)`
  - gates call platform plugins only through `resolve(ctx)`
- Add Step29 contract test (`tests/test_step29_platform_unified_resolve.py`)

---

## Next Work (P2)
Objective: strengthen **PluginObject output contract** and **meta standards**.

- Enforce return schema from `generate(prompt)`:
  - `(text: str, meta: dict)` always
- Standardize `meta` keys:
  - `reason_code` (enum-like string)
  - `provider` (string)
  - `source` (string: explicit|adapter|fallback)
  - `error` (string, optional)
- Centralize provider injection keys (enum/constants) and validate them in tests.

---

## Mid-term Stabilization (P3)
- Observability:
  - log loaded plugin name + source (registry vs adapter) per gate execution
- Contract versioning:
  - add optional `contract_version` field in meta or registry
- Failure catalog:
  - reason_code taxonomy and top-level categories

---

## Hard Contract Rules (Must-Fail)
1. Every platform plugin module must provide `resolve(ctx)`.
2. `resolve(ctx)` returns `Optional[PluginObject]`.
3. `PluginObject` must provide `generate(prompt) -> (text, meta)`.
4. Contract violations **must fail** CI/pytest.
5. Gates must not call any plugin entrypoint other than `resolve(ctx)`.
6. Hybrid rules:
   - discovered plugin file not in registry => **fail**
   - registry entry not importable => **fail**

---

## Long-Term Notes
- Keep hybrid (scan + registry) until the system is mature and external plugin surfaces are designed.
- Any architecture change requires:
  - a new step-numbered test
  - doc version bump per SemVer policy

