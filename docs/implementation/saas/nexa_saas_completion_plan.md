# Nexa SaaS Completion Plan v0.4

**Document type:** Full-scope SaaS completion plan — authoritative implementation reference
**Status:** v0.4 — integrates GPT revision requests M1–M2 and R1–R2 from third review pass
**Supersedes:** `nexa_saas_completion_plan_v0.3.md`
**Prerequisites:** `phase45_p0_implementation_brief_v1.0.md` implemented and green
**Author:** Claude (Opus 4.7)
**Date:** 2026-04-22
**Target segment:** Freelancers and sole proprietors — first killer UC: contract review

---

## READING GUIDE

This document covers everything required beyond Phase 4.5 P0 to operate Nexa as a production SaaS product.

**The gap in one sentence:**
> P0 proves HTTP → DB → Engine → Trace works. SaaS requires async execution, file quarantine, a defined provider operating model, a killer use case, a frontend, cost-accurate billing, email, safe observability with redaction, security hardening, backup/recovery with append-only integrity, an admin support surface, CI/CD, progressive capability activation, mobile access, and MCP integration.

**Segment map:**

| Segment | Content | Unblocks |
|---|---|---|
| **S1** | Async queue (Redis + arq) | Multi-user concurrent runs |
| **S-PROV** | Provider operating model | Billing accuracy, support clarity |
| **S2** | File upload + quarantine + ClamAV safety | Real document ingestion |
| **S3** | Contract review circuit | Killer use case end-to-end |
| **S4** | Next.js frontend | Browser-accessible product |
| **S5** | Stripe + run-count + cost-based quota | Freemium revenue |
| **S6** | Email notifications | Async result delivery |
| **S7** | Sentry + OTel + redaction policy | Safe observability |
| **S8** | Rate limiting + CORS + GDPR + security | Safe public access |
| **S9** | CI/CD pipeline (runs in parallel from sprint 1) | Reliable delivery of all segments |
| **S-OPS** | Data lifecycle, backup, recovery | Operational durability |
| **S-ADMIN** | Internal admin/support surface | Incident response |
| **S10** | Capability bundle activation | Full product surface |
| **S11** | Mobile app (post browser PMF) | Mobile access |
| **S12** | MCP integration | External AI agent access |

**SaaS operability milestones:**

| Milestone | Required segments |
|---|---|
| Minimum viable SaaS (browser UC works) | S1 + S2 + S3 + S4 + S7 (basic Sentry) + S8 (rate limit + CORS) |
| Revenue-generating SaaS | + S5 + S6 + S-PROV + S-OPS (backup running) |
| Operationally mature | + S-ADMIN + S7 (full OTel + redaction) + S9 (automated deploys) |
| Full expansion | + S10 + S11 (post PMF) + S12 |

---

## TABLE CLASSIFICATION: MUTABILITY AND RETENTION CATEGORIES

> **New in v0.3 (R1).** Every table is assigned to exactly one category. This classification governs how retention, archival, and recovery are designed.

| Category | Definition | Tables |
|---|---|---|
| **A — Immutable append-only** | Rows are **never updated and never deleted**, for any reason, including retention management, GDPR flows, and operator action. New state is always a new row. No exceptions. | `execution_record`, `file_upload_events`, `run_action_log`, `execution_record_archive_index`, `execution_retention_audit`, `admin_action_audit`, `user_deletion_audit` |
| **B — Mutable state** | Rows represent current state; updates are expected and legitimate. Rows may be deleted as part of GDPR user-deletion flows. | `workspaces`, `workspace_memberships`, `onboarding_state`, `provider_bindings`, `user_subscriptions`, `file_uploads`, `user_preferences`, `push_notification_tokens` |
| **C — TTL-bounded deletable** | Rows expire after a defined window and are deleted by automated cleanup jobs. | `run_submission_dedupe`, `run_submissions`, `quota_usage` (after 3 periods) |
| **D — Permanent audit** | Rows are never deleted for any reason, including GDPR user deletion requests. Category D is a strict subset of Category A: every Category D table is also Category A. The distinction is that Category D rows are additionally immune to operator-initiated hard-delete workflows. | `admin_action_audit`, `user_deletion_audit`, `execution_retention_audit`, `file_upload_events` |

> **Category A is a hard rule with no exceptions.** `execution_record` is Category A: it is never updated and never hard-deleted, including by retention workflows or GDPR flows. Archival is managed through separate index tables (Category A+D) and read-surface filtering only. GDPR compliance is achieved by ensuring immutable records contain no direct PII — see PII Placement Rule below.

---

## PII PLACEMENT RULE

> **New in v0.4 (R2).** This rule governs where personal identity data may and may not be stored. It makes the retention and GDPR model coherent across all tables.

**Rule: Immutable append-only records (Category A) must not store directly mutable personal identity fields.**

| What this means | Consequence |
|---|---|
| `execution_record`, `run_action_log`, `file_upload_events`, `admin_action_audit` must not contain raw `user_id`, email address, display name, IP address, or any other field that would require mutation for GDPR compliance | These fields never need to be anonymized because they are never stored in immutable rows |
| User linkage in immutable records must use only opaque `user_ref` — a one-way hash (sha256) of the internal user ID | The mapping from `user_ref` → identity lives in mutable tables (Category B) that can be deleted or anonymized independently |
| When a user requests GDPR deletion, mutable identity tables (Category B) are cleared; immutable records are untouched | `execution_record` rows continue to exist but are now orphaned from any identifying user linkage — this is compliant |

**What lives where:**

| Data | Location | Category |
|---|---|---|
| User identity (email, display name, Clerk sub) | Clerk (authoritative) | External |
| User→workspace membership with display info | `workspace_memberships` | B (mutable, GDPR-deletable) |
| User subscription and plan | `user_subscriptions` (keyed by `user_id_ref`) | B (mutable) |
| Run execution records | `execution_record` (keyed by `run_id`, references `workspace_id` and opaque `user_ref`) | A (immutable) |
| Opaque user reference hash | Stored inline in Category A tables as `user_ref` field | Non-PII (hash only) |

**What gets anonymized / deleted during GDPR user deletion:**
- Clerk account → deleted (authoritative identity gone)
- `workspace_memberships` rows → deleted (Category B)
- `user_subscriptions` rows → deleted (Category B)
- `user_preferences` rows → deleted (Category B)
- S3 file objects → deleted
- `execution_record` rows → **not touched** (Category A; `user_ref` is an opaque hash, not PII)
- `file_upload_events` rows → **not touched** (Category A+D; `upload_id` reference only)
- `admin_action_audit` rows → **not touched** (Category A+D; `actor_user_ref` is opaque hash)

**Implication for schema design:** every new Category A table must be reviewed to confirm it contains no raw PII fields before the migration is merged.

---

## SOURCE-OF-TRUTH HIERARCHY

> **New in v0.3 (R2).** For every major state class, one system is authoritative. During incident recovery, always restore the authoritative system first.

| State class | Authoritative source | Secondary (cache / derived) | Recovery direction |
|---|---|---|---|
| Run submission identity | **Postgres** (`run_submissions`) | Redis arq job ID | If Redis lost: re-enqueue from `run_submissions` where `status=submitted` |
| Run execution result | **Postgres** (`execution_record`) | Redis arq result cache | If Redis lost: result is in Postgres; Redis cache is rebuilt on next read |
| Run queue state | **Redis** (arq job list) | Postgres `run_submissions.status` | If Redis lost: reconcile from `run_submissions` vs `execution_record` |
| Workspace / membership | **Postgres** (`workspaces`, `workspace_memberships`) | Clerk org membership (secondary signal) | If Postgres lost: restore from backup; Clerk has display data only |
| User identity / auth | **Clerk** | Postgres user refs (opaque hash) | Clerk is authoritative for identity; Postgres stores opaque refs only |
| Subscription / plan | **Stripe** + **Postgres** (`user_subscriptions`) | — | If diverged: Stripe is authoritative; Postgres is reconciled via webhook replay |
| File object | **S3** | Postgres `file_uploads` metadata | If S3 lost: metadata survives but object is gone; user must re-upload |
| File scan state | **Postgres** (`file_uploads.status`, `file_upload_events`) | — | S3 is object store; scan state is always Postgres |
| Provider health / probe | **Postgres** (`provider_probe_history`) | Redis probe cache | Redis cache is rebuilt on next probe |
| Observability / traces | **Sentry / OTel backend** | — | Sentry/OTel are not authoritative for business state; never recover business data from them |
| Admin action audit | **Postgres** (`admin_action_audit`) | — | Permanent; never recover from a non-Postgres source |
| Quota usage | **Postgres** (`quota_usage`) | — | If lost: rebuild from `execution_record` cost fields for the current period |

---

## WHAT ALREADY EXISTS IN THE CODEBASE

Do not re-implement these. Consume and wire them.

| Module | File | What exists |
|---|---|---|
| Queue models + orchestration | `src/server/worker_queue_models.py`, `worker_queue_orchestration.py` | `QueueJobState`, `WorkerLeasePolicy`, `WorkerOrphanReview`, projection logic — no backend |
| Quota policy (run + cost) | `src/governance/quota.py` | `QuotaPolicy` with `max_run_count`, `max_estimated_cost`, `max_actual_cost`, `QuotaUsageSummary`, `QuotaViolation` — no enforcement |
| Pricing resolver | `src/server/pricing_resolver.py`, `pricing_cache.py`, `pricing_models.py` | `PricingResolver`, `PricingCache`, `ProviderCost` — not wired to quota |
| Adaptive scoring | `src/server/adaptive_scoring.py` | `AdaptiveWeights`, provider scoring — not wired |
| Input safety | `src/safety/input_safety.py` | Credential/PII redaction patterns, `InputSafetyScanner` — not enforced at API boundary |
| Output destinations | `src/automation/output_destination.py` | `DestinationCapability` model — no delivery runtime |
| Trigger model | `src/automation/trigger_model.py` | All trigger sources defined — no scheduler |
| Streaming spec | `docs/specs/execution/execution_streaming_contract.md` | Spec only — no implementation |
| Run control | `src/server/run_control_api.py` | retry/force-reset/mark-reviewed logic — not yet activated |
| Provider health | `src/server/provider_health_api.py`, `provider_probe_api.py` | Health inspection + probe logic — not yet activated |
| Auto recovery | `src/server/run_auto_recovery_scheduler.py`, `run_auto_recovery_policy.py` | Recovery policy and scoring — not wired |
| Recent activity | `src/server/recent_activity_api.py` | Activity read logic — not yet activated |
| Action log | `src/server/run_action_log_api.py` | Run lifecycle logging — not yet activated |
| i18n | `src/ui/i18n.py` | en/ko translations — not consumed by any frontend |
| MCP specs | `docs/specs/integration/mcp_*.md` | 6 spec documents — no implementation |
| UI viewmodels | `src/ui/trace_timeline_viewer.py`, `artifact_viewer.py`, `diff_viewer.py` | Backend viewmodel definitions — not linked to shell |
| Execution record contract | `src/contracts/execution_record_contract.py` | `EXECUTION_RECORD_ALLOWED_STATUSES` etc. |
| Execution record model | `src/storage/models/execution_record_model.py` | `@dataclass(frozen=True)` — immutable by contract |

---

## CANONICAL PROVIDER CATALOG

> **New in v0.3 (M4).** This is the single authoritative provider catalog for all sections of this document. S-PROV and S5 both reference this table. No other provider wording is canonical.

| Provider | Model | Tier | Plan availability | Notes |
|---|---|---|---|---|
| Anthropic | Claude Haiku 3 | economy | Free, Pro, Team | Default for all plans |
| Anthropic | Claude Sonnet 4 | standard | Pro, Team only | Better quality; higher cost |
| OpenAI | GPT-4o | standard | Pro, Team only | Alternative to Sonnet; same plan tier |

**Rules:**
- Free plan: only Claude Haiku 3. Submitting a run that requests Sonnet or GPT-4o on a free plan → HTTP 402 with `provider.tier_not_available_on_plan`.
- Pro/Team plan: any of the three models. Default selection is Claude Haiku 3 unless the circuit or user overrides.
- Model selection is stored in the circuit's node config, not in the run request. The `provider_binding_store` maps `provider_key` (e.g., `anthropic`, `openai`) to Nexa-managed keys.
- Additional models (Gemini, Perplexity, Claude Opus) are deferred until usage patterns justify operational cost.
- BYOK is explicitly deferred (see S-PROV).

**Cost ratios (used by `PricingResolver`):**

| Model | Input cost ratio | Output cost ratio | Source |
|---|---|---|---|
| Claude Haiku 3 | 0.25 (relative) | 1.25 (relative) | Anthropic pricing |
| Claude Sonnet 4 | 3.0 (relative) | 15.0 (relative) | Anthropic pricing |
| GPT-4o | 2.5 (relative) | 10.0 (relative) | OpenAI pricing |

These ratios are maintained in a DB table (`provider_cost_catalog`) and refreshed monthly. `PricingResolver` reads from DB, falls back to `pricing_cache.py`, falls back to hardcoded defaults.

---

## S1. ASYNC EXECUTION INFRASTRUCTURE

### Why this is the primary product bottleneck

P0 runs `Engine.execute()` synchronously. A freelancer uploading a 30-page contract holds an HTTP connection open for 30–60 seconds. No viable UX is possible on top of synchronous blocking runs. **S1 is the primary product-critical bottleneck**, not CI/CD.

> CI/CD (S9) must start in parallel from sprint 1, but the primary product unblocking sequence is S1 (async) → S2 (upload) → S4 (browser). CI/CD enables reliable delivery of those segments.

### What already exists

- `worker_queue_models.py`, `worker_queue_orchestration.py`
- `run_auto_recovery_scheduler.py` + `run_auto_recovery_policy.py`
- `adaptive_scoring.py`
- `run_control_api.py` — retry/force-reset/mark-reviewed (defined, not activated)

### New implementation required

**Queue backend: arq (asyncio-native Redis Queue)**

```
arq>=0.25
redis>=5.0
```

**New files:**

`src/server/queue/__init__.py`
`src/server/queue/redis_client.py` — `create_redis_pool() -> arq.ArqRedis`
`src/server/queue/worker_functions.py` — `execute_run_job` with auto-recovery integration
`src/server/queue/worker_settings.py` — arq configuration, job timeout, retry policy
`src/server/queue/run_launcher.py` — `enqueue_run(run_id, ...) -> str`
`src/server/queue/cleanup_jobs.py` — all scheduled cleanup tasks
`scripts/start_worker.py`

**`run_submission_store_pg.py`** — formally defined in M2 resolution below.

**Auto-recovery:** wires `adaptive_scoring.py` + `run_auto_recovery_policy.py` into worker exception handler for provider fallback re-enqueueing.

**Activated routes:**
```
POST /api/runs/{run_id}/retry
POST /api/runs/{run_id}/force-reset
POST /api/runs/{run_id}/mark-reviewed
GET  /api/runs/{run_id}/actions
```

**Exit criterion:** `POST /api/runs` returns immediately with `status=queued`. Worker executes and stores result. `GET /api/runs/{run_id}` polls to `completed`. 2,775 existing tests green.

---

## S-PROV. PROVIDER OPERATING MODEL

### Decision

**Server-managed provider keys only for initial SaaS.** BYOK is explicitly deferred.

Re-evaluation conditions for BYOK:
1. >15% of Pro support tickets or survey responses explicitly request it
2. An enterprise tier is being defined requiring customer data isolation
3. Operational cost of BYOK is formally assessed against revenue uplift

### Canonical provider catalog

See the **CANONICAL PROVIDER CATALOG** section above. This is the authoritative reference. S-PROV does not redefine it.

### What server-managed means operationally

| Dimension | Server-managed (MVP) |
|---|---|
| Key storage | AWS Secrets Manager via `aws_secrets_manager_binding.py` |
| Cost accounting | Nexa pays provider bills; charges users via Stripe via quota/billing |
| Quota enforcement | Both run-count and cost-based (see S5 for full detail) |
| Provider binding persistence | `provider_binding_store_pg` stores Nexa-managed key references only — no raw API keys in DB |
| Support complexity | Nexa can diagnose provider failures end-to-end |

### `provider_cost_catalog` table

```python
TableSpec(name="provider_cost_catalog", columns=(
    ColumnSpec(sql_definition="catalog_entry_id TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="provider_key TEXT NOT NULL"),
    ColumnSpec(sql_definition="model_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="input_cost_ratio NUMERIC(10,6) NOT NULL"),
    ColumnSpec(sql_definition="output_cost_ratio NUMERIC(10,6) NOT NULL"),
    ColumnSpec(sql_definition="plan_tier TEXT NOT NULL"),
    ColumnSpec(sql_definition="effective_from TIMESTAMPTZ NOT NULL"),
    ColumnSpec(sql_definition="effective_until TIMESTAMPTZ"),
))
```

`PricingResolver` reads from this table first, falls back to `pricing_cache.py`, falls back to hardcoded defaults.

**Exit criterion:** Provider catalog documented in DB, server-managed keys in AWS SM, `PricingResolver` wired to quota enforcement (S5), no BYOK code introduced.

---

## S2. FILE UPLOAD AND STORAGE (WITH QUARANTINE)

### Upload quarantine state model

```
pending_upload
    ↓ (confirm called)
quarantine
    ↓ (scan job picks up)
scanning
    ↓                    ↓
  safe              rejected
                        ↓
                (auto-deleted from S3 within 1h)
```

State stored in `file_uploads.status`. **Every state transition is recorded as a new row in `file_upload_events`** (Category A — append-only). `file_uploads` itself is Category B (mutable state).

**Statement:** Text-level safety scanning (`input_safety.py`) does **not** replace file-level safety scanning (ClamAV). Both are required at different stages.

### File-level safety: ClamAV

```python
import clamd
cd = clamd.ClamdUnixSocket()
result = cd.instream(file_bytes)
```

ClamAV deployed as a sidecar in docker-compose and Railway.

### Extraction limits

| Limit | Value | Behavior |
|---|---|---|
| Max file size | 10 MB | HTTP 413 at presign |
| Max extracted text | 200,000 chars | Truncated with warning |
| Max pages (PDF) | 100 | Pages beyond 100 ignored with warning |
| Extraction timeout | 30 s | `rejected` (reason: `extraction_timeout`) |
| Max DOCX paragraphs | 5,000 | Truncated with warning |

### Malformed file handling

| Condition | Result status | Reason code |
|---|---|---|
| `pypdf` extraction fails | `rejected` | `extraction_failed_malformed` |
| DOCX XML corrupted | `rejected` | `extraction_failed_malformed` |
| Valid MIME, wrong magic bytes | `rejected` | `mime_mismatch` |
| Password-protected PDF | `rejected` | `extraction_failed_protected` |
| ClamAV finds malware signature | `rejected` | `malware_detected` |
| Scan timeout | `rejected` | `scan_timeout` |

### New files

`src/server/file_upload_api.py`
`src/server/file_extractor.py`
`src/server/file_safety_scanner.py`
`src/server/s3_client.py`
`src/server/pg/file_upload_store_pg.py`

### Schema

```python
TableSpec(name="file_uploads", columns=(  # Category B — mutable state
    ColumnSpec(sql_definition="upload_id TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="workspace_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="user_id_ref TEXT NOT NULL"),  # opaque hash, not raw user_id
    ColumnSpec(sql_definition="s3_key TEXT"),
    ColumnSpec(sql_definition="mime_type TEXT"),
    ColumnSpec(sql_definition="file_size_bytes BIGINT"),
    ColumnSpec(sql_definition="status TEXT NOT NULL DEFAULT 'pending_upload'"),
    ColumnSpec(sql_definition="rejection_reason TEXT"),
    ColumnSpec(sql_definition="extracted_text_chars INT"),
    ColumnSpec(sql_definition="created_at TIMESTAMPTZ NOT NULL"),
    ColumnSpec(sql_definition="scanned_at TIMESTAMPTZ"),
    ColumnSpec(sql_definition="expires_at TIMESTAMPTZ NOT NULL"),
))

TableSpec(name="file_upload_events", columns=(  # Category A + D — immutable audit
    ColumnSpec(sql_definition="event_id TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="upload_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="from_status TEXT"),
    ColumnSpec(sql_definition="to_status TEXT NOT NULL"),
    ColumnSpec(sql_definition="reason TEXT"),
    ColumnSpec(sql_definition="occurred_at TIMESTAMPTZ NOT NULL"),
))
```

**New env variables:**
```
NEXA_S3_BUCKET=nexa-uploads-prod
NEXA_S3_REGION=ap-northeast-2
NEXA_S3_PRESIGN_EXPIRY_S=900
NEXA_MAX_UPLOAD_SIZE_BYTES=10485760
CLAMD_SOCKET=/var/run/clamav/clamd.ctl
NEXA_SCAN_TIMEOUT_S=30
```

**Exit criterion:** PDF transitions through `pending_upload → quarantine → scanning → safe`. EICAR test string → `rejected`. Only `safe` files may be used in run submissions.

---

## S3. KILLER USE CASE — CONTRACT REVIEW CIRCUIT

**Four-node circuit:** `document_parser → clause_extractor → plain_language_explainer → question_generator`

**Output format:**
```json
{
  "contract_review_result": {
    "document_ref": "<file_ref>",
    "clauses": [{
      "clause_id": "c_abc123",
      "text": "...",
      "page_ref": {"start": 1240, "end": 1580},
      "risk_level": "HIGH",
      "category": "ip_rights",
      "plain_text": "...",
      "why_it_matters": "..."
    }],
    "pre_signature_questions": [{
      "question": "...",
      "related_clause_ids": ["c_abc123"],
      "priority": "HIGH"
    }]
  }
}
```

**Design constraints:**
- `clause_id` = deterministic hash of `(node_id + clause_index)` — satisfies I5 (determinism)
- `page_ref` = character offset into extracted text, not PDF page number
- Source references preserved across all nodes for UI clause highlighting
- Default model: Claude Haiku 3 (economy tier — runs on Free plan)
- Registered as starter template `contract_review_v1`

**Prompt files:**
- `src/platform/plugins/prompts/contract_review/clause_extraction.prompt`
- `src/platform/plugins/prompts/contract_review/plain_language.prompt`
- `src/platform/plugins/prompts/contract_review/questions.prompt`

**Exit criterion:** Freelancer uploads a PDF, circuit runs to completion, result contains clause explanations + pre-signature questions with source references.

---

## S4. FRONTEND — NEXT.JS WEB APPLICATION

**Stack:** Next.js 14+ (App Router) + Clerk React SDK + Tailwind CSS + Zustand + React Query

**Key screens:**
```
/dashboard
/workspace/[id]/run         ← template gallery + file upload
/workspace/[id]/results/[runId]
/workspace/[id]/trace/[runId]
/pricing
/account
```

**Upload quarantine UX (required by S2 quarantine model):**
- `pending_upload` → "Uploading..."
- `quarantine` / `scanning` → "Scanning for safety..." (spinner)
- `safe` → "Ready" (enable run button)
- `rejected` → "File could not be processed: {i18n key for rejection_reason}"

**Viewmodel consumption:**

| Python viewmodel | Frontend component |
|---|---|
| `trace_timeline_viewer.py` | `TraceTimeline.tsx` |
| `artifact_viewer.py` | `ArtifactViewer.tsx` |
| `diff_viewer.py` | `DiffViewer.tsx` |
| `template_gallery.py` | `TemplateGallery.tsx` |
| `provider_setup_guidance.py` | `ProviderSetupGuide.tsx` |
| `execution_panel.py` | `RunStatusPoller.tsx` |

**i18n:** `next-intl`; keys mirror `_TRANSLATIONS` in `src/ui/i18n.py` for `en` and `ko`.

**Activated routes for S4:**
```
GET  /api/workspaces/{workspace_id}/result-history
GET  /api/templates/starter-circuits
GET  /api/templates/starter-circuits/{template_id}
POST /api/workspaces/{workspace_id}/starter-templates/{template_id}/apply
GET  /api/providers/catalog
GET  /api/workspaces/{workspace_id}/provider-bindings
GET  /api/workspaces/{workspace_id}/provider-bindings/health
GET  /api/workspaces/{workspace_id}/runs
GET  /api/runs/{run_id}/artifacts
GET  /api/artifacts/{artifact_id}
```

**Exit criterion:** Freelancer can sign up, upload a contract PDF, watch quarantine scan complete, submit run, read clause explanations in browser — no CLI.

---

## S5. PAYMENTS AND FREEMIUM (COST-BASED QUOTA)

### Plan structure

| Plan | Price | Run-count limit | Cost cap (estimated) | Model access |
|---|---|---|---|---|
| Free | $0 | 3 runs/month | $0.50/month est. | Claude Haiku 3 only |
| Pro | $19/month | Unlimited | $15/month est. | Claude Haiku 3 + Sonnet 4 + GPT-4o |
| Team | $49/seat/month | Unlimited | $40/month est. | Same as Pro |

> **Model access is governed by the CANONICAL PROVIDER CATALOG.** Free plan access is restricted to Claude Haiku 3. Pro/Team can access Claude Sonnet 4 and GPT-4o in addition.

### Three quota enforcement axes

**Axis 1: Run count** (`QuotaPolicy.max_run_count`)
- Free: 3 runs/calendar month
- Enforced at `POST /api/runs` before queue submission
- Counter: `quota_usage.run_count` per user per period_key

**Axis 2: Estimated cost** (`QuotaPolicy.max_estimated_cost`)
- Pre-run preflight: `PricingResolver.resolve(provider, model)` × estimated token count → `projected_cost`
- If `consumed_estimated_cost + projected_cost > max_estimated_cost` → block HTTP 402 + `quota.cost_preflight_exceeded`
- Uses `pricing_resolver.py` (existing) reading from `provider_cost_catalog` (new) table

**Axis 3: Actual cost** (`QuotaPolicy.max_actual_cost`)
- Post-run: actual token usage from provider response → `quota_usage.consumed_actual_cost`
- Soft block if `consumed_actual_cost > max_actual_cost`: warn user + email
- Hard block if actual cost > 120% of `max_actual_cost` (overage buffer)

### Pre-run cost estimation

`src/server/run_preflight.py`

```python
@dataclass(frozen=True)
class CostEstimate:
    provider: str
    model_id: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    estimation_confidence: Literal["high", "medium", "low"]
```

Token estimator: heuristic (input text length + circuit node count). ±50% accuracy is sufficient for MVP.

### What already exists

- `quota.py`: `QuotaPolicy`, `QuotaScope`, `QuotaUsageSummary`, `QuotaViolation`, check logic
- `pricing_resolver.py`: `PricingResolver.resolve(provider) → ProviderCost`
- `pricing_cache.py`: `PricingCache`

### Schema

```python
TableSpec(name="user_subscriptions", columns=(  # Category B
    ColumnSpec(sql_definition="user_id_ref TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="stripe_customer_id TEXT"),
    ColumnSpec(sql_definition="plan TEXT NOT NULL DEFAULT 'free'"),
    ColumnSpec(sql_definition="status TEXT NOT NULL DEFAULT 'active'"),
    ColumnSpec(sql_definition="period_end TIMESTAMPTZ"),
    ColumnSpec(sql_definition="updated_at TIMESTAMPTZ NOT NULL"),
))

TableSpec(name="quota_usage", columns=(  # Category C
    ColumnSpec(sql_definition="quota_key TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="user_id_ref TEXT NOT NULL"),
    ColumnSpec(sql_definition="workspace_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="period_key TEXT NOT NULL"),
    ColumnSpec(sql_definition="run_count INT NOT NULL DEFAULT 0"),
    ColumnSpec(sql_definition="consumed_estimated_cost NUMERIC(10,6) NOT NULL DEFAULT 0"),
    ColumnSpec(sql_definition="consumed_actual_cost NUMERIC(10,6) NOT NULL DEFAULT 0"),
    ColumnSpec(sql_definition="updated_at TIMESTAMPTZ NOT NULL"),
))
```

**New files:**
`src/server/run_preflight.py`
`src/server/quota_enforcement.py`
`src/server/stripe_client.py`
`src/server/stripe_webhook_handler.py`
`src/server/pg/subscription_store_pg.py`
`src/server/pg/quota_usage_store_pg.py`

**New dependency:** `stripe>=8.0`

**Exit criterion:** Free users blocked after 3 runs OR estimated cost > $0.50. Pro users have cost preflight. Free plan requests for Sonnet/GPT-4o → HTTP 402. Stripe webhook updates plan.

---

## S6. EMAIL AND NOTIFICATIONS

**Provider:** Resend (`resend>=1.0`)

**Events:**

| Event | Trigger | Template |
|---|---|---|
| Welcome | Sign-up | `welcome` |
| Run completed | Worker job completes | `run_completed` |
| Run failed | Worker job fails | `run_failed` |
| Quota warning (80%) | 80% of run-count or cost limit | `quota_warning` |
| Quota exceeded | Hard block triggered | `quota_exceeded` |
| Payment failed | `invoice.payment_failed` Stripe event | `payment_failed` |
| Subscription cancelled | Stripe event | `subscription_cancelled` |
| File rejected | Upload quarantine → rejected | `file_rejected` |

**New files:**
`src/server/email_client.py`
`src/server/email_templates.py`
`src/server/notification_dispatcher.py`

**Exit criterion:** User receives email after async run completes and after file rejection. Welcome email sends on signup.

---

## S7. MONITORING AND OBSERVABILITY (WITH REDACTION POLICY)

### Error tracking: Sentry

```
sentry-sdk[fastapi]>=1.40
```

### Distributed tracing: OpenTelemetry

```
opentelemetry-sdk>=1.24
opentelemetry-exporter-otlp>=1.24
opentelemetry-instrumentation-fastapi>=0.45b0
opentelemetry-instrumentation-sqlalchemy>=0.45b0
opentelemetry-instrumentation-redis>=0.45b0
```

### Redaction policy — 8 mandatory rules

This policy applies to all observability systems: Sentry, OTel traces/spans, structured logs, metrics.

**Rule 1 — Document content must never be emitted.**

The following must never appear in any log line, Sentry event, OTel span attribute, or metric label:
- Extracted text from uploaded files
- `clause_text`, `plain_text`, `why_it_matters`, `question` from contract review results
- `input.text` working context values
- `prompt.*.rendered` values that incorporate user document text
- `provider.*.output` values

**Rule 2 — PII must never be emitted.**

Never emit: email addresses, raw user IDs, Clerk subject refs. Use opaque `user_ref` (sha256 of `user_id`) in all observability fields.

**Rule 3 — Credentials must never be emitted.**

Never emit: API keys, JWT tokens (full or partial), presigned S3 URLs, AWS access keys.

**Rule 4 — Permitted observability fields.**

| Category | Permitted | Forbidden |
|---|---|---|
| Run identity | `run_id`, `workspace_id`, `template_id` | Any payload content |
| User identity | `user_ref` (opaque hash only) | `user_id`, email, Clerk sub |
| Engine execution | node execution count, duration, status | Working context values |
| Quota | `plan`, `run_count`, `cost_ratio` | Actual cost amounts |
| Error info | Exception class name, sanitized stack trace | Error messages containing user data |
| File upload | `upload_id`, `file_size_bytes`, `mime_type`, scan duration | File content, original filename |

**Rule 5 — Sentry scrubbing.**

```python
sentry_sdk.init(
    before_send=scrub_sentry_event,
    send_default_pii=False,
    request_bodies="never",
)
```

`scrub_sentry_event`: removes `request.data` and `request.body`, scrubs fields matching credential/email patterns from `input_safety.py`.

**Rule 6 — OTel SQL statement policy (revised in v0.3 — M3).**

Raw SQL text (`db.statement`) is **forbidden** in observability output by default.

**What happened in v0.2:** The redaction policy allowed `db.statement` truncated to 200 characters. This is unsafe because OTel SQLAlchemy instrumentation captures the full SQL statement including parameter values when using certain instrumentation modes. SQL statements can contain user data fragments (e.g., a query that filters by user-supplied content).

**v0.3 policy:** The `Scrubbing SpanProcessor` in `src/server/log_scrubber.py` must:
- Remove all span attributes with key `db.statement`
- Remove all span attributes with key `db.query.text`
- Preserve permitted normalized identifiers only:
  - `db.operation` — the SQL operation type: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
  - `db.sql.table` — the table name (single word, not a full statement)
  - `nexa.query_label` — an internal label set explicitly in application code (e.g., `"workspace_lookup"`, `"execution_record_insert"`) before the query executes
- If a query needs to be identifiable in traces, the application code must set `nexa.query_label` explicitly using `with tracer.start_as_current_span(...) as span: span.set_attribute("nexa.query_label", "label_name")` before calling the DB

No raw SQL snippet — even truncated or parameter-stripped — is treated as safe observability output by default. Any exception requires explicit justification and code review.

**Rule 7 — Request/response logging.**

HTTP access logs contain only: `method`, `path`, `status_code`, `duration_ms`, `request_id`. No request bodies. No response bodies. Path parameters (`run_id`, `workspace_id`) are permitted. Query parameters are not logged.

**Rule 8 — Log retention.**

- Application logs: 30 days
- Sentry events: 90 days
- OTel traces: 7 days

### Key metrics

- `run.submitted_count` (counter, labels: plan, template)
- `run.completed_duration_s` (histogram, labels: template)
- `run.failure_rate` (gauge, labels: error_family)
- `quota.exceeded_count` (counter, labels: plan, axis)
- `worker.queue_depth` (gauge)
- `db.query_duration_ms` (histogram, labels: `nexa.query_label`)
- `upload.scan_duration_s` (histogram)
- `upload.rejected_count` (counter, labels: rejection_reason)

**New files:**
`src/server/telemetry.py`
`src/server/log_scrubber.py`

**Exit criterion:** A test run that processes a real document generates Sentry events and OTel traces. Automated test asserts no span attribute contains document content strings. No `db.statement` attribute appears in any trace.

---

## S8. SECURITY AND COMPLIANCE HARDENING

### Rate limiting (`slowapi>=0.1.9`)

- Global: 60 req/min per authenticated user
- `POST /api/runs`: 10/min per user
- `POST /api/uploads/presign`: 20/min per user
- Anonymous: 10/min per IP

### Input safety enforcement

`InputSafetyScanner` from `src/safety/input_safety.py` wired at `POST /api/runs`:
- Credential patterns → HTTP 422 + `input.unsafe.credential_detected`
- PII patterns → warn or redact per `workspace.input_policy`

### CORS hardening

`NEXA_CORS_ORIGINS=https://app.nexa.run` (no wildcard in production)

### GDPR — data deletion

`DELETE /api/users/me` → `user_deletion_service.py`:
- Clerk account deletion (authoritative identity removed)
- `workspace_memberships` rows → deleted (Category B)
- `user_subscriptions` rows → deleted (Category B)
- `user_preferences` rows → deleted (Category B)
- S3 file objects → deleted immediately
- Stripe subscription → cancelled
- `user_deletion_audit` row inserted (Category D — permanent)
- `execution_record_archive_index` row inserted with `archive_reason='user_deletion'` for each of the user's runs

**`execution_record` rows are not touched.** Per the PII Placement Rule, `execution_record` contains only opaque `user_ref` (sha256 hash of `user_id`), not raw PII. With Clerk identity deleted and `workspace_memberships` deleted, the `user_ref` in `execution_record` is permanently orphaned from any identifying information — no in-place anonymization is required or performed. Category A immutability is fully preserved.

### Security headers

`SecurityHeadersMiddleware`: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`.

### Audit logging

`run_action_log_api.py` wired for all run lifecycle events.

**Exit criterion:** Rate limiting active. CORS restricted. Input safety enforced. GDPR deletion works. Security headers present.

---

## S9. CI/CD PIPELINE

> CI/CD runs in parallel from sprint 1. It enables reliable delivery of S1–S-ADMIN but does not substitute for building them. Primary product bottleneck remains S1 → S2 → S4.

**`.github/workflows/ci.yml`** — on every PR:
```yaml
- pip install -r requirements.txt && pip install ".[testing]"
- ruff check src tests
- python -m pytest -q --timeout=120
- alembic check
- cd frontend && npm ci && npm run lint && npm run build
```

**`.github/workflows/deploy-staging.yml`** — on merge to `main`:
```yaml
- alembic upgrade head   # Railway release command
- railway deploy
- smoke-test: /healthz + /readyz
```

**`.github/workflows/deploy-production.yml`** — on git tag `v*`:
```yaml
- alembic upgrade head
- railway deploy --environment production
- smoke-test
```

Worker is a separate Railway service. Scale independently.

**Exit criterion:** PR → CI green → merge → staging auto-deploys → tag → production auto-deploys.

---

## S-OPS. DATA LIFECYCLE, BACKUP, AND RECOVERY

### PostgreSQL backup policy

| Component | Specification |
|---|---|
| Base backup frequency | Daily at 02:00 UTC |
| WAL archiving | Continuous |
| Backup retention | 30 days base backups; 7 days WAL |
| Backup destination | `nexa-db-backups-prod` S3 bucket |
| Backup encryption | AES-256 (S3 SSE) |
| Backup verification | Weekly automated restore-and-verify to throwaway instance |
| RTO | < 1 hour (point-in-time recovery) |
| RPO | < 5 minutes (continuous WAL) |

**Restore runbook (`docs/ops/db_restore_runbook.md`):**
```
1. Provision new Postgres 16 instance
2. Restore most recent base backup from S3
3. Apply WAL segments to recovery target time
4. Run: alembic upgrade head
5. Run smoke tests
6. Switch NEXA_SERVER_DB_HOST
7. Verify /readyz → {"alembic": "at_head", "db": "connected"}
8. Reconcile run_submissions vs execution_record for Redis loss (see below)
```

### Redis loss recovery (revised in v0.3 — M2)

**What happened in v0.2:** The Redis durability section referenced a `run_submissions` table for recovery, but that table was not defined anywhere in the plan. This was an undefined recovery claim.

**v0.3 resolution:** `run_submissions` is now a formally defined table, store, and migration component (see schema below). Every `POST /api/runs` inserts a row into `run_submissions` **before** the job is enqueued to Redis. This ensures that if Redis is lost, submitted runs can be recovered.

**Recovery flow after Redis loss:**

```
1. Identify submitted runs that did not complete:
   SELECT * FROM run_submissions
   WHERE status = 'submitted'
   AND submitted_at > now() - interval '48 hours'
   AND run_id NOT IN (
       SELECT run_id FROM execution_record WHERE status IN ('completed','failed','partial','cancelled')
   );

2. For each unrecovered run:
   - If within IDEMPOTENCY_WINDOW_S: re-enqueue via /api/admin/runs/{run_id}/retry
   - If outside window: mark run_submissions.status = 'lost_redis'; notify user to resubmit

3. Update run_submissions.status = 'requeued' for re-enqueued runs
```

**`run_submissions` table (new in v0.3):**

```python
TableSpec(name="run_submissions", columns=(  # Category C — TTL-bounded deletable
    ColumnSpec(sql_definition="run_id TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="workspace_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="user_id_ref TEXT NOT NULL"),
    ColumnSpec(sql_definition="target_ref TEXT NOT NULL"),
    ColumnSpec(sql_definition="input_payload_ref TEXT"),  # file_ref or inline ref
    ColumnSpec(sql_definition="provider_key TEXT NOT NULL"),
    ColumnSpec(sql_definition="model_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="status TEXT NOT NULL DEFAULT 'submitted'"),
    # status: submitted | queued | requeued | lost_redis | completed | failed
    ColumnSpec(sql_definition="submitted_at TIMESTAMPTZ NOT NULL"),
    ColumnSpec(sql_definition="expires_at TIMESTAMPTZ NOT NULL"),
    # expires_at = submitted_at + 48h; cleanup job deletes rows after expiry
))
```

`src/server/pg/run_submission_store_pg.py` — new store

**`run_submissions` retention:** Category C. Cleanup job deletes rows where `expires_at < now()` AND `status IN ('completed', 'failed', 'lost_redis')`. Rows are retained for 48 hours after submission for recovery purposes, then deleted.

**Redis durability expectations (unchanged from v0.2):**

Redis data loss is acceptable with the `run_submissions` recovery flow above. Redis does not store business state — Postgres is authoritative (see Source-of-Truth Hierarchy table).

Redis persistence config: RDB snapshots every 15 min + AOF `appendonly yes, appendfsync everysec`.

### Execution record retention (revised in v0.4 — M1 final resolution)

**What was still wrong in v0.3:** Category A was defined as "Rows are never updated or deleted in place," but S-OPS still described a hard-delete workflow for `execution_record` rows ("permitted only via an audited retention workflow initiated by a human operator"). This created a hidden exception inside the Category A definition — a contradiction that made the classification system untrustworthy.

**v0.4 resolution — explicit answer:**

> **Is `execution_record` ever hard-deleted? No.**

`execution_record` is Category A. Category A means never updated and never deleted — no exceptions, including no operator-initiated hard-delete workflows. The S-OPS hard-delete workflow described in v0.3 is removed entirely.

**What is immutable:** Every row in `execution_record` is a committed, finalized execution artifact. No UPDATE and no DELETE is ever issued against a committed row for any reason.

**How archival is handled (read-surface filtering only):**

| Step | Mechanism |
|---|---|
| Day 90: mark for archive | `cleanup_jobs.py::archive_old_execution_records` inserts a row in `execution_record_archive_index` — does NOT touch `execution_record` |
| Read surfaces | `GET /api/runs/{id}` and `GET /api/workspaces/{id}/runs` filter by archive index — archived runs are excluded from default results but remain accessible via `?include_archived=true` (admin only) |
| Storage cost management | If `execution_record` table size becomes a cost concern, handle through Postgres tablespace tiering, partition archiving to cold storage (e.g., pg_partman), or exporting archived rows to S3 Parquet for analytical storage — never by row deletion |
| GDPR user deletion | Does not touch `execution_record`. Inserts `execution_record_archive_index` row with `archive_reason='user_deletion'`. The immutable record is untouched. Compliance is preserved because `execution_record` contains no direct PII (see PII Placement Rule). |

**How auditability is preserved:**

The `execution_retention_audit` table (Category D, permanent) records every archival event. Because `execution_record` rows are never deleted, `execution_retention_audit` is an audit of archival visibility changes only — not deletion events.

**How query behavior changes after archival:**

- Default queries: archived runs excluded from result sets
- `?include_archived=true`: archived runs included (admin-only parameter)
- Archive index join: O(1) index lookup; no full table scan on `execution_record`

**What was removed from v0.3:**

The hard-delete workflow table entry ("Permitted only via an audited retention workflow initiated by a human operator... before the `execution_record` row is deleted") is removed. It is not replaced. `execution_record` rows are never deleted.

### S3 data lifecycle policy

| Object | Retention | Mechanism |
|---|---|---|
| `rejected` files | Deleted within 1 hour of rejection | S3 lifecycle rule on `status=rejected` tag |
| `expired` uploads (never confirmed) | Deleted after 24 hours | S3 lifecycle: no confirm > 24h |
| `safe` files (active run) | Run lifetime + 90 days | Manual deletion via GDPR or retention flow |
| `safe` files (orphaned) | Deleted after 7 days | Scheduled cleanup job |
| `safe` files (user deleted) | Deleted immediately | `user_deletion_service.py` |
| DB backup objects | 30-day expiry | S3 lifecycle on backup bucket |
| WAL segments | 7-day expiry | S3 lifecycle on backup bucket |

### Scheduled cleanup jobs (`src/server/queue/cleanup_jobs.py`)

| Job | Schedule | What it does |
|---|---|---|
| `cleanup_expired_uploads` | Every hour | Deletes `rejected`/`expired` S3 objects; updates `file_uploads.status` |
| `cleanup_orphaned_uploads` | Daily 03:00 UTC | Deletes S3 objects for deleted runs >7 days ago |
| `cleanup_dedupe_rows` | Every 30 min | Deletes `run_submission_dedupe` where `expires_at < now()` |
| `cleanup_run_submissions` | Every 6 hours | Deletes `run_submissions` where `expires_at < now()` AND status is terminal |
| `cleanup_quota_usage` | Monthly | Deletes quota rows older than 3 periods |
| `archive_old_execution_records` | Daily 04:00 UTC | Inserts `execution_record_archive_index` rows (does NOT mutate `execution_record`) |
| `verify_db_backup` | Weekly Sunday 05:00 UTC | Triggers backup verification pipeline |

### Incident runbooks

Required in `docs/ops/`:
- `db_restore_runbook.md` — full PostgreSQL restore procedure
- `redis_loss_runbook.md` — "Redis went down; recover via run_submissions reconciliation"
- `s3_incident_runbook.md` — "S3 unavailable; handle in-flight uploads"
- `worker_stuck_runbook.md` — "Jobs queued but not processed; diagnose via admin surface"

**Exit criterion:** Daily backup runs. Quarterly restore drill scheduled. Cleanup jobs run. Runbooks exist in `docs/ops/`. `execution_record` rows are never updated by cleanup jobs. `execution_record_archive_index` is queryable.

---

## S-ADMIN. INTERNAL ADMIN AND SUPPORT SURFACE

**Not a public product.** Internal-only, accessible to `role=admin` via existing `AuthorizationGate`.

### What already exists

- `run_control_api.py` — retry/force-reset/mark-reviewed (defined, not activated)
- `provider_health_api.py` + `provider_probe_api.py` — health + probe (defined, not activated)
- `recent_activity_api.py` — activity read (defined, not activated)
- `run_action_log_api.py` — lifecycle log (defined, not activated)

### Admin capabilities

**1. Failed run diagnosis**
```
GET  /api/admin/runs?status=failed&workspace_id=...&since=...
GET  /api/admin/runs/{run_id}/diagnosis
```
Returns: run record + action log + worker job history + provider health at failure time + auto-recovery outcomes.

**2. Stuck job reprocessing**
```
POST /api/admin/runs/{run_id}/force-reset
POST /api/admin/runs/{run_id}/retry
POST /api/admin/queue/reprocess-orphans
```
`reprocess-orphans`: uses `WorkerOrphanReview` from `worker_queue_models.py` + `run_submissions` reconciliation.

**3. Upload management**
```
GET  /api/admin/uploads?status=quarantine&since=...
POST /api/admin/uploads/{upload_id}/force-reject
POST /api/admin/uploads/{upload_id}/force-safe     ← requires reason + 2FA
GET  /api/admin/uploads/{upload_id}/scan-report
```
All mutations logged to `admin_action_audit`.

**4. Quota and subscription inspection**
```
GET  /api/admin/users/{user_ref}/quota-usage
GET  /api/admin/users/{user_ref}/subscription
POST /api/admin/users/{user_ref}/quota-reset
POST /api/admin/users/{user_ref}/plan-override
```

**5. Provider health inspection**

Uses existing `provider_health_api.py` and `provider_probe_api.py`:
```
GET  /api/admin/providers/health
POST /api/admin/providers/{provider_key}/probe
GET  /api/admin/providers/{provider_key}/probe-history
```

**6. Stripe webhook reconciliation**
```
POST /api/admin/webhooks/stripe/replay?event_id=...
GET  /api/admin/webhooks/stripe/recent?limit=20
```

**7. Audit log**
```
GET /api/admin/audit?user_ref=...&action_type=...&since=...
```
Unified view across `run_action_log`, `file_upload_events`, `admin_action_audit`.

### Schema

```python
TableSpec(name="admin_action_audit", columns=(  # Category A + D — immutable permanent
    ColumnSpec(sql_definition="audit_id TEXT PRIMARY KEY"),
    ColumnSpec(sql_definition="actor_user_ref TEXT NOT NULL"),  # opaque hash
    ColumnSpec(sql_definition="action_type TEXT NOT NULL"),
    ColumnSpec(sql_definition="target_type TEXT NOT NULL"),
    ColumnSpec(sql_definition="target_id TEXT NOT NULL"),
    ColumnSpec(sql_definition="reason TEXT"),
    ColumnSpec(sql_definition="payload_summary TEXT"),
    ColumnSpec(sql_definition="occurred_at TIMESTAMPTZ NOT NULL"),
))
```

**New file:** `src/server/admin_api.py`, `src/server/pg/admin_audit_store_pg.py`

**Exit criterion:** Operator can diagnose failed run, reprocess stuck job, inspect quarantined upload, view quota usage, replay Stripe webhook — all without SQL. All mutations logged to `admin_action_audit`.

---

## S10. CAPABILITY BUNDLE ACTIVATION

> Route counts are not the KPI. Capability availability for users is the KPI.

### Capability bundles

| Bundle | Capabilities | Prerequisite |
|---|---|---|
| `core` | Submit run, poll status, result, trace, workspace CRUD | P0 |
| `async_control` | Retry, cancel, force-reset, action log | S1 |
| `upload` | File upload, quarantine status, file-linked runs | S2 |
| `templates` | Starter template gallery, apply template | S4 |
| `provider_management` | Provider catalog, binding setup, health, probe | S-PROV |
| `result_history` | Workspace result history, recent activity | S4 |
| `billing` | Checkout, subscription, customer portal, webhooks | S5 |
| `admin` | All S-ADMIN endpoints | S-ADMIN + admin role |
| `shares` | Public circuit sharing, community hub | Post-PMF |
| `mcp` | MCP manifest, host-bridge | S12 |

**`NEXA_SURFACE_PROFILE`** takes a comma-separated list of bundle names.

### Public shares (later expansion)

Public sharing requires: `public_shares` table, community moderation, legal review of UGC policy. Deferred until core product demonstrates PMF. Do not build to unblock anything in S1–S-ADMIN.

**Exit criterion:** `NEXA_SURFACE_PROFILE` config controls exactly which bundles are active. Each bundle has a contract test asserting its route set.

---

## S11. MOBILE APPLICATION

> **Mobile is not part of the minimum SaaS-operable baseline.** S11 begins only when all three browser PMF criteria are met:
> 1. ≥100 weekly active freelancers using the browser product
> 2. Contract review completion rate ≥60%
> 3. Mobile is a top-3 user request by survey or support ticket volume

When criteria are met:

**Stack:** React Native + Expo + `@clerk/expo` + `expo-document-picker` + `expo-notifications`

**Mobile-specific server additions:**
- `src/server/push_notification_client.py` — Expo Push API
- `push_notification_tokens` table (Category B)
- `pytesseract` for camera-scan OCR (server-side)

API surface is identical to web; no mobile-specific endpoints required.

---

## S12. MCP INTEGRATION

Deferred until S1–S-ADMIN are stable.

Spec files: `docs/specs/integration/mcp_*.md` (6 documents).

Backend routes already defined: `GET /api/integrations/public-mcp/manifest`, `GET /api/integrations/public-mcp/host-bridge`.

New files when S12 begins:
- `src/server/mcp_bridge_runtime.py`
- `src/server/mcp_manifest_runtime.py`

---

## IMPLEMENTATION DEPENDENCY GRAPH

```
Phase 4.5 P0 (complete)
     │
     ├── S9 (CI/CD) ── starts sprint 1, runs in parallel throughout
     │
     ├── S1 (Async Queue) ← PRIMARY product bottleneck #1
     │    │
     │    ├── S-PROV (Provider Model) ← decide before S2/S3
     │    │    │
     │    │    └── S2 (File Upload + Quarantine) ← PRIMARY bottleneck #2
     │    │         │
     │    │         └── S3 (Contract Review Circuit)
     │    │              │
     │    │              └── S4 (Frontend) ← PRIMARY bottleneck #3
     │    │
     │    └── S7 (Monitoring + Redaction) ← add before any external user
     │
     ├── S5 (Billing + Cost Quota) ← after S4 (pricing page needs UI)
     │    └── S6 (Email)
     │
     ├── S8 (Security Hardening) ← before public access
     ├── S-OPS (Backup/Recovery) ← before public access
     ├── S-ADMIN (Admin Surface) ← before public access
     │
     └── S10 (Capability Bundles) ← progressive activation throughout
          └── S11 (Mobile) ← ONLY after browser PMF confirmed
               └── S12 (MCP) ← last; after operational stability
```

### Sprint sequencing

| Sprint | Primary | Parallel | Milestone |
|---|---|---|---|
| 1 | S1 (async queue) | S9 (CI/CD setup) | Runs non-blocking |
| 2 | S-PROV (provider model + catalog) | S7 (Sentry basic) | Provider model decided; errors visible |
| 3 | S2 (upload + quarantine) | S9 (staging deploy) | File upload safe |
| 4 | S3 (contract review circuit) | — | Killer UC backend |
| 5 | S4 skeleton (login + run + result) | S8 (rate limit + CORS) | Browser UI exists |
| 6 | S4 polished (quarantine UX + clause UI) | S-OPS (backup policy) | **Minimum viable SaaS** |
| 7 | S5 (billing + cost quota) | S6 (email) | Freemium active |
| 8 | S-ADMIN (admin surface) | S7 (full OTel + redaction) | Operationally mature |
| 9 | S8 (GDPR + security headers) | S-OPS (restore drill) | Safe public access |
| 10 | S10 (capability bundles) | — | Full API surface |
| 11+ | S11 (mobile) | — | Post browser PMF only |
| Later | S12 (MCP) | — | After operational stability |

**Sprint 6 = minimum viable SaaS.**
**Sprint 8 = revenue-generating and operationally mature SaaS.**

---

## COMPLETE FILE INVENTORY

### New dependencies

```
# S1
arq>=0.25
redis>=5.0

# S2
boto3>=1.34       # promoted from [aws] extra
python-magic>=0.4
pypdf>=3.0
python-docx>=1.0
clamd>=1.0

# S5
stripe>=8.0

# S6
resend>=1.0

# S7
sentry-sdk[fastapi]>=1.40
opentelemetry-sdk>=1.24
opentelemetry-exporter-otlp>=1.24
opentelemetry-instrumentation-fastapi>=0.45b0
opentelemetry-instrumentation-sqlalchemy>=0.45b0
opentelemetry-instrumentation-redis>=0.45b0

# S8
slowapi>=0.1.9

# S11 (post PMF)
pytesseract>=0.3
```

### New backend files

```
# S1 — Async queue
src/server/queue/__init__.py
src/server/queue/redis_client.py
src/server/queue/worker_functions.py
src/server/queue/worker_settings.py
src/server/queue/run_launcher.py
src/server/queue/cleanup_jobs.py
scripts/start_worker.py

# S-PROV — Provider operating model
src/server/pg/provider_cost_catalog_store_pg.py  ← new in v0.3

# S2 — File upload
src/server/file_upload_api.py
src/server/file_extractor.py
src/server/file_safety_scanner.py
src/server/s3_client.py
src/server/pg/file_upload_store_pg.py

# S3 — Contract review
examples/contract_review/contract_review.nex
src/platform/plugins/prompts/contract_review/clause_extraction.prompt
src/platform/plugins/prompts/contract_review/plain_language.prompt
src/platform/plugins/prompts/contract_review/questions.prompt

# S5 — Payments
src/server/run_preflight.py
src/server/quota_enforcement.py
src/server/stripe_client.py
src/server/stripe_webhook_handler.py
src/server/pg/subscription_store_pg.py
src/server/pg/quota_usage_store_pg.py
src/server/pg/run_submission_store_pg.py   ← new in v0.3 (M2)

# S6 — Email
src/server/email_client.py
src/server/email_templates.py
src/server/notification_dispatcher.py

# S7 — Monitoring
src/server/telemetry.py
src/server/log_scrubber.py

# S8 — Security
src/server/rate_limiting.py
src/server/user_deletion_service.py
src/server/security_headers_middleware.py

# S9 — CI/CD
.github/workflows/ci.yml
.github/workflows/deploy-staging.yml
.github/workflows/deploy-production.yml

# S-OPS — Data lifecycle
docs/ops/db_restore_runbook.md
docs/ops/redis_loss_runbook.md
docs/ops/s3_incident_runbook.md
docs/ops/worker_stuck_runbook.md
src/server/pg/execution_archive_store_pg.py    ← new in v0.3 (M1)
src/server/pg/run_submission_store_pg.py       ← listed above under S5

# S-ADMIN — Admin surface
src/server/admin_api.py
src/server/pg/admin_audit_store_pg.py

# S11 (post PMF)
src/server/push_notification_client.py

# S12 (last)
src/server/mcp_bridge_runtime.py
src/server/mcp_manifest_runtime.py
```

### New DB tables

```
# S-PROV
provider_cost_catalog          ← new in v0.3 (Category B)

# S2
file_uploads                   (Category B)
file_upload_events             (Category A + D)

# S5
user_subscriptions             (Category B)
quota_usage                    (Category C)
run_submissions                ← new in v0.3 (Category C)

# S7 / S8
user_preferences               (Category B)
user_deletion_audit            (Category D)

# S-OPS
execution_record_archive_index ← new in v0.3 (Category A + D)
execution_retention_audit      ← new in v0.3 (Category D)

# S-ADMIN
admin_action_audit             (Category A + D)

# S11 (post PMF)
push_notification_tokens       (Category B)
```

### Alembic revisions

```
0001_initial                         (P0)
0002_run_submission_dedupe           (P0)
0003_file_uploads                    (S2) — includes file_upload_events
0004_run_submissions_and_catalog     (S5 + S-PROV) ← new in v0.3
   - run_submissions table
   - provider_cost_catalog table
0005_subscriptions_quota             (S5)
0006_user_preferences                (S6)
0007_user_deletion_audit             (S8)
0008_execution_archive               (S-OPS) ← new in v0.3
   - execution_record_archive_index
   - execution_retention_audit
0009_admin_action_audit              (S-ADMIN)
0010_push_tokens                     (S11)
```

---

## COMPLETE ENVIRONMENT VARIABLES

```bash
# === Database (P0) ===
NEXA_SERVER_DB_HOST=
NEXA_SERVER_DB_PORT=5432
NEXA_SERVER_DB_NAME=nexa
NEXA_SERVER_DB_USER=nexa
NEXA_SERVER_DB_PASSWORD=
NEXA_SERVER_DB_SSLMODE=require

# === App mode (P0) ===
NEXA_DEPENDENCY_MODE=postgres
NEXA_SURFACE_PROFILE=core,async_control,upload,templates,provider_management,result_history
NEXA_ENV=production

# === Auth (P0 / G2) ===
NEXA_AUTH_MODE=clerk
NEXA_CLERK_JWKS_URL=

# === Engine (P0) ===
NEXA_P0_MAX_RUN_DURATION_S=3600
NEXA_P0_ENGINE_THREADPOOL_MAX=4
IDEMPOTENCY_WINDOW_S=86400

# === Redis (S1) ===
NEXA_REDIS_URL=redis://localhost:6379/0
NEXA_WORKER_MAX_JOBS=4

# === S3 / File upload (S2) ===
NEXA_S3_BUCKET=nexa-uploads-prod
NEXA_S3_REGION=ap-northeast-2
NEXA_S3_PRESIGN_EXPIRY_S=900
NEXA_MAX_UPLOAD_SIZE_BYTES=10485760
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# === File safety (S2) ===
CLAMD_SOCKET=/var/run/clamav/clamd.ctl
NEXA_SCAN_TIMEOUT_S=30

# === DB backup (S-OPS) ===
NEXA_DB_BACKUP_S3_BUCKET=nexa-db-backups-prod
NEXA_DB_BACKUP_RETENTION_DAYS=30

# === AI Providers (S-PROV) ===
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# === Stripe (S5) ===
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID_FREE=
STRIPE_PRICE_ID_PRO=
STRIPE_PRICE_ID_TEAM=
NEXA_APP_BASE_URL=https://app.nexa.run

# === Email (S6) ===
RESEND_API_KEY=
NEXA_EMAIL_FROM=noreply@nexa.run

# === Monitoring (S7) ===
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=nexa-api

# === Security (S8) ===
NEXA_CORS_ORIGINS=https://app.nexa.run
```

---

## WHAT THIS PLAN DOES NOT COVER

- Visual circuit editor (drag-and-drop graph UI) — Phase 6 in v2.2
- Team collaboration (comments, approval workflows) — Phase 7+
- BYOK — deferred (S-PROV)
- Batch execution, cross-run memory, regression alerts — v2.2 Phase 10
- A2A protocol — post-MCP
- Enterprise features (SSO, SLA, audit export) — post-PMF
- Self-hosted deployment — post-revenue

---

## CHANGES FROM v0.2

### Mandatory revisions (M1–M4)

| Item | What was wrong in v0.2 | What changed in v0.3 | Where applied |
|---|---|---|---|
| **M1** Execution record retention | `archived=true` soft-delete on committed `execution_record` rows violated I4 (append-only). `ExecutionRecordModel` is `@dataclass(frozen=True)` — in-place mutation is also a code-level violation. | Committed records are never mutated. Archive state lives in `execution_record_archive_index` (append-only). GDPR does not anonymize `execution_record` rows — no PII is stored there in the first place (see PII Placement Rule). | S-OPS execution record retention section; schema; file inventory; migration 0008 |
| **M2** Undefined `run_submissions` recovery | Redis loss recovery cited "re-submit from `run_submissions` table" but that table was defined nowhere — not in schema, not in stores, not in migrations. | `run_submissions` formally defined: schema, `run_submission_store_pg.py`, migration 0004. Recovery flow using this table added to S-OPS Redis loss section. Category C (TTL-bounded, cleanup job deletes after 48h + terminal status). | S1 (insert before enqueue), S-OPS Redis recovery, S-ADMIN reprocess-orphans; schema; file inventory; migration 0004 |
| **M3** SQL statement in OTel | Rule 6 in v0.2 allowed `db.statement` truncated to 200 chars. OTel SQLAlchemy instrumentation captures raw SQL including parameter values by default. SQL can contain user data fragments. | Raw SQL (`db.statement`, `db.query.text`) is **forbidden** by default. Only permitted: `db.operation`, `db.sql.table`, `nexa.query_label` (set explicitly in application code). Explicit justification required for any SQL text in traces. | S7 Rule 6; `log_scrubber.py` spec; S7 exit criterion |
| **M4** Provider catalog inconsistency | S-PROV said "Anthropic Claude: Free+Pro" / "OpenAI GPT: Pro only" without model specificity. S5 said "Claude Haiku only / Claude Sonnet + GPT-4o" without tying to S-PROV. Two sections with different granularity and no cross-reference. | Canonical provider catalog table added at top of document. S-PROV and S5 both reference it. Model-level specificity (Haiku 3, Sonnet 4, GPT-4o) consistent throughout. `provider_cost_catalog` DB table defined. | New CANONICAL PROVIDER CATALOG section; S-PROV; S5; schema; migration 0004 |

### Recommended revisions (R1–R3)

| Item | What changed | Where applied |
|---|---|---|
| **R1** Table mutability classification | New TABLE CLASSIFICATION section added. Every table assigned to exactly one category: A (immutable), B (mutable), C (TTL deletable), D (permanent audit). Categories referenced in schema entries throughout. | New section near top of document; all schema entries updated with category labels |
| **R2** Source-of-truth hierarchy | New SOURCE-OF-TRUTH HIERARCHY section added. For each major state class, one authoritative system is named. Recovery direction specified. Relevant to S-OPS restore runbooks and S-ADMIN incident response. | New section near top; S-OPS restore runbook references it |
| **R3** File/schema/migration consistency | `run_submissions`, `execution_record_archive_index`, `execution_retention_audit`, `provider_cost_catalog`, `provider_cost_catalog_store_pg.py`, `execution_archive_store_pg.py` all added consistently to: schema section, file inventory, migration list. Migration 0004 restructured to cover both `run_submissions` and `provider_cost_catalog`. Migration 0008 added for execution archive tables. | File inventory; schema; migration list |

---

## CHANGES FROM v0.3

### Mandatory revisions (M1–M2)

| Item | What was still wrong in v0.3 | What changed in v0.4 | Where applied |
|---|---|---|---|
| **M1** Category A vs `execution_record` hard-delete | Category A was defined as "Rows are never updated or deleted in place," but S-OPS still described a human-operator hard-delete workflow for `execution_record` rows. This was a hidden exception inside the Category A definition — making the classification system internally contradictory. | Category A redefined as "never updated and never deleted, for any reason, no exceptions." `execution_record` hard-delete workflow removed entirely. Storage cost concerns addressed via tablespace tiering or export to cold storage — never by row deletion. `execution_retention_audit.action` no longer includes `hard_deleted`. | TABLE CLASSIFICATION Category A definition; S-OPS execution record retention section (full rewrite); `execution_retention_audit` schema |
| **M2** GDPR anonymization of immutable execution records | S8 GDPR section stated "PII fields anonymized (not deleted — Category A immutability preserved)" and S-OPS stated "PII fields (if any) are anonymized via a separate anonymization step." Both descriptions implied in-place field mutation of Category A rows — still a contradiction even if framed as "anonymization not deletion." | `execution_record` must not contain any direct PII fields — ever. User linkage is exclusively via opaque `user_ref` (sha256 hash). GDPR deletion removes identity from mutable Category B tables (Clerk, `workspace_memberships`, `user_subscriptions`). `execution_record` rows are untouched because they contain no PII. No anonymization step is performed on immutable records. | S8 GDPR section (full rewrite); PII Placement Rule section (new) |

### Recommended revisions (R1–R2)

| Item | What changed | Where applied |
|---|---|---|
| **R1** Category A/D definitions tightened | Category A: "no exceptions" added explicitly. Category D: clarified as strict subset of Category A, with the additional property of immunity from operator-initiated hard-delete workflows. The hidden "may be anonymized" carve-out in the v0.3 note is removed. Each category now reads as a hard rule. | TABLE CLASSIFICATION table and note |
| **R2** PII Placement Rule added | New subsection immediately after TABLE CLASSIFICATION. Defines which data belongs in immutable records (opaque references only), which belongs in mutable reference tables (direct identity), and what happens to each during GDPR deletion. Eliminates ambiguity about GDPR compliance for Category A tables. | New PII PLACEMENT RULE section |

---

**End of document. Implementation begins with S1 (async queue) and S9 (CI/CD) in sprint 1.**
