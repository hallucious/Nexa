# Nexa Capability Activation and Expansion Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Product expansion specification
Authority scope: Surface profile growth, capability bundles, browser-first expansion, mobile timing, and MCP deferral
Recommended path: `docs/specs/saas/capability_activation_and_expansion_spec.md`

## 1. Purpose

This document defines how the Nexa SaaS grows from a narrow baseline into a broader product surface without losing operational discipline.

Its purpose is to fix:
- why route count is not the main KPI,
- how surface growth should be described in capability terms,
- why browser PMF comes before mobile,
- and why MCP is late rather than early.

## 2. Expansion principle

Expansion must be capability-led, not route-count-led.

A system with more routes is not necessarily a better SaaS.
The correct question is:
- what new user or operator capability becomes safely available?

## 3. Capability bundle model

The SaaS grows through named capability bundles such as:

- `core`
- `async_control`
- `upload`
- `templates`
- `provider_management`
- `result_history`
- `billing`
- `admin`
- `shares`
- `mcp`

These bundles are more meaningful than raw route totals.

## 4. Why capability bundles matter

Capability bundles help preserve:
- product clarity,
- surface-profile control,
- rollout sequencing,
- contract testing,
- and user-facing coherence.

They also prevent false progress reporting such as “we activated many routes” when little user value changed.

## 5. Core bundle

The core bundle is the minimal product surface that allows:
- authenticated workspace use,
- run submission,
- run status polling,
- result retrieval,
- and trace retrieval.

Without this, the SaaS baseline does not exist.

## 6. Async control bundle

This bundle adds operator and lifecycle control around runs such as:
- retry,
- reset,
- cancel-like control if later introduced,
- and lifecycle action visibility.

It depends on the async runtime existing first.

## 7. Upload bundle

This bundle adds document intake and usable-file handling.
It depends on the document safety specification, not merely a route toggle.

## 8. Templates and result-history bundles

These bundles make the product feel like a real application rather than a raw backend:
- starter use cases,
- reusable entry points,
- historical visibility.

## 9. Billing bundle

Billing is a real product capability bundle, not just a webhook receiver.
It includes:
- checkout,
- subscription visibility,
- plan management,
- and user-visible economic boundaries.

## 10. Admin bundle

The admin bundle is explicitly internal-only.
It is a capability bundle because it is part of product operation, but it is not public product marketing surface.

## 11. Public shares and community

Public sharing is deliberately deferred.
It is not required for minimum viable or revenue-generating SaaS.

It requires later decisions around:
- moderation,
- legal policy,
- and community product design.

## 12. Browser-first rule

The browser product is the baseline PMF surface.
Expansion priority must preserve this.

Therefore:
- browser PMF is validated before mobile,
- mobile is not a co-equal early track,
- and browser usability must reach a real user loop first.

## 13. Mobile start condition

Mobile begins only after explicit browser PMF signals exist.

At minimum:
- there is meaningful weekly active browser usage,
- the contract review flow has a healthy completion rate,
- and mobile demand is clearly present.

This prevents premature platform sprawl.

## 14. MCP timing rule

MCP is deferred until:
- the product is operationally stable,
- the SaaS baseline is already supportable,
- and the system is not depending on MCP to justify the core product.

MCP is expansion, not foundation.

## 15. Deferred domains

The following remain outside current activation priority:
- visual graph editor,
- public sharing/community,
- BYOK,
- enterprise-only controls,
- self-hosted packaging,
- broad AI-assisted operations as a baseline requirement.

## 16. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. expansion is described in capability terms,
2. capability bundles remain more important than route totals,
3. browser PMF is prioritized before mobile,
4. public sharing is not treated as a baseline requirement,
5. MCP is deferred until after operational stability,
6. and surface activation remains governed rather than ad hoc.
