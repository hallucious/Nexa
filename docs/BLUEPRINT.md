# HYPER-AI BLUEPRINT

Version: 2.11.0
Status: Stabilization lock-in (Post-Step38 policy diff)  
Last Updated: 2026-02-26  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step39

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

---

## Step37: Isolation layer (soft timeout + crash containment)

### Decision
Pipeline MUST survive misbehaving plugins/providers by containing exceptions and enforcing best-effort timeouts.

### Location
- `src/platform/safe_exec.py`: `safe_call(fn, timeout_ms)`
- `src/platform/worker.py`: provider call wrapped by `safe_call`
- `src/platform/plugin.py`: plugin execution wrapped by `safe_call`

### Notes
- Timeout is **soft** (thread cannot be force-killed in Python); returns `timed_out=True` and continues pipeline.
- Windows/Python3.8 compatible (`ThreadPoolExecutor.shutdown(cancel_futures=...)` not used).

---

## Step38: Policy diff analyzer (reason_trace comparison)

### Decision
System MUST be able to compare two runs and detect where policy paths diverge.

### Location
- `src/pipeline/policy_diff.py`: run-to-run comparison utilities
- `tests/test_step38_policy_diff_report.py`: contract test with synthetic observability logs

### Output concept
- Gate-level diff: decision/reason_code changes
- Trace divergence index via Longest Common Prefix (LCP)


## Step39: Baseline selection via CLI

### Decision
- Add `--baseline <run_id>` to `python -m src.pipeline.cli run`.
- Store the value into `RunMeta.baseline_version_id` so downstream tools (policy diff/drift checks) can reference it.

### Notes
- If the baseline directory does not exist under `runs/<run_id>`, we continue with a warning; diff tooling may skip.

### Location
- `src/pipeline/cli.py` (run command arguments + RunMeta creation)


## Step39: Baseline drift detector (Phase2)

### Decision
- After `runner.run()` completes, if `baseline_version_id` resolves to an existing directory `runs/<baseline_id>`, run a baseline drift detector.
- Drift detector compares policy snapshots between baseline run and current run using existing policy diff core.

### Drift classification rules
- **Hard drift**: `decision` changed OR `reason_code` changed.
- **Soft drift**: `decision` and `reason_code` unchanged; only `reason_trace` differs.

### Output contract
- Create `runs/<current_run_id>/DRIFT_REPORT.json` (deterministic; stable ordering by `gate_id`).
- Append to `runs/<current_run_id>/OBSERVABILITY.jsonl` one line event:
  - `event`: `DRIFT_DETECTED`
  - `baseline_id`, `current_id`
  - `hard_count`, `soft_count`

### Location
- `src/pipeline/drift_detector.py` (new; post-run comparison + report writing)
- `src/pipeline/cli.py` (calls drift detector immediately after `runner.run()`)
