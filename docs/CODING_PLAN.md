# HYPER-AI CODING PLAN

Version: 2.8.0  
Status: Stabilization lock-in (Post-Step36)  
Last Updated: 2026-02-25  
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)  
Related Steps: Step11–Step37

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

## Step37 (MINOR): Plugin isolation hardening

Goal:
- 플러그인/워커 실행이 timeout 또는 예외로 실패해도 파이프라인이 죽지 않도록 격리한다.

Deliverables:
- `src/platform/safe_exec.py`: `safe_call(fn, timeout_ms)` 유틸
- `GateBlueprint.timeout_ms` 추가 및 orchestrator가 worker 호출에 전달(호환 TypeError fallback)
- `ProviderTextWorker.generate_text(..., timeout_ms=...)` 지원
- `safe_execute_plugin(plugin, timeout_ms, **kwargs)` 헬퍼 제공
- 테스트: timeout 발생 시 빠르게 반환하고 에러가 TIMEOUT으로 표준화됨

Done checklist:
- [ ] timeout/crash가 발생해도 pytest가 중단되지 않음
- [ ] timeout 시 error='TIMEOUT'
- [ ] GateBlueprint.timeout_ms로 gate별 설정 가능
