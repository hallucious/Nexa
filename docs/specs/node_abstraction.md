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


---

# Archived Initial Version (Preserved)

# Unified Node Abstraction
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines the structural and behavioral contract of a Node.
All Engine execution depends on this abstraction.

----------------------------------------------------------------------
1. Core Principle

A Node is the smallest executable unit in an Engine.

All functional behavior must be encapsulated inside Nodes.
No logic may exist outside Nodes except Engine-level control rules.

----------------------------------------------------------------------

2. Identity

Each Node must:

- Have a unique node_id within the Engine.
- Have a stable identifier across revision unless structurally replaced.
- Be referenced by Channels and Flow rules.

node_id collision is forbidden.

----------------------------------------------------------------------

3. Input / Output Contract

Each Node must define:

- Input schema
- Output schema

Rules:

- Input schema must be explicit.
- Output schema must be explicit.
- Channel connections must satisfy type compatibility.
- Schema mutation during runtime is forbidden.

Schemas are structural contracts, not suggestions.

----------------------------------------------------------------------

4. Execution Model (v1 Constraint)

All Nodes must execute:

- Synchronously
- Deterministically by default
- Within Pre/Core/Post pipeline

Async execution is not allowed in v1.

----------------------------------------------------------------------

5. Pre/Core/Post Pipeline

Every Node execution must follow:

1. Pre
   - Input validation
   - Environment checks
   - Policy validation

2. Core
   - Main functional logic
   - Pure computation preferred

3. Post
   - Output validation
   - Metadata recording
   - Trace update

Skipping any stage is forbidden.

----------------------------------------------------------------------

6. Side Effect Policy

Default rule:

Nodes must be Pure.

Meaning:

- No external state mutation
- No file writes
- No network calls
- No database writes

Exception:

Future Action Node spec may explicitly allow controlled side effects.

----------------------------------------------------------------------

7. Isolation Rule

A Node:

- Cannot contain another Engine (v1 constraint)
- Cannot dynamically modify Engine structure during execution
- Cannot modify Flow rules

Nodes are execution units, not structural controllers.

----------------------------------------------------------------------

8. Error Handling

A Node must:

- Return structured result
- Return success/failure state
- Provide reason_code on failure
- Never silently fail

Unhandled exceptions are forbidden.

----------------------------------------------------------------------

9. Trace Integration

Each Node execution must record:

- Start time
- End time
- Execution duration
- Status (success/failure/skipped)
- Pre/Core/Post status
- Output snapshot (if allowed by policy)

Trace recording is mandatory.

----------------------------------------------------------------------

10. Determinism Recording

If randomness is used:

- Random seed must be recorded
- Model parameters must be recorded
- Temperature or stochastic variables must be recorded

Non-deterministic execution without recording is forbidden.

----------------------------------------------------------------------

Contract Rule:

Any Engine implementation violating this Node abstraction
is considered structurally invalid.

End of Node Abstraction Spec v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- NODE-001
- NODE-002
- NODE-003
- NODE-004
- NODE-005
- NODE-006
- PIPE-001
- PIPE-002
- PIPE-003
- PIPE-004
- PIPE-005