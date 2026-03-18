Spec ID: terminology
Version: 1.0.1
Status: Active
Category: foundation
Depends On:

# Terminology Specification
Version: 1.0.1
Status: Official Contract

Purpose:
Defines Nexa’s core terminology (Engine/Node/Channel/Flow/Trace, etc.).
All specs are written based on this terminology.


## Version Notation Rule
- The official document version format is fixed as `Version: X.Y.Z` (SemVer, **without** the `v` prefix).
- Notation such as `v1.0.0` is allowed only for **references/quotes/archives inside the document body**; in that case, use a different key such as `Archived-Version:` or `Example-Version:`.
- Automated contract tests parse the `^Version:` line in active spec documents, so a second `Version:` line in the body can break synchronization.
## Definitions
- Engine: An executable graph unit composed of Nodes, Channels, and Flows (with Revision/Execution/Trace).
- Node: The minimum execution unit inside an Engine (follows the Pre/Core/Post pipeline).
- Channel: A **data path** that delivers output from one Node to another Node’s input.
- Flow: A **control rule** that defines execution order (data transformation belongs to the Channel/Node domain).
- Revision: An immutable structural version of the Engine created when the structure changes.
- Execution: A single run of the Engine (with a unique execution_id).
- Trace: A **graph-based** record of execution results (including unexecuted nodes, immutable).

## Validation Mapping
Related rule domains: ENG, NODE, CH


---

# Archived Initial Version (Preserved)

# Terminology Specification
Archived-Version: v1.0.0
Status: Official Contract

Purpose:
This document defines the canonical terminology of Nexa.
All structural, execution, and validation rules depend on these definitions.
No other interpretation is allowed.

----------------------------------------------------------------------
1. Engine

Definition:
An Engine is a complete executable graph composed of Nodes and Channels.

Properties:
- Has a single entry point.
- Has a defined graph structure.
- Is versioned (revision-based).
- Can be executed.
- Produces a Trace.
- Is subject to structural constraints.

An Engine is the smallest independently executable structural unit.

----------------------------------------------------------------------

2. Node

Definition:
A Node is the smallest functional execution unit inside an Engine.

Properties:
- Has a unique identifier within an Engine.
- Has defined input schema.
- Has defined output schema.
- Executes synchronously (v1 constraint).
- Follows Pre/Core/Post execution stages.
- Must obey side-effect policy.

A Node does not contain other Engines (v1 constraint).

----------------------------------------------------------------------

3. Channel

Definition:
A Channel is a directional data path connecting one Node’s output
to another Node’s input.

Properties:
- Data-only.
- No control logic.
- Must satisfy type compatibility.
- Cannot form cycles unless explicitly allowed by future spec.

Channels represent data flow only.

----------------------------------------------------------------------

4. Flow

Definition:
Flow defines execution control rules between Nodes.

Properties:
- Determines execution order.
- May contain branching rules.
- May contain conditional logic.
- Is separate from Channel (data flow).

Flow represents control logic only.

----------------------------------------------------------------------

5. Execution

Definition:
Execution is a single runtime invocation of an Engine.

Properties:
- Has unique execution_id.
- Produces a full Trace.
- Stores input snapshot.
- Stores structural revision reference.
- Stores execution metadata (time, cost, status).

----------------------------------------------------------------------

6. Trace

Definition:
Trace is the complete recorded state of an Engine execution.

Properties:
- Graph-based (not linear-only).
- Includes executed Nodes.
- Includes skipped Nodes.
- Includes failed Nodes.
- Includes Pre/Core/Post status.
- Immutable after completion.

Trace is the canonical execution record.

----------------------------------------------------------------------

7. Revision

Definition:
Revision is a structural version of an Engine.

Properties:
- Created upon structural modification.
- Immutable once published.
- Linked to execution records.
- Comparable via structural fingerprint.

----------------------------------------------------------------------

8. Proposal

Definition:
A Proposal is a suggested structural modification generated
by analysis or AI reasoning.

Properties:
- Never auto-applied.
- Must pass structural constraints.
- Must create a new Revision upon approval.
- Linked to statistical evidence when applicable.

----------------------------------------------------------------------

9. Structural Fingerprint

Definition:
A Structural Fingerprint is a deterministic representation
of an Engine’s structural identity.

Properties:
- Derived from Nodes + Channels + Flow.
- Used for similarity comparison.
- Used for statistical grouping.
- Independent from execution data.

----------------------------------------------------------------------

10. Side Effect

Definition:
Any external state mutation beyond Node output.

v1 Policy:
- Pure-first.
- Side effects are disallowed unless explicitly defined
  by future Action Node specification.

----------------------------------------------------------------------

11. Determinism

Definition:
The degree to which identical inputs and structure
produce identical outputs.

v1 Policy:
- Determinism preferred.
- Non-determinism allowed but must be controlled.
- Execution metadata must record randomness parameters.

----------------------------------------------------------------------

Contract Rule:

All other specifications must use the terminology defined here.
Any contradiction invalidates the dependent spec.

End of Terminology Spec v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Related rule domains:
- ENG (engine-level terminology consistency)
- NODE (node identity consistency)
- CH (channel terminology correctness)
