# HYPER-AI CODING PLAN

Version: 2.9.0  
Status: Stabilization lock-in (Post-Step38)  
Last Updated: 2026-02-26  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step38

---

## Step36 (MINOR): Policy trace

Goal:
- Record policy evaluation path as `reason_trace` for every decision (PASS 포함).

Deliverables:
- Extend `PolicyDecision` with `reason_trace: list[str]`
- Update `src/policy/gate_policy.py` evaluate_g* to populate `reason_trace`
- Propagate into `OBSERVABILITY.jsonl` (runner event includes `reason_trace`)
- Add test: `tests/test_step36_policy_trace_written.py`

---

## Step37 (MINOR): Plugin/Worker isolation (timeout + crash containment)

Goal:
- Ensure pipeline survivability even when plugins/providers hang or crash.

Deliverables:
- Add `src/platform/safe_exec.py` (`safe_call`)
- Wrap provider calls in `ProviderTextWorker` with timeout support
- Wrap plugin execution (`safe_execute_plugin`) with timeout support
- Add tests: `tests/test_step37_plugin_isolation_timeout.py`

---

## Step38 (MINOR): Policy diff analyzer

Goal:
- Compare two runs using `reason_trace` and summarize divergences.

Deliverables:
- Add `src/pipeline/policy_diff.py`
- Add test with synthetic `OBSERVABILITY.jsonl`: `tests/test_step38_policy_diff_report.py`

Acceptance:
- Report identifies first divergence point (LCP) and decision/reason_code changes per gate.
