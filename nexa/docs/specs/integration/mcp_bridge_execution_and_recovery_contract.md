# MCP Bridge Execution and Recovery Contract v0.1

## Recommended save path
`docs/specs/integration/mcp_bridge_execution_and_recovery_contract.md`

## 1. Purpose

This document defines the executable bridge layer and recovery guidance surface for the MCP-facing public integration boundary.

## 2. Main Public Objects

### 2.1 Bridge/export layer
- `PublicMcpInvocation`
- `PublicMcpToolExport`
- `PublicMcpResourceExport`
- `PublicMcpAdapterExport`
- `PublicMcpAdapterScaffold`
- `PublicMcpHostRouteBinding`
- `PublicMcpFrameworkDispatch`
- `PublicMcpHttpDispatch`
- `PublicMcpHostBridgeExport`
- `PublicMcpHostBridgeScaffold`

### 2.2 Recovery layer
- `PublicMcpRecoveryHint`

Role:
- declare retryability
- safe same-request retry guidance
- recommended next action

## 3. Executable Helper Rule

Bridge helpers may:
- normalize request arguments
- build dispatch plans
- execute bound framework/http handlers
- normalize responses into public boundary objects
- return structured execution reports

Bridge helpers must not:
- bypass route contracts
- bypass response contracts
- fabricate success outside the real handler result

## 4. Recovery Guidance Rule

Recovery guidance must be standardized and derived from execution category/phase semantics.
It should help external consumers decide whether to:
- retry the same request
- change the request
- inspect route binding
- treat the failure as non-retryable

## 5. Decision

The executable bridge layer is the operational surface of the public MCP boundary, and recovery hints are part of that operational contract.
