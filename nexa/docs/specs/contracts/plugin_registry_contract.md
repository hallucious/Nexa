Spec ID: plugin_registry_contract
Version: 1.0.0
Status: Active
Category: contracts
Depends On:

## 1. Purpose

This spec defines the **Plugin Registry** contract used by the platform to:

1. Register plugins with an explicit `(plugin_id, plugin_version)` identity.
2. Resolve a plugin entry by explicit version or by `"latest"` (highest SemVer).
3. Enforce **compatibility** between a plugin and the current runtime contracts.
4. Provide a stable interface for capability negotiation to resolve plugin references safely.

This contract exists to prevent “ambient plugin injection” and to make executions **reproducible**.

## 2. Terminology

- **Plugin ID**: stable identifier (string), e.g. `"dummy_echo"`.
- **Plugin Version**: SemVer string, e.g. `"1.0.0"`.
- **Plugin Ref**: a reference to a plugin by `(plugin_id, plugin_version)`.
- **Plugin Entry**: registry-resolved executable object (entrypoint/factory) plus manifest.
- **Requires**: minimum contract versions required by a plugin.

## 3. SemVer Rules

- `plugin_version` MUST be valid SemVer: `MAJOR.MINOR.PATCH` (integers).
- `"latest"` is a special version selector that resolves to the highest SemVer registered for the `plugin_id`.

## 4. Data Model

### 4.1 PluginRequires

Fields:

- `node_exec_min: str` (SemVer) — minimum compatible `NODE-EXEC` spec version.
- `plugin_contract_min: str` (SemVer) — minimum compatible `PLUGIN-CONTRACT` spec version.

### 4.2 PluginManifest (v1)

Fields (minimum):

- `plugin_id: str`
- `plugin_version: str` (SemVer)
- `description: str`
- `stages_allowed: list[str]` — non-empty; values in `{ "pre", "core", "post" }`
- `default_timeout_ms: int`
- `side_effects: list[str]` — may be empty
- `requires: PluginRequires`
- `tags: list[str] | None`
- `metadata: dict | None`

Validation requirements:

- `plugin_id` MUST be a non-empty string.
- `plugin_version` MUST be valid SemVer.
- `stages_allowed` MUST be a non-empty list, each value MUST be one of `{pre, core, post}`.
- `default_timeout_ms` MUST be positive integer.

### 4.3 PluginEntry

A registry-resolved entry MUST contain:

- `manifest: PluginManifest`
- `entrypoint: callable` (or class with `__call__`), the executable target
- `factory: callable | None` (optional) — if provided, used to instantiate the plugin

## 5. Registry Interface Contract

A registry implementation MUST support:

### 5.1 register

Registers a plugin entry.

- Input: `manifest: PluginManifest`, `entrypoint: callable`, optional `factory`
- Behavior:
  - MUST validate manifest.
  - MUST reject duplicate registration of the same `(plugin_id, plugin_version)` with a deterministic error.
- Errors:
  - Duplicate: `ValueError` (recommended) or a custom deterministic exception type.

### 5.2 resolve

Resolves an entry for execution.

- Input: `plugin_id: str`, `version: str`
  - `version` is SemVer or `"latest"`.
- Output: `PluginEntry`
- Behavior:
  - If `version == "latest"`, MUST resolve to the highest SemVer for the given `plugin_id`.
  - If not found:
    - For *required* resolution flows: raise `KeyError` (recommended) or deterministic “not found” error.
    - For *optional* resolution flows (e.g., capability negotiation when `required=False`): caller MUST NOT crash; it should return `None`.

## 6. Compatibility

### 6.1 Compatibility Check Function

Registry MUST provide a compatibility check:

- `is_compatible(current_node_exec: str, current_plugin_contract: str, requires: PluginRequires) -> bool`

Rules:

- Compatible iff:
  - `current_node_exec >= requires.node_exec_min`
  - `current_plugin_contract >= requires.plugin_contract_min`

SemVer comparisons are numeric by `(MAJOR, MINOR, PATCH)`.

### 6.2 Enforcement Point

Before executing a resolved plugin, the runtime MUST enforce compatibility using the plugin's `requires`.

If incompatible:
- For required plugins: raise deterministic `RuntimeError` (recommended) with a clear message.
- For optional plugins: behave as “unavailable” (return `None` from resolution layer).

## 7. Stage Allowed Enforcement

Before executing a plugin at stage `S ∈ {pre, core, post}`:

- The runtime MUST ensure `S in manifest.stages_allowed`.
- If violated:
  - required: raise deterministic `RuntimeError`
  - optional: treat as unavailable

## 8. Timeout Defaults

If caller does not specify a timeout, runtime MUST use:

- `manifest.default_timeout_ms`

## 9. Integration: Capability Negotiation

When capability negotiation receives a plugin reference (PluginRef / tuple / dict form), it MUST:

1. Attempt registry resolve.
2. If resolve fails and capability is optional → return `None` (no KeyError propagation).
3. If resolve fails and capability is required → raise a deterministic error.

## 10. Observability / Trace Requirements

When a plugin is executed via the registry:

- OBSERVABILITY events MUST include:
  - `plugin_id`
  - `plugin_version`
  - `stage`
- CT-TRACE (if enabled) SHOULD include:
  - `plugin_id`
  - `plugin_version`
  - execution outcome (success/failure) and reason_code (if available)

## 11. Backward Compatibility Notes

- This spec does NOT require legacy “direct callable injection” to be removed immediately,
  but any *reference form* MUST prefer registry resolution to guarantee versioned execution.
