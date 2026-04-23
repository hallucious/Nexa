# Nexa Strategy

Version: 1.1.0
Status: Official Strategy Direction

---

## 1. Product Identity

Nexa is a **structurally verifiable AI execution engine**.

It is not a simple automation tool; it controls execution based on **structure / constraints / reproducibility / Trace**.

Core differentiators:
- Deterministic execution (dependency-based execution)
- Full execution trace (per node)
- Contract-driven architecture
- Regression detection and policy gating

---

## 2. Primary Target

The primary target is **enterprise R&D teams**.

Reason: they have strong needs for reproducibility, audit logs, failure analysis, and cost control.

---

## 3. MVP Scope (Completed)

- Structural design: Engine / Node / Circuit / Channel / Flow
- Structural validation: Validation Engine
- Actual execution: Runtime (dependency-based scheduling)
- Full graph Trace persistence (including unexecuted nodes)
- Reproducibility based on execution_id
- Node behavior composition based on ExecutionConfig
- Regression detection (typed reason codes + severity)
- Policy evaluation (PolicyDecision: PASS / WARN / FAIL)
- CLI (execution, diff, regression commands)

---

## 4. Philosophy / Priorities

- Simple-first
- Priority: structural simplicity > stability > reproducibility > cost > performance
- No automatic application: changes are applied only as a new Revision after user approval

---

## 5. UI Direction (Lower Priority)

- Expand in stages: Guided → Builder → Advanced
- Keep the internal model intact, but proceed with UX after structural stabilization

---

## 6. Next Strategic Goals

**Phase 3**: CLI regression gating — automatic blocking in CI/CD based on PASS/WARN/FAIL

**Phase 4**: Configuration-based policies — customize regression rules by circuit/run

**Phase 5**: Visual Circuit Builder — improve developer productivity

---

End of Strategy
