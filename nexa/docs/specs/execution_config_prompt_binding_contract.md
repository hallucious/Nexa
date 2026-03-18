Spec ID: execution_config_prompt_binding_contract
Version: 1.0.0
Status: Partial
Category: misc
Depends On:


# ExecutionConfig Prompt Binding Contract

Version: 1.0.0

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

## Runtime Resolution Algorithm

NodeExecutionRuntime MUST resolve prompts using the following algorithm.

1. Read prompt_ref from ExecutionConfig
2. If prompt_version exists:
   PromptRegistry.get(prompt_ref, prompt_version)
3. If prompt_version does not exist:
   PromptRegistry.get(prompt_ref)  (latest version)
4. The registry returns a PromptSpec
5. PromptSpec.render(context) is executed
6. The rendered prompt string is sent to ProviderExecutor

---

## Rendering Contract

PromptSpec.render(context) MUST:

- Validate required inputs
- Enforce type constraints from inputs_schema
- Produce a final prompt string

Errors during render MUST raise PromptSpecError.

---

## Failure Conditions

Runtime MUST stop execution if:

- prompt_ref does not exist
- prompt_version does not exist
- prompt file cannot be loaded
- PromptSpec.render fails

These failures are considered **configuration errors**.

---

## Example ExecutionConfig

{
  "config_id": "answer.basic",
  "version": "1.0.0",
  "prompt_ref": "g1_design",
  "prompt_version": "v1",
  "provider_ref": "provider.openai",
  "output_mapping": {
    "answer": "answer"
  }
}

---

## Runtime Flow

ExecutionConfig
↓
PromptRegistry.get(prompt_ref, prompt_version)
↓
PromptSpec
↓
PromptSpec.render(context)
↓
ProviderExecutor
↓
NodeExecutionRuntime output

---

## Compatibility

Legacy prompt nodes are supported through the legacy execution plan adapter.

Legacy nodes:
prompt string → format(**context)

Modern nodes:
PromptRegistry → PromptSpec → render()

---

## Future Extensions

This contract allows future additions:

- prompt policies
- prompt caching
- prompt audit logs
- prompt A/B testing

All extensions MUST remain backward compatible with this contract.
