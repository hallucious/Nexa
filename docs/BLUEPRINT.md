# BLUEPRINT

Version: 1.4.2

## 1. Foundation Layer (Canonical Architecture Memory)

본 프로젝트의 기초 설계 문서는 다음 문서에 의해 계층적으로 관리된다:

- docs/FOUNDATION_MAP.md

구조 변경 또는 계약 변경 작업 시 반드시 FOUNDATION_MAP을 참조하고,
영향받는 문서들의 상태 및 SemVer를 확인해야 한다.

## 2. Active Specifications

현재 코드와 1:1로 동기화되는 활성 spec 문서 목록:

- docs/specs/execution_model.md
- docs/specs/trace_model.md
- docs/specs/validation_engine_contract.md
- docs/specs/validation_rule_catalog.md

### 2.1 추가된 Active Specs (Step67~84 누적)

아래 항목들은 기존 목록에 누적 추가된 활성 spec(코드/테스트와 동기화)이다:

- docs/specs/terminology.md
- docs/specs/node_execution_contract.md  (NODE-EXEC v1.0.0)
- docs/specs/docs_specs_circuit_trace_contract.md  (CT-TRACE v1.0.0, circuit trace contract)
- docs/specs/provider_contract.md  (AI-PROVIDER v1.0.0)
- docs/specs/plugin_contract.md  (PLUGIN-CONTRACT v1.0.0)
- docs/specs/prompt_contract.md  (PROMPT-CONTRACT v1.0.0)
- docs/specs/plugin_registry_contract.md  (PLUGIN-REGISTRY v1.0.0)
- docs/specs/observability_metrics.md  (OBSERVABILITY, opt-in 이벤트/메트릭)

### 2.2 ExecutionConfig Layer Active Specs (Step121~125 누적)

아래 항목들은 ExecutionConfig 계층 도입에 따라 누적 추가된 활성 spec이다:

- docs/specs/execution_config_canonicalization_contract.md
- docs/specs/execution_config_schema_contract.md

주의:
- Active spec 목록의 Source-of-Truth는 본 문서(BLUEPRINT)이다.
- docs/FOUNDATION_MAP.md는 문서 카탈로그/레이어링을 제공하지만, Active spec 결정 기준이 아니다.
- spec-version sync 계약 테스트는 BLUEPRINT의 Active spec 목록을 파싱해, 각 spec 문서의 Version:과 src/contracts/spec_versions.py의 매핑이 일치하는지 강제한다.

구조/계약 변경 시 위 문서들과 코드, 테스트는 반드시 동기화되어야 한다.

## 3. ExecutionConfig Architecture (Step120~125)

Node type은 존재하지 않는다.

Node는 하나의 공통 실행 컨테이너이며,
행동 다양성은 ExecutionConfig 조합으로만 표현한다.

핵심 원칙:

- Node = execution container
- Behavior = ExecutionConfig composition
- NodeSpec = ExecutionConfig reference
- ExecutionConfig identity = canonical hash

실행 계층:

Engine
→ GraphExecutionRuntime
→ NodeSpec
→ NodeSpecResolver
→ ExecutionConfigRegistry
→ ExecutionConfig Schema Validation
→ ExecutionConfig Hash
→ NodeExecutionRuntime Slot Pipeline

## 4. ExecutionConfig Hash Identity (Step121)

ExecutionConfig ID는 실행 의미의 정체성이다.

- 같은 구성 = 같은 ID
- 실행 의미 변경 = 다른 ID
- label / notes / metadata는 ID에 영향을 주지 않는다

권장 형식:

- ec_<short-hash>

## 5. ExecutionConfig Registry (Step122)

ExecutionConfig는 repo 내부 registry/에 저장된다.

권장 구조:

registry/
  execution_configs/
    ec_xxxxxxxx/
      1.0.0.json

Circuit/NodeSpec은 ExecutionConfig 전체를 포함하지 않고 reference만 가진다.

## 6. ExecutionConfig Schema Validation (Step125)

ExecutionConfigRegistry는 JSON 로드 후 schema validation을 통과한 config만 허용한다.

최소 강제 필드:

- config_id
- version

타입 강제:

- pre_plugins: list
- post_plugins: list
- validation_rules: list
- output_mapping: dict

ExecutionConfig는 검증됨 / canonical / hashable / registry-managed 상태여야 한다.
