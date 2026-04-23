[DESIGN]
[UI_COMMIT_BOUNDARY_STRIPPING_SPEC v0.2]

1. PURPOSE

This document defines the canonical rule for handling the `.nex.ui` section
when a Nexa artifact crosses the commit boundary:

Working Save
→ approval/commit flow
→ Commit Snapshot

Its purpose is to make the following behavior explicit and enforceable:

- `ui` may exist in Working Save
- `ui` must not cross into canonical Commit Snapshot state
- commit builders must strip or reject `ui`
- commit-time handling of `ui` must be deterministic and role-safe
- editor continuity must remain separate from approved structural truth

This specification exists to connect:

- `.nex.ui` schema
- UI section branch rules
- UI typed model binding
- UI public API exposure
- Working Save / Commit Snapshot storage lifecycle

2. CORE DECISION

The commit boundary is a hard truth boundary.

Official rule:

- Working Save may contain canonical `ui`
- Commit Snapshot must not contain canonical `ui`
- commit creation must explicitly remove `ui` from the structural snapshot artifact
- no implicit carry-over is allowed

Preferred default behavior:
- strip `ui` during Working Save → Commit Snapshot conversion
- preserve UI continuity only on the Working Save side or in separate UI-owned storage
- never embed editor continuity as approved snapshot truth

3. CORE PRINCIPLES

3.1 Commit creation is not a generic copy operation.
3.2 Approved structural truth must be cleaner and narrower than editable draft state.
3.3 UI continuity and editor ergonomics are not approval truth.
3.4 Commit builders must behave deterministically for the same approved input.
3.5 Snapshot purity must win over convenience carry-over.
3.6 If a caller tries to force `ui` across the boundary, the system must reject or strip explicitly.
3.7 Snapshot-side `ui` must never look canonical at any layer.

4. BOUNDARY OVERVIEW

Source side:
- WorkingSaveModel
- may include `ui: UISection | None`
- may include invalid, stale, or shell-specific UI continuity state

Boundary:
- approval satisfied
- snapshot creation invoked
- commit builder constructs canonical approved structural artifact

Target side:
- CommitSnapshotModel
- must not contain canonical `ui`
- must contain only approved structural snapshot state

5. WHAT IS ALLOWED TO CROSS THE COMMIT BOUNDARY

The following may cross, subject to existing approval/validation rules:

- approved circuit structure
- approved resources
- approved structural state baseline
- commit validation summary
- commit approval summary
- lineage metadata
- commit identity metadata

The following must not cross as canonical snapshot content:

- panel visibility/layout
- viewport/zoom/selection
- node visual positions as editor continuity state
- theme/layout choice
- unsent designer text
- local compare pairs
- session draft form state
- shell compatibility hints
- transient UI diagnostics

6. WHY UI MUST NOT CROSS

6.1 Snapshot role purity
Commit Snapshot is approval-gated structural truth, not editor workspace continuity.

6.2 Reproducibility clarity
Snapshot consumers must not need to wonder whether visual/editor state is authoritative.

6.3 Diff / rollback cleanliness
Snapshot-to-snapshot comparison should not be polluted by transient editor noise.

6.4 Public API stability
Snapshot-side canonical `ui` would contradict typed model and public API rules.

6.5 Replaceable UI architecture
Because shells/modules are replaceable, snapshot truth must not embed one shell's continuity assumptions.

7. COMMIT BUILDER INPUT / OUTPUT RULE

7.1 Canonical input

Input:
- approved WorkingSaveModel
- approval/precheck/validation outputs
- commit creation request/context

7.2 Canonical output

Output:
- CommitSnapshotModel
- no canonical `ui` field
- no snapshot-authoritative UI continuation block

7.3 Non-canonical caller payload
If an external caller provides an explicit snapshot payload that still contains `ui`:
- the builder must not silently accept it
- the builder must either reject it or strip it explicitly

8. COMMIT-TIME HANDLING MODES

The system may support two explicit commit-time handling modes.

8.1 Strict reject mode
If `ui` is present in proposed snapshot content:
- reject snapshot creation
- emit explicit finding/error
- require caller cleanup before retry

Use when:
- internal commit pipeline needs maximum canonical strictness
- test/contract enforcement is the priority

8.2 Strip-with-note mode
If `ui` is present in proposed snapshot content:
- remove it deterministically
- emit explicit note/finding that `ui` was stripped
- continue snapshot creation only if all non-UI approval conditions are satisfied

Use when:
- commit builder accepts Working Save as source object
- ergonomics matter, but canonical snapshot output must remain clean

Preferred default:
- strip-with-note for source Working Save conversion
- strict reject for direct snapshot payload construction APIs

9. REQUIRED BEHAVIOR FOR SOURCE WORKING SAVE CONVERSION

When the source artifact is a normal Working Save:

9.1 If `ui` is absent
- proceed normally

9.2 If `ui` is present
- do not copy `ui` into snapshot core
- do not reinterpret `ui` as structural metadata
- optionally record a non-authoritative note that UI state was excluded
- create snapshot without canonical `ui`

9.3 If `ui` contains forbidden truth crossover content
Examples:
- `ui.commit_is_approved = true`
- `ui.validation_status = "passed"`
- `ui.storage_role = "commit_snapshot"`

Then:
- treat as invalid input contamination
- do not silently normalize
- raise explicit finding/error before snapshot creation completes

10. REQUIRED BEHAVIOR FOR DIRECT SNAPSHOT CONSTRUCTION APIS

If a lower-level or advanced API attempts to construct a Commit Snapshot directly:

10.1 If payload contains `ui`
- reject by default

10.2 If a migration/repair tool explicitly enables salvage mode
- preserve raw `ui` only as non-canonical auxiliary data outside snapshot core
- emit explicit non-canonical notes
- never expose it as canonical `CommitSnapshotModel.ui`

11. COMMIT BUILDER ALGORITHM GUIDELINE

Recommended canonical flow:

Step 1.
Receive approved Working Save + approval context

Step 2.
Validate that snapshot creation is allowed

Step 3.
Construct CommitSnapshotModel from approved structural domains only:
- meta
- circuit
- resources
- state baseline
- validation
- approval
- lineage

Step 4.
Ignore / strip `ui`

Step 5.
If stripping occurred, optionally emit:
- UI_SECTION_STRIPPED_AT_COMMIT
or equivalent informational finding/note

Step 6.
Return canonical Commit Snapshot

12. FINDING / ERROR CATEGORIES

Recommended commit-boundary-specific categories:

- UI_SECTION_STRIPPED_AT_COMMIT
- UI_SECTION_REJECTED_AT_COMMIT
- UI_FORBIDDEN_TRUTH_CROSSOVER
- UI_SECTION_NON_CANONICAL_SNAPSHOT_ATTEMPT
- UI_SECTION_ROLE_VIOLATION

Severity guidance:

12.1 Informational
- benign Working Save `ui` stripped during normal snapshot creation

12.2 Warning
- unexpected but harmless snapshot-side UI residue in migration/salvage contexts

12.3 Blocking / error
- attempted direct canonical snapshot with `ui`
- any authoritative-looking truth crossover inside `ui`

13. RELATIONSHIP TO LINEAGE / AUDIT

The system may record that a snapshot came from a Working Save that had UI state,
but it must do so only as non-authoritative audit metadata if ever needed.

Allowed example:
- commit creation log says: "source working save contained UI continuity state; excluded from snapshot"

Forbidden example:
- snapshot core contains `ui` because lineage wants provenance

Lineage tracks structural ancestry, not editor continuity payloads.

14. RELATIONSHIP TO WORKING SAVE CONTINUITY

Stripping `ui` at commit does not mean UI continuity is lost entirely.

Allowed continuity paths:
- Working Save retains its own `ui`
- editor keeps separate user/workspace preference storage
- shell-specific restore state remains outside snapshot truth

This means:
- the user may still continue editing with familiar layout/state
- but the approved snapshot remains clean

15. EXAMPLE OUTCOMES

15.1 Normal Working Save commit

Input:
- WorkingSaveModel(..., ui=UISection(...))

Output:
- CommitSnapshotModel(...)
- note: UI_SECTION_STRIPPED_AT_COMMIT

15.2 Working Save with no UI

Input:
- WorkingSaveModel(..., ui=None)

Output:
- CommitSnapshotModel(...)
- no UI-related note required

15.3 Direct snapshot construction attempt carrying UI

Input:
- proposed Commit Snapshot payload with `ui`

Output:
- rejection by default
- UI_SECTION_REJECTED_AT_COMMIT

15.4 Working Save with forbidden truth crossover inside UI

Input:
- WorkingSaveModel.ui contains authoritative-looking commit/validation/execution truth

Output:
- blocking error
- no snapshot created

16. TEST REQUIREMENTS

Minimum contract tests should verify:

- Working Save with `ui` commits into snapshot without canonical `ui`
- Working Save without `ui` commits normally
- direct snapshot payload with `ui` is rejected or stripped according to explicit mode
- forbidden truth crossover inside `ui` blocks snapshot creation
- emitted findings/notes are explicit and role-aware
- resulting CommitSnapshotModel has no canonical `ui`

17. MINIMUM FIRST IMPLEMENTATION

The first implementation of this rule should support:

- deterministic stripping of `ui` during Working Save → Commit Snapshot conversion
- explicit informational note for benign stripping
- blocking rejection for direct canonical snapshot `ui` attempts
- blocking rejection for truth-crossover contamination inside `ui`
- tests proving `CommitSnapshotModel` remains free of canonical `ui`

18. FINAL DECISION

The `.nex.ui` section is officially a Working Save-only continuity surface.

At the commit boundary, `ui` must not cross into canonical Commit Snapshot truth.

Any commit builder, API, or model path that allows canonical snapshot-side `ui`
is invalid.

19. LOCALIZATION COMMIT-BOUNDARY RULES

19.1 UI-owned locale/app-language preference is stripped together with the rest of canonical `ui` during Working Save -> Commit Snapshot conversion.

19.2 Commit builders must not serialize translated chrome strings, locale-specific rendered status text,
or UI language preference into canonical snapshot truth.

19.3 If continuity across commit is desired, it must remain on the Working Save side or separate UI-owned storage,
not inside approved structural snapshot state.
