# Nexa Docs Index

This directory is the consolidated documentation set for Nexa, excluding historical implementation-plan folders.

Canonical root-level project documents are expected to remain outside this docs bundle:

- `README.md` — public/project entry point
- `ROADMAP.md` — vision, strategy, scope, and roadmap single source of truth
- `ARCHITECTURE.md` — architecture, invariants, execution rules, and forbidden patterns
- `NEXA_FOR_AI.md` — AI coding assistant working guide

## Current Docs Layout

- `process/` — working rules and collaboration process
- `ai/` — AI-assistant-facing guidance retained inside docs, if mirrored here
- `specs/architecture/` — core architecture specs
- `specs/contracts/` — runtime-facing contracts
- `specs/storage/` — consolidated storage lifecycle, schema, and API specs
- `specs/designer/` — consolidated Designer AI specification family
- `specs/ui/` — UI adapter, panel view models, shell, i18n, and runtime-bootstrap specs
- `specs/plugins/` — consolidated plugin builder/runtime lifecycle specs
- `specs/ops/` — consolidated operator-only AI-assisted operations specs
- `specs/server/` — server/runtime API boundary contracts
- `specs/saas/` — SaaS/product platform specs
- `specs/indexes/` — spec catalog and dependency maps
- `archive/` — historical decision bundles retained for traceability, not active implementation targets

## Rule

When documentation conflicts, prefer the root canonical documents first, then this index, then the relevant consolidated spec family.
