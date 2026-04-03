Spec ID: context_key_schema_contract
Version: 1.1.0
Status: Active
Category: contracts
Depends On: docs/specs/architecture/context_key_schema.md

# Context Key Schema Contract

## 1. Purpose

This contract locks the canonical format and allowed domains for all Working Context keys in Nexa.

Working Context keys are the shared data namespace through which nodes, prompts, providers, plugins, and the runtime exchange values during circuit execution.

Without a stable key schema, the following degrade:
- dependency graph resolution
- plugin namespace isolation
- execution trace readability
- determinism guarantees
- protection against pipeline fallback

## 2. Canonical Key Format

All Working Context keys must conform to one of the following canonical forms:

```
input.<field>
output.<field>
<context-domain>.<resource-id>.<field>
```

where the three-segment form is used only for:

```
prompt
provider
plugin
system
```

Canonical regex:

```
^(?:input\.[a-z0-9_]+|output\.[a-z0-9_]+|(?:prompt|provider|plugin|system)\.[a-z0-9_]+\.[a-z0-9_]+)$
```

## 3. Allowed Domains

| Domain   | Description                        |
|----------|------------------------------------|
| input    | External inputs to the circuit     |
| prompt   | Rendered prompt outputs            |
| provider | AI provider outputs                |
| plugin   | Plugin execution results           |
| system   | Runtime internal values            |
| output   | Final node output values           |

No other top-level domain is permitted.

## 4. Identifier Segment Rules

Both `<resource-id>` and `<field>` must:
- contain only lowercase letters, digits, and underscores
- match the regex fragment `[a-z0-9_]+`
- not be empty

Uppercase letters, hyphens, spaces, and dots within a segment are forbidden.

## 5. Canonical Examples

The following keys are canonical and must remain valid:

```
input.text
prompt.main.rendered
provider.openai.output
plugin.search.result
system.trace.status
output.value
```

## 6. Plugin Write Restriction

Plugins may only write to keys under the `plugin` domain:

```
plugin.<plugin_id>.<field>
```

Writing to any of the following domains is forbidden for plugins:

```
input.*
prompt.*
provider.*
system.*
output.*
```

This restriction protects the integrity of the runtime state and prevents plugins from corrupting provider outputs, prompt state, or final outputs.

## 7. Enforcement

This contract is enforced by:
- `src/contracts/context_key_schema.py` — constants, regex, and validator
- `tests/test_context_key_schema_contract.py` — automated contract tests
- `src/contracts/spec_versions.py` — version registration

## 8. Version History

| Version | Change                        |
|---------|-------------------------------|
| 1.1.0   | Domain-aware key family: input/output use short form; prompt/provider/plugin/system remain resource-scoped |
| 1.0.0   | Initial contract definition   |
