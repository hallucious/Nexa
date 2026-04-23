# MCP Response and Execution Report Contract v0.1

## Recommended save path
`docs/specs/integration/mcp_response_and_execution_report_contract.md`

## 1. Purpose

This document defines the response-side public contracts for the MCP-facing integration surface.

## 2. Main Public Objects

### 2.1 Response contract layer
- `PublicMcpResponseContract`
- `PublicMcpNormalizedResponse`

Role:
- declare response shape
- declare success status codes
- declare response media type
- declare response body kind and required top-level keys

### 2.2 Execution report layer
- `PublicMcpExecutionError`
- `PublicMcpExecutionReport`

Role:
- represent lifecycle-aware execution outcomes
- distinguish success and failure in one normalized report shape
- carry phase/category metadata

## 3. Canonical Rules

1. response normalization must validate success codes and media type
2. response contracts may additionally enforce body-kind and required-key constraints
3. execution reports must expose phase and error category explicitly
4. normalized response and execution report surfaces remain public boundary objects, not internal transport leaks

## 4. Standardized Lifecycle Phases

Representative phases:
- `dispatch_build`
- `binding_lookup`
- `handler_execution`
- `response_normalization`
- `completed`

## 5. Standardized Error Categories

Representative categories:
- `request_contract_error`
- `binding_error`
- `handler_error`
- `response_contract_error`
- `response_decode_error`
- `response_error`
- `unexpected_error`

## 6. Decision

The MCP-facing public integration surface must be explicit on the response side as well as the request side.
