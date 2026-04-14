# MCP Argument and Route Contract v0.1

## Recommended save path
`docs/specs/integration/mcp_argument_and_route_contract.md`

## 1. Purpose

This document defines how request-side arguments are expressed and normalized in the MCP-facing public integration surface.

## 2. Main Public Objects

### 2.1 Field/schema layer
- `PublicMcpArgumentField`
- `PublicMcpArgumentSchema`

Role:
- describe path/query/body fields
- requiredness
- value kinds
- additional-field policy

### 2.2 Route-family layer
- `PublicMcpRouteContract`
- `PublicMcpNormalizedArguments`

Role:
- classify route families
- declare transport profile
- expose normalized path/query/body projections

## 3. Transport Profiles

Representative transport profiles include:
- `no-arguments`
- `path-only`
- `query-only`
- `body-only`
- `path-and-query`
- `path-and-body`

These profiles make route-family normalization explicit rather than implementation-only.

## 4. Canonical Rules

1. argument schemas must remain public and inspectable
2. route-family normalization must be explicit
3. path/query/body collisions must be rejected
4. required-field and unknown-field validation must happen before dispatch
5. route-family transport profile must be enforced, not merely documented

## 5. Relationship to Code

Primary builders/helpers:
- `build_public_mcp_argument_schemas()`
- `build_public_mcp_route_contracts()`
- adapter/bridge normalization helpers

## 6. Decision

The MCP-facing request surface is contract-driven at both the field level and the route-family normalization level.
