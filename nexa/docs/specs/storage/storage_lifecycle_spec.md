# Storage Lifecycle Spec v0.1

## 1. Purpose

This specification defines the lifecycle relationship between:
- Working Save
- Commit Snapshot
- Execution Record

## 2. Lifecycle Principles

1. Save, commit, and execute are different boundaries.
2. Working Save must never be blocked by structural invalidity alone.
3. Commit Snapshot must never be created from unresolved blocking state.
4. Execution Record must always reference a Commit Snapshot.
5. Execution history must not bloat Working Save.
6. Temporary draft clutter must not leak into Commit Snapshot.
7. Execution outcome must not rewrite structural truth.
8. Canonical storage semantics must be owned by storage/lifecycle APIs.
9. CLI / export / replay / audit paths must consume lifecycle-owned semantics rather than re-derive them locally.

## 3. Lifecycle States

- Editing -> Working Save
- Review-Ready -> Working Save
- Approved -> Commit Snapshot created
- Executing -> Execution Record initialized
- Executed -> Execution Record finalized

## 4. Transition Summary

### Create or edit draft
-> Working Save updated

### Validate draft
-> Working Save runtime summary updated

### Review / approval
-> approved / rejected / revision requested / blocked

### Commit creation
-> new Commit Snapshot created

### Run execution
-> new Execution Record initialized

### Finalize execution
-> Execution Record finalized
-> optional last-run summary reflected back to Working Save

## 5. Truth-Ordering Rule

If competing execution metadata exists during lifecycle normalization:
- sufficiently substantive native execution truth wins first
- richer materializable execution truth wins next
- thin identity-only execution data may be preserved only where identity must survive
- weaker stale derived metadata must not overwrite stronger truth

## 6. Decision

Nexa storage is a three-layer lifecycle system:
Working Save preserves editable present state,
Commit Snapshot freezes approved structural state,
Execution Record preserves one realized execution history.
