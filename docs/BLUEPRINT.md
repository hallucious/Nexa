# HYPER-AI BLUEPRINT

Version: 2.4.0\
Status: Stabilization lock-in (Post-Step33 ReasonCode policy taxonomy)\
Last Updated: 2026-02-25\
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text
fix)\
Related Steps: Step11, Step29, Step30, Step31, Step32, Step33

------------------------------------------------------------------------

## Core Objective

-   Build a framework that structurally minimizes bug probability via AI
    collaboration.
-   Priority: Reproducibility \> Contract stability \> Test evidence \>
    Expandability.

------------------------------------------------------------------------

## Platform Plugin Architecture (Step29)

All platform plugins expose a single entrypoint:

`resolve(ctx: GateContext) -> Optional[PluginObject]`

------------------------------------------------------------------------

## Meta contract (Step30)

When a plugin returns `meta: dict`, required keys include:

-   `reason_code`
-   `provider`
-   `vendor`
-   `source`
-   `contract_version`

------------------------------------------------------------------------

## ProviderKey contract (Step31)

`meta["provider"]` is the **routing/engine key** (how the call was
routed), not vendor/model identity.

Allowed values: - `gpt` - `gemini` - `local` - `none`

------------------------------------------------------------------------

## Vendor identity contract (Step32)

`meta["vendor"]` captures vendor identity (separate from ProviderKey).

Allowed values: - `openai` - `google` - `anthropic` - `perplexity` -
`local` - `none`

Optional identity fields: - `product`, `model`, `tool` (strings)

------------------------------------------------------------------------

## Failure catalog taxonomy (Step33)

### Why Step33 exists

Reason codes must stay **small and stable**. If reason_code grows
without policy, the contract drifts and becomes un-analyzable.

### ReasonCode is a top-level category

`meta["reason_code"]` MUST represent a **high-level category** only.

Concrete causes MUST be expressed via: - `meta["detail_code"]` (short
machine-friendly token), and/or - `meta["error"]` (human-readable
string)

### Approved top-level ReasonCode set

ReasonCode is intentionally limited to these categories:

-   `SUCCESS`
-   `SKIPPED`
-   `PROVIDER_MISSING`
-   `PROVIDER_ERROR`
-   `CONTRACT_VIOLATION`
-   `POLICY_REJECTED`
-   `INTERNAL_ERROR`

### Expansion policy (hard rule)

A new ReasonCode may be added only if ALL are true: 1. The failure
pattern repeats (\>= 3 occurrences) in real runs. 2. The category
meaning cannot be expressed safely via `detail_code`. 3. The category
has a stable, system-level interpretation across gates. 4. A regression
test and docs MINOR bump are included.

Otherwise, use `detail_code`.

Example:

``` json
{
  "reason_code": "PROVIDER_ERROR",
  "detail_code": "timeout"
}
```
