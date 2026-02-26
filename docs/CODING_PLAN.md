# HYPER-AI CODING PLAN

Version: 2.10.0  
Status: Stabilization lock-in (Post-Step38)  
Last Updated: 2026-02-26  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step39

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


## Step39 (MINOR): CLI baseline run id

Goal:
- Allow users to specify a baseline run for drift / policy-diff comparison.

Deliverables:
- Add CLI argument: `--baseline <run_id>`
- Persist into `RunMeta.baseline_version_id`
- Add/extend tests (if needed) to validate `baseline_version_id` is written into `runs/<run_id>/META.json`

Validation:
- `python -m src.pipeline.cli run --request "hello" --baseline <existing_run_id>`
- Confirm `runs/<new_run_id>/META.json` contains `baseline_version_id`.
