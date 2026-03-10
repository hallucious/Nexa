Spec ID: plugin_executor_contract
Version: 1.0.0
Status: Partial
Category: contracts
Depends On:

# Nexa Plugin Executor Contract

## Purpose

PluginExecutor is the single execution entrypoint for plugins.

Both runtime graph execution and AI tool calls use this executor.

## Responsibilities

1. Validate plugin permissions
2. Execute plugin
3. Validate output namespace
4. Write results to Working Context

## Write Validation

All keys must match:

plugin.<plugin_id>.*

Otherwise runtime raises PluginWriteViolationError.

## Execution Paths

Graph Execution:

NodeExecutionRuntime → PluginExecutor → Plugin

AI Tool Execution:

Provider Tool Bridge → PluginExecutor → Plugin