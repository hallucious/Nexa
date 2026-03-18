# Nexa Strategy

Version: 1.1.0
Status: Official Strategy Direction

---

## 1. Product Identity

Nexa is a **structurally verifiable AI execution engine**.

It is not a simple automation tool, but a system that controls execution based on **structure / constraints / reproducibility / Trace**.

Core differentiators:
- Deterministic execution (deterministic, dependency-based execution)
- Full execution trace (per-node)
- Contract-driven architecture
- Regression detection and policy gating (regression detection + policy gating)

---

## 2. Primary Target

The primary target is **enterprise R&D teams**.

Reason: strong requirements for reproducibility, audit logs, failure analysis, and cost control.

---

## 3. MVP Scope (Completed)

- Structural design: Engine / Node / Circuit / Channel / Flow
- Structural validation: Validation Engine
- Actual execution: Runtime (dependency-based scheduling)
- Full graph Trace storage (including non-executed nodes)
- Reproducibility via execution_id
- Node behavior composition via ExecutionConfig
- Regression detection (typed reason codes + severity)
- Policy evaluation (PolicyDecision: PASS / WARN / FAIL)
- CLI (execution, diff, regression commands)

---

## 4. Philosophy / Priorities

- Simple-first
- Priority: structural simplicity > stability > reproducibility > cost > performance
- No automatic application: applied only as a new Revision after user approval

---

## 5. UI Direction (Lower Priority)

- Expand in stages: Guided → Builder → Advanced
- Maintain internal model, UX to be developed after structural stabilization

---

## 6. Next Strategic Goals

**Phase 3**: CLI regression gating — automatic blocking in CI/CD based on PASS/WARN/FAIL

**Phase 4**: configuration-based policy — customizable regression rules per circuit/run

**Phase 5**: Visual Circuit Builder — improve developer productivity

---

End of Strategy
