# HYPER-AI CODING PLAN

Version: 2.1.0  
Status: Stabilization lock-in (Post-Step29)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11, Step29, Step30

---

## Current status
- Step11: Hybrid registry/discovery contract locked.
- Step29: Platform plugin unified entrypoint `resolve(ctx)` locked.
- Step30: Meta contract locked for plugin flows returning `meta: dict`.
- pytest baseline: **69 passed, 3 skipped** (post-step29) / unchanged by step30 target.

---

## Phase: Stabilization lock-in

### P0 (Done)
- Hybrid registry + discovery comparison (orphan/missing detection).

### P1 (Done)
- Unify platform plugin entrypoint to `resolve(ctx)`.
- Update gates to call platform plugins only via `resolve(ctx)`.

### P2 (This change; MINOR)
**Goal:** Standardize plugin `meta` payload to enable observability and stable failure cataloging.

Deliverables:
- `src/platform/plugin_contract.py`
  - `ReasonCode` enum
  - `CONTRACT_VERSION`
  - `normalize_meta()` helper
- Update affected platform plugins that return `meta: dict` (e.g., G4/G6/G7) to always emit required meta keys.
- `tests/test_step30_plugin_meta_contract.py`
  - Enforce required meta keys and allowed reason_code values.

---

## Hard contract rules (post-step30)

### Entry point
1. All platform plugins expose `resolve(ctx)`.
2. Gates call platform plugins only through `resolve(ctx)`.

### Meta contract (when meta exists)
3. Any plugin output that includes `meta: dict` MUST include:
   - `reason_code`, `provider`, `source`, `contract_version`
4. `reason_code` MUST be one of `ReasonCode` enum values.
5. Contract violations MUST fail pytest.

---

## Follow-ups (next)

### P3: Provider key / source standardization
- Standardize provider naming across plugins (`gpt`, `gemini`, explicit plugin keys).
- Add log hook to record loaded plugin ids and providers.

### P4: Failure catalog
- Expand ReasonCode taxonomy only when repeated failure patterns are observed.
- Keep ReasonCode set small and stable.
