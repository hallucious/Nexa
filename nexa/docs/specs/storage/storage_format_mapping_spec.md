# Storage Format Mapping Spec v0.1

## 1. Purpose

This document maps lifecycle layers to concrete artifact formats.

## 2. Mapping Decision

- `.nex` with `storage_role=working_save` -> Working Save
- `.nex` with `storage_role=commit_snapshot` -> Commit Snapshot
- `.nexb` -> distribution bundle
- execution record store / trace store -> Execution Record layer
- artifact store -> append-only artifact payload storage

## 3. `.nex` Family Strategy

Nexa keeps `.nex` as the main structured storage family.
The family is role-aware rather than split into separate top-level user-visible file extensions.

Reason:
- preserves continuity
- avoids premature file-format explosion
- keeps user mental model simple
- allows Working Save and Commit Snapshot to share one bounded backbone while still keeping lifecycle semantics separate

## 4. `.nexb` Rule

`.nexb` is a portability / distribution wrapper.
It is not itself a lifecycle layer.

It may package:
- one primary `.nex`
- plugins
- optional manifest / resources

## 5. Trace and Artifact Rule

Trace and artifact payloads remain external / reference-oriented.

- Working Save: summaries / refs only
- Commit Snapshot: structural refs only
- Execution Record: refs + lightweight summaries

## 6. Compatibility Rule

Legacy `.nex` without `storage_role` defaults to `working_save`.

## 7. Decision

Nexa keeps `.nex` as the main artifact family, distinguished internally by explicit `storage_role`, while Execution Record remains the run-history layer rather than a `.nex` role.
