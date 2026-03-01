# BLUEPRINT
Version: 1.0.0

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

구조/계약 변경 시 위 문서들과 코드, 테스트는 반드시 동기화되어야 한다.
