[DESIGN]
[UI_SECTION_BRANCH_RULES_SPEC v0.2]

1. PURPOSE

This document defines the parser / validator branch rules
for the `.nex.ui` section in Nexa.

Its purpose is to make the following boundary explicit and enforceable:

- `ui` is allowed for Working Save
- `ui` is excluded from Commit Snapshot by default
- `ui` must never become engine-owned truth
- parser / validator behavior must remain role-aware

This specification exists to connect:

- `.nex` unified top-level schema
- role-aware `.nex` parser / validator branching
- UI State Ownership & Persistence rules
- `.nex.ui` section schema rules

2. CORE DECISION

`ui` is a role-sensitive section.

It must be interpreted differently depending on `meta.storage_role`.

Official rule:

- `working_save` → `ui` allowed
- `commit_snapshot` → `ui` absent by default
- legacy or invalid role inference must not silently reinterpret `ui` as structural truth

3. CORE PRINCIPLES

3.1 Parser must resolve storage role before applying `ui` rules.
3.2 `ui` handling is validation-sensitive, not raw-parse-sensitive.
3.3 `ui` must never influence structural validity semantics.
3.4 `ui` warnings must remain UI-scoped.
3.5 `ui` branch rules must not break Working Save loadability.
3.6 `ui` presence in Commit Snapshot must not be silently normalized into approved truth.
3.7 Unknown `ui` content must fail soft unless a future strict mode explicitly tightens behavior.

4. ROLE RESOLUTION PRECONDITION

Before any `ui`-specific rule is applied, the loader must have already completed:

- JSON parse
- minimal top-level shape recognition
- `meta.storage_role` resolution

Role resolution follows existing `.nex` branch rules:

- explicit `storage_role` wins
- missing legacy `storage_role` defaults to `working_save`
- parser must not guess role from `ui` presence alone

5. BRANCH MATRIX

5.1 Working Save
- `ui` may be present
- `ui` may be absent
- invalid `ui` should usually produce findings, not artifact rejection
- stale `ui` references may be dropped during restore
- unsupported `ui` module state may degrade gracefully

5.2 Commit Snapshot
- `ui` should be absent
- `ui` presence is non-canonical
- validator should emit a role violation finding
- strict commit validation may reject it
- parser must not treat it as approved structural content

5.3 Unknown / unresolved role
- parser must not apply Working Save permissiveness blindly
- parser should stop at role-resolution failure before deeper `ui` interpretation

6. STAGE-BY-STAGE LOAD RULES

6.1 Raw Parse Stage
Rules:
- `ui` is treated as an ordinary JSON field during raw parse
- no role-specific meaning is applied yet
- malformed JSON fails before any `ui` logic exists

6.2 Top-Level Shape Stage
Rules:
- `ui` is never part of the shared required backbone
- required shared fields remain:
  - meta
  - circuit
  - resources
  - state
- missing `ui` must not fail backbone shape checks

6.3 Role Resolution Stage
Rules:
- parser resolves `meta.storage_role`
- `ui` presence must not alter role inference
- legacy `.nex` without `storage_role` defaults to `working_save`

6.4 Role-Specific Validation Stage
Rules:
- only here do `ui`-specific branch rules become active
- validator applies Working Save or Commit Snapshot rules accordingly

7. WORKING SAVE RULES

7.1 Presence Rule
`ui` may be present in Working Save.

Reason:
Working Save is the editable, always-saveable current-state artifact,
and UI continuity belongs naturally there.

7.2 Absence Rule
Missing `ui` is valid.

Reason:
A Working Save remains valid even if the shell chooses defaults.

7.3 Invalid UI Subsection Rule
If one or more `ui` subsections are invalid:

- structural validity must remain separate
- parser should still load the Working Save when possible
- validator should emit UI-scoped findings
- shell may ignore invalid subsections and restore defaults

7.4 Stale Reference Rule
If `ui.selection`, `ui.panels`, or similar sections reference missing objects:

- stale references may be dropped
- the artifact remains loadable
- a UI-scoped warning may be recorded

7.5 Unsupported Shell / Module State Rule
If `ui.shell_compatibility` points to an unsupported shell or module version:

- artifact remains loadable
- shell falls back best-effort
- no structural invalidity is implied

8. COMMIT SNAPSHOT RULES

8.1 Presence Rule
`ui` should be absent in Commit Snapshot.

Reason:
Commit Snapshot is approval-gated structural truth,
not editor workspace continuity.

8.2 Non-Canonical Presence Rule
If `ui` is present in a Commit Snapshot:

- validator must emit a role violation finding
- commit creation pipeline should reject or strip it before finalization
- parser must keep it non-authoritative if loaded for inspection/migration

8.3 No Silent Promotion Rule
`ui` content in Commit Snapshot must never be reinterpreted as:

- approval truth
- validation truth
- commit lineage truth
- structural metadata truth

8.4 Migration / Inspection Rule
If an old or imported snapshot contains `ui` accidentally:

- loader may preserve it for migration visibility
- but validator must mark it as non-canonical
- downstream commit logic must not re-emit it silently

9. FINDING CATEGORIES

The validator should classify `ui` issues separately from core structural blocking issues.

Recommended categories:

- UI_SECTION_INVALID
- UI_SECTION_STALE_REFERENCE
- UI_SECTION_UNSUPPORTED_SHELL
- UI_SECTION_ROLE_VIOLATION
- UI_SECTION_UNKNOWN_FIELD
- UI_SECTION_NON_CANONICAL_COMMIT_CONTENT

10. SEVERITY GUIDELINES

10.1 Working Save
Typical severities:
- stale reference → warning
- unsupported shell state → warning
- malformed optional subsection → warning or confirmation-required only if shell-critical
- forbidden truth crossover inside `ui` → blocked or high-severity warning depending on policy

10.2 Commit Snapshot
Typical severities:
- `ui` presence at all → role violation
- authoritative truth copied into `ui` → blocked
- harmless leftover shell hint → warning in migration mode, blocked in strict commit mode

11. FORBIDDEN TRUTH CROSSOVER CHECKS

Regardless of role, validator must inspect whether `ui` contains authoritative-looking copies of engine truth.

Examples that must be flagged:

- `ui.commit_is_approved = true`
- `ui.validation_status = "passed"` as authoritative source
- `ui.execution_output = ...` as truth source
- `ui.storage_role = "commit_snapshot"`
- `ui.trace_history = [...]` as authoritative execution history

Rules:
- such content is invalid because it blurs the UI/engine boundary
- in Working Save this is a serious finding
- in Commit Snapshot this should normally be blocking

12. COMMIT CREATION PIPELINE RULES

When converting Working Save → Commit Snapshot:

- `ui` must not cross the commit boundary by default
- commit builders should either:
  - drop `ui`, or
  - reject snapshot creation until `ui` is excluded

Preferred default:
- drop `ui` from the structural commit artifact
- preserve editor continuity only in Working Save lineage, not snapshot truth

13. LOAD API BEHAVIOR GUIDELINES

13.1 `load_nex()`
- may return a Working Save with UI findings
- may load a Commit Snapshot carrying non-canonical `ui` only for inspection/migration
- must surface findings explicitly

13.2 `validate_working_save()`
- tolerates `ui`
- emits UI-scoped findings without collapsing loadability

13.3 `validate_commit_snapshot()`
- treats `ui` presence as non-canonical
- should reject in strict approval/commit contexts

14. TYPED MODEL GUIDELINES

14.1 WorkingSaveModel
- may contain `ui: UISection | None`

14.2 CommitSnapshotModel
- should not expose authoritative `ui`
- if migration tooling temporarily preserves raw `ui`,
  it must be represented as non-canonical auxiliary data, not core snapshot state

15. EXAMPLE OUTCOMES

15.1 Valid Working Save
{
  "meta": {"storage_role": "working_save"},
  "circuit": {},
  "resources": {},
  "state": {},
  "ui": {
    "schema_version": "1.0.0",
    "panels": {"visible_panels": ["graph", "designer"]}
  }
}

Result:
- loadable
- valid as Working Save
- normal UI restore path

15.2 Valid Working Save Without UI
{
  "meta": {"storage_role": "working_save"},
  "circuit": {},
  "resources": {},
  "state": {}
}

Result:
- loadable
- valid as Working Save
- shell defaults apply

15.3 Non-Canonical Commit Snapshot
{
  "meta": {"storage_role": "commit_snapshot"},
  "circuit": {},
  "resources": {},
  "state": {},
  "validation": {},
  "approval": {},
  "lineage": {},
  "ui": {
    "schema_version": "1.0.0",
    "appearance": {"active_theme_id": "dark"}
  }
}

Result:
- parser may load for inspection
- validator emits UI_SECTION_ROLE_VIOLATION
- strict commit validation rejects

16. MINIMUM FIRST IMPLEMENTATION

The first implementation of these branch rules should support:

- role-aware `ui` handling after storage_role resolution
- Working Save `ui` permissive validation
- Commit Snapshot `ui` role violation detection
- forbidden truth crossover detection inside `ui`
- non-canonical commit-snapshot `ui` findings
- safe degradation for stale/unsupported Working Save UI state

17. FINAL DECISION

The `.nex.ui` section is officially a Working Save-oriented continuity section.

Parser and validator behavior must branch by storage role.

Any interpretation of `.nex.ui` as approved structural, validation, execution, or storage truth is invalid.

18. LOCALIZATION BRANCH RULES

18.1 Working Save
- `ui.preferences.app_language` is allowed
- `ui.preferences.locale` is allowed
- formatting preferences are allowed when UI-owned
- translated rendered message blobs are non-canonical and should be rejected or dropped

18.2 Commit Snapshot
- canonical `ui` remains absent by default
- canonical app-language / locale preference must not cross the commit boundary inside snapshot truth
- any snapshot-side raw localized UI payload is a role-violation finding, not canonical state

18.3 Validation should classify forbidden localized payloads separately from ordinary UI preference data.
