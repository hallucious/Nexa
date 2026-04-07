[DESIGN]
[VALIDATION_REASON_CODE_LOCALIZATION_SPEC v0.1]

1. PURPOSE

This document defines how validation reason codes are localized in Nexa UI.

Its purpose is to preserve strong diagnostic stability while still allowing human-readable multilingual presentation.

2. CORE DECISION

Validation reason codes remain canonical and machine-facing.
Localized text is a UI-facing projection of those codes.

3. CANONICAL BOUNDARY

Validator output keeps:
- reason_code
- severity
- target_ref
- finding category
- other structured fields

The validator does not emit translated truth as the canonical output.

4. UI RESOLUTION RULE

The UI resolves:
- localized finding title
- localized body text
- localized remediation hint
- localized severity label

from the canonical reason_code and related structured finding fields.

5. DEBUG / ADVANCED VIEW RULE

Advanced or diagnostic views may show both:
- localized message
- raw reason_code

This is preferred for expert transparency.

6. REASON CODE KEY MODEL

Preferred localization key style:
- validation.reason_code.<reason_code>.title
- validation.reason_code.<reason_code>.body
- validation.reason_code.<reason_code>.hint

Example concept:
- validation.reason_code.SUBCIRCUIT_CHILD_REF_NOT_FOUND.title

7. MISSING REASON-CODE LOCALIZATION

If localized text is missing for a known reason code:
- show fallback localized generic validation text if available
- otherwise show the raw reason_code visibly
- never silently hide the finding

8. SEVERITY LOCALIZATION

Severity categories such as blocked, warning, confirmation_required remain canonical internally and are localized only at presentation time.

9. STORAGE / EXECUTION BOUNDARY

Localized reason-code text must not be persisted as though it were the canonical validation result.
Canonical validation output remains language-neutral.

10. FINAL DECISION

Nexa validation must preserve stable reason_code truth and localize only the user-facing presentation layer.
