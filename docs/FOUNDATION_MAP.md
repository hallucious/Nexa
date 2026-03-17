# FOUNDATION_MAP
Version: 1.3.0
Status: Canonical Foundation Index (Architecture Memory)

## 1. 목적
이 문서는 Nexa 프로젝트의 foundation 문서 집합을 현재 실제 파일 구조 기준으로 고정하고,
각 문서가 코드/테스트/문서 거버넌스에서 어떤 역할을 가지는지 명시한다.

이 문서의 목적은 다음과 같다.

1. foundation 문서의 실제 경로를 단일 기준으로 고정
2. Active / Partial / Planned 상태를 명확히 구분
3. 문서 구조 변경 시 BLUEPRINT / spec catalog / 테스트와 동기화 기준 제공
4. 코드와 문서의 불일치 탐지 기준 제공

---

## 2. 사용 규칙

1. Active 문서는 현재 코드/테스트/거버넌스와 동기화된 공식 문서다.
2. Partial 문서는 방향성과 구조는 유효하지만 코드/테스트 반영이 일부만 완료된 문서다.
3. Planned 문서는 아직 구현/계약 반영 전의 미래 설계 문서다.
4. 문서 경로 변경 시 반드시 FOUNDATION_MAP, BLUEPRINT, 관련 테스트를 함께 갱신한다.
5. Active spec 목록의 최종 Source of Truth는 `docs/specs/_active_specs.yaml` 이다.
6. FOUNDATION_MAP의 Active 문서 경로는 현재 실제 파일 위치와 일치해야 한다.

---

## 3. 문서 상태 정의

- Active: 현재 코드/테스트/문서 계약과 동기화된 공식 기준 문서
- Partial: 유효한 설계 문서이지만 코드 또는 테스트 반영이 부분적임
- Planned: 미래 확장 또는 후속 구현을 위한 계획 문서

---

## 4. Deprecations 정책

- 유효한 내용은 항상 보존된다.
- obsolete 내용은 삭제된다.
- Nexa 문서 시스템에서는 deprecated 문서를 장기간 유지하지 않는다.
- obsolete 문서는 Deprecations 섹션으로 이동하지 않고 **삭제**하는 정책을 사용한다.
- 비활성 spec은 `docs/specs/_draft/` 디렉토리로 이동한다.

---

# Layer 1. Doctrine / Foundation

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| terminology | docs/specs/foundation/terminology.md | Active | 공식 용어집 | 문서 / 코드 / UX |

---

# Layer 2. Engine Core Contracts

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| execution_model | docs/specs/architecture/execution_model.md | Active | 공식 실행 모델 | src/engine/engine.py |
| trace_model | docs/specs/architecture/trace_model.md | Active | trace model 계약 | src/engine/trace.py |
| node_abstraction | docs/specs/architecture/node_abstraction.md | Active | node 추상화 | src/engine/* |
| node_execution_contract | docs/specs/architecture/node_execution_contract.md | Active | node 실행 계약 | src/engine/*, src/circuit/* |
| circuit_contract | docs/specs/architecture/circuit_contract.md | Active | Circuit 정의 계약 | src/circuit/*, src/engine/* |
| universal_provider_architecture | docs/specs/architecture/universal_provider_architecture.md | Active | universal provider 구조 | src/providers/* |

---

# Layer 3. Contracts / Runtime Integration

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| execution_environment_contract | docs/specs/contracts/execution_environment_contract.md | Active | 실행 환경 계약 | src/platform/*, src/providers/* |
| plugin_contract | docs/specs/contracts/plugin_contract.md | Active | plugin execution 계약 | src/platform/* |
| plugin_registry_contract | docs/specs/contracts/plugin_registry_contract.md | Active | plugin registry 계약 | src/platform/* |
| prompt_contract | docs/specs/contracts/prompt_contract.md | Active | prompt contract | src/prompts/* |
| provider_contract | docs/specs/contracts/provider_contract.md | Active | provider contract | src/providers/* |
| validation_engine_contract | docs/specs/contracts/validation_engine_contract.md | Active | validation engine contract | src/engine/validation/* |
| execution_config_canonicalization_contract | docs/specs/contracts/execution_config_canonicalization_contract.md | Active | execution config canonicalization 계약 | src/contracts/* |
| execution_config_schema_contract | docs/specs/contracts/execution_config_schema_contract.md | Active | execution config schema 계약 | src/contracts/* |
| context_key_schema_contract | docs/specs/contracts/context_key_schema_contract.md | Active | working context key schema 계약 | src/contracts/context_key_schema.py |

---

# Layer 4. Validation / Policy

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| validation_rule_catalog | docs/specs/policies/validation_rule_catalog.md | Active | validation rule catalog | src/engine/validation/* |
| validation_rule_lifecycle | docs/specs/policies/validation_rule_lifecycle.md | Active | validation rule lifecycle | src/engine/validation/* |

---

# Layer 5. Indexes / Catalogs

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| spec_catalog | docs/specs/indexes/spec_catalog.md | Active | 전체 spec catalog | 문서 거버넌스 |
| spec_dependency_map | docs/specs/indexes/spec_dependency_map.md | Active | spec dependency map | 문서 거버넌스 |

---

# Layer 6. ExecutionConfig Specs

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| execution_config_prompt_binding_contract | docs/specs/execution_config_prompt_binding_contract.md | Active | execution config ↔ prompt binding 계약 | src/contracts/* |
| execution_config_registry_contract | docs/specs/execution_config_registry_contract.md | Active | execution config registry 계약 | src/contracts/* |

---

## Active Foundation Docs
아래 문서는 현재 기준으로 Active 상태이며, 실제 파일 경로와 반드시 일치해야 한다.

- docs/specs/foundation/terminology.md
- docs/specs/contracts/execution_environment_contract.md
- docs/specs/architecture/circuit_contract.md
- docs/specs/architecture/node_abstraction.md
- docs/specs/architecture/node_execution_contract.md
- docs/specs/architecture/execution_model.md
- docs/specs/architecture/trace_model.md
- docs/specs/architecture/universal_provider_architecture.md
- docs/specs/contracts/plugin_contract.md
- docs/specs/contracts/plugin_registry_contract.md
- docs/specs/contracts/prompt_contract.md
- docs/specs/contracts/provider_contract.md
- docs/specs/contracts/validation_engine_contract.md
- docs/specs/policies/validation_rule_catalog.md
- docs/specs/policies/validation_rule_lifecycle.md
- docs/specs/indexes/spec_catalog.md
- docs/specs/indexes/spec_dependency_map.md
- docs/specs/contracts/execution_config_canonicalization_contract.md
- docs/specs/contracts/context_key_schema_contract.md
- docs/specs/contracts/execution_config_schema_contract.md
- docs/specs/execution_config_prompt_binding_contract.md
- docs/specs/execution_config_registry_contract.md

---

## Sync Notes

1. `docs/specs/_active_specs.yaml` 은 Active spec 목록의 최종 기준이다. 테스트가 이 파일을 읽는다.
2. FOUNDATION_MAP의 Active 항목은 `_active_specs.yaml` 과 논리적으로 일치해야 한다.
3. 비활성 spec은 repository에서 제거되며, active spec만 유지된다
4. 인코딩은 반드시 UTF-8로 저장한다.
