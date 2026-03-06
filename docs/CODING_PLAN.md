# Hyper-AI CODING PLAN

Version: 2.1.0

------------------------------------------
Step110~116: Node Runtime + Plugins + NodeSpec + GraphExecutionRuntime + Engine Delegation (완료)
------------------------------------------

요약:
- Step110~111: NodeExecutionRuntime에 PluginResult/Artifact append-only lifecycle 통합
- Step112~113: plugin_loader 도입 및 node spec plugin auto-wiring
- Step114: NodeSpec validation contract (fail-fast schema + plugin id verification)
- Step115: Sequential GraphExecutionRuntime 추가 (순차 DAG 실행 + channel propagation)
- Step116: Engine → NodeExecutionRuntime delegation path 추가 (handler 없을 때 runtime 위임)

핵심 실행 구조(현재):
- Engine: semantics/trace/fixpoint + (handler 기반 실행) + (runtime 위임 실행)
- GraphExecutionRuntime: DAG 스케줄러(순차) + NodeExecutionRuntime 호출
- NodeExecutionRuntime: provider/plugins/artifacts/runtime trace

완료 조건:
- python -m pytest -q 전체 통과
- Step116 delegation contract 테스트 통과

------------------------------------------
Step67~84: Engine/Circuit 안정화 + 핵심 계약 고정 (완료)
------------------------------------------

요약:
- Circuit Runtime Adapter: conditional edge(우선순위) + trace wiring + node execution pipeline 결합
- CT-TRACE v1.0.0: node enter/exit, circuit finish, conditional edge 선택/조건 결과 기록
- NODE-EXEC v1.0.0: Pre/Core/Post 파이프라인 + AI는 Core-only
- AI-PROVIDER v1.0.0: ProviderResult + reason_code 정규화
- PLUGIN-CONTRACT v1.0.0: PluginResult envelope + stage-aware + reason_code 정규화
- PROMPT-CONTRACT v1.0.0: PromptSpec hash/render + PromptRegistry
- OBSERVABILITY(opt-in): node/stage/prompt 이벤트 기록(기존 API 비파괴)
- PLUGIN-REGISTRY v1.0.0: 버전 레지스트리 + negotiate에서 안전 resolve(옵션일 때 KeyError 방지)
- Step84: 203 passed / 9 skipped / warnings 재현되지 않음 (stabilization checkpoint)

완료 조건(증명):
- `python -m pytest -q` → 203 passed, 9 skipped (Step84 기준)

다음 목표(후속 Step 제안):
- “노드/프롬프트/AI/플러그인 시스템”을 문서/계약 기준으로 더 명확히 고정
- 이후 “회로(circuit) 시스템” 확장(모듈/서브그래프/분기/저장 등)로 진행

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

---------------------------------------------------------------------
Step51: Validation → Trace Violation Structure Contract
---------------------------------------------------------------------
목표:
- Validation 실패/경고(violations)를 Trace에 표준 dict 구조로 기록한다.
- Validation timestamp를 Trace.meta.validation.at에 기록한다.
- spec-version sync: VALIDATION_ENGINE_CONTRACT_VERSION을 1.1.0으로 올리고, 코드/테스트로 강제한다.

변경:
- docs/specs/validation_engine_contract.md: 1.0.0 → 1.1.0 (MINOR)
  - "Execution 금지" 의미를 "노드 실행 금지"로 명확화 (Trace 반환은 허용)
  - Trace.validation_violations를 dict 스키마로 강제
  - Trace.meta.validation.at timestamp 기록 강제
- src/engine/engine.py
  - trace.validation_violations: list[dict]로 기록
  - trace.meta.validation: {at, contract_version, rule_catalog_version} 기록
- src/contracts/spec_versions.py
  - VALIDATION_ENGINE_CONTRACT_VERSION = "1.1.0"
- tests/test_engine_validation_trace_violation_contract.py 추가
  - 위 계약 강제

완료 조건:
- python -m pytest -q 전체 통과
- validation 실패 케이스에서 violations dict 구조 + timestamp 존재


---------------------------------------------------------------------
Step55: Channel Validation Expansion (CH-001)
---------------------------------------------------------------------
- ValidationEngine에 CH-001 추가 (channel src/dst node_id 존재성 검증)
- validation_rule_catalog.md Implemented Rules(Authoritative) 섹션 추가 및 버전 1.1.0 bump
- spec_versions.py VALIDATION_RULE_CATALOG_VERSION 동기화
- test_ch_001_contract.py 신규 추가
