# HYPER-AI CODING PLAN

Version: 2.7.0  
Status: Stabilization lock-in (Post-Step36)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step36

---

## Step36 (MINOR): Policy trace

Goal:
- Record policy evaluation path as `reason_trace` for every decision (PASS 포함).

Deliverables:
- Extend `PolicyDecision` with `reason_trace: list[str]`
- Update `src/policy/gate_policy.py` evaluate_g* to populate `reason_trace`
- Propagate into `OBSERVABILITY.jsonl` (runner event includes `reason_trace`)
- Add test: `tests/test_step36_policy_trace_written.py`
