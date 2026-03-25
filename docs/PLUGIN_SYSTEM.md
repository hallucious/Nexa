# Plugin System

Plugins extend nodes with non-AI computation capabilities.

See contracts:
* `docs/specs/contracts/plugin_contract.md`
* `docs/specs/contracts/plugin_registry_contract.md`

---

# Plugin Responsibilities

* data transformation
* ranking outputs
* formatting results
* validation and evaluation
* filtering

---

# When Plugins Execute

Plugins execute within node phases:

* **pre**: data preparation before the AI call
* **core**: tool calls alongside the AI call
* **post**: output processing after the AI call

The order in which a plugin runs depends on the node's execution configuration, not a fixed system pipeline.

---

# Plugin Write Restrictions (Strict)

```text
plugin.<plugin_id>.*    ← allowed

prompt.*                ← forbidden
provider.*              ← forbidden
output.*                ← forbidden
artifact.*              ← forbidden
input.*                 ← forbidden
```

---

# Plugin Result Surface

There are currently two practical result surfaces in the runtime line:

1. `src/platform/plugin.py`
   * safe execution wrapper for contract-oriented plugin execution
   * returns the richer plugin execution envelope used by savefile-aligned execution

2. `src/platform/plugin_result.py`
   * lightweight normalization/result bridge used by `NodeExecutionRuntime`
   * preserves output / artifacts / trace handling for graph execution

This split is currently intentional in the accepted runtime line.

---

# Current Plugin Runtime Roles

## Practical runtime execution side

* `src/engine/node_execution_runtime.py`
* `src/platform/plugin_result.py`

## Runtime bridge loader for savefile entry references

* `src/platform/plugin_auto_loader.py`

This loader resolves entry strings such as `module_name.function_name` for savefile/plugin-entry execution paths.

## Canonical versioned registry side

* `src/platform/plugin_version_registry.py`

This registry remains the source for explicit `(plugin_id, plugin_version)` resolution used by versioned capability negotiation and registry-based plugin flows.

## Execution contract / safe execution side

* `src/platform/plugin.py`

## Bundle / savefile compatibility side

* `src/contracts/nex_plugin_resolver.py`
* `src/contracts/nex_plugin_integration.py`
* `src/contracts/savefile_executor_aligned.py`

---

# Removed Legacy Paths

The following legacy ownership paths are no longer part of the active runtime line:

* `src/engine/plugin_loader.py`
* `src/platform/plugin_registry.py`

New plugin work must not recreate them.

---

# Safety Model

Plugins must:
* avoid modifying core runtime structures
* avoid side effects outside the allowed namespace
* produce deterministic results given the same inputs

---

End of Plugin System Document
