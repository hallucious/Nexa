# `.nex` Load / Validate API Spec v0.1

## 1. Purpose

This document defines the public loading and validation APIs for `.nex` artifacts.

## 2. Public API Surface

- `load_nex(...)`
- `validate_working_save(...)`
- `validate_commit_snapshot(...)`

## 3. `load_nex()`

Canonical unified loader.

Responsibilities:
- parse raw `.nex`
- resolve storage role
- run role-specific validation when requested
- construct typed model
- return `LoadedNexArtifact`

## 4. `validate_working_save()`

Permissive current-state validator.

It may report findings without rejecting loadability.

## 5. `validate_commit_snapshot()`

Strict execution-anchor validator.

Blocking findings make the artifact unacceptable as committed structure.

## 6. Result Models

### LoadedNexArtifact
- storage_role
- parsed_model
- findings
- load_status
- source_path
- migration_notes

### ValidationReport
- role
- findings
- blocking_count
- warning_count
- result

## 7. Rule

`load_nex()` is the unified entry point, but validation semantics remain explicitly split by role.
