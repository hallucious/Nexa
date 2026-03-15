# BLUEPRINT

Version: 1.4.3

────────────────
Architecture Constitution
────────────────

Nexa는 Execution Engine 기반 아키텍처를 따른다.

Nexa의 핵심 설계 원칙은
docs/FOUNDATION_RULES.md
문서에 정의된 Architecture Constitution을 따른다.

이 문서는 Nexa의 최상위 설계 규칙을 정의한다.

다음 규칙은 변경될 수 없는 시스템 invariant이다.

1. Nexa는 workflow tool이 아니라 execution engine이다.
2. Node는 유일한 실행 단위이다.
3. Circuit은 실행을 수행하지 않고 연결만 담당한다.
4. execution은 dependency 기반이어야 한다.
5. artifact는 append-only immutable 구조이다.
6. deterministic execution을 유지해야 한다.
7. plugin write 영역은 plugin.<plugin_id>.* 로 제한된다.
8. working context schema는 고정된 key 구조를 따른다.
9. contract-driven architecture를 유지한다.
10. spec-version synchronization을 유지한다.

이 규칙을 위반하는 구현은 Nexa 아키텍처 위반으로 간주된다.

모든 구현과 리팩토링은
Architecture Constitution을 기준으로 검증되어야 한다.


## 1. Foundation Layer (Canonical Architecture Memory)

본 프로젝트의 기초 설계 문서는 다음 문서에 의해 계층적으로 관리된다:

- docs/FOUNDATION_MAP.md

구조 변경 또는 계약 변경 작업 시 반드시 FOUNDATION_MAP을 참조하고,
영향받는 문서들의 상태 및 SemVer를 확인해야 한다.

## 2. Active Specifications

현재 코드와 1:1로 동기화되는 활성 spec 문서 목록.

Source-of-Truth: `docs/specs/indexes/_active_specs.yaml`

Active spec 경로는 _active_specs.yaml 이 최종 기준이며,
아래 목록은 주요 spec 참조 목록이다.

### 2.1 Foundation / Terminology

- docs/specs/foundation/terminology.md

### 2.2 Architecture Core Contracts

- docs/specs/architecture/execution_model.md
- docs/specs/architecture/trace_model.md
- docs/specs/architecture/node_abstraction.md
- docs/specs/architecture/node_execution_contract.md
- docs/specs/architecture/circuit_contract.md
- docs/specs/architecture/universal_provider_architecture.md

### 2.3 Contracts Layer

- docs/specs/contracts/execution_environment_contract.md
- docs/specs/contracts/provider_contract.md
- docs/specs/contracts/plugin_contract.md
- docs/specs/contracts/prompt_contract.md
- docs/specs/contracts/plugin_registry_contract.md
- docs/specs/contracts/validation_engine_contract.md
- docs/specs/contracts/execution_config_canonicalization_contract.md
- docs/specs/contracts/execution_config_schema_contract.md

### 2.4 Policies

- docs/specs/policies/validation_rule_catalog.md
- docs/specs/policies/validation_rule_lifecycle.md

### 2.5 Indexes

- docs/specs/indexes/spec_catalog.md
- docs/specs/indexes/spec_dependency_map.md

### 2.6 ExecutionConfig Binding / Registry (Top-level)

- docs/specs/execution_config_prompt_binding_contract.md
- docs/specs/execution_config_registry_contract.md

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
→ NodeExecutionRuntime Slot Stages

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
