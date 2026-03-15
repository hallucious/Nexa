# FOUNDATION_MAP
Version: 1.1.0
Status: Canonical Foundation Index (Architecture Memory)

## 1. 목적
이 문서는 Nexa 프로젝트의 foundation 문서 집합을 현재 실제 파일 구조 기준으로 고정하고,
각 문서가 코드/테스트/문서 거버넌스에서 어떤 역할을 가지는지 명시한다.

이 문서의 목적은 다음과 같다.

1. foundation 문서의 실제 경로를 단일 기준으로 고정
2. Active / Partial / Planned / Deprecated 상태를 명확히 구분
3. 문서 구조 변경 시 BLUEPRINT / spec catalog / 테스트와 동기화 기준 제공
4. 코드와 문서의 불일치 탐지 기준 제공

---

## 2. 사용 규칙

1. Active 문서는 현재 코드/테스트/거버넌스와 동기화된 공식 문서다.
2. Partial 문서는 방향성과 구조는 유효하지만 코드/테스트 반영이 일부만 완료된 문서다.
3. Planned 문서는 아직 구현/계약 반영 전의 미래 설계 문서다.
4. Deprecated 문서는 더 이상 기준 문서로 사용하지 않는다.
5. 문서 경로 변경 시 반드시 FOUNDATION_MAP, BLUEPRINT, 관련 테스트를 함께 갱신한다.
6. Active spec 목록의 최종 Source of Truth는 `docs/specs/indexes/_active_specs.yaml` 이다.
7. FOUNDATION_MAP의 Active 문서 경로는 현재 실제 파일 위치와 일치해야 한다.

---

## 3. 문서 상태 정의

- Active: 현재 코드/테스트/문서 계약과 동기화된 공식 기준 문서
- Partial: 유효한 설계 문서이지만 코드 또는 테스트 반영이 부분적임
- Planned: 미래 확장 또는 후속 구현을 위한 계획 문서
- Deprecated: 더 이상 기준으로 사용하지 않는 문서

---

## 4. Deprecations 정책

- 유효한 내용은 항상 보존된다.
- obsolete 내용은 삭제된다.
- Nexa 문서 시스템에서는 deprecated 문서를 장기간 유지하지 않는다.  
- obsolete 문서는 Deprecations 섹션으로 이동하지 않고 **삭제**하는 정책을 사용한다.

---

# Layer 1. Doctrine / Foundation

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| Strategic Direction & Evolution Policy | docs/STRATEGY.md | Partial | 프로젝트 장기 방향과 진화 정책 | 전략 / 진화 |
| architectural_doctrine | docs/specs/foundation/architectural_doctrine.md | Partial | 상위 아키텍처 원칙과 doctrine | 전체 구조 |
| terminology | docs/specs/foundation/terminology.md | Active | 공식 용어집 | 문서 / 코드 / UX |
| runtime_responsibility | docs/specs/foundation/runtime_responsibility.md | Partial | 런타임 책임 분리 원칙 | 엔진 / 런타임 |
| definition_registry | docs/specs/foundation/definition_registry.md | Partial | 정의 레지스트리 개념 | registry / loading |
| definition_versioning_and_migration_strategy | docs/specs/foundation/definition_versioning_and_migration_strategy.md | Partial | 정의 버전 및 마이그레이션 전략 | versioning / migration |
| determinism_policy | docs/specs/policies/determinism_policy.md | Partial | 결정성 및 재현성 정책 | 실행 / trace |
| engine_constraints | docs/specs/policies/engine_constraints.md | Partial | 엔진 제약 조건 | 엔진 코어 |
| entry_policy | docs/specs/policies/entry_policy.md | Partial | 엔트리 정책 | bootstrap / entry |
| execution_environment_contract | docs/specs/contracts/execution_environment_contract.md | Active | 실행 환경 계약 | src/platform/*, src/providers/* |

---

# Layer 2. Engine Core Contracts

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| circuit_contract | docs/specs/architecture/circuit_contract.md | Active | Circuit 정의 계약 | src/circuit/*, src/engine/* |
| circuit_runtime_model | docs/specs/architecture/circuit_runtime_model.md | Partial | circuit runtime model | src/circuit/* |
| compiled_resource_graph_contract | docs/specs/architecture/compiled_resource_graph_contract.md | Partial | compiled resource graph 계약 | src/engine/* |
| context_key_schema | docs/specs/architecture/context_key_schema.md | Partial | working context key schema | src/engine/* |
| Execution State Model | docs/specs/architecture/Execution State Model.md | Planned | 실행 상태 모델 확장 | 추후 |
| execution_model | docs/specs/architecture/execution_model.md | Active | 공식 실행 모델 | src/engine/engine.py |
| graph_execution_contract | docs/specs/architecture/graph_execution_contract.md | Partial | graph execution 계약 | src/engine/graph_execution_runtime.py |
| node_abstraction | docs/specs/architecture/node_abstraction.md | Active | node 추상화 | src/engine/* |
| node_execution_contract | docs/specs/architecture/node_execution_contract.md | Active | node 실행 계약 | src/engine/*, src/circuit/* |
| node_runtime_architecture | docs/specs/architecture/node_runtime_architecture.md | Partial | node runtime 구조 | src/engine/node_execution_runtime.py |
| Subgraph & Reusable Module | docs/specs/architecture/Subgraph & Reusable Module.md | Planned | subgraph / reusable module | 추후 |
| trace_model | docs/specs/architecture/trace_model.md | Active | trace model 계약 | src/engine/trace.py |
| universal_provider_architecture | docs/specs/architecture/universal_provider_architecture.md | Active | universal provider 구조 | src/providers/* |
| working_context_contract | docs/specs/architecture/working_context_contract.md | Partial | shared working context 계약 | src/engine/* |

---

# Layer 3. Contracts / Runtime Integration

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| drift_detector_contract | docs/specs/contracts/drift_detector_contract.md | Partial | drift detector 계약 | src/engine/drift_detector.py |
| execution_config_canonicalization_contract | docs/specs/contracts/execution_config_canonicalization_contract.md | Active | execution config canonicalization 계약 | src/contracts/* |
| execution_config_schema_contract | docs/specs/contracts/execution_config_schema_contract.md | Active | execution config schema 계약 | src/contracts/* |
| plugin_contract | docs/specs/contracts/plugin_contract.md | Active | plugin execution 계약 | src/platform/* |
| plugin_executor_contract | docs/specs/contracts/plugin_executor_contract.md | Partial | plugin executor 계약 | src/platform/* |
| plugin_registry_contract | docs/specs/contracts/plugin_registry_contract.md | Active | plugin registry 계약 | src/platform/* |
| prompt_contract | docs/specs/contracts/prompt_contract.md | Active | prompt contract | src/prompts/* |
| provider_contract | docs/specs/contracts/provider_contract.md | Active | provider contract | src/providers/* |
| validation_engine_contract | docs/specs/contracts/validation_engine_contract.md | Active | validation engine contract | src/engine/validation/* |

---

# Layer 4. Validation / Policy / Observability

| 문서 | 경로 | 상태 | 설명 | 관련 코드 / 모듈 |
|---|---|---:|---|---|
| docs_specs_circuit_trace_contract | docs/specs/history/docs_specs_circuit_trace_contract.md | Partial | circuit trace history / contract lineage | src/circuit/trace.py |
| node_execution_pipeline | docs/specs/history/node_execution_pipeline.md | Partial | node execution pipeline history | src/engine/* |
| pipeline_test_migration_plan | docs/specs/history/pipeline_test_migration_plan.md | Partial | legacy test migration 계획 | tests/* |
| legacy_removal_plan | docs/specs/history/legacy_removal_plan.md | Partial | legacy 제거 계획 | migration / cleanup |
| observability_and_metrics | docs/specs/policies/observability_and_metrics.md | Partial | observability 방향 문서 | observability |
| observability_metrics | docs/specs/policies/observability_metrics.md | Partial | observability metrics 계약 | src/utils/observability.py |
| policy_engine | docs/specs/policies/policy_engine.md | Planned | policy engine 설계 | 추후 |
| safe_replay_contract | docs/specs/policies/safe_replay_contract.md | Partial | safe replay 계약 | src/engine/safe_replay.py |
| side_effect_policy | docs/specs/policies/side_effect_policy.md | Partial | side effect 정책 | runtime / IO |
| static_validation_rules | docs/specs/policies/static_validation_rules.md | Partial | static validation rules 설계 | src/engine/validation/* |
| validation_rule_catalog | docs/specs/policies/validation_rule_catalog.md | Active | validation rule catalog | src/engine/validation/* |
| validation_rule_lifecycle | docs/specs/policies/validation_rule_lifecycle.md | Active | validation rule lifecycle | src/engine/validation/* |

---

# Layer 5. Indexes / Catalogs

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| spec_catalog | docs/specs/indexes/spec_catalog.md | Active | 전체 spec catalog | 문서 거버넌스 |
| spec_dependency_map | docs/specs/indexes/spec_dependency_map.md | Active | spec dependency map | 문서 거버넌스 |

---

# Layer 6. Additional Specs (Top-level under docs/specs)

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| circuit_savefile_contract | docs/specs/circuit_savefile_contract.md | Partial | circuit savefile 계약 | serialization |
| engine_savefile_contract | docs/specs/engine_savefile_contract.md | Partial | engine savefile 계약 | serialization |
| execution_config_prompt_binding_contract | docs/specs/execution_config_prompt_binding_contract.md | Active | execution config ↔ prompt binding 계약 | src/contracts/* |
| execution_config_registry_contract | docs/specs/execution_config_registry_contract.md | Active | execution config registry 계약 | src/contracts/* |
| provider_abstraction_contract | docs/specs/history/redundant/provider_abstraction_contract.md | Partial | provider abstraction 초안 문서 | providers |

---

# Layer 7. Product / Expansion

| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| SaaS Product Definition | docs/product/SaaS Product Definition.md | Planned | SaaS 제품 정의 | 제품 |
| User Profile (Preset) | docs/product/User Profile (Preset).md | Planned | 사용자 프로필 / preset | UX / 제품 |
| Visual Editor Architecture | docs/product/Visual Editor Architecture.md | Planned | visual editor 구조 | UX / UI |

---

## 4. Active Foundation Docs
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

---

## 5. Sync Notes

1. `docs/specs/indexes/_active_specs.yaml` 은 Active spec 목록의 최종 기준이다.
2. FOUNDATION_MAP의 Active 항목은 `_active_specs.yaml` 과 논리적으로 일치해야 한다.
3. 경로 이동이 발생하면 다음 세 곳을 함께 갱신한다.
   - `docs/FOUNDATION_MAP.md`
   - `docs/BLUEPRINT.md`
   - 관련 문서 계약 테스트
4. 인코딩은 반드시 UTF-8로 저장한다.