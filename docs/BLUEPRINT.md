# HYPER-AI BLUEPRINT

Version: 2.8.0  
Status: Stabilization lock-in (Post-Step36 policy trace)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step37

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

## Step37: Plugin isolation hardening (timeout + crash containment)

### Decision
- GateBlueprint에 `timeout_ms`(soft timeout) 필드 추가.
- Worker/Plugin 실행은 `safe_call`(ThreadPoolExecutor 기반)로 감싸서 timeout/예외 시 파이프라인이 죽지 않게 한다.

### Notes
- Timeout은 Python thread 특성상 'soft timeout'이다(강제 kill 불가). 대신 runner/orchestrator는 timeout 발생 시 즉시 STOP/FAIL로 수렴시키고 observability에 기록한다.
