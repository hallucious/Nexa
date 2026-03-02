# Hyper-AI CODING PLAN

Version: 1.9.0

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


---------------------------------------------------------------------
Step48: Trace Immutability Contract 강화
---------------------------------------------------------------------

목표:
- Engine 실행 완료 후 반환된 Trace 객체는 외부에서 변경 불가능해야 함

추가/변경 사항:
- tests/test_trace_immutability_contract.py 추가
  - structural_fingerprint 변경 시 예외 발생
  - node_status 변경 시 예외 발생

완료 조건:
- python -m pytest -q 전체 통과
- Trace 객체 외부 변조 시도 시 예외 발생


---------------------------------------------------------------------
Step49: Engine Trace에 Spec-Version Stamp 추가 (Execution Artifact Sync)
---------------------------------------------------------------------

목표:
- Engine 실행 결과(ExecutionTrace.meta)에 활성 spec 버전을 함께 기록하여,
  spec-version sync를 실행 산출물 레벨까지 강화

추가/변경 사항:
- src/engine/engine.py
  - ExecutionTrace.meta에 spec_versions 필드 추가
    - execution_model: ENGINE_EXECUTION_MODEL_VERSION
    - trace_model: ENGINE_TRACE_MODEL_VERSION
- tests/test_engine_spec_version_in_trace_contract.py 추가
  - trace.meta.spec_versions 값이 contracts/spec_versions.py와 일치하는지 검증

완료 조건:
- python -m pytest -q 전체 통과
- trace.meta.spec_versions가 상수와 정확히 일치


---------------------------------------------------------------------
Step50: Trace Serialization Stability Contract
---------------------------------------------------------------------
목표:
- ExecutionTrace가 공식 직렬화 API를 제공해야 함 (to_dict / to_json)
- 동일 Trace 인스턴스에 대해 stable 직렬화 결과는 반복 호출 시 100% 동일해야 함
- meta / snapshot은 JSON-safe 강제를 통과해야 함 (비-JSON 타입은 계약 위반)

추가 사항:
- src/engine/trace.py
  - ExecutionTrace.to_dict(stable=True) / to_json(stable=True) 추가
  - stable=True일 때 nodes는 node_id 정렬 기반으로 결정적 출력
  - enum -> .value, datetime -> isoformat() 문자열
  - meta/input_snapshot/output_snapshot JSON-safe 강제 (TypeError on violation)
- tests/test_trace_serialization_stability_contract.py 추가
  - trace.to_json(stable=True) 반복 호출 결과 동일성 검증

완료 조건:
- python -m pytest -q 전체 통과
- stable=True 직렬화 결과 반복 호출 시 완전 동일


추가 사항:
- tests/test_trace_serialization_stability_contract.py 추가
  - trace.to_dict() 기반 JSON 비교
  - sort_keys=True로 안정성 강제

완료 조건:
- python -m pytest -q 전체 통과
- 반복 직렬화 결과 완전 동일
