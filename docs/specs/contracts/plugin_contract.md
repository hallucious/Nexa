# Nexa Plugin Contract
Spec ID: PLUGIN-CONTRACT
Version: 1.1.0
Status: Draft
Scope: Plugin capability execution within Nexa Node Runtime
Related Specs:
- NODE-EXEC
- AI-PROVIDER
- NEXA-WORKING-CONTEXT
- PLUGIN-EXECUTOR

--------------------------------------------------

## 1. Purpose

This contract standardizes how Plugins (tools) behave inside Nexa Engine.

Plugins represent capability tools executed by Node runtime or invoked by AI providers.

Plugins are deterministic execution components that operate on the Nexa Working Context through a controlled executor.

--------------------------------------------------

## 2. Terminology

Plugin  
A deterministic capability tool invoked by Node runtime or AI tool bridge.

PluginRequest  
Input payload passed to a plugin.

PluginResult  
Standardized output envelope returned by a plugin.

Stage  
Execution stage defined in NODE-EXEC.

Working Context  
Shared execution data structure used by Node runtime.

Plugin Namespace  
plugin.<plugin_id>.*

reason_code  
Platform-wide failure taxonomy key.

--------------------------------------------------

## 3. Contract Invariants

1. A Plugin MUST return a PluginResult envelope.
2. A Plugin MUST NOT mutate shared runtime state directly.
3. All mutations MUST be returned through PluginResult.
4. Plugin execution MUST be deterministic.
5. Plugin execution MUST respect timeout constraints.
6. Plugins MUST NOT raise uncaught exceptions.
7. Plugins MUST write only within their namespace.
8. Plugin execution MUST pass through PluginExecutor.

--------------------------------------------------

## 4. Plugin Namespace Rule

Plugins MUST only write keys under:

plugin.<plugin_id>.*

Example:

plugin.search.results  
plugin.search.score  
plugin.translate.text

Plugins MUST NOT write to:

input.*  
prompt.*  
provider.*  
system.*  
output.*

Violations MUST raise PluginWriteViolationError.

--------------------------------------------------

## 5. PluginRequest (Input Contract)

Required fields:

plugin_id: string  
stage: string ("PRE" | "CORE" | "POST")  
payload: object (JSON-serializable)

Optional:

metadata: object | null

Constraints:

metadata MUST NOT contain secrets.

--------------------------------------------------

## 6. PluginResult (Output Contract)

PluginResult MUST include:

success: boolean  
data: object | null  
error: string | null  
reason_code: string | null  

metrics:
latency_ms: integer  
resource_usage: object | null

--------------------------------------------------

## 7. PluginResult Semantics

If success == true:

data MUST be non-null (may be empty object)  
error MUST be null  
reason_code MUST be null

If success == false:

data MUST be null  
error MUST be non-null  
reason_code MUST be non-null

--------------------------------------------------

## 8. reason_code Minimum Set

PLUGIN.timeout  
PLUGIN.invalid_input  
PLUGIN.execution_error  
PLUGIN.policy_blocked  
SYSTEM.unexpected_exception

--------------------------------------------------

## 9. Return-Only Mutation Rule

PluginResult.data MAY include:

patch  
artifacts

patch  
Key-value updates merged into Working Context namespace.

artifacts  
Indexed output references for downstream resources.

Plugins MUST NOT directly modify:

NodeExecutionRuntime state  
Working Context internal structures  
Provider execution state

--------------------------------------------------

## 10. Plugin Executor Integration

All plugin execution MUST go through PluginExecutor.

Responsibilities:

1. Validate plugin namespace writes.
2. Execute plugin safely.
3. Convert PluginResult into context updates.
4. Enforce timeout and resource limits.
5. Record observability metrics.

Execution paths:

NodeExecutionRuntime → PluginExecutor → Plugin

Provider Tool Bridge → PluginExecutor → Plugin

--------------------------------------------------

## 11. AI Tool Invocation

Plugins MAY be invoked by AI providers through a tool call interface.

AI provider MUST NOT directly execute plugins.

Instead:

Provider Tool Bridge → PluginExecutor → Plugin

This ensures:

permission enforcement  
sandbox guarantees  
context integrity

--------------------------------------------------

## 12. Sandbox Requirements

If external plugins are supported:

1. Plugin execution MUST be sandboxed.
2. Execution time MUST be bounded.
3. Memory usage SHOULD be constrained.
4. Network access MUST follow policy.

--------------------------------------------------

## 13. Node Runtime Integration

Node runtime MUST:

1. Pass stage to plugin.
2. Route execution through PluginExecutor.
3. Merge PluginResult.patch into Working Context.
4. Track plugin execution in observability traces.
5. Prevent plugin from bypassing runtime control flow.

--------------------------------------------------

## 14. Observability

Plugins MUST report latency.

Plugins MAY report:

resource_usage

Plugins MUST NOT leak:

secrets  
provider credentials  
system tokens

--------------------------------------------------

## 15. Non-Goals (v1.1.0)

Streaming plugins  
Long-running distributed workflows  
Persistent plugin-managed state  
Cross-node mutation

--------------------------------------------------

End of PLUGIN-CONTRACT v1.1.0