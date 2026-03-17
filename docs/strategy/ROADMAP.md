# Nexa Roadmap

---

# Phase 1 — Core Engine Stabilization ✓ Complete

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
* CLI: diff, regression, summary commands
* Regression policy reason detail (trigger lines)

Current baseline: 688 passed, 3 skipped

---

# Phase 3 — CLI Regression Gating

Goal: Make regression policy actionable in CI/CD.

* `--baseline` flag for comparison run
* Exit code driven by PolicyDecision
* Configurable policy rules per-circuit or per-run

---

# Phase 4 — Developer Platform

* Configuration-driven policy rules
* Plugin versioning and marketplace
* CLI improvements and debugging dashboards

---

# Phase 5 — Circuit Builder

* Visual circuit editor
* Node configuration UI
* Runtime monitoring

---

# Long-Term

Nexa as a general-purpose runtime for AI computation systems — production pipelines, multi-agent systems, AI research infrastructure.

---

End of Roadmap
