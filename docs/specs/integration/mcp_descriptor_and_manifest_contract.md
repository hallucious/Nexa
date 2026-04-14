# MCP Descriptor and Manifest Contract v0.1

## Recommended save path
`docs/specs/integration/mcp_descriptor_and_manifest_contract.md`

## 1. Purpose

This document defines the public descriptor/export/manifest layer for Nexa’s MCP-facing integration boundary.

## 2. Main Public Objects

### 2.1 Descriptor layer
- `PublicMcpToolDescriptor`
- `PublicMcpResourceDescriptor`
- `PublicMcpCompatibilitySurface`

Role:
- classify public routes as tool-like or resource-like
- preserve route name, method, path, description, and type references

### 2.2 Manifest layer
- `PublicMcpManifestTool`
- `PublicMcpManifestResource`
- `PublicMcpManifest`

Role:
- package the current public integration surface into a protocol-facing export artifact
- include request-side and response-side contract references
- include compatibility metadata

### 2.3 Compatibility layer
- `PublicMcpCompatibilityPolicy`

Role:
- declare manifest version, schema version, supported versions, and adapter/host-bridge compatibility expectations

## 3. Canonical Rules

1. every exported tool/resource must come from a real public route family
2. manifest export must preserve route identity and contract identity
3. compatibility metadata must be explicit, not implied by version strings alone
4. manifest export is an inspectable contract artifact, not just a convenience dump

## 4. Relationship to Code

Primary builders:
- `build_public_mcp_tools()`
- `build_public_mcp_resources()`
- `build_public_mcp_compatibility_surface()`
- `build_public_mcp_manifest()`
- `build_public_mcp_compatibility_policy()`

## 5. Decision

The descriptor/manifest layer is the public, inspectable contract artifact for the MCP-facing integration surface.
