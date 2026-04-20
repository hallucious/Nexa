Spec ID: validation_rule_lifecycle
Version: 1.0.0
Status: Partial
Category: policies
Depends On:

# Validation Rule Lifecycle
Version: 1.0.0
Status: Official Contract

Purpose:
Defines lifecycle governance for rule_id in validation_rule_catalog.md.

---------------------------------------------------------------------
1. Rule Stability Principle
---------------------------------------------------------------------
- rule_id values are stable identifiers.
- Once introduced in Implemented Rules (Authoritative), they MUST NOT be reused
  for different semantics.

---------------------------------------------------------------------
2. Severity Change Policy
---------------------------------------------------------------------
- Changing severity (error ↔ warning) requires MINOR version bump
  of validation_rule_catalog.md.
- MAJOR bump required if behavioral semantics change (execution gating impact).

---------------------------------------------------------------------
3. Deprecation Policy
---------------------------------------------------------------------
- Deprecated rules MUST remain documented.
- Deprecation requires:
  - Marking rule as DEPRECATED in catalog notes.
  - Version bump (MINOR).
- Removal requires MAJOR version bump and new rule_id if semantics persist.

---------------------------------------------------------------------
4. Experimental Rules
---------------------------------------------------------------------
- Experimental rules MUST use prefix EXP-XXX.
- EXP rules are not allowed in Implemented Rules table.
- EXP rules must not block execution (severity cannot be error).

---------------------------------------------------------------------
5. Backward Compatibility
---------------------------------------------------------------------
- Minor/Patch updates must not alter existing rule semantics.
- Tests must prevent drift between:
  - validation_rule_catalog.md
  - validation_rule_lifecycle.md
  - runtime-facing version constants where applicable
