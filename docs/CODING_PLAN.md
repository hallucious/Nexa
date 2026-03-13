# Hyper-AI CODING PLAN

Version: 2.1.0

------------------------------------------
Step67~84: Engine/Circuit 안정화 + 핵심 계약 고정 (완료)
------------------------------------------

요약:
- Circuit Runtime Adapter: conditional edge(우선순위) + trace wiring + node execution stages 결합
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
Step121: ExecutionConfig Canonicalization / Hash Identity (완료)
------------------------------------------

목표:
- ExecutionConfig를 실행 의미 기반 canonical hash로 식별
- 같은 구성은 같은 ID, 실행 의미 변경은 다른 ID가 되도록 강제
- canonicalization 계약을 문서/테스트/코드로 고정

구현:
- src/engine/execution_config_hash.py
- docs/specs/execution_config_canonicalization_contract.md
- tests/test_step121_execution_config_hash_contract.py

완료 조건:
- canonical hash 생성 테스트 통과
- 전체 pytest 통과 유지

------------------------------------------
Step122: ExecutionConfig Registry Loader (완료)
------------------------------------------

목표:
- repo 내부 registry/execution_configs/에서 ExecutionConfig를 로드
- ref → config resolution, version lookup, 캐싱 계약 고정

구현:
- src/platform/execution_config_registry.py
- tests/test_step122_execution_config_registry_contract.py

완료 조건:
- registry lookup / missing config / missing version / cache 테스트 통과
- 전체 pytest 통과 유지

------------------------------------------
Step123: NodeExecutionRuntime Slot Stages (완료)
------------------------------------------

목표:
- NodeExecutionRuntime이 ExecutionConfig 스타일 입력을 받아 slot stages를 실행
- legacy Artifact / NodeResult / NodeTrace 계약 유지

구현:
- src/engine/node_execution_runtime.py
- tests/test_step123_nodeslot_stages_contract.py

실행 슬롯:
1. pre_plugins
2. prompt_render
3. provider_execute
4. post_plugins
5. validation
6. output_mapping

완료 조건:
- legacy runtime 계약 유지
- ExecutionConfig bridge 테스트 통과
- 전체 pytest 통과 유지

------------------------------------------
Step124: NodeSpec → ExecutionConfig Resolution (완료)
------------------------------------------

목표:
- NodeSpec이 execution_config_ref를 통해 ExecutionConfigRegistry와 연결되도록 구현
- Node는 실행 로직이 아닌 reference만 가지는 구조를 확정

구현:
- src/engine/node_spec_resolver.py
- tests/test_step124_node_spec_resolution_contract.py

완료 조건:
- resolution success / missing config / invalid ref / missing version 테스트 통과
- 전체 pytest 통과 유지

------------------------------------------
Step125: ExecutionConfig Schema Validation (완료)
------------------------------------------

목표:
- ExecutionConfigRegistry 로드 전에 schema validation을 강제
- 잘못된 config JSON을 조기 차단
- ExecutionConfig를 검증됨 / canonical / hashable / registry-managed 실행 단위로 고정

구현:
- src/platform/execution_config_schema.py
- docs/specs/execution_config_schema_contract.md
- tests/test_step125_execution_config_schema_contract.py

최소 강제 필드:
- config_id
- version

타입 강제:
- pre_plugins: list
- post_plugins: list
- validation_rules: list
- output_mapping: dict

완료 조건:
- schema validation contract 테스트 통과
- 전체 pytest 통과 유지

------------------------------------------
다음 작업
------------------------------------------

Step126: ExecutionConfig Version Negotiation

목표:
- ExecutionConfig ref에서 version negotiation 규칙 정의
- 1 / 1.x / 1.2 / 1.2.3 형태의 ref를 안정적으로 해석
- registry lookup을 version compatibility-aware 로 확장
