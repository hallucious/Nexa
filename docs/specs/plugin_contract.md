# Plugin Contract
- Spec ID: PLUGIN-CONTRACT
- Version: 1.0.0
- Status: Draft
- Scope: Stage-aware tool execution within NODE-EXEC pipeline
- Related Specs: NODE-EXEC@1.0.0, AI-PROVIDER@1.0.0

---

## 1. Purpose

This contract standardizes how Plugins (tools) behave inside the Engine.
Plugins are stage-aware, return-only mutation components executed within Pre/Core/Post.

---

## 2. Terminology

- Plugin: A deterministic tool invoked by Node runtime.
- PluginRequest: Input payload to a plugin.
- PluginResult: Standardized output envelope.
- Stage: PRE | CORE | POST (as defined in NODE-EXEC).
- reason_code: Platform-wide failure taxonomy key.

---

## 3. Contract Invariants

1. A Plugin MUST return a PluginResult envelope (no raw dict returns).
2. A Plugin MUST NOT mutate shared state directly.
3. All side effects MUST be explicit and documented.
4. A Plugin MUST be stage-aware (stage passed in request).
5. A Plugin MUST respect timeout constraints.
6. A Plugin MUST NOT raise uncaught exceptions.

---

## 4. PluginRequest (Input Contract)

Required:

- `plugin_id: string`
- `stage: string` ("PRE" | "CORE" | "POST")
- `payload: object` (JSON-serializable)

Optional:

- `metadata: object | null` (no secrets allowed)

---

## 5. PluginResult (Output Contract)

### 5.1 Schema

PluginResult MUST include:

- `success: boolean`
- `data: object | null`
- `error: string | null`
- `reason_code: string | null`
- `metrics: object`
  - `latency_ms: integer` (required)
  - `resource_usage: object | null`

### 5.2 Semantics

If `success == true`:
- `data` MUST be non-null (may be empty dict)
- `error` MUST be null
- `reason_code` MUST be null

If `success == false`:
- `data` MUST be null
- `error` MUST be non-null
- `reason_code` MUST be non-null

---

## 6. reason_code Minimum Set

- `PLUGIN.timeout`
- `PLUGIN.invalid_input`
- `PLUGIN.execution_error`
- `PLUGIN.policy_blocked`
- `SYSTEM.unexpected_exception`

---

## 7. Return-Only Mutation Rule

PluginResult.data MAY contain:

- `patch`: object (merged into node working data)
- `artifacts`: object (indexed output references)

Plugins MUST NOT:

- Directly modify runtime context
- Access engine internals
- Persist secrets

---

## 8. Sandbox Requirements

If external plugins are supported:

1. Plugin execution MUST be sandboxed.
2. Execution time MUST be bounded.
3. Memory usage SHOULD be constrained.
4. Network access MUST follow policy.

---

## 9. Node Integration Rules

Node runtime MUST:

1. Pass stage to plugin.
2. Convert PluginResult into NodeResult patch logic.
3. Record stage + plugin_id in CT-TRACE (if enabled).
4. Never allow plugin to bypass NODE-EXEC stage boundaries.

---

## 10. Observability

Plugin MUST report latency.
Plugin MAY report resource usage.
Plugin MUST NOT leak sensitive information.

---

## 11. Non-Goals (v1.0.0)

- Streaming plugins
- Long-running distributed workflows
- Persistent plugin-managed state
- Cross-node mutation

---

End of PLUGIN-CONTRACT v1.0.0
