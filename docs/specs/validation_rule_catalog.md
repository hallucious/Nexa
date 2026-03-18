Spec ID: validation_rule_catalog
Version: 2.0.0
Status: Active
Category: policies
Depends On:


# Validation Rule Catalog
Version: 2.0.0
Status: Official Contract

Purpose:
Defines the canonical catalog of rule_id values for Nexa validation.

This document is the authoritative rule catalog used by ValidationEngine.

### Implemented Rules (Authoritative)
The following rules are currently enforced by ValidationEngine.

| rule_id | name | severity | location_type | message |
|---|---|---|---|---|
| ENG-001 | Missing Entry Node | error | engine | Engine must define entry_node_id. |
| ENG-003 | Cycle Detected | error | engine | Engine graph must be DAG. |
| NODE-001 | Duplicate node_id | error | engine | Duplicate node_id detected. |
| CH-001 | Invalid Channel | error | engine | Channel references invalid node. |
| DET-001 | Determinism Missing | error | engine | Determinism config required. |
| DET-002 | Provider Missing | error | node | provider_ref required. |
| DET-003 | Model Missing | error | node | model required. |
| DET-004 | Temperature Missing | error | node | temperature required. |
| DET-005 | Seed Missing | error | node | seed required. |
| DET-006 | Prompt Missing | error | node | prompt_ref required. |
| DET-007 | Invalid Temperature Range | error | node | temperature must be between 0 and 2. |

## Domains
ENG, ENT, CH, FLOW, NODE, PIPE, SIDE, DET, TRACE

## Canonical rule_ids
- ENG-001..008
- ENT-001..005
- CH-001..005
- FLOW-001..005
- NODE-001..006
- PIPE-001..005
- SIDE-001..003
- DET-001..007
- TRACE-001..004

---

## Current Validation Scope (v2)

ValidationEngine currently enforces:

### Engine Structural Constraints
- Entry node existence
- DAG constraint
- Duplicate node_id detection
- Channel reference integrity

### Determinism Preconditions
- Engine-level determinism configuration presence
- Node-level provider_ref presence
- Node-level model presence
- Node-level temperature presence
- Node-level seed presence
- Node-level prompt_ref presence
- Temperature range validity (0 ≤ temperature ≤ 2)

---

## Stability Rule

- rule_id values MUST remain stable across minor and patch changes.
- If rule semantics change, the spec version MUST be incremented appropriately.
- A new rule_id MUST be introduced if semantic continuity cannot be preserved.

---

# Archived Initial Version (Preserved)

# Validation Rule Catalog
Archived-Version: v1.0.0
Status: Official Contract

Purpose:
Defines the canonical set of rule_id values for Nexa v1 validation.
Rule IDs are stable identifiers. They must not change unless semantics change.

----------------------------------------------------------------------
Conventions
- Prefix domains:
  - ENG: Engine-level structural rules
  - ENT: Entry policy rules
  - CH:  Channel / schema compatibility rules
  - FLOW: Flow/control rules
  - NODE: Node contract rules
  - PIPE: Pre/Core/Post stages rules
  - SIDE: Side-effect policy rules
  - DET: Determinism/reproducibility rules
  - TRACE: Trace model rules (validation-time structural requirements)

- Severity guidance (v1 default):
  - All rules below are ERROR unless explicitly marked WARNING.

----------------------------------------------------------------------
ENG Rules (Engine Structural Constraints)
- ENG-001 (ERROR) Missing Entry Node (0 entry)
- ENG-002 (ERROR) Multiple Entry Nodes (>=2 entry)
- ENG-003 (ERROR) Cycle Detected (DAG violation)
- ENG-004 (ERROR) Dynamic Structure Mutation Declared/Detected (v1 forbidden)
- ENG-005 (ERROR) Hidden Execution Logic Outside Nodes
- ENG-006 (ERROR) Revision Integrity Violation (in-place mutation / no new revision)
- ENG-007 (ERROR) Structural Fingerprint Missing/Invalid
- ENG-008 (ERROR) Engine Graph Missing Node/Channel Definitions

----------------------------------------------------------------------
ENT Rules (Entry Policy)
- ENT-001 (ERROR) Entry Node Missing Input Schema
- ENT-002 (ERROR) Entry Node Missing Output Schema
- ENT-003 (ERROR) External Input Schema Mismatch (type/shape)
- ENT-004 (ERROR) Default Input Injection Is Implicit (not declared)
- ENT-005 (ERROR) Default Input Not Recorded Requirement Missing

----------------------------------------------------------------------
CH Rules (Channel + Schema Compatibility)
- CH-001 (ERROR) Channel References Missing Node (src/dst)
- CH-002 (ERROR) Channel Direction Invalid (input→output reverse)
- CH-003 (ERROR) Output→Input Schema Type Mismatch
- CH-004 (ERROR) Implicit Coercion Required (v1 forbidden)
- CH-005 (ERROR) Channel Missing Port/Field Mapping (if mapping model exists)

----------------------------------------------------------------------
FLOW Rules (Control Semantics)
- FLOW-001 (ERROR) Flow References Missing Node
- FLOW-002 (ERROR) Flow Mutates Data (violates Flow/Channel separation)
- FLOW-003 (ERROR) Channel Encodes Control Logic (violates separation)
- FLOW-004 (WARNING) Unreachable Node Detected (advisory in v1)
- FLOW-005 (WARNING) Dead Branch Detected (statistical; advisory)

----------------------------------------------------------------------
NODE Rules (Unified Node Abstraction)
- NODE-001 (ERROR) Duplicate node_id within Engine
- NODE-002 (ERROR) Node Missing Input Schema
- NODE-003 (ERROR) Node Missing Output Schema
- NODE-004 (ERROR) Node Declares Async Execution (v1 forbidden)
- NODE-005 (ERROR) Node Attempts Structural Control (mutate Flow/Engine)
- NODE-006 (ERROR) Node Returns Unstructured Result / Silent Failure Policy Violation

----------------------------------------------------------------------
STAGE Rules (Pre/Core/Post Stages)
- PIPE-001 (ERROR) Pre Stage Missing/Bypassed
- PIPE-002 (ERROR) Core Stage Missing
- PIPE-003 (ERROR) Post Stage Missing/Bypassed
- PIPE-004 (ERROR) Post Not Guaranteed on Failure
- PIPE-005 (ERROR) Status Not Resolved in Post

----------------------------------------------------------------------
SIDE Rules (Side-Effect Policy)
- SIDE-001 (ERROR) Node Declares Side-Effect Capability (v1 forbidden)
- SIDE-002 (ERROR) IO Operation Detected/Requested (file/db/network)
- SIDE-003 (ERROR) Shared Mutable State Mutation Detected/Requested

----------------------------------------------------------------------
DET Rules (Determinism & Reproducibility)
- DET-001 (ERROR) Determinism Configuration Missing
- DET-002 (ERROR) Model Identifier Missing (name/provider)
- DET-003 (ERROR) Model Version Missing
- DET-004 (ERROR) Temperature/Stochastic Param Missing
- DET-005 (ERROR) Random Seed Used But Not Recorded
- DET-006 (ERROR) Prompt Reference/Hash Missing (when AI node exists)
- DET-007 (WARNING) Environment Drift Detected (advisory)

----------------------------------------------------------------------
TRACE Rules (Trace Model Requirements Declared Pre-Execution)
- TRACE-001 (ERROR) Trace Schema Definition Missing
- TRACE-002 (ERROR) Node State Coverage Requirement Missing (must include non-executed nodes)
- TRACE-003 (ERROR) Pre/Core/Post Status Fields Missing
- TRACE-004 (ERROR) Immutability Guarantee Missing (declared contract absent)

----------------------------------------------------------------------
Stability Rule
- rule_id values must remain stable across minor/patch changes.
- If rule semantics change, increment the corresponding spec SemVer MINOR/MAJOR,
  and introduce a new rule_id if necessary.

End of Validation Rule Catalog v1.0.0
