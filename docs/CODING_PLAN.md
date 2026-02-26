# HYPER-AI CODING PLAN

Version: 3.1.0  
Status: Step41 planning (Capability Negotiation v1)  
Last Updated: 2026-02-26  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step41

---

## Step40: Plugin System v1 — Implemented

Baseline for Step41:
- In-tree plugins expose `PLUGIN_MANIFEST`
- Discovery validates registry consistency and injection uniqueness
- `PLATFORM_API_VERSION` enforced
- pytest passing at Step40 baseline

---

# Step41: Capability Negotiation v1 — Implementation Plan

## Goal
Centralize and standardize plugin/provider selection so that
all gates follow the same deterministic, testable rules.

This reduces scattered fallback logic and makes expansions safe.

---

## Deliverables

1) New negotiation module
- Add `src/platform/capability_negotiation.py`
- Provide a single entrypoint:
  - `negotiate(*, gate_id, capability, ctx, priority_chain, required=False) -> NegotiationResult`

2) Negotiation result contract
- fields:
  - `selected_target` (providers/plugins/context.plugins)
  - `selected_key`
  - `selected_plugin_id` (from manifest if available)
  - `missing` (bool)
  - `priority_chain` (attempted order)
  - `reason_code`:
    - `CAPABILITY_MISSING` (optional missing)
    - `CAPABILITY_REQUIRED_MISSING` (required missing)
    - `CAPABILITY_SELECTED` (resolved)

3) Gate integration (minimal change)
- Replace scattered fallback logic with `negotiate(...)`
- Keep behavior identical to existing priority rules:
  - G3: context override → perplexity → missing
  - G6: dedicated → gemini → gpt → missing
  - G7: dedicated → gpt → missing
  - G5: exec tool → subprocess fallback (still allowed)

4) Observability integration
- Append `CAPABILITY_NEGOTIATED` event per negotiation:
  - `gate_id`, `capability`, `selected`, `missing`, `priority_chain`

5) Tests
- Unit tests for negotiation:
  - deterministic selection order
  - optional missing → `CAPABILITY_MISSING`
  - required missing → `CAPABILITY_REQUIRED_MISSING`
  - context override wins for `fact_check`
- Regression:
  - Step37 timeout tests remain passing
  - Step39 drift tests remain passing
  - Step40 manifest tests remain passing

---

## Acceptance Criteria
- All gates use negotiation module (single source of truth).
- Selection is deterministic.
- Missing capability behavior consistent and logged.
- pytest fully passes.

---

## Non-Goals
- External plugin loading
- Priority override policy beyond fixed chain
- Runtime UI

---

## Implementation Order
1) Add negotiation module + result types
2) Add/extend reason_code enum entries if needed
3) Add unit tests for negotiation
4) Integrate in G6 + G3 first, run pytest
5) Expand to other gates in small steps
6) GitHub backup (main)
7) Obsidian note (1:1 with commit)
