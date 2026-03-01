# Terminology Specification
Version: 1.0.0
Status: Official Contract

Purpose:
Hyper-AI의 핵심 용어(Engine/Node/Channel/Flow/Trace 등)를 정의한다.
모든 spec은 이 용어를 기준으로 작성된다.

## Definitions
- Engine: Node와 Channel, Flow로 구성된 실행 가능한 그래프 단위(Revision/Execution/Trace를 가진다).
- Node: Engine 내부 최소 실행 단위(Pre/Core/Post 파이프라인을 따른다).
- Channel: Node 출력 → 다른 Node 입력으로 전달되는 **데이터 경로**.
- Flow: 실행 순서를 정의하는 **제어 규칙**(데이터 변형은 Channel/Node 영역).
- Revision: 구조 변경 시 생성되는 Engine의 구조 버전(불변).
- Execution: Engine 1회 실행(고유 execution_id).
- Trace: 실행 결과의 **그래프 기반** 기록(미실행 노드 포함, 불변).

## Validation Mapping
Related rule domains: ENG, NODE, CH


---

# Archived Initial Version (Preserved)

# Terminology Specification
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines the canonical terminology of Hyper-AI.
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
- Follows Pre/Core/Post execution pipeline.
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