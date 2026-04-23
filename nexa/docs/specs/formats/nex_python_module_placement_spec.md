[PYTHON_MODULE_PLACEMENT_SPEC v0.1]

1. Purpose

This specification defines where the new `.nex` storage-role system should live
inside the Nexa Python codebase.

The goal is to separate:

- contract definitions
- typed models
- parser / validator logic
- file IO
- lifecycle orchestration

without mixing them into one large savefile module.

2. Core Placement Principles

2.1 Contracts belong in `src/contracts/`.
2.2 Typed storage models belong in `src/storage/models/`.
2.3 Parser and validator branching logic belong in `src/storage/loaders/` and `src/storage/validators/`.
2.4 File/path IO belongs in `src/io/` or `src/storage/io/`.
2.5 Lifecycle orchestration belongs in `src/storage/` as higher-level services.
2.6 Execution Record must remain separate from `.nex` role models.
2.7 Backward migration helpers must not leak into runtime execution code.

3. Recommended Directory Layout

src/
  contracts/
    nex_contract.py
    working_save_contract.py
    commit_snapshot_contract.py
    execution_record_contract.py

  storage/
    __init__.py

    models/
      __init__.py
      shared_sections.py
      working_save_model.py
      commit_snapshot_model.py
      loaded_nex_artifact.py
      execution_record_model.py

    loaders/
      __init__.py
      nex_loader.py
      role_resolution.py
      legacy_migration.py

    validators/
      __init__.py
      shared_validator.py
      working_save_validator.py
      commit_snapshot_validator.py

    services/
      __init__.py
      commit_snapshot_service.py
      execution_record_service.py
      lifecycle_service.py

    refs/
      __init__.py
      artifact_refs.py
      trace_refs.py

  io/
    nex_file_io.py
    execution_record_io.py

4. contracts/ Placement

4.1 src/contracts/nex_contract.py
Purpose:
- unified `.nex` contract summary
- shared top-level backbone rules
- storage_role enum definition

4.2 src/contracts/working_save_contract.py
Purpose:
- Working Save section requirements
- always-saveable invariants
- working-save-specific semantic rules

4.3 src/contracts/commit_snapshot_contract.py
Purpose:
- approval-gated structural snapshot rules
- commit invariants
- snapshot-specific validation requirements

4.4 src/contracts/execution_record_contract.py
Purpose:
- run-scoped execution record contract
- history / trace / artifact reference rules

Rule:
- contracts define truth
- contracts do not perform file IO
- contracts do not own runtime execution logic

5. storage/models/ Placement

5.1 shared_sections.py
Contains:
- MetaBase
- CircuitModel
- ResourcesModel
- StateModel
- shared support models reused by both `.nex` roles

5.2 working_save_model.py
Contains:
- WorkingSaveMeta
- RuntimeIssueModel
- ValidationSummaryCardModel
- LastRunCardModel
- ArtifactSummaryCardModel
- RuntimeModel
- UIModel
- DesignerDraftModel
- WorkingSaveModel

5.3 commit_snapshot_model.py
Contains:
- CommitSnapshotMeta
- CommitValidationModel
- CommitApprovalModel
- CommitLineageModel
- CommitSnapshotModel

5.4 loaded_nex_artifact.py
Contains:
- ValidationFinding
- LoadedNexArtifact
- ValidationReport

5.5 execution_record_model.py
Contains:
- ExecutionRecord typed model family
- separate from `.nex` typed role models

Rule:
- models are in-memory objects only
- no parsing side effects here
- no path reading here

6. storage/loaders/ Placement

6.1 nex_loader.py
Public home of:
- load_nex(...)

Responsibilities:
- parse source
- check shared backbone
- resolve role
- invoke role validator
- construct typed model
- return LoadedNexArtifact

6.2 role_resolution.py
Responsibilities:
- resolve `meta.storage_role`
- apply legacy fallback
- reject invalid roles

6.3 legacy_migration.py
Responsibilities:
- missing storage_role fallback handling
- deprecated field normalization
- migration note generation

Rule:
- loader layer coordinates
- it does not define contract truth by itself

7. storage/validators/ Placement

7.1 shared_validator.py
Responsibilities:
- validate shared top-level backbone
- validate shared schema sections:
  meta / circuit / resources / state

7.2 working_save_validator.py
Public home of:
- validate_working_save(...)

Responsibilities:
- validate working-save-only sections:
  runtime / ui / designer
- enforce permissive semantic rules
- produce findings without over-rejecting

7.3 commit_snapshot_validator.py
Public home of:
- validate_commit_snapshot(...)

Responsibilities:
- validate commit-snapshot-only sections:
  validation / approval / lineage
- enforce strict semantic rules
- reject blocked structural state

Rule:
- validator modules must remain separated
- do not collapse into one generic validator

8. io/ Placement

8.1 io/nex_file_io.py
Responsibilities:
- read `.nex` from file path
- write `.nex` back to file path
- serialization helpers

8.2 io/execution_record_io.py
Responsibilities:
- read/write execution records
- run directory persistence
- execution history file conventions

Rule:
- raw filesystem concerns belong here
- typed validation belongs elsewhere

9. storage/services/ Placement

9.1 commit_snapshot_service.py
Responsibilities:
- create Commit Snapshot from approved proposal
- ensure approval/precheck/preview linkage
- strip working-draft clutter
- assign commit_id

9.2 execution_record_service.py
Responsibilities:
- initialize execution record at run start
- finalize at run end
- attach trace/artifact refs
- write summary back to Working Save if needed

9.3 lifecycle_service.py
Responsibilities:
- high-level transitions:
  Working Save → Commit Snapshot → Execution Record
- orchestration only, not raw parsing

Rule:
- service layer is where lifecycle behavior lives
- not inside contracts, not inside low-level loaders

10. Why This Split Is Correct

10.1 It matches the three-layer storage lifecycle. 
10.2 It keeps `.nex` role parsing separate from execution history.
10.3 It avoids the old “one giant savefile module” trap.
10.4 It makes migration safer.
10.5 It allows future CLI/UI/editor code to depend on stable services rather than raw dicts.

11. Minimal Import Surface Recommendation

Recommended public imports:

from src.storage.loaders.nex_loader import load_nex
from src.storage.validators.working_save_validator import validate_working_save
from src.storage.validators.commit_snapshot_validator import validate_commit_snapshot
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact, ValidationReport

12. Forbidden Placement Mistakes

Do NOT:
- put WorkingSaveModel and CommitSnapshotModel into runtime modules
- mix execution-record models into `.nex` loader files
- place lifecycle services inside contracts/
- make io/ modules decide semantic validity
- make validators perform commit creation side effects

13. Official Decision

The `.nex` storage-role system will be implemented with a layered Python module structure:

- contracts = truth rules
- models = typed in-memory objects
- loaders = role-aware unified load entry
- validators = role-specific acceptance logic
- io = filesystem serialization
- services = lifecycle orchestration