# Unified Node Abstraction
Version: 1.0.0
Status: Official Contract

Purpose:
Node의 구조/행동 계약을 정의한다.

## Contract
- node_id는 Engine 내에서 유일해야 한다.
- 입력/출력 스키마는 명시되어야 한다.
- v1: Sync-first, Pre/Core/Post 강제.
- v1: Pure-first(사이드이펙트 금지).
- 구조(Engine/Flow/Channel) 변경은 실행 중 금지.
- 실패는 구조화된 reason_code를 포함해야 한다(침묵 실패 금지).

## Validation Mapping
Enforced by: NODE-001..006, PIPE-001..005
