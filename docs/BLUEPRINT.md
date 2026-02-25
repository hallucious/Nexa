# HYPER-AI BLUEPRINT

Version: 2.7.0  
Status: Stabilization lock-in (Post-Step36 policy trace)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step36

---

## Step36: Policy trace (reason_trace)

### Decision
Every policy decision MUST include a human-readable trace of the evaluation path.

### Location
- `PolicyDecision.reason_trace: list[str]` (always present; may be empty)
- Propagated into:
  - `GateResult.meta["reason_trace"]` (where applicable)
  - `runs/<run_id>/OBSERVABILITY.jsonl` as `reason_trace`

### Why
- Enables “why STOP/FAIL” postmortems without re-running.
- Makes policy refactors observable (branch changes become diff-able).
