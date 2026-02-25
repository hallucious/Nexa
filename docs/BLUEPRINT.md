# HYPER-AI BLUEPRINT

Version: 2.5.0\
Status: Stabilization lock-in (Post-Step34 run_dir observability
artifact)\
Last Updated: 2026-02-25\
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text
fix)\
Related Steps: Step11, Step29, Step30, Step31, Step32, Step33, Step34

------------------------------------------------------------------------

## Step34: Run-level observability artifact (source of truth)

### Decision

Observability is persisted as a run artifact, not only console output.

### Artifact

`runs/<run_id>/OBSERVABILITY.jsonl`

-   JSON Lines format (1 line = 1 gate execution event)
-   Always appended once per gate execution (including crashes)
-   Best-effort (never breaks pipeline)

### Minimal schema (stable)

Each event MUST include: - `run_id` - `gate` - `decision` - `source` -
`provider` (ProviderKey or "none") - `vendor` (VendorKey or "none") -
`reason_code` (may be null if unavailable) - `detail_code` (may be
null) - `started_at` - `finished_at` - `execution_time_ms`

### Rationale

-   Makes debugging and regression analysis reproducible.
-   Enables offline aggregation without parsing console logs.
