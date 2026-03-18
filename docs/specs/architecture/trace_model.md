Spec ID: trace_model
Version: 1.4.0
Status: Official Contract
Category: architecture
Depends On:

# Trace Model Specification

Purpose:
Defines the format of execution evidence (Trace).
Trace is the **only execution evidence** of Nexa and is the canonical source for debugging/reproducibility/audit/statistics.

---

1. Core Requirements (v1)

---

Trace MUST satisfy the following:

* Graph-based: A record MUST exist for **all nodes** in the Engine graph (including non-executed ones).
* Immutable: Trace MUST NOT be modified after creation.
* Complete: Pre/Core/Post states MUST be recorded per node.
* Identified:

  * execution_id (unique)
  * revision_id (structure version)
  * structural_fingerprint (structure identity hash)

---

2. ExecutionTrace (Top-level)

---

ExecutionTrace MUST include at least the following fields:

* execution_id: str

* revision_id: str

* structural_fingerprint: str

* started_at: datetime

* finished_at: datetime | null

* duration_ms: int | null

* validation_success: bool | null

* validation_violations: list[(rule_id, message)] | null  (minimum reference format)

* nodes: Mapping[node_id -> NodeTrace]  (MUST include all node_id)

* meta: dict (optional)

---

3. NodeTrace (Per-node)

---

NodeTrace MUST include at least the following fields:

* node_id: str

* node_status: NodeStatus

  * not_reached | success | failure | skipped

* pre_status: StageStatus

* core_status: StageStatus

* post_status: StageStatus

  * success | failure | skipped

* reason_code: str | null

* message: str | null

* input_snapshot: dict | null (optional)

* output_snapshot: dict | null (optional)

* meta: dict | null (optional)

---

4. Node Coverage Rule (Hard Requirement)

---

Trace MUST include all node_ids of the Engine.

* If even one node_id is missing, the Trace is invalid,
  and Validation/Execution MUST be treated as failure.

---

5. Failure Semantics (v1)

---

* If a node fails, downstream nodes MAY be recorded as node_status=skipped.
* However, skipped and not_reached have different meanings:

  * not_reached: Not reached at all in the graph/Flow (e.g., branch not selected)
  * skipped: Reachable but execution was omitted due to upstream failure/policy

---

6. Immutability Rule

---

Trace/NodeTrace MUST NOT be modified after creation.
(In Python implementations, dataclass(frozen=True) is used as the baseline.)

---

7. Validation Mapping

---

Enforced by rule_ids:

* TRACE-001
* TRACE-002
* TRACE-003
* TRACE-004

---

# Archived Initial Version (Preserved)

# Trace Model Specification

Archived-Version: v1.0.0
Status: Official Contract

Purpose:
This document defines how execution results are recorded.
Trace is the canonical runtime record of an Engine execution.

Trace is immutable once finalized.

---

1. Trace Definition

Trace is a complete graph-based snapshot of an Execution.

It must include:

* Engine revision reference
* execution_id
* input snapshot
* full Node state graph
* execution metadata
* final status

Trace is not a linear log.
Trace preserves structural topology.

---

2. Graph Preservation Rule

Trace must preserve:

* All Nodes in the Engine (executed or not)
* All Channels
* Flow rules (reference)
* Structural fingerprint reference

Linear-only trace storage is forbidden.

---

3. Node State Recording

For every Node in the Engine,
Trace must record:

* node_id
* execution status (success / failure / skipped / not_reached)
* Pre/Core/Post stage status
* start_time
* end_time
* duration
* output snapshot (if allowed by policy)
* error reason_code (if failure)

Nodes that never executed must still appear in Trace.

---

4. Execution Status Model

Allowed Node statuses:

* success
* failure
* skipped
* not_reached

Allowed Execution statuses:

* success
* failure

Partial success state is forbidden in v1.

---

5. Skip and Failure Semantics

If a Node fails:

* Downstream Nodes must be marked as skipped.
* Failure propagation must be traceable.

If Flow condition prevents execution:

* Node must be marked as skipped.
* Condition reference must be recorded.

---

6. Metadata Recording

Trace must include:

* execution_id
* revision_id
* structural fingerprint
* execution start timestamp
* execution end timestamp
* total duration
* cost metrics (if applicable)
* environment version
* determinism parameters

Missing metadata invalidates Trace.

---

7. Immutability Rule

Once Execution completes:

* Trace must become immutable.
* No modification allowed.
* No patching allowed.
* Corrections require new Execution.

---

8. Trace Integrity Rule

Trace must:

* Be internally consistent.
* Match the Engine revision used.
* Match structural fingerprint.
* Preserve Node execution ordering.

Trace inconsistency invalidates execution record.

---

9. Trace as Canonical Evidence

Trace is:

* The source of statistical analysis.
* The source of proposal generation.
* The source of audit and reproducibility.
* The source of debugging.

Any analysis must rely only on Trace.

---

10. Storage Independence

Trace format must:

* Be serializable.
* Be exportable.
* Be storage backend independent.

Persistence mechanism is implementation detail,
but Trace schema must remain stable per version.

---

Contract Rule:

Execution without full Trace generation is forbidden.

Trace is mandatory for every Execution.

End of Trace Model Specification v1.0.0

---

## Validation Mapping

Enforced by rule_ids:

* TRACE-001
* TRACE-002
* TRACE-003
* TRACE-004

================================================================================
8) Serialization Contract (Added in v1.2.0)
===========================================

1. Purpose

* ExecutionTrace must provide a deterministic serialization API suitable for:

  * artifact storage
  * diffing
  * replay/audit
  * policy comparison

2. Required APIs

* ExecutionTrace.to_dict(stable: bool = True) -> dict
* ExecutionTrace.to_json(stable: bool = True, ensure_ascii: bool = False, indent: int | None = None) -> str

3. Determinism Requirements (stable=True)

* Repeated calls MUST produce identical output for the same trace instance.
* nodes MUST be emitted in deterministic order (node_id sorted).
* datetime values MUST be emitted as ISO-8601 strings (datetime.isoformat()).
* enum values MUST be emitted as their .value string.
* meta / input_snapshot / output_snapshot MUST be JSON-safe:

  * allowed: dict (string keys only), list/tuple, str, int, float, bool, None
  * any non-JSON-safe type MUST raise TypeError (contract violation).

4. Scope

* This contract constrains *output determinism*, not internal storage.
* The specific JSON string formatting is not mandated, but stable=True MUST be deterministic.

---

8. Validation Snapshot (Optional)

---

Location:
trace.meta.validation.snapshot

Structure:
{
"snapshot_version": "1",
"applied_rules": ["<RULE_ID>", ...]
}

Rules:

* applied_rules MUST be lexicographically sorted.
* applied_rules MUST NOT contain duplicates.
* snapshot MUST NOT be included in structural_fingerprint calculation.
* snapshot is immutable once trace is finalized.

---

9. Execution Fingerprint

---

trace.execution_fingerprint MUST exist.

Definition:
execution_fingerprint =
SHA256(structural_fingerprint + ":" + environment_fingerprint)

Rules:

* structural_fingerprint MUST remain environment invariant.
* execution_fingerprint MUST change if environment_fingerprint changes.
