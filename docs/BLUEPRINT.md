# HYPER-AI BLUEPRINT

Version: 2.3.0\
Status: Stabilization lock-in (Post-Step32 Vendor contract)\
Last Updated: 2026-02-25\
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text
fix)\
Related Steps: Step11, Step29, Step30, Step31, Step32

------------------------------------------------------------------------

## Core Objective

-   Build a framework that structurally minimizes bug probability via AI
    collaboration.
-   Priority: Reproducibility \> Contract stability \> Test evidence \>
    Expandability.

------------------------------------------------------------------------

## Platform Plugin Architecture (Step29)

### Single entrypoint

All platform plugins expose:

`resolve(ctx: GateContext) -> Optional[PluginObject]`

Legacy `resolve_*` entrypoints are deprecated.

------------------------------------------------------------------------

## Meta contract (Step30)

Any plugin returning `meta: dict` must include:

-   `reason_code`
-   `provider`
-   `source`
-   `contract_version`

Additional keys are allowed.

------------------------------------------------------------------------

## ProviderKey contract (Step31)

### Meaning of `provider`

`meta["provider"]` represents the **routing/engine key** inside this
system (how the call was routed), not the vendor/model identity.

Allowed values (minimal set): - `gpt` - `gemini` - `local` - `none`

Rules: 1. `meta["provider"]` MUST be one of the allowed ProviderKey
values. 2. Provider normalization occurs in
`plugin_contract.normalize_meta`. 3. Violations fail pytest.

------------------------------------------------------------------------

## Vendor identity contract (Step32)

### Why Step32 exists

ProviderKey is intentionally small and stable. Vendor/model identity is
separated to prevent enum drift while preserving observability.

### Required vendor key (when meta exists)

Any plugin output that includes `meta: dict` MUST also include:

-   `vendor` (enum string)

### Allowed `vendor` values

-   `openai`
-   `google`
-   `anthropic`
-   `perplexity`
-   `local`
-   `none`

### Optional identity fields

The following fields are optional (strings) and may be present when
useful: - `product` (e.g., `codex`, `sonar`) - `model` (e.g.,
`gpt-5-codex`, `sonar-pro`) - `tool` (e.g., `codex-cli`)

### Rules

1.  `meta["vendor"]` MUST be one of the allowed vendor values when meta
    exists.
2.  `vendor` normalization must occur in
    `plugin_contract.normalize_meta` (or a sibling helper).
3.  Violations fail pytest.

------------------------------------------------------------------------

## Stabilization Goals

-   Eliminate implicit behavior.
-   Enforce contract-first evolution.
-   Lock structural invariants via tests.
