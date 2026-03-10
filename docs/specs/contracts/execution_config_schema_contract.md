Spec ID: execution_config_schema_contract
Version: 1.0.0
Status: Partial
Category: contracts
Depends On:

# ExecutionConfig Schema Contract

Version: 1.0.0

## 목적

ExecutionConfig JSON을 registry 로드 전에 구조적으로 검증한다.

ExecutionConfig는 검증됨 / canonical / hashable / registry-managed 상태여야 하며,
schema validation은 registry resolution의 선행 조건이다.

## 최소 필수 필드

- config_id: string
- version: string

## 선택 필드

- prompt_ref: string
- provider_ref: string
- pre_plugins: list[string]
- post_plugins: list[string]
- validation_rules: list[string]
- output_mapping: dict[string, string]

## 타입 규칙

- pre_plugins는 list여야 한다.
- post_plugins는 list여야 한다.
- validation_rules는 list여야 한다.
- output_mapping은 dict여야 한다.

## 오류 정책

schema 위반 시 ExecutionConfigSchemaError를 발생시킨다.

## 실행 계층 내 위치

ExecutionConfig JSON
→ Schema Validation
→ Canonicalization / Hash
→ Registry Resolution
→ NodeExecutionRuntime
