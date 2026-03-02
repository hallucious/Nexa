# Hyper-AI CODING PLAN

Version: 1.6.0

  ------------------------------------------
  Step45: DAG 상태 전파 규칙 (ALL_SUCCESS)
  ------------------------------------------

목표: - 다중 부모 노드 실행 조건을 ALL_SUCCESS 정책으로 확정 -
execution_model.md 계약 갱신 - 이후 단계에서 실행 로직 구현 준비

완료 조건: - execution_model.md v1.2.0 반영 - 테스트 전략 정의

------------------------------------------------------------------------

# Archived Initial Version (Preserved)

# Hyper-AI CODING PLAN

Version: v1.0.0

Phase 1: - Core Engine Implementation - Constraint Enforcement System -
Graph-based Trace Model

Phase 2: - Statistical Analysis Layer - Proposal Engine

Phase 3: - Guided UI Layer

  ----------------------------------------------------
  Step46: Legacy Isolation & Engine Canonicalization
  ----------------------------------------------------

목표: - src/pipeline 실구현을 src/legacy/pipeline 으로 이동 -
src/pipeline 을 shim-only 구조로 전환 - Engine canonical entrypoint
invariant 테스트 추가

완료 조건: - test_engine_is_canonical_entrypoint.py 통과 - src.engine.\*
내부에서 src.legacy 직접 import 없음 - 전체 pytest 통과 유지


---------------------------------------------------------------------
Step47: Engine Determinism Contract 강화 (T1)
---------------------------------------------------------------------

목표:
- Engine의 구조적 결정성(determinism)을 계약(테스트)으로 강화
- 동일 그래프 구조에서 실행 반복 시, 노드별 구조 결과(signature)가 동일해야 함

추가/변경 사항:
- tests/test_engine_determinism_contract.py 추가
  - node_status + (pre/core/post) stage status + reason_code 기반 signature 비교
  - execution_id, revision_id, timestamp 등 비결정 필드는 비교 대상에서 제외

완료 조건:
- python -m pytest -q 전체 통과
- 50회 반복 실행에서 signature 동일
