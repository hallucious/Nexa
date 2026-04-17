# Plugin Context I/O Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_context_io_contract.md`

## 1. Purpose

This document defines the canonical context input/output contract for plugins in Nexa.

It establishes:
- how a bound plugin reads from Working Context
- how a bound plugin writes back to Working Context
- how plugin input/output shape is represented
- how context key-space discipline is preserved
- how partial outputs, final outputs, and artifact emissions differ
- how PluginExecutor standardizes plugin-facing I/O behavior

## 2. Core Decision

1. Plugin I/O is Working Context based.
2. A plugin does not receive arbitrary runtime memory.
3. A plugin reads only explicitly bound context inputs.
4. A plugin writes only explicitly allowed context outputs.
5. Plugin I/O shape must be explicit enough for runtime, validation, trace, and future AI readers.
6. Partial output, final output, and artifact emission must remain distinguishable.

## 3. Non-Negotiable Boundaries

- Working Context boundary
- Node boundary
- Policy boundary
- Executor boundary
- Trace boundary

## 4. Core Vocabulary

- Context Input
- Context Output
- Input Extraction
- Output Emission
- Partial Output
- Final Output
- Artifact Emission

## 5. Canonical I/O Lifecycle

BoundPluginRuntime
-> Context Input Extraction
-> PluginExecutor Invocation
-> Raw Plugin Result
-> Context Output Emission
-> Optional Artifact Emission
-> Trace / Outcome Recording

## 6. Canonical Context Input Object

PluginContextInput
- input_instance_id: string
- binding_ref: string
- execution_instance_ref: string
- resolved_reads: list[ResolvedContextRead]
- normalized_input_payload: object
- input_shape_version: string
- extraction_notes: string | null

## 7. Canonical Context Output Object

PluginContextOutput
- output_instance_id: string
- binding_ref: string
- execution_instance_ref: string
- emitted_writes: list[ResolvedContextWrite]
- output_payload: object | null
- output_shape_version: string
- output_status: enum("partial", "final", "empty", "failed")
- emission_notes: string | null

## 8. Input Extraction Rules

- start from bound read declarations
- undeclared keys must not be exposed
- missing required input must be explicit
- normalization must not fabricate semantic values
- extraction must remain traceable

## 9. Output Emission Rules

- start from bound write declarations
- undeclared or disallowed writes must be blocked
- output mode must be explicit
- partial and final output must remain distinct
- emission must remain traceable and policy-enforced

## 10. Normalized Input Payload

Runtime may provide a normalized payload for convenience and executor stability, but it must derive only from allowed reads and remain reconstructable from execution truth.

## 11. Raw Plugin Result vs Emitted Output

Runtime must distinguish:
1. raw plugin return value
2. normalized runtime output payload
3. actual Working Context writes
4. artifact emissions

## 12. Partial Output vs Final Output

Partial output must never silently overwrite final output semantics.

## 13. Artifact Emission Relationship

Artifact emission must be explicit, execution-linked, and distinct from ordinary context writes.

## 14. Missing Input and Malformed Output Handling

The system must distinguish:
- required input missing
- optional input absent
- malformed input shape
- blocked extraction due to policy
- unavailable upstream input

And for output:
- shape mismatch
- disallowed target
- blocked external path
- artifact emission failure
- partial-only vs final-missing
- total output failure

## 15. Relationship to PluginExecutor

PluginExecutor must receive:
- bound runtime identity
- normalized input payload
- read/write declarations
- policy-constrained output rules
- runtime constraints

It must not invent new context authority.

## 16. Canonical Findings Categories

Examples:
- CONTEXT_INPUT_REQUIRED_MISSING
- CONTEXT_INPUT_OPTIONAL_MISSING
- CONTEXT_INPUT_POLICY_BLOCKED
- CONTEXT_OUTPUT_TARGET_DISALLOWED
- CONTEXT_OUTPUT_SHAPE_INVALID
- CONTEXT_OUTPUT_PARTIAL_ONLY
- CONTEXT_ARTIFACT_EMISSION_FAILED
- CONTEXT_EXECUTOR_RESULT_UNMAPPABLE

## 17. Explicitly Forbidden Patterns

- whole-context exposure
- undeclared writes
- final-output ambiguity
- artifact/context collapse
- silent missing-input tolerance
- executor-side authority invention

## 18. Relationship to Existing PRE / CORE / POST Stage Structure

This contract does not delete the existing PRE / CORE / POST execution-stage vocabulary used in the broader plugin direction.

Interpretation rule:
- PRE / CORE / POST remains execution-stage vocabulary
- this Context I/O contract defines execution-time data interaction boundaries inside that broader execution model
- coexistence is required unless an explicit migration document says otherwise

## 19. Relationship to Existing Plugin Contract v1.1.0

This document should be read as a cumulative refinement of the existing plugin direction based on deterministic capability components, Working Context, and PluginExecutor.

It does not claim that the older direction has been replaced by silence.

## 20. Canonical Summary

- Plugin I/O is Working Context based.
- A bound plugin reads only explicitly allowed context input.
- A bound plugin writes only explicitly allowed context output.
- Raw plugin return value, context output, and artifact emission are distinct layers.
- Partial output and final output must remain distinguishable.

## 21. Final Statement

A plugin in Nexa should not read arbitrary runtime data and should not dump arbitrary output back into the system.

It should read explicit Working Context inputs, produce governed outputs, and emit traceable results under a stable context I/O contract.

That is the canonical meaning of Plugin Context I/O in Nexa.
