# HYPER-AI CODING PLAN

Version: 2.4.0\
Status: Stabilization lock-in (Post-Step33)\
Last Updated: 2026-02-25\
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text
fix)\
Related Steps: Step11, Step29, Step30, Step31, Step32, Step33

------------------------------------------------------------------------

## Current status

-   Step11: Hybrid registry/discovery contract locked.
-   Step29: Unified `resolve(ctx)` entrypoint locked.
-   Step30: Meta required keys + ReasonCode locked.
-   Step31: ProviderKey (routing key) enum locked.
-   Step32: VendorKey (vendor identity) enum locked.
-   Step33: Failure catalog taxonomy (ReasonCode policy) locked.
-   pytest baseline: 76 passed, 3 skipped (post-step32).

------------------------------------------------------------------------

## Phase: Stabilization lock-in

### P0--P4 (Done)

-   Step11--Step32 complete (registry/discovery, resolve(ctx), meta
    keys, provider/vendor).

### P5 (Current; MINOR -- Step33)

Goal: Prevent ReasonCode drift by fixing a stable taxonomy and expansion
policy.

Deliverables: - Add `POLICY_REJECTED` to `ReasonCode` enum. - Preserve
backward compatibility (`infer_reason_code` kept). - Add
`tests/test_step33_reason_code_policy_rejected.py` to assert enum
contains POLICY_REJECTED. - Docs: define ReasonCode as top-level
categories + expansion policy, and recommend `detail_code`.

------------------------------------------------------------------------

## Hard contract rules (post-step33)

1.  ReasonCode is a stable, high-level category set.
2.  Concrete causes go to `detail_code` and/or `error`.
3.  Adding a new ReasonCode requires docs MINOR bump + tests.
