# Node Execution Pipeline Specification (Pre/Core/Post)
Version: 1.0.0
Status: Official Contract

Purpose:
모든 Node가 따라야 하는 Pre/Core/Post 파이프라인을 정의한다.

## Rules
- Pre: 입력/정책/환경 검증
- Core: 주 기능 실행(부작용 금지)
- Post: 출력 검증 + 메타데이터/Trace 기록(실패 시에도 실행)

## Validation Mapping
Enforced by: PIPE-001..005
