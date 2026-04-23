# Phase 4.5 Document Set Index v1

## Recommended save path
`docs/specs/meta/phase45_document_set_index.md`

## 1. Purpose

This document is the official index for the Phase 4.5 document set in Nexa.

Its purpose is to:

- define the canonical Phase 4.5 document groups
- fix where each group should live in the docs structure
- explain the role of each document
- define the recommended reading order
- reduce future confusion between:
  - decision records
  - architecture/gate summaries
  - server implementation contracts
  - implementation-sequence planning

This document is an index.
It does not replace the underlying specs.

## 2. Core Decision

Phase 4.5 documents must be split by role, not only by topic.

Official rule:

- decision / gate / architecture-summary documents belong under:
  `docs/specs/meta/phase45_decisions/`
- server implementation contracts belong under:
  `docs/specs/server/`
- future implementation-order planning documents may live under:
  `docs/specs/meta/` unless a better stable home is later chosen

In short:

Do not mix decision records and server contracts into one flat folder.

## 3. Canonical Folder Structure

### 3.1 Decision / Gate / Summary Folder

`docs/specs/meta/phase45_decisions/`

Canonical contents:

1. `phase45_implementation_gate_checklist.md`
2. `01_hosting_cloud_decision.md`
3. `02_database_decision.md`
4. `03_authentication_decision.md`
5. `04_secret_and_provider_credential_decision.md`
6. `05_server_api_shape_decision.md`
7. `06_mobile_web_session_continuity_decision.md`
8. `phase45_architecture_summary.md`

### 3.2 Server Contract Folder

`docs/specs/server/`

Canonical contents:

1. `engine_server_boundary_contract.md`
2. `run_launch_api_contract.md`
3. `run_status_api_contract.md`
4. `run_result_api_contract.md`
5. `artifact_persistence_and_retrieval_contract.md`
6. `trace_persistence_and_query_contract.md`
7. `run_record_persistence_contract.md`
8. `auth_adapter_contract.md`
9. `database_append_only_lineage_persistence_contract.md`
10. `engine_boundary_type_mapping.md`
11. `worker_execution_contract.md`

## 4. Why This Split Exists

### 4.1 Decision records are not the same as server contracts

Examples:
- AWS-first
- PostgreSQL
- Clerk

These are not endpoint or runtime-shape specs.
They are top-level architectural decisions and gate answers.

### 4.2 Server contracts are implementation-facing

Examples:
- run launch shape
- run status shape
- artifact retrieval
- trace query
- worker execution lifecycle

These directly constrain implementation.

### 4.3 Mixing them weakens document clarity

If all Phase 4.5 docs sit in one folder, then:
- gate decisions
- implementation rules
- boundary rules

become harder to distinguish during coding and review.

## 5. Recommended Reading Order

### Stage A — Understand whether Phase 4.5 may begin

Read in this order:

1. `docs/specs/meta/phase45_decisions/phase45_implementation_gate_checklist.md`
2. `docs/specs/meta/phase45_decisions/phase45_architecture_summary.md`

Purpose:
- understand the gate
- understand the chosen direction set

### Stage B — Understand the six infrastructure decisions

Read in this order:

1. `01_hosting_cloud_decision.md`
2. `02_database_decision.md`
3. `03_authentication_decision.md`
4. `04_secret_and_provider_credential_decision.md`
5. `05_server_api_shape_decision.md`
6. `06_mobile_web_session_continuity_decision.md`

Purpose:
- understand the adopted infrastructure stack
- understand why those choices were made

### Stage C — Understand engine/server separation

Read in this order:

1. `docs/specs/server/engine_server_boundary_contract.md`
2. `docs/specs/server/engine_boundary_type_mapping.md`

Purpose:
- understand the Layer Boundary
- understand how boundary objects map onto documented engine-side candidates

### Stage D — Understand run lifecycle from server perspective

Read in this order:

1. `docs/specs/server/run_launch_api_contract.md`
2. `docs/specs/server/worker_execution_contract.md`
3. `docs/specs/server/run_status_api_contract.md`
4. `docs/specs/server/run_result_api_contract.md`
5. `docs/specs/server/run_record_persistence_contract.md`

Purpose:
- understand admission
- understand async execution lifecycle
- understand status/result retrieval
- understand product continuity records

### Stage E — Understand persistent truth surfaces

Read in this order:

1. `docs/specs/server/artifact_persistence_and_retrieval_contract.md`
2. `docs/specs/server/trace_persistence_and_query_contract.md`
3. `docs/specs/server/database_append_only_lineage_persistence_contract.md`

Purpose:
- understand append-only artifact handling
- understand trace preservation/query rules
- understand DB persistence discipline

### Stage F — Understand auth isolation

Read:

1. `docs/specs/server/auth_adapter_contract.md`

Purpose:
- keep provider-specific auth logic out of engine-core semantics

## 6. Document Roles

### 6.1 Gate Checklist
Answers:
- may production-grade Phase 4.5 implementation begin?

### 6.2 Decision Records
Answer:
- what infrastructure choices were adopted?

### 6.3 Architecture Summary
Answers:
- what is the one-page integrated picture?
- is the gate passed?

### 6.4 Boundary Contract
Answers:
- what belongs to the engine?
- what belongs to the server?

### 6.5 Type Mapping
Answers:
- how do boundary objects attach to current documented engine-side candidates?

### 6.6 Run Contracts
Answers:
- how is a run launched?
- how does async worker orchestration behave?
- how is status read?
- how is result read?
- how is run history persisted?

### 6.7 Persistence Contracts
Answers:
- how are artifact/trace/history truths preserved in product persistence?

### 6.8 Auth Adapter Contract
Answers:
- how is Clerk isolated so auth choice does not leak into engine-core meaning?

## 7. Current Strong Recommendation

The current document set is strong enough for implementation-oriented planning.

That means:

- no major new direction contract is missing
- the current next step should be implementation ordering, not more top-level architecture drift
- future additions should be narrow and implementation-driven

## 8. Recommended Next Document

The most rational next document is:

`docs/specs/meta/phase45_implementation_sequence.md`

Reason:
- the direction set is now broad enough
- the remaining problem is execution order, not missing high-level architecture

## 9. What Must Never Happen

The following are forbidden:

1. moving all six infrastructure decision records into `docs/specs/server/`
2. flattening decision records and implementation contracts into one undifferentiated folder
3. treating worker execution lifecycle as equivalent to engine execution semantics
4. treating type-mapping docs as if they replace actual engine verification
5. letting future implementation notes silently override formal decision records

## 10. Final Statement

The Phase 4.5 document set in Nexa is now large enough that indexing is no longer optional.

This index fixes:
- where the documents live
- what role each document plays
- how they should be read
- what should come next

That clarity is necessary before Phase 4.5 implementation begins in earnest.
