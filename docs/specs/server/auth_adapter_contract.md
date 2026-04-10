# Auth Adapter Contract v1

## Recommended save path
`docs/specs/server/auth_adapter_contract.md`

## 1. Purpose

This document defines the canonical authentication adapter boundary for Nexa's server/product layer.

Its purpose is to prevent auth-provider specifics from leaking into engine-core semantics and to keep the chosen auth provider replaceable.

## 2. Core Decision

Authentication is a server/product concern and must cross into the rest of the server code through an explicit adapter boundary.

Official rule:

- auth provider specifics stay behind the adapter
- product/server code consumes normalized auth identity/session objects
- engine-core contracts must not depend on Clerk-specific shapes
- replacing the auth provider must not require rewriting engine-core semantics

## 3. Recommended Initial Provider

Current recommended provider:
- Clerk

Important:
This contract does not make Clerk invisible.
It makes Clerk replaceable.

## 4. Adapter Responsibility

The auth adapter should normalize at least:

- authenticated user identity
- session validity
- organization/team context if later needed
- role/claim extraction needed by product authorization
- logout/session invalidation checks where relevant

## 5. Recommended Normalized Objects

### 5.1 AuthenticatedIdentity
Suggested fields:
- `user_id`
- `email` optional
- `display_name` optional
- `organization_refs` optional
- `provider_name`
- `provider_subject_ref`

### 5.2 SessionContext
Suggested fields:
- `session_id`
- `authenticated_user_id`
- `issued_at`
- `expires_at`
- `is_valid`

### 5.3 AuthorizationInput
Suggested fields:
- `user_id`
- `workspace_id`
- `requested_action`
- `role_context`

## 6. What the Adapter Must Hide

The adapter should hide from downstream code:

- raw Clerk SDK response shapes
- Clerk webhook/event payload structure unless explicitly isolated
- provider-specific token parsing details
- provider-specific claim naming quirks

## 7. Engine Boundary Rule

The engine must not depend on:
- Clerk user objects
- Clerk session token structures
- provider-specific auth SDK types

The server may pass normalized refs such as:
- `requested_by_user_ref`
- `auth_context_ref`

But these remain normalized product/server objects, not provider-specific core semantics.

## 8. Authorization Rule

Authentication and authorization are related, but distinct.

Recommended rule:
- auth adapter proves identity/session
- product authorization layer decides what that identity is allowed to do
- the engine receives already-authorized normalized launch/query context

## 9. What Must Never Happen

The following are forbidden:

1. Clerk-specific types leaking into engine-core contracts
2. route handlers embedding provider-specific auth logic everywhere without a shared adapter
3. treating auth provider choice as engine architecture
4. bypassing adapter normalization and passing raw SDK objects across the server layer

## 10. Final Statement

The Nexa auth adapter exists for one reason:

auth providers may change;
engine truth must not.

That boundary must remain explicit if Nexa is to preserve architectural replaceability.
