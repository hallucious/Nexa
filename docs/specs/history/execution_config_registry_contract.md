
# ExecutionConfig Registry Contract

Version: 1.0.0

This specification defines how ExecutionConfig definitions are stored,
resolved, and loaded by the runtime engine.

This spec extends:

- execution_config_schema_contract.md
- execution_config_canonicalization_contract.md

and integrates with:

- node_execution_contract.md
- graph_execution_contract.md
- provider_contract.md
- prompt_contract.md

---

# 1. Purpose

ExecutionConfigRegistry is responsible for resolving
ExecutionConfig definitions referenced by nodes in a circuit.

Nodes never embed execution logic directly.
Instead they reference an ExecutionConfig through:

execution_config_ref

The registry loads and validates the configuration before execution.

---

# 2. Registry Directory Structure

ExecutionConfig definitions are stored in the repository registry.

Example:

registry/
  execution_configs/
    answer.basic/
      1.0.0.json
      1.1.0.json
    reasoning.chain/
      1.0.0.json

Rules:

- config_id = directory name
- version = JSON filename
- version MUST follow semantic versioning

---

# 3. ExecutionConfig JSON Example

{
  "config_id": "answer.basic",
  "version": "1.0.0",
  "prompt_ref": "g1_design",
  "prompt_version": "v1",
  "provider_ref": "provider.openai",
  "pre_plugins": [],
  "post_plugins": [],
  "validation_rules": [],
  "output_mapping": {
    "answer": "answer"
  }
}

---

# 4. Registry Resolution API

ExecutionConfigRegistry exposes the following interface.

resolve(config_id: str, version: Optional[str] = None) -> ExecutionConfigModel

Behavior:

version not provided
→ latest semantic version is selected

version provided
→ exact version must exist

config not found
→ ExecutionConfigNotFoundError

---

# 5. Resolution Algorithm

Resolution must follow the exact sequence below.

1. locate directory

registry/execution_configs/{config_id}

2. list version files

*.json

3. determine version

if version specified:
  select that version

else:
  select highest semantic version

4. load JSON

5. validate using schema contract

6. canonicalize using canonicalization contract

7. return ExecutionConfigModel

---

# 6. Runtime Integration

ExecutionConfigRegistry is used by NodeSpecResolver.

Runtime flow:

GraphExecutionRuntime
↓
NodeSpecResolver
↓
ExecutionConfigRegistry.resolve()
↓
ExecutionConfigModel
↓
NodeExecutionRuntime.execute()

---

# 7. Error Conditions

The registry MUST raise errors for:

missing config directory
missing version file
invalid JSON
schema validation failure
canonicalization failure

---

# 8. Determinism Requirement

Registry resolution must be deterministic.

Given identical repository state:

resolve(config_id)

must always return the same configuration.

---

# 9. Caching (Optional)

Registry implementations may cache resolved configs.

However:

cache must be invalidated if underlying files change.

---

# 10. Future Extensions

The registry design allows the following future features:

remote registry
signed configs
config policy enforcement
registry observability metrics

All extensions must remain backward compatible.
