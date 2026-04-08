# Nexa Roadmap

---

# Phase 1 — Core Engine Stabilization + Runtime Durability Closure ✓ Complete

* DAG-based circuit execution
* Dependency-based node scheduling
* Artifact system (append-only, hashed)
* Execution trace (per-node, immutable)
* Provider abstraction (OpenAI, Anthropic, Gemini)
* Plugin system (restricted namespaces)
* Validation engine
* Contract-driven architecture

---

# Phase 2 — Observability and Determinism Tooling ✓ Complete

* Execution timeline, replay, determinism validator
* Artifact hashing, snapshot, diff
* Regression detector (typed reason codes, severity)
* Regression formatter and policy engine (PASS/WARN/FAIL)
* Audit pack, provenance graph, run comparator
* CLI: run, compare, diff, export, replay, info, and task commands
* Regression policy reason detail (trigger lines)

Current baseline at closeout: `1283 passed, 3 skipped`

---

# Phase 3 — Role-Aware Savefile / Storage Lifecycle ✓ Complete baseline

* unified `.nex` family with `working_save` / `commit_snapshot`
* Execution Record treated as run-history layer rather than a savefile role
* canonical savefile lifecycle entry points across create / serialize / load / validate
* role-aware `.nex` loading / validation / typed-model split
* storage semantics concentrated in lifecycle APIs rather than scattered CLI-only interpretation
* commit-boundary rules for UI-owned continuity state

---

# Phase 4 — UI Foundation / i18n Foundation ✓ Complete baseline

* adapter / view-model boundary across the UI sector
* Core 5 module view-model surfaces: Graph / Inspector / Validation / Execution / Designer
* expanded surfaces: Trace / Timeline / Artifact / Storage / Diff
* builder shell / workflow / interaction / dispatch / execution-adapter / end-user-flow hub surfaces
* workspace-level surfaces: visual editor / runtime monitoring / node configuration
* English / Korean localization foundation and persistence boundary
* canonical Working Save-side UI continuity with snapshot-side canonical UI exclusion

---

# Phase 5 — Product-Flow Shell Convergence ◐ Late convergence

* journey projection
* runbook projection
* handoff projection
* readiness projection
* E2E path projection
* closure projection
* transition projection
* gateway projection tied to proposal/commit and execution-launch workflow gates

Interpretation:
- the shell can now describe lifecycle position, next action, boundary closure, and gate state
- the remaining gap is final live end-to-end proof, not absence of shell/product-flow structure

---

# Public Baseline (current)

* Official retained demo consolidated to `examples/real_ai_bug_autopsy_multinode/`
* Provider environment guidance unified across OpenAI, Codex, Claude, Gemini, and Perplexity
* Canonical public CLI clarified as `src.cli.nexa_cli:main`
* Role-aware `.nex` storage and UI continuity boundary are implemented in code and tests
* Product-flow shell convergence exists across journey / runbook / handoff / readiness / E2E path / closure / transition / gateway
* Current repository baseline: `1844 passed, 9 skipped`
* Authoritative implementation baseline commit: `f143396`

---

# Next Technical Focus

* finish the last live end-to-end proof only if a real commit/run/follow-through gap is still found
* otherwise shift from shell convergence to broader product-facing implementation and UX realization

---

# Long-Term

Nexa as a general-purpose runtime for AI computation systems — production pipelines, multi-agent systems, AI research infrastructure.

---

End of Roadmap
