# FOUNDATION_MAP
Version: 1.0.0
Status: Canonical Foundation Index (Architecture Memory)

## 1. 목적
이 문서는 Hyper-AI의 기초 설계 문서를 계층 구조로 고정하고,
각 문서가 현재 코드/계약/개발 단계에서 어떤 역할과 상태를 갖는지 명시한다.

## 2. 사용 규칙
1) 문서는 **유효한 내용은 누적 유지**하고, 업데이트로 인해 **더 이상 적용되지 않는 내용은 삭제**한다.
   - Deprecations로 이동/이유/대체 규칙을 적는 절차는 필요하지 않다.

2) 구조 변경 또는 계약 변경 작업 시작 전, FOUNDATION_MAP에서 관련 문서의 상태/연관 영역을 확인한다.
3) 변경으로 인해 문서 내용이 달라져야 하면, 해당 문서의 SemVer를 올리고(문서 거버넌스 규칙 준수) BLUEPRINT의 활성 spec 목록을 갱신한다.
4) Planned 문서는 코드와 불일치해도 허용되지만, Active/Partial 문서는 코드/테스트와 가능한 한 동기화한다.

## 3. 문서 상태 정의
- Active: 코드/테스트/계약과 동기화된 정식 근거 문서
- Partial: 방향/스케치 수준. 일부만 코드/계약에 반영됨
- Planned: 아직 구현/계약 반영 전. 미래 확장 영역
- Deprecated: 더 이상 사용하지 않음(필요 시 문서에서 제거/대체 문서로 통합 가능)
---

# Layer 1. Doctrine (불변 철학 / 최상위 원칙)
| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| Strategic Direction & Evolution Policy | docs/Strategic Direction & Evolution Policy v1.0.md | Partial | 프로젝트의 진화 정책/방향성 | 전략/진화 정책 |
| Architectural Doctrine | docs/specs/Architectural Doctrine v1.0.md | Partial | 아키텍처 핵심 원칙/금기 | 전체 |
| determinism_policy | docs/specs/determinism_policy.md | Partial | 결정성/재현성 원칙 | 실행/Trace |
| terminology | docs/specs/terminology.md | Partial | 용어 정의(사용자/내부 공통) | 문서/UX |
| engine_constraints | docs/specs/engine_constraints.md | Partial | 엔진 제약 조건(그래프/실행 범위) | 엔진 |
| entry_policy | docs/specs/entry_policy.md | Partial | entry 관련 정책 | 엔진/검증 |

---

# Layer 2. Engine Core Contracts (핵심 실행 모델/추적/노드)
| 문서 | 경로 | 상태 | 설명 | 관련 코드/모듈(대표) |
|---|---|---:|---|---|
| node_abstraction | docs/specs/node_abstraction.md | Partial | 노드 추상화/역할 | src/engine/* (계약 영향) |
| node_execution_pipeline | docs/specs/node_execution_pipeline.md | Partial | 노드 실행 파이프라인(단계) | src/engine/engine.py (확장 예정) |
| execution_model | docs/specs/execution_model.md | Active | 실행 의미(상태 전파 포함) | src/engine/engine.py |
| trace_model | docs/specs/trace_model.md | Active | Trace 불변/커버리지 계약 | src/engine/trace.py |
| Execution State Model | docs/specs/Execution State Model v0.1.md | Planned | 실행 상태 모델(확장) | 추후 |
| Runtime Responsibility | docs/specs/Runtime Responsibility v0.1.md | Planned | 런타임 책임 분리(엔진/노드/외부) | 추후 |
| Subgraph & Reusable Module | docs/specs/Subgraph & Reusable Module v0.1.md | Planned | 서브그래프/모듈 재사용 | 추후 |

---

# Layer 3. Validation & Control (검증/정책/관측성)
| 문서 | 경로 | 상태 | 설명 | 관련 코드/모듈(대표) |
|---|---|---:|---|---|
| validation_engine_contract | docs/specs/validation_engine_contract.md | Active | Validation Engine 출력/동작 계약 | src/engine/validation/* |
| validation_rule_catalog | docs/specs/validation_rule_catalog.md | Active | rule_id 카탈로그 | src/engine/validation/* |
| Static Validation Rules | docs/specs/Static Validation Rules v0.2.md | Partial | 정적 규칙 설계(확장) | src/engine/validation/* |
| Policy Engine | docs/specs/Policy Engine v0.1.md | Planned | 정책 엔진(확장) | 추후 |
| side_effect_policy | docs/specs/side_effect_policy.md | Planned | 부작용/IO 정책 | 추후 |
| Observability & Metrics | docs/specs/Observability & Metrics v0.1.md | Partial | 관측성/메트릭 확장 | OBSERVABILITY.jsonl 등 |

---

# Layer 4. Product & Expansion (제품/UX/레지스트리/마이그레이션)
| 문서 | 경로 | 상태 | 설명 | 관련 영역 |
|---|---|---:|---|---|
| SaaS Product Definition | docs/specs/SaaS Product Definition v1.0.md | Planned | SaaS 제품 정의(후순위) | 제품 |
| Visual Editor Architecture | docs/specs/Visual Editor Architecture v0.1.md | Planned | 시각 편집기(후순위) | UX/UI |
| User Profile (Preset) | docs/specs/User Profile (Preset) v0.1.md | Planned | 사용자 프리셋/프로필 | UX/제품 |
| Definition Registry | docs/specs/Definition Registry v0.1.md | Planned | 정의/엔진 저장/불러오기(레지스트리) | 저장/공유 |
| Definition Versioning & Migration Strategy | docs/specs/Definition Versioning & Migration Strategy v0.1.md | Planned | 정의 버전/마이그레이션 전략 | 저장/공유 |
