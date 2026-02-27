# Execution Model Specification (Sync-first)
Version: 1.1.0
Status: Official Contract

Purpose:
Engine 실행 모델(v1)을 정의한다.
v1은 Sync-first이며, Validation 성공 시에만 실행이 진행된다.

----------------------------------------------------------------------
1) Model (v1)
----------------------------------------------------------------------

- Sync-first (Async/Parallel 금지)
- 실행 전 Validation 필수(실패 시 실행 차단)
- Entry부터 시작
- Node는 Pre/Core/Post 파이프라인을 따른다
- 실패 시 downstream은 skipped로 기록될 수 있다(향후 단계에서 확장)

----------------------------------------------------------------------
2) Minimal Execution Semantics (v1.1.0)
----------------------------------------------------------------------

v1.1.0에서는 “실제 Node 실행”을 아직 구현하지 않더라도,
Engine.execute()가 최소 실행 의미를 Trace에 남겨야 한다.

- Validation 성공 시:
  - entry_node는 SUCCESS로 기록한다.
  - entry_node의 pre/core/post는 모두 SUCCESS로 기록한다.
- 그 외 노드는 NOT_REACHED 유지한다.
- Validation 실패 시:
  - 모든 노드는 NOT_REACHED 유지한다.
  - validation 결과(성공/위반 목록)는 Trace에 반드시 포함된다.

----------------------------------------------------------------------
3) Validation Mapping
----------------------------------------------------------------------

Enforced by rule_ids:
- ENG-001..
- NODE-001..
- ENG-003
- TRACE-001..004
