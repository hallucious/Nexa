# MCP Public Integration Architecture v0.1

## Recommended save path
`docs/specs/integration/mcp_public_integration_architecture.md`

## 1. Purpose

This document defines the architectural position of the public MCP-facing integration surface in Nexa.

## 2. Core Decision

Nexa does not treat MCP as the engine.
MCP is a protocol-mapping layer above the curated public SDK boundary.

Official structure:

Nexa engine / server truth
→ `src.sdk.server`
→ `src.sdk.integration`
→ MCP-style tool/resource surface
→ external host or client

## 3. Architectural Principles

1. the MCP layer is derived from public SDK/server truth
2. it must not invent routes or runtime semantics not present in the public boundary
3. it may normalize protocol shape, but it must not redefine execution truth
4. request/response contracts remain explicit and inspectable
5. executable bridge helpers remain additive and do not replace server truth

## 4. Boundary Objects

The integration surface currently contains these major layers:
- descriptors (tool/resource identity)
- manifest/export surface
- argument schemas
- route-family normalization contracts
- response contracts
- executable host bridge helpers
- execution reports and recovery hints

## 5. Non-Goals

This architecture does not yet define:
- full MCP runtime hosting
- transport/session orchestration
- ecosystem packaging/distribution

## 6. Decision

The MCP-facing surface is a public integration boundary derived from Nexa’s curated SDK and server surface, not a replacement for either.
