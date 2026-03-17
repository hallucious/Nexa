# BLUEPRINT

Version: 1.5.0

────────────────
Architecture Constitution
────────────────

Nexa는 Execution Engine 기반 아키텍처를 따른다.

핵심 설계 원칙은 docs/architecture/FOUNDATION_RULES.md 문서에 정의된 Constitution을 따른다.

변경될 수 없는 시스템 invariant:

1. Nexa는 workflow tool이 아니라 execution engine이다.
2. Node는 유일한 실행 단위이다.
3. Circuit은 실행을 수행하지 않고 연결만 담당한다.
4. 시스템 수준 실행은 dependency 기반이다. 고정 pipeline은 금지된다.
5. Node 내부에는 pre/core/post 단계가 존재하지만, 이는 단일 노드의 내부 계약이다.
6. artifact는 append-only immutable 구조이다.
7. deterministic execution을 유지해야 한다.
8. plugin write 영역은 plugin.<plugin_id>.* 로 제한된다.
9. working context schema는 고정된 key 구조를 따른다.
10. contract-driven architecture를 유지한다.
11. spec-version synchronization을 유지한다.

이 규칙을 위반하는 구현은 Nexa 아키텍처 위반으로 간주된다.


## 1. Foundation Layer

본 프로젝트의 기초 설계 문서는 다음 문서에 의해 계층적으로 관리된다:

- docs/FOUNDATION_MAP.md

구조 변경 또는 계약 변경 작업 시 반드시 FOUNDATION_MAP을 참조하고,
영향받는 문서들의 상태 및 SemVer를 확인해야 한다.

## 2. Active Specifications

현재 코드와 동기화되는 활성 spec 문서.

Source-of-Truth: `docs/specs/_active_specs.yaml`

### 2.1 Foundation / Terminology

- docs/specs/foundation/terminology.md

### 2.2 Architecture Core

- docs/specs/architecture/execution_model.md
- docs/specs/architecture/trace_model.md
- docs/specs/architecture/node_abstraction.md
- docs/specs/architecture/node_execution_contract.md
- docs/specs/architecture/circuit_contract.md
- docs/specs/architecture/universal_provider_architecture.md

### 2.3 Contracts

- docs/specs/contracts/execution_environment_contract.md
- docs/specs/contracts/provider_contract.md
- docs/specs/contracts/plugin_contract.md
- docs/specs/contracts/prompt_contract.md
- docs/specs/contracts/plugin_registry_contract.md
- docs/specs/contracts/validation_engine_contract.md
- docs/specs/contracts/execution_config_canonicalization_contract.md
- docs/specs/contracts/execution_config_schema_contract.md
- docs/specs/contracts/context_key_schema_contract.md

### 2.4 Policies

- docs/specs/policies/validation_rule_catalog.md
- docs/specs/policies/validation_rule_lifecycle.md

### 2.5 Indexes

- docs/specs/indexes/spec_catalog.md
- docs/specs/indexes/spec_dependency_map.md

### 2.6 ExecutionConfig

- docs/specs/execution_config_prompt_binding_contract.md
- docs/specs/execution_config_registry_contract.md

## 3. ExecutionConfig Architecture

Node type은 존재하지 않는다.

Node는 하나의 공통 실행 컨테이너이며,
행동 다양성은 ExecutionConfig 조합으로만 표현한다.

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
→ NodeExecutionRuntime

## 4. Regression Policy Architecture

contracts/regression_reason_codes.py  (single source of truth)
  ↓
engine/execution_regression_detector.py  (RegressionResult)
  ↓
engine/execution_regression_policy.py   (PolicyDecision: PASS/WARN/FAIL)
  ↓
formatter / CLI

Policy rules (default):
- HIGH severity regression → FAIL
- MEDIUM severity regression → WARN
- LOW severity / no regression → PASS
