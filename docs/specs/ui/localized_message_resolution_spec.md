[DESIGN]
[LOCALIZED_MESSAGE_RESOLUTION_SPEC v0.1]

1. PURPOSE

This document defines how Nexa resolves localized user-facing messages from stable machine-facing sources.

Its purpose is to keep message rendering understandable for users while preserving stable internal identifiers for runtime, validation, and storage logic.

2. CORE DECISION

User-facing messages must be resolved from canonical machine-facing values.
Canonical values themselves must remain untranslated in engine truth.

3. RESOLUTION INPUTS

Message resolution may start from:
- reason_code
- severity
- status value
- storage role
- action type
- generic UI message key

4. RESOLUTION FLOW

Canonical source
→ localization lookup key
→ locale bundle lookup
→ fallback behavior
→ rendered user-facing message

5. REASON CODE RULE

Reason codes remain stable machine-facing identifiers.
They must not be replaced by translated strings in engine/storage truth.

6. STATUS LABEL RULE

Status values such as blocked, warning, approved, running, completed must remain canonical internally.
UI may render localized labels for them.

7. CONTEXTUAL MESSAGE SHAPE

When needed, message resolution may include:
- title
- body
- help hint
- next action hint

These remain UI-facing projections, not engine-owned truth.

8. PLACEHOLDER RULE

If a message uses placeholders:
- placeholders come from canonical fields
- localization controls phrasing, not source-of-truth semantics

9. NON-GOAL

This system does not translate raw user-authored content or arbitrary machine literals.
It resolves standardized product-facing messages.

10. FINAL DECISION

Localized messages in Nexa must be resolved from stable canonical values through a UI-owned message-resolution layer.
