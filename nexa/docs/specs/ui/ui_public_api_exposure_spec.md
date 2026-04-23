[DESIGN]
[UI_PUBLIC_API_EXPOSURE_SPEC v0.2]

1. PURPOSE

This document defines how the `.nex.ui` section is exposed
through the public loading and validation API surface in Nexa.

Its purpose is to make the following boundary explicit at the API level:

- `load_nex()` may expose canonical `ui` only for Working Save
- `validate_working_save()` may validate and report on `ui`
- `validate_commit_snapshot()` must not accept canonical snapshot-side `ui`
- callers must not infer UI authority from raw field presence
- public return types must preserve role-aware `ui` semantics

This specification exists to connect:

- `.nex` unified load/validate API
- role-aware typed model construction
- `.nex.ui` schema
- `ui` section branch rules
- `WorkingSaveModel` vs `CommitSnapshotModel` binding rules

2. CORE DECISION

The public API must expose `ui` by role, not by convenience.

Official rule:

- Working Save → canonical `ui` may be returned
- Commit Snapshot → canonical `ui` must not be returned
- non-canonical snapshot-side `ui` may appear only as findings and optional migration auxiliary data

3. CORE PRINCIPLES

3.1 Public APIs must preserve storage-role semantics.
3.2 API consumers must not need to guess whether `ui` is authoritative.
3.3 `ui` exposure must never blur editor continuity and structural truth.
3.4 Validation APIs must classify `ui` findings separately from core engine truth.
3.5 Snapshot approval/commit APIs must remain stricter than general load APIs.
3.6 Legacy compatibility must not silently normalize invalid `ui` usage.
3.7 API ergonomics must not override ownership boundaries.

4. RELEVANT PUBLIC API SURFACE

Canonical public functions:

- load_nex(...)
- validate_working_save(...)
- validate_commit_snapshot(...)

Optional later helpers may exist, but the canonical rule must remain centered on these three entrypoints.

5. CANONICAL RETURN TYPES

5.1 LoadedNexArtifact

LoadedNexArtifact
- storage_role: Literal["working_save", "commit_snapshot"]
- parsed_model: WorkingSaveModel | CommitSnapshotModel
- findings: list[ValidationFinding]
- load_status: Literal["loaded", "loaded_with_findings", "rejected"]
- source_path: str | None
- migration_notes: list[str] | None
- non_canonical_aux: dict | None

Rules:
- `storage_role` is mandatory
- `parsed_model` type must already reflect role-aware construction
- `non_canonical_aux` is optional and never authoritative

5.2 ValidationReport

ValidationReport
- role: Literal["working_save", "commit_snapshot"]
- findings: list[ValidationFinding]
- blocking_count: int
- warning_count: int
- result: Literal["pass", "pass_with_findings", "blocked"]

Rules:
- validation report role must be explicit
- UI findings may be included, but must stay role-aware
- result semantics must not be altered by UI convenience logic

6. load_nex() EXPOSURE RULES

6.1 Working Save input with valid `ui`

Input:
- role = working_save
- valid `ui`

Result:
- `storage_role = "working_save"`
- `parsed_model = WorkingSaveModel(..., ui=UISection(...))`
- `findings` may be empty or include non-blocking UI warnings
- `load_status = "loaded"` or `loaded_with_findings`

6.2 Working Save input without `ui`

Result:
- `storage_role = "working_save"`
- `parsed_model = WorkingSaveModel(..., ui=None)`
- shell defaults remain possible

6.3 Working Save input with invalid / partial `ui`

Result:
- Working Save should still load when possible
- valid subsections may bind partially
- invalid subsections may be dropped or nullified
- `findings` must record UI-scoped issues
- structural role remains Working Save

6.4 Commit Snapshot input without `ui`

Result:
- `storage_role = "commit_snapshot"`
- `parsed_model = CommitSnapshotModel(...)`
- no canonical `ui` is returned

6.5 Commit Snapshot input with raw non-canonical `ui`

Result:
- `storage_role = "commit_snapshot"`
- `parsed_model = CommitSnapshotModel(...)`
- `findings` includes `UI_SECTION_ROLE_VIOLATION` or equivalent
- `non_canonical_aux["raw_ui_section"]` may optionally preserve original data for migration/inspection
- no canonical snapshot `ui` is exposed through `parsed_model`

7. validate_working_save() RULES

7.1 Purpose
`validate_working_save()` validates editable present-state artifacts.

7.2 `ui` treatment
- `ui` is allowed
- missing `ui` is valid
- stale or invalid `ui` should normally not block loadability by itself
- forbidden truth crossover inside `ui` may escalate severity appropriately

7.3 Findings
Recommended finding families:
- UI_SECTION_INVALID
- UI_SECTION_STALE_REFERENCE
- UI_SECTION_UNSUPPORTED_SHELL
- UI_SECTION_UNKNOWN_FIELD
- UI_FORBIDDEN_TRUTH_CROSSOVER

7.4 Result semantics
- ordinary UI continuity issues usually produce warnings
- severe truth-crossover inside `ui` may produce blocked status if policy demands
- validator must still distinguish UI findings from structural/approval/execution findings

8. validate_commit_snapshot() RULES

8.1 Purpose
`validate_commit_snapshot()` validates approved structural snapshot artifacts.

8.2 `ui` treatment
- canonical snapshot-side `ui` is not allowed
- any raw `ui` presence is non-canonical
- snapshot validation must be stricter than Working Save validation

8.3 Findings
Recommended finding families:
- UI_SECTION_ROLE_VIOLATION
- UI_SECTION_NON_CANONICAL_COMMIT_CONTENT
- UI_FORBIDDEN_TRUTH_CROSSOVER

8.4 Result semantics
- harmless migration residue may be warning-only in non-strict inspection mode
- strict approval/commit contexts should reject snapshot-side `ui`
- authoritative-looking truth copies inside `ui` should be blocking

9. ROLE-AWARE ACCESS PATTERNS

API consumers must branch on role explicitly.

Correct pattern:

if artifact.storage_role == "working_save":
    ui = artifact.parsed_model.ui
else:
    ui = None

Incorrect pattern:

if hasattr(artifact.parsed_model, "ui"):
    ...

Reason:
public behavior must depend on role semantics, not incidental field probing.

10. EDITOR CONSUMER RULES

10.1 Working Save editors
- may consume `WorkingSaveModel.ui`
- must tolerate `ui=None`
- may use findings to decide whether to restore partially or reset to defaults

10.2 Snapshot inspectors
- must not assume snapshot UI continuity
- should inspect `non_canonical_aux` only for migration/debug tooling if exposed
- must not present snapshot-side raw `ui` as canonical saved workspace state

11. COMMIT BUILDER / SNAPSHOT CREATOR RULES

Any API that turns a Working Save into a Commit Snapshot must follow:

- read from `WorkingSaveModel`
- ignore or strip canonical `ui`
- validate resulting snapshot without `ui`
- never copy `WorkingSaveModel.ui` into `CommitSnapshotModel`

If a caller tries to force snapshot-side `ui`,
the API should:
- reject the attempt, or
- drop `ui` and emit explicit notes/findings

12. AUXILIARY MIGRATION EXPOSURE RULES

Public APIs may optionally expose auxiliary migration data.

Allowed example:
LoadedNexArtifact.non_canonical_aux = {
  "raw_ui_section": {...},
  "preservation_reason": "snapshot carried non-canonical ui"
}

Rules:
- auxiliary exposure must be explicitly labeled non-canonical
- auxiliary data must not be merged into `parsed_model`
- normal editor/runtime consumers should not rely on it

13. ERROR / FINDING PRESENTATION RULES

Public APIs should make `ui` findings inspectable without overstating them.

Recommended guidance:
- keep UI-specific finding codes distinct
- do not report UI panel/layout issues as structural graph errors
- do not hide forbidden truth crossover inside generic warnings
- surface role-violation findings explicitly

14. EXAMPLE API OUTCOMES

14.1 load_nex() on valid Working Save

Return:
LoadedNexArtifact(
  storage_role="working_save",
  parsed_model=WorkingSaveModel(..., ui=UISection(...)),
  findings=[],
  load_status="loaded",
)

14.2 load_nex() on Working Save with stale UI references

Return:
LoadedNexArtifact(
  storage_role="working_save",
  parsed_model=WorkingSaveModel(..., ui=partial_or_none),
  findings=[UI_SECTION_STALE_REFERENCE, ...],
  load_status="loaded_with_findings",
)

14.3 load_nex() on clean Commit Snapshot

Return:
LoadedNexArtifact(
  storage_role="commit_snapshot",
  parsed_model=CommitSnapshotModel(...),
  findings=[],
  load_status="loaded",
)

14.4 load_nex() on non-canonical Commit Snapshot carrying `ui`

Return:
LoadedNexArtifact(
  storage_role="commit_snapshot",
  parsed_model=CommitSnapshotModel(...),
  findings=[UI_SECTION_ROLE_VIOLATION],
  load_status="loaded_with_findings",
  non_canonical_aux={"raw_ui_section": {...}},
)

15. STRICT VS INSPECTION MODE GUIDELINES

15.1 Inspection mode
Goal:
- allow legacy/migration visibility
- surface findings
- avoid silent normalization

Behavior:
- non-canonical snapshot `ui` may be preserved in auxiliary data
- artifact may still load for inspection

15.2 Strict approval / commit mode
Goal:
- guarantee canonical snapshot artifacts

Behavior:
- snapshot-side `ui` should cause rejection or forced stripping before snapshot finalization
- public API should make this behavior explicit

16. MINIMUM FIRST IMPLEMENTATION

The first implementation of this API exposure rule should support:

- `load_nex()` role-aware canonical `ui` exposure
- `validate_working_save()` UI-aware findings
- `validate_commit_snapshot()` snapshot-side `ui` role violation handling
- `LoadedNexArtifact.non_canonical_aux` optional path
- explicit role-based consumer guidance
- strict-vs-inspection distinction for snapshot-side `ui`

17. FINAL DECISION

The public Nexa load/validate API must expose `.nex.ui`
only as canonical typed state for Working Save artifacts.

Commit Snapshot artifacts must remain free of canonical `ui`
at the public API level.

Any public API behavior that makes snapshot-side `ui`
look authoritative is invalid.

18. LOCALIZATION API EXPOSURE RULES

18.1 `load_nex()` may expose canonical UI-owned app-language / locale preference only for Working Save.

18.2 `validate_working_save()` may return findings about invalid locale/app-language preference values or forbidden rendered-string payloads.

18.3 `validate_commit_snapshot()` must not expose canonical snapshot-side locale/UI preference as authoritative data.

18.4 Public APIs must preserve the distinction between:
- canonical locale/app-language preference
- non-canonical rendered localized payloads
- separate AI response language policy outside `.nex.ui`
