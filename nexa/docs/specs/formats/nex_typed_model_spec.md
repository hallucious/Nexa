# `.nex` Typed Model Spec v0.1

## 1. Purpose

This document defines the typed in-memory model layer for `.nex` artifacts.

## 2. Model Family

- shared section models
- `WorkingSaveModel`
- `CommitSnapshotModel`
- `LoadedNexArtifact` wrapper

## 3. Shared Section Models

Shared shape models include:
- `MetaBase`
- `CircuitModel`
- `ResourcesModel`
- `StateModel`

Shared shape does not mean identical lifecycle semantics.

## 4. Working Save Model

```text
WorkingSaveModel
- meta: WorkingSaveMeta
- circuit: CircuitModel
- resources: ResourcesModel
- state: StateModel
- runtime: RuntimeModel
- ui: UIModel
- designer: DesignerDraftModel | None
```

This model may represent invalid or incomplete drafts.

## 5. Commit Snapshot Model

```text
CommitSnapshotModel
- meta: CommitSnapshotMeta
- circuit: CircuitModel
- resources: ResourcesModel
- state: StateModel
- validation: CommitValidationModel
- approval: CommitApprovalModel
- lineage: CommitLineageModel
```

This model must represent approved structural state only.

## 6. LoadedNexArtifact Wrapper

```text
LoadedNexArtifact
- storage_role
- parsed_model
- findings
- load_status
```

The wrapper keeps role explicit after load.

## 7. Current Direction

Role-aware typed model separation is current storage architecture.
Generic one-model savefile handling is forbidden.
Execution Record remains a separate run-history model family rather than part of the `.nex` role split.

## 8. Decision

Nexa typed `.nex` loading is role-aware and model-separated.
