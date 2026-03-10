Spec ID: node_execution_contract
Version: 1.1.0
Status: Active
Category: architecture
Depends On:
# Node Execution Contract
Version: 1.1.0

- Spec ID: NODE-EXEC
- Scope: Node runtime contract inside Engine; defines deterministic execution stages and responsibilities.

## 1. Purpose
Define the canonical execution contract for a Node. The contract standardizes:
- execution stages and allowed actions per stage
- responsibilities for AI calls and Plugin calls
- state mutation rules (return-value only)
- baseline inputs/outputs required for integration with Flow/Circuit and Trace/Observability

## 2. Terminology
- Node: an execution unit that transforms inputs to outputs under an Engine-managed contract.
- AI: the worker that performs the primary reasoning/generation work.
- Prompt: the work instruction used by AI.
- Plugin: an external tool callable by the Node under contract constraints.
- Circuit/Flow: the connection rules that route Node outputs to subsequent Nodes.
- Engine: the runtime platform that executes circuits/flows and enforces contracts.

## 3. Contract Invariants
1. Node stages are fixed: Pre → Core → Post.
2. AI calls are allowed **only** in Core.
3. Plugin calls are allowed in Pre/Core/Post.
4. Plugins **must not** mutate Node/Engine state directly; all changes are applied via explicit return values.
5. Default mode is orchestration: the Node defines the plugin call sequence.
6. Tool-calling (AI-directed plugin selection) is **out of scope** for v1.0.0 as a normative contract. v1 implementations MAY use internal/adaptor-level tool-call shapes for testing or experimentation, but such shapes are not part of the stable public contract unless promoted via a versioned spec change with explicit guardrails.

## 4. Stage Responsibilities

### 4.1 Pre
Allowed:
- input validation / normalization
- prompt resolution (template rendering, variable binding)
- plugin calls for data preparation (e.g., fetch, lookup)
Not allowed:
- AI calls

### 4.2 Core
Allowed:
- AI call (primary execution)
- plugin calls used as tools in support of Core execution
Not allowed:
- bypassing AI call if the Node is classified as AI-required (policy may define exceptions)

### 4.3 Post
Allowed:
- output validation / normalization
- persistence or notifications via plugins
- trace / observability emission (finalization)
Not allowed:
- AI calls

## 5. Node I/O (Minimum Requirements)

### 5.1 NodeInput (minimum fields)
- node_id: string (required)
- circuit_id: string (required)
- execution_id: string (required)
- data: object/dict (required) — channel-passed payload from upstream nodes
- context: object/dict (optional) — immutable execution context
- metadata: object/dict (optional) — auxiliary debug/observability data

### 5.2 NodeResult (minimum fields)
- success: boolean (required)
- output: object/dict | null (required)
- reason_code: string | null (required)
- error: string | null (required)
- metrics: object (required)
  - latency_ms: integer (required)
  - tokens_used: integer | null (optional)

## 6. Failure Taxonomy (High-level)
Node must map failures to the platform taxonomy (ReasonCode catalog). At minimum, support:
- VALIDATION: input_schema_error, output_schema_error
- AI: timeout, provider_error, policy_refusal
- PLUGIN: crash, timeout, invalid_output
- FLOW: condition_not_matched
- SYSTEM: unexpected_exception

## 7. Trace & Observability Requirements
- Node execution must be traceable at least at stage boundaries.
- Trace MUST be able to answer:
  - which node ran, in what order
  - success/failure and reason_code
  - selected edge/condition outcome (when Flow is conditional)
- Prompt fingerprints and detailed tool-call logs are optional extensions for v1.1+.

## 8. Non-goals (v1.0.0)
- AI-directed tool calling (tool-calling) and its guardrails
- parallel execution semantics
- distributed execution, sandbox hardening beyond current policy
