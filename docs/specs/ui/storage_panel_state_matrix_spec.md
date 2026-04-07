[DESIGN]
[STORAGE_PANEL_STATE_MATRIX_SPEC v0.1]

1. PURPOSE

This document defines the official state matrix used to interpret
Working Save, Commit Snapshot, and Execution Record combinations
inside the Nexa Storage Panel.

Its purpose is to make the following explicit:

- which storage combinations are valid
- which combinations are valid but warning-bearing
- which combinations are impossible at the canonical model layer
- how the Storage Panel should interpret each valid combination
- which distinctions must remain visible to the user

This specification exists because the Storage Panel must not collapse
three different truth domains into one vague "current file" concept.

2. CORE DECISION

The Storage Panel must interpret storage state as a 3-way matrix:

- Working Save
- Commit Snapshot
- Execution Record

Official rule:

- each layer keeps its own semantics
- presence/absence combinations must be interpreted explicitly
- mismatch conditions must surface as diagnostics rather than being silently normalized
- canonical model impossibilities must not be hidden by UI projection

3. STORAGE LAYERS

3.1 Working Save
Meaning:
- editable present-state draft
- may be incomplete or invalid
- may contain UI-owned continuity state
- may contain latest-run summaries as draft-side continuity, not as authoritative history

3.2 Commit Snapshot
Meaning:
- approved structural anchor
- non-editable truth layer
- may act as execution anchor, diff target, or rollback target

3.3 Execution Record
Meaning:
- run history bound to a commit anchor
- non-editable historical truth
- may expose outputs, artifacts, trace, and verifier summaries

4. MATRIX AXES

Axis A: presence
- has_working_save
- has_commit_snapshot
- has_execution_record

Axis B: linkage consistency
- does Working Save point to the latest Commit Snapshot cleanly?
- does Execution Record point to the latest Commit Snapshot cleanly?
- does Working Save point to a latest run that is actually present?

Axis C: panel focus
- draft_focus
- commit_focus
- execution_focus
- lifecycle_overview

5. VALID PRIMARY COMBINATIONS

5.1 WS only
Combination:
- Working Save present
- Commit Snapshot absent
- Execution Record absent

Interpretation:
- draft-only workspace
- editable state exists
- no approved anchor yet
- no latest run history loaded

Expected UI meaning:
- panel_mode may be draft_focus or lifecycle_overview
- compare-to-commit action disabled
- no commit/run refs implied

5.2 WS + CS
Combination:
- Working Save present
- Commit Snapshot present
- Execution Record absent

Interpretation:
- editable draft with approved anchor
- may be in sync with latest commit or have uncommitted changes

Expected UI meaning:
- show both draft and latest commit
- keep draft-vs-commit status explicit
- do not imply a loaded latest run

5.3 WS + CS + ER (matching)
Combination:
- all three present
- Execution Record commit_id matches latest Commit Snapshot commit_id
- Working Save source_commit_id aligns with latest Commit Snapshot when applicable

Interpretation:
- fully linked editable + approved + historical state
- highest-value normal operating combination

Expected UI meaning:
- show all three cards
- relationship graph must remain explicit
- no stale-anchor diagnostic required

5.4 WS + CS + ER (mismatched latest run)
Combination:
- all three present
- Execution Record commit_id does not match latest Commit Snapshot commit_id

Interpretation:
- valid but warning-bearing state
- the latest loaded run is not anchored to the latest loaded commit snapshot

Expected UI meaning:
- preserve all three layers
- surface stale/mismatched anchor warning
- do not silently relabel the run as if it belonged to the latest commit

5.5 CS only
Combination:
- Working Save absent
- Commit Snapshot present
- Execution Record absent

Interpretation:
- pure approved-structure inspection state

Expected UI meaning:
- commit_focus or lifecycle_overview
- no draft editability implied
- no run history implied

5.6 CS + ER
Combination:
- Working Save absent
- Commit Snapshot present
- Execution Record present
- Execution Record commit_id matches Commit Snapshot commit_id

Interpretation:
- approved anchor with attached historical run

Expected UI meaning:
- show approved structure and historical execution together
- still no editable draft semantics

5.7 ER only
Combination:
- Working Save absent
- Commit Snapshot absent
- Execution Record present

Interpretation:
- history-first inspection state
- allowed when run history is loaded independently of current draft/commit context

Expected UI meaning:
- execution_focus or lifecycle_overview
- run remains non-editable history
- absence of latest commit card is allowed
- UI must not invent the missing commit snapshot as if loaded

5.8 lifecycle overview from latest references
Combination:
- active source is none
- one or more latest refs are supplied

Interpretation:
- overview mode rather than artifact-focus mode

Expected UI meaning:
- panel_mode = lifecycle_overview
- cards may still appear if latest refs exist
- role truth remains per-card, not collapsed into one synthetic artifact

6. VALID WARNING-BEARING COMBINATIONS

6.1 Working Save references a commit that is not loaded
Combination:
- Working Save latest-run/validation summary refers to a commit id
- latest Commit Snapshot object not loaded

Expected UI meaning:
- missing_commit_ref diagnostic
- no fake commit card

6.2 Working Save references a run that is not loaded
Combination:
- Working Save runtime.last_run contains run_id
- latest Execution Record object not loaded

Expected UI meaning:
- missing_run_ref diagnostic
- no fake execution card

6.3 Resume anchor requires revalidation
Combination:
- Working Save last_run.resume_ready = false

Expected UI meaning:
- lifecycle warning visible
- this is still a Working Save, not a failed commit snapshot or failed execution record

6.4 Working Save vs Commit Snapshot stale source anchor
Combination:
- Working Save validation/runtime source_commit_id differs from loaded latest Commit Snapshot commit_id

Expected UI meaning:
- stale reference warning
- draft-vs-commit distinction preserved

7. CANONICAL IMPOSSIBILITIES / FORBIDDEN COLLAPSES

The following are not valid canonical state interpretations.

7.1 Commit Snapshot treated as editable draft
Forbidden:
- showing commit snapshot as if it were Working Save truth

7.2 Execution Record treated as current draft
Forbidden:
- presenting historical run outputs as editable structural state

7.3 Working Save treated as approved merely because a Commit Snapshot exists
Forbidden:
- visually collapsing draft and approved truth into one “current approved file” state

7.4 Execution Record without commit binding inside canonical model
Forbidden at model layer:
- canonical Execution Record must have commit_id

7.5 Snapshot-side UI continuity treated as structural truth
Forbidden:
- any UI continuity state influencing matrix interpretation of storage truth

8. MATRIX INTERPRETATION RULES

8.1 Presence does not imply collapse.
If two or three layers are present, they must remain separately identifiable.

8.2 Missing linked objects must surface as diagnostics.
Absence is not permission to synthesize implied truth.

8.3 Relationship labels must remain reference-based.
Examples:
- Working Save -> latest commit
- latest commit -> latest run

8.4 Panel focus must not overwrite role truth.
Example:
- execution_focus does not make the run the current editable draft

9. MINIMUM TEST EXPECTATIONS

The Storage Panel test suite should verify at least:

- WS only
- WS + CS
- WS + CS + ER matching
- WS + CS + ER mismatched
- CS only
- CS + ER
- ER only
- lifecycle_overview with latest refs
- missing commit ref diagnostic
- missing run ref diagnostic
- resume revalidation warning

10. FINAL DECISION

The Storage Panel must project storage lifecycle through an explicit 3-way matrix.

The important rule is not merely which artifact is active.
The important rule is whether Working Save, Commit Snapshot, and Execution Record
are present, consistent, stale, missing, or history-only.

This matrix exists to keep Nexa UI storage semantics precise,
engine-aligned, and resistant to ambiguity.
