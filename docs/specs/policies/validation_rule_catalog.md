Spec ID: validation_rule_catalog
Version: 1.2.0
Status: Partial
Category: policies
Depends On:

# Validation Rule Catalog
Version: 1.2.0
Status: Official Contract

Purpose:
Standard catalog of rule_id values for Nexa v1 validation.

### Implemented Rules (Authoritative)
The following rules are currently enforced by ValidationEngine (code).

| rule_id | name | severity | location_type | message |
|---|---|---|---|---|
| ENG-001 | Missing Entry Node | error | engine | Engine must define exactly one entry_node_id. |
| NODE-001 | Duplicate node_id | error | engine | Duplicate node_id detected in EngineStructure. |
| CH-001 | Channel References Missing Node | error | engine | Channel references undefined src or dst node_id. |
| ENG-003 | Cycle Detected | error | engine | Engine graph must be a DAG (cycle detected). |


## Domains
ENG, ENT, CH, FLOW, NODE, PIPE, SIDE, DET, TRACE

## Canonical rule_ids (v1)
- ENG-001..008
- ENT-001..005
- CH-001..005
- FLOW-001..017 (006..017 reserved, see Control-Flow Rule Addendum v1.2.0)
- NODE-001..006
- PIPE-001..005
- SIDE-001..003
- DET-001..007
- TRACE-001..004


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

---

## Control-Flow Rule Addendum v1.2.0

The following control-flow-oriented rules are reserved or clarified by:

`docs/specs/execution/circuit_graph_control_flow_contract.md`

### Active clarification

| rule_id | status | severity | meaning |
|---|---|---:|---|
| ENG-003 | implemented | error | raw graph cycle / DAG violation |
| ENG-004 | cataloged | error | dynamic structure mutation declared/detected |
| NODE-005 | cataloged | error | node attempts structural control |
| FLOW-003 | cataloged | error | channel encodes hidden control logic |
| FLOW-004 | cataloged | warning | unreachable node detected |
| FLOW-005 | cataloged | warning | dead branch detected |

### Planned / reserved future anchors

| rule_id | status | severity | meaning |
|---|---|---:|---|
| FLOW-006 | reserved | error | unsupported conditional branch node used as executable feature |
| FLOW-007 | reserved | error | unsupported loop node used as executable feature |
| FLOW-008 | reserved | error | ambiguous output binding across fan-in |
| FLOW-009 | reserved | error | invalid branch decision input |
| FLOW-010 | reserved | error | ambiguous branch selection policy |
| FLOW-011 | reserved | error | missing branch target |
| FLOW-012 | reserved | error | missing loop termination policy |
| FLOW-013 | reserved | error | unbounded loop |
| FLOW-014 | reserved | error | invalid loop body reference |
| FLOW-015 | reserved | error | loop artifact policy missing |
| FLOW-016 | reserved | error | dependency merge missing required upstream inputs |
| FLOW-017 | reserved | warning | optional upstream dependency consumed without declaration |

Reserved rule ids must not be treated as implemented until corresponding validator tests exist.
They are included here to prevent future branch/loop implementations from inventing conflicting status vocabulary.
