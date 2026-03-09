# Prompt Contract
Version: 1.0.0


-   Spec ID: PROMPT-CONTRACT
-   Version: 1.0.0
-   Status: Draft
-   Scope: Structured prompt definition used by NODE-EXEC Core stage
-   Related Specs: NODE-EXEC@1.0.0, AI-PROVIDER@1.0.0

------------------------------------------------------------------------

## 1. Purpose

This contract formalizes Prompt as a first-class platform artifact. A
Prompt is not a raw string. It is a versioned, structured instruction
document used by AI Provider within Node Core execution.

------------------------------------------------------------------------

## 2. Terminology

-   PromptSpec: Versioned prompt definition object.
-   Template: Parameterized prompt body.
-   Variables Schema: Definition of allowed variables and types.
-   Rendered Prompt: Final string passed to AI Provider.
-   prompt_hash: Deterministic hash of template + variables.

------------------------------------------------------------------------

## 3. Contract Invariants

1.  Every Prompt MUST have a stable `prompt_id`.
2.  Every Prompt MUST have a semantic `version`.
3.  Template MUST be immutable within a version.
4.  Variables MUST conform to declared schema.
5.  Rendering MUST be deterministic given same inputs.
6.  Prompt MUST NOT contain embedded secrets.

------------------------------------------------------------------------

## 4. PromptSpec Schema

Required fields:

-   `prompt_id: string`
-   `version: string` (SemVer)
-   `template: string`
-   `variables_schema: object`
-   `description: string`

Optional fields:

-   `metadata: object | null`
-   `tags: array[string] | null`

Example:

{ "prompt_id": "summarize_v1", "version": "1.0.0", "template":
"Summarize the following text:`\n`{=tex}`\n{{input_text}}`{=tex}",
"variables_schema": { "input_text": "string" }, "description": "Basic
summarization prompt" }

------------------------------------------------------------------------

## 5. Rendering Rules

1.  Rendering MUST replace declared variables only.
2.  Undefined variables MUST raise validation error.
3.  Extra variables MUST raise validation error.
4.  Rendering MUST produce a string.
5.  Rendering MUST be side-effect free.

------------------------------------------------------------------------

## 6. Hashing Rule

`prompt_hash` MUST be SHA256 of:

template + sorted(variable_names)

This enables savefile reproducibility and trace linking.

------------------------------------------------------------------------

## 7. Node Integration Rules

During NODE-EXEC Core stage:

1.  Node MUST load PromptSpec.
2.  Node MUST validate variables against schema.
3.  Node MUST render prompt.
4.  Rendered string is passed to AI Provider.
5.  prompt_id, version, prompt_hash SHOULD be recorded in CT-TRACE.

------------------------------------------------------------------------

## 8. Observability

Trace SHOULD include:

-   prompt_id
-   version
-   prompt_hash

Prompt content MAY be redacted depending on policy.

------------------------------------------------------------------------

## 9. Non-Goals (v1.0.0)

-   Prompt chaining
-   Dynamic prompt mutation
-   Embedded tool instructions
-   Streaming prompt fragments

------------------------------------------------------------------------

End of PROMPT-CONTRACT v1.0.0
