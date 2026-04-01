# `.nex` Parser / Validator Branch Rules v0.1

## 1. Purpose

This document defines how Nexa parsers and validators branch when loading a `.nex` artifact.

## 2. Core Rule

The parser must:
1. parse JSON
2. check shared backbone
3. resolve `meta.storage_role`
4. apply role-specific schema rules
5. apply role-specific semantic validation
6. construct typed model

## 3. Legacy Fallback

If `meta.storage_role` is missing:
- default to `working_save`

This is for compatibility only.

## 4. Working Save Validation Philosophy

- permissive
- diagnostic
- current-state oriented

Allowed even with findings:
- missing entry
- missing output
- unresolved provider/plugin
- validation_failed status
- execution_failed status
- pending designer metadata

## 5. Commit Snapshot Validation Philosophy

- strict
- approval-gated
- execution-anchor oriented

Required:
- validation exists
- approval exists
- lineage exists
- validation_result is non-blocking
- approval completed
- no unresolved blocking structural issue

## 6. Acceptance Matrix

### Working Save
- invalid JSON -> reject
- missing backbone -> reject
- missing runtime/ui -> reject
- missing entry/output -> load with findings
- provider unresolved -> load with findings

### Commit Snapshot
- invalid JSON -> reject
- missing backbone -> reject
- missing validation/approval/lineage -> reject
- failed validation result -> reject
- approval incomplete -> reject
- blocked structure -> reject

## 7. Decision

Working Save is load-first.
Commit Snapshot is reject-first.
Both are `.nex`, but they do not share the same acceptance policy.
