# Designer Document Placement and Gap Audit v0.1

## Recommended save path
`docs/specs/designer/designer_document_placement_and_gap_audit.md`

## 1. Purpose

This document finalizes the Designer specification bundle for Nexa by:

- fixing the canonical project paths
- distinguishing canonical spec names from temporary recreated delivery files
- grouping the documents by role
- checking for duplicate-role documents
- checking for blocking missing documents inside the current Designer documentation track

This is a document-governance audit, not a new architecture contract.

## 2. Core Decision

The Designer bundle is now large enough that filename drift and duplicate-role confusion
would become a maintenance risk.

Official rule:

- canonical project paths must be fixed explicitly
- recreated delivery files are temporary handoff artifacts, not canonical filenames
- document role overlap must be called out
- missing-document checks must be explicit

In short:

The Designer spec bundle must now be treated as a governed document set.

## 3. Canonical Designer Bundle by Path

### 3.1 Architecture Layer

1. `docs/specs/architecture/designer_ai_integration_architecture.md`

Role:
- defines what Designer AI is
- fixes its position above the execution engine
- prevents Designer AI from being treated as an execution resource

### 3.2 Input-Boundary Layer

2. `docs/specs/designer/designer_session_state_card.md`

Role:
- canonical input card for Designer AI

3. `docs/specs/designer/designer_ai_input_exposure_rules.md`

Role:
- what may be exposed to Designer AI

4. `docs/specs/designer/designer_ai_input_redaction_rules.md`

Role:
- what must be hidden, masked, or downgraded before exposure

5. `docs/specs/designer/designer_ai_input_priority_rules.md`

Role:
- precedence rules when inputs conflict

6. `docs/specs/designer/designer_ai_input_refresh_triggers.md`

Role:
- when Designer AI input must be recomputed

### 3.3 Proposal Pipeline Layer

7. `docs/specs/designer/designer_intent_contract.md`

Role:
- normalized intent contract

8. `docs/specs/designer/session_card_to_intent_mapping_rules.md`

Role:
- mapping from session card to normalized intent

9. `docs/specs/designer/circuit_patch_contract.md`

Role:
- canonical patch proposal contract

10. `docs/specs/designer/intent_to_patch_mapping_rules.md`

Role:
- mapping from intent to patch plan

11. `docs/specs/designer/designer_validator_precheck_contract.md`

Role:
- structured precommit proposal evaluation contract

12. `docs/specs/designer/patch_plan_to_precheck_evaluation_rules.md`

Role:
- mapping from patch plan to validation precheck

13. `docs/specs/designer/circuit_draft_preview_contract.md`

Role:
- canonical preview contract

14. `docs/specs/designer/precheck_to_preview_mapping_rules.md`

Role:
- mapping from validation precheck to draft preview

15. `docs/specs/designer/preview_to_approval_decision_rules.md`

Role:
- valid approval outcomes after preview

16. `docs/specs/designer/approval_to_commit_gateway_rules.md`

Role:
- commit eligibility and rejection rules after approval

### 3.4 Governance / Index Layer

17. `docs/specs/designer/designer_spec_index.md`

Role:
- official index for the whole Designer bundle

18. `docs/specs/designer/designer_document_placement_and_gap_audit.md`

Role:
- canonical path audit, duplicate-role check, and gap audit

## 4. Temporary Delivery Files That Are Not Canonical Filenames

The following file names were created only to re-deliver content when prior sandbox links expired.

They are valid delivery artifacts, but they are **not** the canonical filenames that should live in the repository.

### 4.1 Recreated delivery files

- `precheck_to_preview_mapping_rules_recreated.md`
- `preview_to_approval_decision_rules_recreated.md`
- `approval_to_commit_gateway_rules_recreated.md`

Rule:
- these should not become permanent repository filenames
- their contents should be stored under the canonical paths listed in Section 3

## 5. Duplicate-Role Check

### 5.1 True duplicate-role documents
No true duplicate-role canonical documents were found inside the Designer bundle itself.

### 5.2 Temporary duplicate deliveries
There are temporary duplicate deliveries caused by link-expiration recovery:

- canonical intent-to-preview/approval/commit documents
- recreated handoff copies of the same documents

These are not conceptual duplicates.
They are delivery duplicates.

### 5.3 Governance rule
If both canonical-name and recreated-name versions exist in a working folder,
keep only the canonical-name version in the repository structure.

## 6. Role-Boundary Check

### 6.1 Input-boundary track
This track is now complete enough to answer the question:

"What information should be provided to the called AI for circuit generation?"

Documents that answer that question:

- Designer AI Integration Architecture
- Designer Session State Card
- Designer AI Input Exposure Rules
- Designer AI Input Redaction Rules
- Designer AI Input Priority Rules
- Designer AI Input Refresh Triggers
- Designer Spec Index

### 6.2 Downstream pipeline track
This track is now complete enough at the document level to describe the post-input proposal flow:

- Intent
- Patch
- Precheck
- Preview
- Approval
- Commit

This does not mean the code is implemented.
It means the document chain exists.

## 7. Blocking Missing-Document Check

### 7.1 Missing documents for the current input-boundary question
No blocking missing document was found.

The current input-boundary question is sufficiently covered by:

- Session State Card
- Exposure Rules
- Redaction Rules
- Priority Rules
- Refresh Triggers

### 7.2 Missing documents for the current downstream documentation chain
No blocking missing document was found inside the current proposal-pipeline documentation track.

The sequence is document-complete from:
- Session Card
through
- Commit Gateway

## 8. Non-Blocking Future Documents

The following could be useful later, but are not blocking for the current document bundle.

### 8.1 Designer implementation checklist
Possible future path:

`docs/specs/designer/designer_implementation_checklist.md`

Role:
- implementation-time checklist for connecting specs to code
- contract sync, validator sync, storage sync, UI sync, tests

### 8.2 Designer prompt/output operational template
Possible future path:

`docs/specs/designer/designer_prompt_operational_template.md`

Role:
- practical runtime prompt envelope for the called AI
- how the session state card is actually serialized into prompt input
- output formatting expectations during real invocation

### 8.3 Designer contract-to-code integration map
Possible future path:

`docs/specs/designer/designer_contract_to_code_integration_map.md`

Role:
- which runtime/storage/UI modules must consume which Designer contracts

These are future implementation-support documents, not missing core design docs.

## 9. Canonical Repository Rule

For repository storage, the Designer spec bundle should use:

- the canonical filenames from Section 3
- no `_recreated` suffix files
- no duplicate delivery copies
- one authoritative file per document role

## 10. Practical Next Step

The next practical step after this audit is not more document invention.

It is one of the following:

1. place the current files into their canonical repository paths
2. delete temporary recreated delivery copies from the working area after canonical placement
3. begin code-side integration planning using the current spec bundle

## 11. Decision

The Designer documentation track is now structurally organized.

Current status:

- canonical paths fixed
- temporary recreated files identified
- duplicate-role confusion resolved
- no blocking missing spec found for the current Designer documentation scope

From this point, the correct movement is document placement cleanup and then implementation-side integration planning.
