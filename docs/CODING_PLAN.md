# HYPER-AI CODING PLAN

Version: 2.3.0\
Status: Stabilization lock-in (Post-Step32)\
Last Updated: 2026-02-25\
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text
fix)\
Related Steps: Step11, Step29, Step30, Step31, Step32

------------------------------------------------------------------------

## Current status

-   Step11: Hybrid registry/discovery contract locked.
-   Step29: Unified `resolve(ctx)` entrypoint locked.
-   Step30: Meta required keys + ReasonCode locked.
-   Step31: ProviderKey (routing key) enum locked.
-   Step32: Vendor identity enum introduced (separates vendor/model from
    ProviderKey).
-   pytest baseline: 74 passed, 3 skipped (post-step31).

------------------------------------------------------------------------

## Phase: Stabilization lock-in

### P0 (Done)

Hybrid registry + discovery comparison.

### P1 (Done)

resolve(ctx) unification.

### P2 (Done; MINOR -- Step30)

Meta contract standardization.

### P3 (Done; MINOR -- Step31)

ProviderKey enum + provider normalization.

### P4 (Current; MINOR -- Step32)

Goal: Standardize vendor identity for observability without bloating
ProviderKey.

Deliverables: - Extend `src/platform/plugin_contract.py` - `VendorKey`
enum - `normalize_meta(..., vendor=...)` support (or `normalize_vendor`
helper) - Update plugins that emit `meta: dict` to include `vendor` (and
optionally product/model/tool). - Add
`tests/test_step32_vendor_key_contract.py` - Enforce allowed vendor
values when meta exists.

------------------------------------------------------------------------

## Hard Contract Rules (post-step32)

1.  All plugins expose `resolve(ctx)`.
2.  When meta exists, required keys include: `reason_code`, `provider`,
    `source`, `contract_version`, `vendor`.
3.  `reason_code` must be ReasonCode enum.
4.  `provider` must be ProviderKey enum (routing key).
5.  `vendor` must be VendorKey enum (vendor identity).
6.  Contract violations fail pytest.

------------------------------------------------------------------------

## Next

-   Failure catalog strategy (ReasonCode evolution policy).
-   Optional: formalize product/model fields if/when needed.
