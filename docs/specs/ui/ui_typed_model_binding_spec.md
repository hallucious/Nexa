[DESIGN]
[UI_TYPED_MODEL_BINDING_SPEC v0.1]

1. PURPOSE

This document defines how the `.nex.ui` section is bound
to the in-memory typed model layer in Nexa.

Its purpose is to make the following model-level boundary explicit:

- `WorkingSaveModel` may contain `ui`
- `CommitSnapshotModel` must not contain authoritative `ui`
- `LoadedNexArtifact` must preserve storage-role clarity
- migration or inspection paths must not blur UI-owned state into engine-owned truth

This specification exists to connect:

- `.nex` unified top-level schema
- `.nex.ui` schema
- `ui` branch rules
- role-aware typed model construction

2. CORE DECISION

The typed model family must preserve the same rule already fixed at schema
and parser/validator level:

- `working_save` → `ui` allowed as typed UI-owned state
- `commit_snapshot` → `ui` excluded from authoritative core typed state

This means the `ui` section is not a generic shared typed field.
It is role-bound.

3. CORE PRINCIPLES

3.1 Typed models must preserve UI/engine ownership boundaries.
3.2 Shared top-level field shape must not override semantic role boundaries.
3.3 `ui` belongs to editable continuity state, not approved structural truth.
3.4 Typed model convenience must not reintroduce forbidden truth crossover.
3.5 Migration handling may preserve raw data temporarily, but never as authoritative role truth.
3.6 Downstream consumers must not need to guess whether `ui` is authoritative.
3.7 The model layer must remain explicit enough for editor, validator, and commit builder code.

4. MODEL FAMILY OVERVIEW

The relevant model family is:

LoadedNexArtifact
├─ storage_role
├─ parsed_model
│  ├─ WorkingSaveModel
│  └─ CommitSnapshotModel
├─ findings
└─ load_status

Within that family:

- `WorkingSaveModel` is the editable present-state model
- `CommitSnapshotModel` is the approved structural snapshot model
- `LoadedNexArtifact` is the explicit role-aware wrapper

5. ROLE BINDING RULE

The `ui` section must bind by role, not by mere field presence.

Canonical rule:

5.1 Working Save
`ui` may bind into a typed `UISection | None`

5.2 Commit Snapshot
`ui` must not bind into the authoritative `CommitSnapshotModel` core

5.3 Legacy / migration inspection
raw non-canonical `ui` may be preserved only in auxiliary migration space,
not in the canonical snapshot model surface

6. WORKINGSAVEMODEL RULES

6.1 Canonical shape

WorkingSaveModel
- meta: WorkingSaveMeta
- circuit: CircuitModel
- resources: ResourcesModel
- state: StateModel
- runtime: RuntimeSection | None
- ui: UISection | None
- designer: DesignerSection | None

6.2 Meaning of `ui`
In `WorkingSaveModel`, `ui` means:

- editor continuity
- panel/layout restore
- selection/filter restore
- shell compatibility hints
- appearance/layout restore
- lightweight session continuity

6.3 Rules
- `ui=None` is valid
- invalid `ui` may degrade to findings + `ui=None` or partial typed restore
- `ui` must remain explicitly UI-owned
- `ui` must not affect structural semantics inside `WorkingSaveModel`

7. COMMITSNAPSHOTMODEL RULES

7.1 Canonical shape

CommitSnapshotModel
- meta: CommitMeta
- circuit: CircuitModel
- resources: ResourcesModel
- state: StateBaselineModel
- validation: CommitValidationSection
- approval: CommitApprovalSection
- lineage: CommitLineageSection

7.2 No canonical `ui`
`CommitSnapshotModel` must not contain a canonical `ui: UISection | None` field.

Reason:
Commit Snapshot represents approved structural state,
not editor workspace continuity.

7.3 Rules
- absence of `ui` in canonical snapshot model is intentional
- snapshot consumers must not expect UI continuity data
- commit builders must not copy `ui` into canonical snapshot typed state

8. AUXILIARY MIGRATION HANDLING

Some loaders or migration tools may temporarily encounter a `.nex` artifact
with:

- `storage_role = commit_snapshot`
- but also a raw `ui` field present

In that case, the typed model layer may preserve such data only as
non-canonical auxiliary migration content.

Example auxiliary shape:

NonCanonicalAuxiliaryData
- raw_ui_section: dict | None
- migration_notes: list[str]
- preservation_reason: str | None

Rules:
- auxiliary preservation is for inspection/migration only
- auxiliary `raw_ui_section` is not part of canonical snapshot truth
- downstream engine/editor logic must not consume it as normal snapshot state

9. LOADEDNEXARTIFACT WRAPPER RULES

LoadedNexArtifact
- storage_role: Literal["working_save", "commit_snapshot"]
- parsed_model: WorkingSaveModel | CommitSnapshotModel
- findings: list[ValidationFinding]
- load_status: Literal["loaded", "loaded_with_findings", "rejected"]
- source_path: str | None
- migration_notes: list[str] | None
- non_canonical_aux: dict | None

Rules:
- wrapper makes role explicit
- callers must branch on `storage_role`, not inspect for `ui` field guessing
- `non_canonical_aux` must never silently merge into `parsed_model`

10. TYPE CONSTRUCTION RULES

10.1 If role = working_save
- parse `ui` using UISection schema
- construct `WorkingSaveModel.ui`
- attach UI-scoped findings if needed

10.2 If role = commit_snapshot and no raw `ui`
- construct canonical `CommitSnapshotModel`
- no UI binding path exists

10.3 If role = commit_snapshot and raw `ui` exists
- do not bind to canonical snapshot core
- emit non-canonical role-violation finding
- optionally preserve raw data in auxiliary migration space

11. PARTIAL UI RESTORE RULES

For `WorkingSaveModel`, partial `ui` binding is allowed when safe.

Examples:
- panel state valid, selection stale
- theme/layout valid, shell compatibility unsupported
- viewport valid, trace filter state unknown

Preferred behavior:
- bind valid subsections
- drop invalid/stale subsections
- emit UI-scoped findings

This keeps Working Save ergonomics strong without polluting structural validity.

12. FORBIDDEN PATTERNS

The typed model layer must not do any of the following:

12.1 SharedBaseModel with `ui` for all roles
Bad:
BaseNexModel(meta, circuit, resources, state, ui)

Reason:
this falsely implies `ui` is semantically shared across roles.

12.2 Automatic snapshot `ui` carry-over
Bad:
CommitSnapshotModel.ui = WorkingSaveModel.ui

Reason:
this crosses the commit boundary with UI clutter.

12.3 Silent canonicalization of non-canonical snapshot `ui`
Bad:
if snapshot has `ui`, just accept it normally

Reason:
this normalizes forbidden content into approved model state.

12.4 Role inference from `ui` presence
Bad:
if `ui` exists, assume Working Save

Reason:
role comes from storage-role resolution, not convenience heuristics.

13. EXAMPLE MODEL OUTCOMES

13.1 Working Save with UI

Input role:
- working_save

Input contains:
- valid `ui`

Typed result:
- `LoadedNexArtifact.storage_role = "working_save"`
- `parsed_model = WorkingSaveModel(..., ui=UISection(...))`

13.2 Working Save without UI

Input role:
- working_save

Input contains:
- no `ui`

Typed result:
- `LoadedNexArtifact.storage_role = "working_save"`
- `parsed_model = WorkingSaveModel(..., ui=None)`

13.3 Commit Snapshot without UI

Input role:
- commit_snapshot

Typed result:
- `LoadedNexArtifact.storage_role = "commit_snapshot"`
- `parsed_model = CommitSnapshotModel(...)`

13.4 Commit Snapshot with raw UI (non-canonical)

Input role:
- commit_snapshot
- raw `ui` present

Typed result:
- `LoadedNexArtifact.storage_role = "commit_snapshot"`
- `parsed_model = CommitSnapshotModel(...)`
- `findings += UI_SECTION_ROLE_VIOLATION`
- `non_canonical_aux["raw_ui_section"] = {...}` (optional migration path only)

14. EDITOR / COMMIT BUILDER IMPLICATIONS

14.1 Editor surfaces
- should operate primarily on `WorkingSaveModel`
- may rely on `WorkingSaveModel.ui` when present
- must tolerate `ui=None`

14.2 Commit builders
- must read from `WorkingSaveModel`
- must intentionally exclude `ui` when creating `CommitSnapshotModel`

14.3 Snapshot readers
- must not expect UI continuity as part of canonical snapshot state
- should treat any auxiliary raw `ui` only as migration residue

15. MINIMUM FIRST IMPLEMENTATION

The first implementation of this binding rule should support:

- `WorkingSaveModel.ui: UISection | None`
- no canonical `CommitSnapshotModel.ui`
- role-aware typed construction
- auxiliary preservation path for non-canonical snapshot `ui`
- UI-scoped findings attached during Working Save binding
- role-violation findings for snapshot-side raw `ui`

16. FINAL DECISION

The `.nex.ui` section is officially bound only to `WorkingSaveModel`
as canonical typed state.

`CommitSnapshotModel` must remain free of authoritative `ui`.

Any future typed-model design that makes `ui` a generic shared role field is invalid.
