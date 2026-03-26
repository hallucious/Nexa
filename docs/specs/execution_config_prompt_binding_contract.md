Spec ID: execution_config_prompt_binding_contract
Version: 1.1.0
Status: Active
Category: misc
Depends On:


# ExecutionConfig Prompt Binding Contract

Version: 1.1.0

This document extends the existing **ExecutionConfig Schema Contract** and defines
how ExecutionConfig interacts with the Prompt system (PromptRegistry / PromptSpec).

This specification **does not replace** execution_config_schema_contract.md.
Instead it adds runtime semantics for prompt resolution.

---

## Relationship to Existing Specs

This spec builds on:

- execution_config_schema_contract.md
- prompt_contract.md
- provider_contract.md
- node_execution_contract.md

Execution order:

ExecutionConfig JSON
→ Schema Validation
→ Canonicalization
→ Registry Resolution
→ Prompt Resolution (this spec)
→ Provider Execution

---

## Prompt Resolution Fields

ExecutionConfig may contain the following prompt fields.

### prompt_ref

Type: string

Identifier of the prompt stored in the prompt registry.

Example:

g1_design

Registry path:

registry/prompts/{prompt_ref}/vX.md

---

### prompt_version

Type: string (optional)

Specifies the version of the prompt file.

Example:

v1

If omitted:

PromptRegistry MUST resolve the latest available version.

---

## Runtime Prompt Path Boundary

NodeExecutionRuntime uses a two-path resolution model.

### Path A — Modern Path (canonical)

Used when the PromptRegistry can resolve prompt_ref, OR when prompt_version is explicitly set.

Behavior:
1. PromptRegistry.get(prompt_ref, prompt_version) is called
2. A PromptSpec is returned
3. PromptSpec.render(inputs) is executed
4. The rendered string is sent to ProviderExecutor

Failure behavior:
- If prompt_version is set and the file is missing → ValueError (hard fail, no fallback)
- If the file is found but render fails → ValueError (hard fail)

### Path B — Bounded Legacy Compatibility Path

Used when:
- prompt_version is NOT set
- AND the PromptRegistry cannot resolve prompt_ref (FileNotFoundError or RuntimeError)

Behavior:
- Falls back to a deterministic placeholder: "{prompt_ref}:{context}"
- This path is explicit and bounded — it is NOT silent failure
- It exists for execution configs that use symbolic prompt_ref values without a registry-backed spec

Rules:
- New execution configs MUST use Path A (registry-backed prompt spec)
- Path B is retained only for symbolic prompt_ref values in legacy and test configs
- Path B is NOT triggered when prompt_version is set (that always hard-fails)

---

## Runtime Resolution Algorithm

NodeExecutionRuntime resolves prompts using the following algorithm.

1. Read prompt_ref from ExecutionConfig
2. If prompt_version exists:
   PromptRegistry.get(prompt_ref, prompt_version) — hard fail if not found
3. If prompt_version does not exist:
   PromptRegistry.get(prompt_ref)  (latest version)
   — if not found: use bounded legacy fallback "{prompt_ref}:{context}"
4. PromptSpec.render(inputs) is executed
5. The rendered prompt string is sent to ProviderExecutor

---

## Rendering Contract

PromptSpec.render(context) MUST:

- Validate required inputs
- Enforce type constraints from inputs_schema
- Produce a final prompt string

Errors during render MUST raise PromptSpecError, which is re-raised as ValueError by the runtime.

---

## Failure Conditions

Runtime MUST stop execution if:

- prompt_version is set and prompt_ref does not exist in registry
- prompt_version is set and version file is not found
- prompt file cannot be loaded (PromptLoaderError)
- PromptSpec.render fails (PromptSpecError)

These failures are considered **configuration errors**.

The bounded legacy fallback (Path B) is NOT a failure — it is deterministic behavior
for symbolic prompt_ref values without a registry entry.

---

## Prompt Subsystem Architecture

Two separate prompt subsystems coexist in the repository.

### src/platform/prompt_*.py — Runtime-facing modern layer

Used by: NodeExecutionRuntime
PromptSpec format: format-string {var} with Python type schema
PromptRegistry: loads from registry/prompts/{id}/vX.md with PROMPT_SPEC header

### legacy_prompts/* — Domain-level legacy/test layer

Used by: test_step79, test_prompt_registry_contract, test_step80
PromptSpec format: {{var}} mustache-style with JSON Schema validation
Contracts: prompt_hash, render(variables=...) API

These two layers are NOT unified. The split is intentional and documented.
New runtime-level features MUST use src/platform/prompt_*.py.
The legacy_prompts/* layer is retained only for its bounded legacy/test contract behavior and is no longer part of `src/`.

---

## Example ExecutionConfig — Modern Path

{
  "config_id": "answer.basic",
  "version": "1.0.0",
  "prompt_ref": "g1_design",
  "prompt_version": "v1",
  "prompt_inputs": {"question": "input.question"},
  "provider_ref": "provider.openai",
  "output_mapping": {
    "answer": "answer"
  }
}

---

## Example ExecutionConfig — Legacy Compatibility Path

{
  "config_id": "legacy.node",
  "prompt_ref": "symbolic.prompt",
  "provider_ref": "provider.openai"
}

Behavior: If "symbolic.prompt" is not in the registry and no version is set,
falls back to deterministic "{symbolic.prompt}:{context}".

---

## Runtime Flow

ExecutionConfig
↓
PromptRegistry.get(prompt_ref, prompt_version?)
↓ (success)                ↓ (not found + no version set)
PromptSpec                 Legacy fallback "{prompt_ref}:{context}"
↓
PromptSpec.render(inputs)
↓
ProviderExecutor
↓
NodeExecutionRuntime output

---

## Future Extensions

This contract allows future additions:

- prompt policies
- prompt caching
- prompt audit logs
- prompt A/B testing

All extensions MUST remain backward compatible with this contract.
Full legacy path (Path B) removal is a future task requiring migration of all
symbolic prompt_ref usages to registry-backed specs.
