# Nexa Phase 4.5 P0 — Implementation Brief v1.0

**Document type:** Implementation directive — self-contained reference for the implementing AI agent (GPT)
**Status:** Approved for implementation. No further plan revision required.
**Approval:** Product owner (재선) — 2026-04-22
**Plan lineage:** phase45_p0_plan_v0.1 → v0.2 → v0.3 → v0.4 (promote_to_v1.0 by GPT third review)
**Baseline repo:** commit `e86fe48` region; current upload `nexa_913b12d` (2,775 tests passing)

---

## HOW TO USE THIS DOCUMENT

This brief is the single authoritative reference for P0 implementation. It supersedes all earlier draft plan versions for implementation purposes.

Read order:
1. §1 — Project identity and invariants (never violate these)
2. §2 — Approved technical decisions (your stack is fixed)
3. §3 — Codebase state (what already exists vs what you must create)
4. §4 — Vertical slice scope (exactly 9 routes, nothing more)
5. §5 — Step-by-step implementation spec (Step231–238 + 235A)
6. §6 — File inventory (complete list of edits and new files)
7. §7 — Invariant compliance matrix (verify each before submitting)
8. §8 — Test requirements (all must be green; zero regressions)
9. §9 — Risk register (13 known risks + mitigations already decided)
10. §10 — Design decision rationale (why each decision was made)
11. §11 — Auth architecture decision record (G2 detail)

Do not invent new files, new patterns, or new abstractions beyond what is specified. If something is ambiguous, the rule is: do the minimum that satisfies the spec.

---

## 1. PROJECT IDENTITY AND INVARIANTS

### 1.1 What Nexa is

Nexa is a **deterministic AI execution engine**, not a workflow tool. It makes AI computation:
- deterministic
- observable
- auditable
- reproducible

The fixed execution model (never change this structure):
```
Circuit → Node → Execution Runtime → Prompt / Provider / Plugin → Artifact → Trace
```

### 1.2 Constitutional invariants I1–I8

These are the highest-level rules. Any implementation that violates them must be rejected and rewritten.

**I1. Node is the only execution unit.**
All computation occurs inside nodes. Circuits, prompts, providers, and plugins support nodes but do not replace them.

**I2. Circuit defines topology only; it does not execute.**
Circuit connects nodes and resolves dependencies. Execution happens in the runtime.

**I3. Dependency-driven execution.**
Execution order is determined by dependency resolution. Fixed pipeline order (prompt → provider → plugin) is forbidden.

**I4. Artifacts are append-only.**
Once created, an artifact must never be modified. New results create new artifacts. In database terms: INSERT only; no UPDATE against committed records.

**I5. Deterministic execution.**
Given identical inputs and configuration, execution must produce identical artifacts. Any code that introduces nondeterminism (e.g., timestamp-based branching, random seeding without fixed seed) is forbidden.

**I6. Plugin isolation.**
Plugins may only write to `plugin.<plugin_id>.*`. They must not modify other runtime domains.

**I7. Contract-driven architecture.**
All system behavior is governed by explicit contracts: frozen dataclasses, typed schemas, and contract tests. Code that bypasses contracts must be rejected.

**I8. No cross-layer imports.**
- `src/engine/**` must never import from `src/server/**`
- `src/server/**` may import from `src/engine/engine.py` (public boundary only)
- `src/server/**` must not import from `src/circuit/**` or `src/engine/validation/**` directly
- These rules are enforced by AST-scan contract tests (see §8)

### 1.3 P0 operational constraint (not a constitutional invariant)

**P0-S1. Storage-role truth.**
`working_save` and `commit_snapshot` are distinct storage roles. P0 public HTTP routes may only execute against `commit_snapshot` artifacts. `working_save` execution is accessible only in dev/test environments via explicit env flag (`NEXA_DEV_ALLOW_WORKING_SAVE_EXEC=1`), and must not be reachable via any public API route.

> Note: P0-S1 is not numbered I9. The constitutional invariant set I1–I8 is defined in `docs/FOUNDATION_RULES.md` and `docs/ARCHITECTURE_CONSTITUTION.md`. Adding a 9th numbered invariant without a formal constitution amendment would create an undocumented extension. P0-S1 is an operational constraint for this phase only.

---

## 2. APPROVED TECHNICAL DECISIONS (GATES G1–G4)

All four decisions are final. Do not revisit them.

### G1. Database + ORM stack

**Approved: PostgreSQL 16 + SQLAlchemy 2.0 Core + asyncpg + Alembic**

- SQLAlchemy **Core** only. `declarative_base()`, `DeclarativeBase`, ORM sessions, and relationship mappers are **forbidden**.
- Rationale: every Store in this codebase uses `dict-row-in / dict-row-out` shape. ORM identity-map provides no value and would force store-method rewrites.
- All queries use `sqlalchemy.text()` or `sqlalchemy.Table` constructs.
- Alembic manages schema migrations. The initial revision is bootstrapped from `render_postgres_schema_statements()` in `src/server/migration_foundation.py`.

Environment variables (consumed by `src/server/database_foundation.py`):
```
NEXA_SERVER_DB_HOST       (default: localhost)
NEXA_SERVER_DB_PORT       (default: 5432)
NEXA_SERVER_DB_NAME       (default: nexa)
NEXA_SERVER_DB_USER       (default: nexa)
NEXA_SERVER_DB_PASSWORD   (env var name, not value; default env var: NEXA_SERVER_DB_PASSWORD)
NEXA_SERVER_DB_SSLMODE    (default: require)
NEXA_SERVER_DB_APP_NAME   (default: nexa_server)
```

### G2. Authentication

**Approved: Clerk + PyJWT + JWKS cache**

Full detail in §11. Short form:
- Use Clerk as the identity provider for P0.
- `verify_session_token(token: str) -> VerifiedClaimsBundle` — verifies RS256 JWT against Clerk's JWKS endpoint.
- Auth boundary (`AuthorizationGate`, `RequestAuthContext`) stays IdP-agnostic.
- Future migration to self-hosted auth is a separate decision, not part of this implementation.
- Dev bypass: `NEXA_AUTH_MODE=dev_stub` (forbidden in production).

### G3. Secret backend

**Approved: environment variables for dev/staging; AWS Secrets Manager as optional production backend**

- `boto3` is **not** in `requirements.txt`.
- AWS Secrets Manager support is behind `pyproject.toml` optional extra `[aws]`.
- P0 dev and staging use env vars exclusively.
- `src/server/aws_secrets_manager_binding.py` already exists and uses local imports; it remains an optional backend, not a required dependency.

### G4. Hosting target

**Approved: local docker-compose (dev) + Railway (staging)**

- Local: `docker-compose.yml` with Postgres 16 + app service.
- Staging: Railway with Postgres addon. G4 does not imply AWS Secrets Manager (G3 and G4 are independent).
- Production hosting is a P1 decision (ECS vs Fly vs Railway prod-tier).
- Staging must run with `NEXA_AUTH_MODE=clerk` before it becomes externally accessible (see §11).

---

## 3. CODEBASE STATE

### 3.1 Test baseline

```
python -m pytest -q
2,784 tests collected / 2,775 passed / 9 skipped / 0 failed
runtime: ~98 s
```

This is the hard baseline. After every implementation step, run the full suite. Zero regressions are permitted.

### 3.2 What already exists (do not recreate)

| What | Location | Notes |
|---|---|---|
| FastAPI app factory | `src/server/fastapi_binding.py:3143` `build_app()` and `:3193` `create_fastapi_app(dependencies, config) -> FastAPI` | **Do not duplicate.** Consume as-is. |
| 133 route definitions | `src/server/fastapi_binding.py::FastApiRouteBindings.build_router()` | All 133 routes are defined. You will add a surface-profile filter on top. |
| DI container contract | `src/server/fastapi_binding_models.py::FastApiRouteDependencies` | 58 typed provider/writer callables, all defaulting to `_none_*` / `_empty_*` / `_noop_*` stubs. You will build concrete PG implementations and wire them in. |
| Postgres connection model | `src/server/database_foundation.py::PostgresConnectionSettings` and `load_postgres_connection_settings_from_env()` | Use these directly. |
| Schema DDL generator | `src/server/migration_foundation.py::render_postgres_schema_statements()` and `build_initial_server_migration()` | Use for Alembic bootstrap. |
| InMemory stores (all 5) | `src/server/workspace_registry_store.py::InMemoryWorkspaceRegistryStore` (and analogues for onboarding, provider_binding, feedback, managed_secret_metadata) | Do NOT modify. They remain the test reference and dev-mode fallback. Your PG stores mirror their public method surfaces. |
| Clerk auth adapter | `src/server/auth_adapter.py::ClerkAuthAdapter` | Exists but `verify_session_token` is not yet implemented. You add it. |
| AWS Secrets Manager binding | `src/server/aws_secrets_manager_binding.py` | Exists. Optional backend. No change needed. |
| Engine entry point | `src/engine/engine.py::Engine.execute(revision_id, strict_determinism) -> ExecutionTrace` | The engine is fully functional. You call it via the bridge; you do not modify it. |
| Server→engine DTOs | `src/server/boundary_models.py` — `EngineRunLaunchRequest`, `EngineRunLaunchResponse`, `EngineResultEnvelope`, `EngineRunStatusSnapshot`, etc. | Typed; use as-is. |
| EngineLaunchAdapter | `src/server/adapters.py::EngineLaunchAdapter` — `build_request(...)`, `accepted(...)`, `rejected(...)`, `to_execution_binding(...)` | DTO mapping layer; use as-is. |
| StorageRole enum | `src/storage/models/shared_sections.py` | Contains `StorageRole.COMMIT_SNAPSHOT`, `StorageRole.WORKING_SAVE`. Use for P0-S1 enforcement. |
| LoadedNexArtifact / CommitSnapshotModel | `src/storage/models/loaded_nex_artifact.py`, `src/storage/models/commit_snapshot_model.py` | Return types for target resolver. |
| ExecutionRecordModel | `src/storage/models/execution_record_model.py` | Schema reference for `execution_record_store_pg`. |
| Run admission service | `src/server/run_admission.py::RunAdmissionService` | Contains `engine_launch_decider` injection point. You replace the default noop with the real bridge. |
| Worker queue models | `src/server/worker_queue_orchestration.py` | In-memory projection only. P0 does not add a queue backend. Leave unchanged. |
| CLI | `src/cli/nexa_cli.py` | Working. Do not touch. |
| Examples | `examples/real_ai_bug_autopsy_multinode/` | Use the `.nex` files here as seed data in `dev_seed.py`. |

### 3.3 What is missing (you must create)

| # | Gap |
|---|---|
| M2 | No ASGI entrypoint or uvicorn script |
| M3 | No DB driver in `requirements.txt` (`sqlalchemy`, `asyncpg`, `alembic`) |
| M4 | No Postgres store implementations (only InMemory variants exist) |
| M5 | `render_postgres_schema_statements()` is never executed against a real DB |
| M6 | All 58 `FastApiRouteDependencies` fields wired to stubs — no real DB providers |
| M7 | No server→engine execution path (`Engine.execute()` never called from HTTP) |
| M10 | `ClerkAuthAdapter.verify_session_token()` not implemented |
| M14 | No `_validate_p0_configuration()` startup guard |
| M15 | No `p0_slice` surface profile filter |
| M16 | No `/healthz` or `/readyz` endpoints |
| M17 | No Alembic setup |
| M18 | No `docker-compose.yml` or `.env.example` |
| M19 | No `dev_seed.py` |

### 3.4 Legacy files (do not touch in P0)

Five legacy files remain in the codebase. Leave them as-is. They are tracked for a post-P0 Refactor Safety Scanner pass.
```
src/circuit/legacy_validator.py
src/storage/legacy_savefile_bridge.py
src/providers/legacy_provider_result.py
src/providers/legacy_provider_execution.py
src/providers/legacy_provider_trace.py
```

---

## 4. VERTICAL SLICE SCOPE

### 4.1 The proof goal

P0 must prove: **a real HTTP client can submit a `.nex` for execution against a real Postgres database, the engine runs it, and the trace is readable via HTTP.** Nothing more.

### 4.2 Active routes (9 of 133)

Surface profile `NEXA_SURFACE_PROFILE=p0_slice` exposes exactly these routes:

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness (always 200 if process is alive) |
| GET | `/readyz` | Readiness: DB connected + Alembic at head + provider readiness |
| GET | `/api/workspaces` | List authenticated user's workspaces |
| POST | `/api/workspaces` | Create workspace |
| GET | `/api/workspaces/{workspace_id}` | Workspace detail |
| POST | `/api/runs` | Submit a `.nex` for execution |
| GET | `/api/runs/{run_id}` | Poll run status |
| GET | `/api/runs/{run_id}/result` | Final output envelope |
| GET | `/api/runs/{run_id}/trace` | Execution trace events |

All other 124 routes remain syntactically defined in `build_router()` but are filtered out by the surface profile and return 404.

### 4.3 Execution mode

Synchronous. `Engine.execute()` is called directly from the request thread, offloaded to a bounded threadpool. No queue, no worker process. Async queue is P1.

### 4.4 Provider readiness precondition

`POST /api/runs` requires the workspace to have at least one valid provider binding. `dev_seed.py` seeds a dev-stub binding so the E2E test can complete. `/readyz` includes a provider readiness check.

### 4.5 `/readyz` payload

```json
{
  "status": "ok",
  "db": "connected",
  "alembic": "at_head",
  "provider_mode": "dev_stub",
  "provider_ready": true
}
```

`provider_mode` distinguishes dev-stub readiness from real-provider readiness. External testers use this to interpret the readiness level correctly.

---

## 5. STEP-BY-STEP IMPLEMENTATION SPEC

Steps must be executed in order. Run `python -m pytest -q` after each step before proceeding. A red baseline blocks all subsequent steps.

### Step231 — Dependency manifest update

**Files to edit:** `requirements.txt`, `pyproject.toml`

Add to `requirements.txt` (append; do not remove existing entries):
```
sqlalchemy>=2.0
asyncpg>=0.29
alembic>=1.13
pyjwt[crypto]>=2.8
uvicorn[standard]>=0.27
```

Add to `pyproject.toml` under `[project.optional-dependencies]`:
```toml
aws     = ["boto3>=1.34"]
testing = ["testcontainers[postgres]>=4.0", "pytest-asyncio>=0.23"]
```

`boto3` must not appear in base `requirements.txt`.

**Exit criterion:** `pip install -r requirements.txt` succeeds; `python -m pytest -q` still reports 2,775 passed.

---

### Step232 — ASGI entrypoint + surface-profile wrapper

**Do not create a new app factory.** `create_fastapi_app(dependencies, config)` already exists at `fastapi_binding.py:3193`. Consume it.

**New file: `src/server/p0_configuration.py`**

```python
from __future__ import annotations

import os


def _validate_p0_configuration(
    idempotency_window_s: int,
    max_run_duration_s: int,
) -> None:
    """Mandatory startup guard. Must use RuntimeError, never assert.

    Python's -O / -OO optimization flags strip assert statements silently.
    A stripped guard would allow misconfigured deployments to start without
    any error, defeating the purpose of the check.
    """
    if idempotency_window_s <= max_run_duration_s:
        raise RuntimeError(
            f"Configuration error: IDEMPOTENCY_WINDOW_S ({idempotency_window_s}s) "
            f"must be greater than NEXA_P0_MAX_RUN_DURATION_S ({max_run_duration_s}s). "
            "A run that outlives the idempotency window can be submitted twice. "
            "Raise IDEMPOTENCY_WINDOW_S or lower NEXA_P0_MAX_RUN_DURATION_S."
        )


def get_idempotency_window_s() -> int:
    return int(os.environ.get("IDEMPOTENCY_WINDOW_S", "86400"))


def get_max_run_duration_s() -> int:
    return int(os.environ.get("NEXA_P0_MAX_RUN_DURATION_S", "3600"))
```

**New file: `src/server/surface_profile.py`**

```python
from __future__ import annotations

import os
from fastapi import APIRouter

_P0_SLICE_PATHS = frozenset({
    "/healthz",
    "/readyz",
    "/api/workspaces",
    "/api/workspaces/{workspace_id}",
    "/api/runs",
    "/api/runs/{run_id}",
    "/api/runs/{run_id}/result",
    "/api/runs/{run_id}/trace",
})

def filter_router(router: APIRouter) -> APIRouter:
    """Return router filtered by NEXA_SURFACE_PROFILE.

    p0_slice: expose exactly the 9 P0 routes.
    full: expose all 133 routes unchanged.

    Filtering happens AFTER build_router() constructs the full router.
    This is route exposure control only — not dependency minimization.
    The full router is always constructed internally.
    """
    profile = os.environ.get("NEXA_SURFACE_PROFILE", "full").strip().lower()
    if profile == "full":
        return router
    if profile == "p0_slice":
        filtered = APIRouter()
        for route in router.routes:
            if getattr(route, "path", None) in _P0_SLICE_PATHS:
                filtered.routes.append(route)
        return filtered
    raise RuntimeError(f"Unknown NEXA_SURFACE_PROFILE: {profile!r}")
```

**New file: `src/server/health_routes.py`**

```python
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})

@router.get("/readyz")
async def readyz(db_check=None, alembic_check=None, provider_check=None) -> JSONResponse:
    # db_check, alembic_check, provider_check are injected via dependency_factory
    # Each returns a dict with the relevant status fields.
    # Aggregate and return.
    # If any check fails, return 503.
    ...
```

> Note: The readyz route must be wired to real check callables via `dependency_factory.py`. The checks are: (1) run a trivial DB query, (2) run `alembic current` and compare to `alembic heads`, (3) confirm at least one provider binding exists for the seeded workspace.

**New file: `src/server/asgi.py`**

```python
from __future__ import annotations

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.p0_configuration import (
    _validate_p0_configuration,
    get_idempotency_window_s,
    get_max_run_duration_s,
)
from src.server.dependency_factory import build_default_dependencies
from fastapi.middleware.cors import CORSMiddleware
import os

# Mandatory startup validation — runs at module load time.
# Uses RuntimeError, not assert. assert is stripped by -O/-OO flags.
_validate_p0_configuration(
    idempotency_window_s=get_idempotency_window_s(),
    max_run_duration_s=get_max_run_duration_s(),
)

_dependencies = build_default_dependencies()
_config = FastApiBindingConfig(
    title="Nexa API",
    version="0.1.0",
)

app = create_fastapi_app(dependencies=_dependencies, config=_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("NEXA_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**New file: `src/server/__main__.py`**

```python
import uvicorn
uvicorn.run("src.server.asgi:app", host="0.0.0.0", port=8000, reload=True)
```

**New file: `src/server/dependency_factory.py`**

```python
from __future__ import annotations

import os
from src.server.fastapi_binding_models import FastApiRouteDependencies

def build_default_dependencies() -> FastApiRouteDependencies:
    mode = os.environ.get("NEXA_DEPENDENCY_MODE", "in_memory").strip().lower()
    if mode == "postgres":
        from src.server.pg.dependencies_factory import build_postgres_dependencies
        from src.server.pg.engine import create_async_engine_from_env
        engine = create_async_engine_from_env()
        return build_postgres_dependencies(engine)
    # Default: in-memory stubs (test/dev)
    return FastApiRouteDependencies()
```

**Exit criterion:** `python -m src.server` starts (even with in-memory stubs); `GET /healthz` → 200; `NEXA_SURFACE_PROFILE=p0_slice` non-P0 route → 404; 2,775 tests still pass.

---

### Step233 — Postgres Store layer

New package `src/server/pg/`. All stores use SQLAlchemy **Core** exclusively.

**`src/server/pg/engine.py`**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from src.server.database_foundation import (
    load_postgres_connection_settings_from_env,
    build_postgres_connection_url,
)
import os

def create_async_engine_from_env() -> AsyncEngine:
    settings = load_postgres_connection_settings_from_env(os.environ)
    password = os.environ.get(settings.password_env_var, "")
    url = build_postgres_connection_url(settings, password=password)
    async_url = url.replace("postgresql://", "postgresql+asyncpg://")
    return create_async_engine(async_url, pool_size=5, max_overflow=10)
```

**`src/server/pg/workspace_registry_store_pg.py`**

Implement the same public method surface as `InMemoryWorkspaceRegistryStore`:
- `write_workspace_row(row: Mapping[str, Any]) -> dict[str, Any]`
- `write_membership_row(row: Mapping[str, Any]) -> dict[str, Any]`
- `write_workspace_bundle(workspace_row, membership_row) -> dict[str, Any]`
- `get_workspace_row(workspace_id: str) -> Optional[dict[str, Any]]`
- `get_workspace_rows_for_user(user_id: str) -> list[dict[str, Any]]`
- `get_membership_rows_for_user(user_id: str) -> list[dict[str, Any]]`

Use `sqlalchemy.text()` for all queries. Tables are defined in `database_foundation.get_server_schema_families()`.

Apply identical validation logic as the InMemory version (same required fields, same normalization).

**`src/server/pg/onboarding_state_store_pg.py`**

Mirror `InMemoryOnboardingStateStore` public method surface.

**`src/server/pg/provider_binding_store_pg.py`**

Mirror `InMemoryProviderBindingStore` public method surface.

**`src/server/pg/execution_record_store_pg.py`**

New store (no InMemory counterpart). Schema reference: `src/storage/models/execution_record_model.py`.

Rules:
- **INSERT only.** Never issue UPDATE against a committed record.
- Superseded runs: new row with `supersedes_run_id = <old_run_id>` as forward link.
- Single complete row inserted at finalization. (Sync execution completes before insert.)

Public methods:
- `insert_execution_record(record: Mapping[str, Any]) -> dict[str, Any]`
- `get_execution_record(run_id: str) -> Optional[dict[str, Any]]`
- `get_execution_records_for_workspace(workspace_id: str) -> list[dict[str, Any]]`

**`src/server/pg/run_submission_dedupe_store_pg.py`**

New store. Schema: table `run_submission_dedupe` with columns `(dedupe_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL)`.

Public methods:
- `get_dedupe_entry(dedupe_key: str) -> Optional[dict[str, Any]]`
- `insert_dedupe_entry(dedupe_key: str, run_id: str, expires_at: str) -> dict[str, Any]`

**`src/server/pg/dependencies_factory.py`**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.pg.workspace_registry_store_pg import WorkspaceRegistryStorePG
from src.server.pg.onboarding_state_store_pg import OnboardingStateStorePG
from src.server.pg.provider_binding_store_pg import ProviderBindingStorePG
from src.server.pg.execution_record_store_pg import ExecutionRecordStorePG
from src.server.pg.run_submission_dedupe_store_pg import RunSubmissionDedupeStorePG

def build_postgres_dependencies(async_engine: AsyncEngine) -> FastApiRouteDependencies:
    ws_store = WorkspaceRegistryStorePG(async_engine)
    ob_store = OnboardingStateStorePG(async_engine)
    pb_store = ProviderBindingStorePG(async_engine)
    er_store = ExecutionRecordStorePG(async_engine)
    dd_store = RunSubmissionDedupeStorePG(async_engine)

    return FastApiRouteDependencies(
        workspace_rows_provider=ws_store.get_workspace_rows_for_user,
        workspace_row_provider=ws_store.get_workspace_row,
        workspace_registry_writer=ws_store.write_workspace_bundle,
        # ... wire all 58 callables
        # Leave unused callables at their default stubs (FastApiRouteDependencies defaults)
    )
```

**Exit criterion:** Contract test `test_pg_store_interface_parity.py` passes (see §8).

---

### Step234 — Alembic migration bootstrap

**Edit: `src/server/database_foundation.py`**

Add the `run_submission_dedupe` schema family to `get_server_schema_families()`:

```python
SchemaFamily(
    family_name="run_submission_dedupe",
    persistence_mode="append_only",
    tables=(
        TableSpec(
            name="run_submission_dedupe",
            columns=(
                ColumnSpec(sql_definition="dedupe_key TEXT PRIMARY KEY"),
                ColumnSpec(sql_definition="run_id TEXT NOT NULL"),
                ColumnSpec(sql_definition="created_at TIMESTAMPTZ NOT NULL"),
                ColumnSpec(sql_definition="expires_at TIMESTAMPTZ NOT NULL"),
            ),
            indexes=(
                IndexSpec(name="idx_rsd_expires_at", columns=("expires_at",), unique=False),
            ),
        ),
    ),
)
```

This edit is mandatory to preserve the zero-drift guarantee between `alembic upgrade head` and `render_postgres_schema_statements()`.

**New files:**

`alembic.ini` — standard Alembic config pointing to `alembic/env.py`.

`alembic/env.py` — async-compatible env using `asyncpg`. Reads DB URL from `NEXA_SERVER_DB_*` env vars via `load_postgres_connection_settings_from_env`.

`alembic/versions/0001_initial.py`:
```python
def upgrade() -> None:
    from src.server.migration_foundation import build_initial_server_migration
    migration = build_initial_server_migration()
    for statement in migration.steps[0].statements:
        op.execute(statement)
```

`alembic/versions/0002_run_submission_dedupe.py`:
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS run_submission_dedupe (
            dedupe_key TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rsd_expires_at
            ON run_submission_dedupe (expires_at);
    """)
```

**Deploy-time only.** App startup performs head-mismatch fail-fast check only — it does not run migrations. Add this to `src/server/asgi.py` startup:
```python
# Pseudo-code; implement as async startup event
async def _check_alembic_head():
    current = await get_alembic_current_revision()
    expected = await get_alembic_head_revision()
    if current != expected:
        raise RuntimeError(f"DB migration required: at {current}, need {expected}")
```

**Exit criterion:** `alembic upgrade head` on an empty DB creates all tables; `test_alembic_bootstrap_matches_foundation.py` passes.

---

### Step235 — Server→engine bridge

**New file: `src/server/engine_bridge.py`**

```python
from __future__ import annotations

from typing import Callable
from fastapi.concurrency import run_in_threadpool

from src.engine.engine import Engine
from src.server.boundary_models import (
    EngineRunLaunchRequest,
    EngineRunLaunchResponse,
    EngineResultEnvelope,
)
from src.server.adapters import EngineLaunchAdapter
from src.server.execution_target_resolver import ExecutionTargetResolver, StorageRole


async def run_engine_async(
    request: EngineRunLaunchRequest,
    *,
    target_resolver: ExecutionTargetResolver,
    allowed_target_roles: frozenset[StorageRole] = frozenset({StorageRole.COMMIT_SNAPSHOT}),
    strict_determinism: bool = False,
    max_run_duration_s: int = 3600,
) -> tuple[EngineRunLaunchResponse, EngineResultEnvelope]:
    """Async wrapper. Offloads sync Engine.execute() to threadpool.

    Never call Engine.execute() directly from an async handler.
    FastAPI's async event loop would be blocked for the entire run duration,
    starving all other requests (R9 event-loop starvation).
    """
    return await run_in_threadpool(
        _run_engine_sync,
        request,
        target_resolver=target_resolver,
        allowed_target_roles=allowed_target_roles,
        strict_determinism=strict_determinism,
        max_run_duration_s=max_run_duration_s,
    )


def _run_engine_sync(
    request: EngineRunLaunchRequest,
    *,
    target_resolver: ExecutionTargetResolver,
    allowed_target_roles: frozenset[StorageRole],
    strict_determinism: bool,
    max_run_duration_s: int,
) -> tuple[EngineRunLaunchResponse, EngineResultEnvelope]:
    # 1. Resolve target — typed, role-tagged
    target = target_resolver(
        workspace_ref=request.workspace_ref,
        target_ref=request.execution_target.target_ref,
    )

    # 2. Enforce P0-S1 storage-role policy
    if target.storage_role not in allowed_target_roles:
        from src.server.execution_target_resolver import UnauthorizedTargetRole
        raise UnauthorizedTargetRole(
            f"Storage role {target.storage_role!r} is not permitted in this context. "
            f"Allowed roles: {allowed_target_roles!r}"
        )

    # 3. Build Engine and execute
    engine = Engine.from_execution_binding(
        EngineLaunchAdapter.to_execution_binding(
            request,
            circuit=target.circuit_dict,
            state=target.state_dict,
        )
    )
    trace = engine.execute(
        revision_id=request.run_request_id,
        strict_determinism=strict_determinism,
    )

    # 4. Convert trace to server envelope
    launch_response = EngineLaunchAdapter.accepted(
        run_id=request.run_request_id,
        initial_status="completed",
    )
    result_envelope = _trace_to_result_envelope(trace, request=request)
    return launch_response, result_envelope


def _trace_to_result_envelope(trace, *, request) -> EngineResultEnvelope:
    # Convert ExecutionTrace → EngineResultEnvelope
    # Use existing adapter in src/server/adapters.py if available
    ...
```

**I8 compliance note:** `engine_bridge.py` imports `src.engine.engine.Engine` only. It must not import from `src.circuit.*`, `src.engine.validation.*`, or `src.engine.graph_*`. The AST contract test in Step238 enforces this.

**Wire into run_admission.py:**
```python
# In the dependency factory, set:
engine_launch_decider = lambda req: run_engine_async(req, target_resolver=..., ...)
```

**Exit criterion:** `POST /api/runs` triggers a real `Engine.execute()` call; trace is persisted; `GET /api/runs/{id}/trace` returns ≥1 event.

---

### Step235A — Execution target resolution & idempotency boundary

**New file: `src/server/execution_target_resolver.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any
from src.storage.models.shared_sections import StorageRole


class UnauthorizedTargetRole(Exception):
    pass


@dataclass(frozen=True)
class ExecutionTarget:
    storage_role: StorageRole
    circuit_dict: dict[str, Any]
    state_dict: dict[str, Any]


ExecutionTargetResolver = Callable[[str, str], ExecutionTarget]
# Callable[[workspace_ref, target_ref], ExecutionTarget]


def build_default_target_resolver(
    workspace_artifact_source_provider,
) -> ExecutionTargetResolver:
    """Build a resolver that fetches the artifact from the provider
    and returns a typed ExecutionTarget with role information."""
    def resolve(workspace_ref: str, target_ref: str) -> ExecutionTarget:
        artifact = workspace_artifact_source_provider(workspace_ref)
        if artifact is None:
            raise ValueError(f"No artifact found for workspace {workspace_ref!r}")
        # Determine storage_role from artifact type
        ...
        return ExecutionTarget(
            storage_role=StorageRole.COMMIT_SNAPSHOT,
            circuit_dict=artifact.circuit,
            state_dict=artifact.state,
        )
    return resolve
```

**New file: `src/server/run_submission_dedupe.py`**

```python
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def build_dedupe_key(workspace_id: str, idempotency_key: str) -> str:
    raw = f"{workspace_id}:{idempotency_key}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_idempotency_window_s() -> int:
    return int(os.environ.get("IDEMPOTENCY_WINDOW_S", "86400"))


def compute_expiry(now_iso: str, window_s: int) -> str:
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    expiry = now + timedelta(seconds=window_s)
    return expiry.isoformat()


def is_within_window(expires_at_iso: str) -> bool:
    expiry = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return now < expiry
```

**Behavior in `POST /api/runs` handler:**

1. Extract `X-Idempotency-Key` header (optional).
2. If present: compute `dedupe_key = sha256(workspace_id + idempotency_key)`.
3. Query `run_submission_dedupe_store`: if entry exists and `is_within_window(expires_at)`: return prior `run_id` with HTTP 200, skip engine.
4. If not present or window expired: proceed to engine. After successful submission, insert dedupe entry with `expires_at = now + IDEMPOTENCY_WINDOW_S`.

**P0 defaults:**
- `IDEMPOTENCY_WINDOW_S`: 86400 s (24 h)
- `NEXA_P0_MAX_RUN_DURATION_S`: 3600 s (1 h)
- Startup assertion in `asgi.py` (via `_validate_p0_configuration`) ensures `86400 > 3600`.

**Exit criterion:** `test_run_submission_idempotency.py` passes — duplicate `X-Idempotency-Key` within window returns same `run_id`, single engine invocation.

---

### Step236 — Clerk JWT verification

**Edit: `src/server/auth_adapter.py`**

Add to `ClerkAuthAdapter`:
```python
def verify_session_token(self, token: str) -> VerifiedClaimsBundle:
    """Verify Clerk JWT. Returns claims bundle, not AuthenticatedIdentity.

    The existing normalize path (claims → AuthenticatedIdentity) is reused
    unchanged. This keeps the auth boundary IdP-agnostic.
    """
    from src.server.clerk_jwks import get_public_key_for_token
    import jwt  # PyJWT

    public_key = get_public_key_for_token(token)
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"verify_aud": False},  # Adjust per Clerk tenant config
    )
    return VerifiedClaimsBundle(claims=claims)
```

**New file: `src/server/clerk_jwks.py`**

```python
from __future__ import annotations

import os
import time
import threading
from typing import Optional
import httpx
import jwt  # PyJWT

_jwks_cache: dict = {}
_jwks_lock = threading.Lock()
_jwks_fetched_at: float = 0.0
_JWKS_TTL_S = 600  # 10 minutes


def get_public_key_for_token(token: str):
    """Fetch JWKS, cache for TTL, return matching public key.
    On JWKS endpoint outage: serve stale key if available (R4 mitigation).
    """
    jwks = _get_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
    raise ValueError(f"No matching public key for kid={kid!r}")


def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    with _jwks_lock:
        now = time.monotonic()
        if now - _jwks_fetched_at < _JWKS_TTL_S and _jwks_cache:
            return _jwks_cache
        try:
            url = os.environ["NEXA_CLERK_JWKS_URL"]  # e.g. https://<tenant>.clerk.accounts.dev/.well-known/jwks.json
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_fetched_at = now
        except Exception:
            if _jwks_cache:
                pass  # Serve stale on outage
            else:
                raise
        return _jwks_cache
```

**Dev bypass:**
```python
import os
NEXA_AUTH_MODE = os.environ.get("NEXA_AUTH_MODE", "clerk")
NEXA_ENV = os.environ.get("NEXA_ENV", "development")

def verify_or_stub(token: str) -> VerifiedClaimsBundle:
    if NEXA_AUTH_MODE == "dev_stub":
        if NEXA_ENV == "production":
            raise RuntimeError("dev_stub auth mode is forbidden in production")
        return VerifiedClaimsBundle(claims={"sub": "dev_user", "email": "dev@local"})
    return clerk_adapter.verify_session_token(token)
```

**Staging deploy gate:** Railway staging must be deployed with `NEXA_AUTH_MODE=clerk` and valid `NEXA_CLERK_JWKS_URL`. The `dev_stub` bypass is acceptable for local docker-compose and CI only. This gate is independent of the `NEXA_ENV=production` check: the production check prevents dev-stub at runtime; the staging gate prevents external exposure before auth is wired.

---

### Step237 — Developer environment

**New file: `docker-compose.yml`**

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: nexa
      POSTGRES_USER: nexa
      POSTGRES_PASSWORD: nexa_dev
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  app:
    build: .
    command: python -m src.server
    environment:
      NEXA_SERVER_DB_HOST: db
      NEXA_SERVER_DB_NAME: nexa
      NEXA_SERVER_DB_USER: nexa
      NEXA_SERVER_DB_PASSWORD: nexa_dev
      NEXA_SERVER_DB_SSLMODE: disable
      NEXA_DEPENDENCY_MODE: postgres
      NEXA_SURFACE_PROFILE: p0_slice
      NEXA_AUTH_MODE: dev_stub
      NEXA_ENV: development
    depends_on:
      - db
    ports:
      - "8000:8000"
    volumes:
      - .:/app

volumes:
  pg_data:
```

**New file: `.env.example`**

```
# Database
NEXA_SERVER_DB_HOST=localhost
NEXA_SERVER_DB_PORT=5432
NEXA_SERVER_DB_NAME=nexa
NEXA_SERVER_DB_USER=nexa
NEXA_SERVER_DB_PASSWORD=nexa_dev
NEXA_SERVER_DB_SSLMODE=disable

# App mode
NEXA_DEPENDENCY_MODE=postgres          # in_memory | postgres
NEXA_SURFACE_PROFILE=p0_slice          # p0_slice | full
NEXA_ENV=development                   # development | staging | production

# Auth
NEXA_AUTH_MODE=dev_stub                # dev_stub | clerk
NEXA_CLERK_JWKS_URL=                   # Required when NEXA_AUTH_MODE=clerk

# Engine
NEXA_P0_MAX_RUN_DURATION_S=3600
NEXA_P0_ENGINE_THREADPOOL_MAX=4
IDEMPOTENCY_WINDOW_S=86400

# AWS (optional — only if using AWS Secrets Manager)
# Install with: pip install "nexa[aws]"
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_DEFAULT_REGION=
```

**New file: `scripts/dev_seed.py`**

```python
"""Seed one workspace + one .nex artifact + one dev-stub provider binding.

Run after `alembic upgrade head`:
    python scripts/dev_seed.py
"""
import asyncio
import os
from src.server.pg.engine import create_async_engine_from_env
from src.server.pg.workspace_registry_store_pg import WorkspaceRegistryStorePG
from src.server.pg.provider_binding_store_pg import ProviderBindingStorePG
# ... load example .nex from examples/real_ai_bug_autopsy_multinode/
```

Seeds:
- One workspace (id: `dev_workspace_001`, owner: `dev_user`)
- One membership row
- One `.nex` artifact (loaded from `examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex`)
- One provider binding with dev-stub key (enables `/readyz` `provider_ready: true`)

---

### Step238 — E2E + contract tests

All new tests must pass; all 2,775 existing tests must still pass. Target total: ~2,797.

**`tests/e2e/test_p0_vertical_slice.py`**

Uses `testcontainers[postgres]`. Boots the full app with real Postgres. Drives the 9 P0 routes in sequence:
1. POST /api/workspaces → workspace_id
2. POST /api/runs → run_id
3. Poll GET /api/runs/{run_id} until status in {"completed", "failed"}
4. GET /api/runs/{run_id}/result → assert output envelope present
5. GET /api/runs/{run_id}/trace → assert ≥1 node execution event

**`tests/contract/test_engine_does_not_import_server.py`**

AST scan: walk all `.py` files under `src/engine/`. Assert no `import src.server` or `from src.server` found anywhere.

**`tests/contract/test_server_does_not_import_circuit_internals.py`**

AST scan: walk all `.py` files under `src/server/`. Assert:
- No `import src.circuit` or `from src.circuit` (direct circuit internals forbidden)
- No `import src.engine.validation` or `from src.engine.validation` (internal validation layer forbidden)
- `src.engine.engine` imports are **permitted** (this is the public boundary)
- `src.providers.*` and `src.platform.*` are **not** fenced at this stage

**`tests/contract/test_alembic_bootstrap_matches_foundation.py`**

Run `alembic upgrade head` against a temporary DB. Run `render_postgres_schema_statements()`. Assert every table name in the DDL output is present in the live DB schema. Zero drift.

**`tests/contract/test_pg_store_interface_parity.py`**

For each pair (InMemoryStore, PGStore): assert both have identical public method names (using `inspect.getmembers` filtered to non-dunder callables). Prevents silent divergence between test reference and production implementation.

**`tests/contract/test_surface_profile_route_set.py`**

Assert:
- Under `p0_slice`: exactly the 9 routes respond (not 404)
- Under `p0_slice`: at least one non-P0 route returns 404
- Under `full`: all 133 routes are mounted

**`tests/contract/test_execution_target_role_policy.py`**

Assert:
- `COMMIT_SNAPSHOT` target → proceeds to engine
- `WORKING_SAVE` target without `NEXA_DEV_ALLOW_WORKING_SAVE_EXEC=1` → `UnauthorizedTargetRole` → HTTP 409
- `WORKING_SAVE` target with flag in non-production → permitted

**`tests/contract/test_run_submission_idempotency.py`**

Assert:
- First POST /api/runs with `X-Idempotency-Key: K` → run_id_1, engine called once
- Second POST /api/runs with `X-Idempotency-Key: K` within window → same run_id_1, engine not called again
- POST after window expiry → new run_id, engine called again

**`tests/contract/test_execution_record_insert_only.py`**

Assert that `ExecutionRecordStorePG` never issues UPDATE statements against committed records. Check by mocking the SQLAlchemy connection and asserting no `update()` construct is emitted.

**`tests/contract/test_target_resolver_canonical_input.py`**

Assert that `build_default_target_resolver` returns identical `ExecutionTarget` for identical `(workspace_ref, target_ref)` inputs — required for I5 (determinism).

**`tests/contract/test_idempotency_window_gt_run_duration.py`**

Assert:
- `_validate_p0_configuration(86400, 3600)` → no exception
- `_validate_p0_configuration(3600, 3600)` → `RuntimeError`
- `_validate_p0_configuration(1800, 3600)` → `RuntimeError`
- Test verifies `RuntimeError`, not bare `assert` — confirming the non-optimizable guard path

---

## 6. FILE INVENTORY

### Edited files

| File | Change |
|---|---|
| `requirements.txt` | +5 deps (`sqlalchemy`, `asyncpg`, `alembic`, `pyjwt[crypto]`, `uvicorn[standard]`). `boto3` not added. |
| `pyproject.toml` | +`[aws]` and `[testing]` optional extras |
| `src/server/auth_adapter.py` | Add `verify_session_token(token) -> VerifiedClaimsBundle` to `ClerkAuthAdapter` |
| `src/server/run_admission.py` | Replace default `engine_launch_decider` lambda with real bridge via dependency injection |
| `src/server/database_foundation.py` | Add `run_submission_dedupe` schema family to `get_server_schema_families()` |

### New files

```
alembic.ini
alembic/env.py
alembic/versions/0001_initial.py
alembic/versions/0002_run_submission_dedupe.py

docker-compose.yml
.env.example
scripts/dev_seed.py

src/server/__main__.py
src/server/asgi.py
src/server/surface_profile.py
src/server/health_routes.py
src/server/dependency_factory.py
src/server/clerk_jwks.py
src/server/engine_bridge.py
src/server/execution_target_resolver.py
src/server/run_submission_dedupe.py
src/server/p0_configuration.py

src/server/pg/__init__.py
src/server/pg/engine.py
src/server/pg/workspace_registry_store_pg.py
src/server/pg/onboarding_state_store_pg.py
src/server/pg/provider_binding_store_pg.py
src/server/pg/execution_record_store_pg.py
src/server/pg/run_submission_dedupe_store_pg.py
src/server/pg/dependencies_factory.py

tests/e2e/test_p0_vertical_slice.py
tests/contract/test_engine_does_not_import_server.py
tests/contract/test_server_does_not_import_circuit_internals.py
tests/contract/test_alembic_bootstrap_matches_foundation.py
tests/contract/test_pg_store_interface_parity.py
tests/contract/test_surface_profile_route_set.py
tests/contract/test_execution_target_role_policy.py
tests/contract/test_run_submission_idempotency.py
tests/contract/test_execution_record_insert_only.py
tests/contract/test_target_resolver_canonical_input.py
tests/contract/test_idempotency_window_gt_run_duration.py
```

### Not touched

Everything not listed above. Specifically:
- `src/engine/**` — zero edits
- `src/contracts/**` — zero edits
- `src/circuit/**` — zero edits
- `src/designer/**` — zero edits
- `src/providers/**` — zero edits
- `src/platform/**` — zero edits
- `src/plugins/**` — zero edits
- `src/ui/**` — zero edits
- `src/sdk/**` — zero edits
- `src/cli/**` — zero edits
- All `InMemory*Store` classes — zero edits
- All 550+ existing test files — zero edits
- All 5 legacy files — zero edits

---

## 7. INVARIANT COMPLIANCE MATRIX

Before submitting any PR, verify each row.

| Invariant | P0 action | How to verify |
|---|---|---|
| I1 Node is only execution unit | No edits to engine | `find src/engine -newer requirements.txt` shows no changes |
| I2 Circuit defines topology only | No edits to circuit | Same |
| I3 Dependency-driven execution | Engine scheduler untouched | Same |
| I4 Artifacts append-only | `execution_record_store_pg`: INSERT only; `supersedes_run_id` as forward-link on new row; no UPDATE | `test_execution_record_insert_only.py` |
| I5 Deterministic execution | `strict_determinism` threaded unchanged; typed resolver canonicalizes inputs | `test_target_resolver_canonical_input.py` |
| I6 Plugin isolation | No plugin changes | No files in `src/platform/plugins/**` modified |
| I7 Contract-driven | Typed resolver, typed idempotency, typed role contracts; `RuntimeError` guard is itself a contract artifact | All contract tests in Step238 |
| I8 Cross-layer imports | `engine_bridge.py` imports `src.engine.engine.Engine` only; reverse direction forbidden; `src/server` cannot import `src.circuit.*` or `src.engine.validation.*` | `test_engine_does_not_import_server.py` + `test_server_does_not_import_circuit_internals.py` |
| P0-S1 Storage-role truth | P0 routes: `COMMIT_SNAPSHOT` only; `WORKING_SAVE` behind env flag + `allowed_target_roles` | `test_execution_target_role_policy.py` |

---

## 8. TEST REQUIREMENTS

Hard rules:
1. `python -m pytest -q` must show **zero failures** after every step.
2. The 2,775 existing tests must never regress.
3. All 11 new contract/E2E tests must pass.
4. Target total: ~2,797 passing.

Never write a test that forces a pass by mocking the system under test into a vacuous state. Tests must exercise real behavior.

Contract tests are more important than E2E tests for day-to-day safety. Run them first. The E2E test requires Docker and a running Postgres container — run it in CI or explicitly.

---

## 9. RISK REGISTER

These risks are known and their mitigations are already specified. Do not re-open them as design questions.

| ID | Risk | Mitigation (already decided) |
|---|---|---|
| R1 | PG store interface drifts from InMemory | `test_pg_store_interface_parity.py` |
| R2 | Alembic ↔ foundation drift | `test_alembic_bootstrap_matches_foundation.py`; `database_foundation.py` edited to include dedupe family |
| R3 | Sync engine blocks request thread | `run_in_threadpool` in `engine_bridge.py`; `NEXA_P0_ENGINE_THREADPOOL_MAX`; `NEXA_P0_MAX_RUN_DURATION_S` cap |
| R4 | Clerk JWKS outage | JWKS cache (10 min TTL) with stale-serve fallback in `clerk_jwks.py` |
| R5 | New deps break existing tests | Run full suite after Step231 before continuing |
| R6 | `full` profile in prod without wiring | `/readyz` fail-fast; startup log enumerates active profile |
| R7 | Cross-layer import violation | Bi-directional AST contract tests |
| R8 | Append-only violation in PG schema | INSERT-only DDL; `test_execution_record_insert_only.py` |
| R9 | Event-loop starvation | `run_in_threadpool` is mandatory, not optional; bounded threadpool |
| R10 | Duplicate run submission (client retry) | `X-Idempotency-Key` + `run_submission_dedupe` table |
| R11 | Wrong storage-role execution anchor | Typed `ExecutionTargetResolver`; `allowed_target_roles` policy |
| R12 | Provider readiness gap | Seeded binding in `dev_seed.py`; `provider_mode` field in `/readyz` |
| R13 | Trace payload blow-up | Trace projection size cap; pagination on trace endpoint |
| R14 | `IDEMPOTENCY_WINDOW_S` ≤ `NEXA_P0_MAX_RUN_DURATION_S` | `_validate_p0_configuration()` raises `RuntimeError` at startup; `test_idempotency_window_gt_run_duration.py` |

---

## 10. DESIGN DECISION RATIONALE

These decisions were reached through a three-round triangular review (Claude ↔ GPT). Do not reopen them unless directed by the product owner.

| Decision | Rationale |
|---|---|
| `create_fastapi_app` consumed, not recreated | It already exists at `fastapi_binding.py:3193`. Recreating it would cause divergence between two app assembly paths. Discovered via GPT first review (v0.1→v0.2 factual correction). |
| SQLAlchemy Core, not ORM | Store shape is `dict-row-in / dict-row-out`. ORM adds abstraction cost with no value. GPT first review, Q5. |
| `boto3` as `[aws]` extra, not base dep | v0.1 draft had `boto3` in base requirements — a self-contradiction with the G3 decision. GPT first review, Q6. |
| PG stores mirror InMemory interface, no `StoreProtocol` | `StoreProtocol` abstraction was considered and rejected as premature. The interface parity is enforced by contract test instead. GPT first review, Q3. |
| `supersedes_run_id` as forward-link on new row only | I4 (append-only) requires that existing records are never modified. A forward-link on the new row avoids any UPDATE on the old row. GPT first review, Q4. |
| `_validate_p0_configuration()` raises `RuntimeError`, not `assert` | Python `-O`/`-OO` optimization flags strip all `assert` statements silently. A startup guard using `assert` would not fire in optimized runtimes. GPT third review, N1. |
| `IDEMPOTENCY_WINDOW_S > NEXA_P0_MAX_RUN_DURATION_S` constraint | If a run outlives the idempotency window, a retry would create a duplicate run while the original is still active. The startup guard enforces the constraint at deploy time. GPT second review, B1/F2. |
| `I9` not added to constitutional invariant set | Storage-role truth is load-bearing for P0 but belongs in the operational-constraint layer. Adding I9 without a constitution amendment would create an undocumented extension to I1–I8. GPT second review, B2. |
| Sync execution for P0, queue deferred to P1 | Async execution + workers would add Redis/SQS, lease management, and projection rehydration to P0 scope. The tradeoff is accepted: sync runs are limited by `NEXA_P0_MAX_RUN_DURATION_S`. |
| `testcontainers-postgres` for E2E test | E2E test requires a real Postgres container. `testcontainers` is more realistic than a pytest fixture DB for a vertical slice proof. GPT second review, Q11. |
| Reverse import fence excludes `src.providers.*` and `src.platform.*` | These modules have no formally defined public/internal boundary yet. Blanket-fencing them would block future legitimate server-side access before the boundary is defined. GPT second review, B3/F4. |

---

## 11. AUTH ARCHITECTURE DECISION RECORD

### Decision

**For P0:** Use Clerk as the identity provider, verified via PyJWT + JWKS cache.

**Auth boundary shape:** IdP-agnostic. The layers are:

```
HTTP Request
    ↓
ClerkAuthAdapter.verify_session_token(token) → VerifiedClaimsBundle
    ↓
(existing normalize path) claims → AuthenticatedIdentity
    ↓
AuthorizationGate / RequestAuthContext   ← IdP-agnostic from here down
    ↓
Route handler
```

The only Clerk-specific code lives in `ClerkAuthAdapter` and `clerk_jwks.py`. Everything from `AuthenticatedIdentity` downward is IdP-neutral. Replacing Clerk with another provider in the future means replacing only those two files.

### Future migration policy (product owner directive)

A migration to a self-hosted authentication system (e.g., Ory Kratos, custom JWT issuer) is **not part of P0 or any currently planned phase**. It will be re-evaluated as a separate agenda item only when all of the following conditions are met:

1. **System stability:** the core product is stable in production with measurable user retention.
2. **Cost case:** Clerk licensing cost has become material relative to the product's revenue or operating budget.
3. **Control case:** there is a specific product or compliance requirement that Clerk cannot satisfy but a self-hosted system would.
4. **Strategic case:** migrating auth provides a clear competitive or strategic advantage that outweighs the engineering cost.

Until all four conditions are met, Clerk remains the auth provider. This decision avoids premature infrastructure investment and preserves engineering capacity for product-facing work.

### Implementation constraints

- `NEXA_AUTH_MODE=dev_stub` is forbidden when `NEXA_ENV=production`.
- `NEXA_AUTH_MODE=dev_stub` is forbidden on any external-facing staging deployment (Railway staging must use `NEXA_AUTH_MODE=clerk`).
- `AuthorizationGate` and `RequestAuthContext` must never reference Clerk-specific types directly.
- `verify_session_token()` must return `VerifiedClaimsBundle` (raw verified claims), not `AuthenticatedIdentity`. The normalization step is kept separate so it remains reusable across IdPs.

### Environment variables

```
NEXA_AUTH_MODE=dev_stub|clerk
NEXA_CLERK_JWKS_URL=https://<tenant>.clerk.accounts.dev/.well-known/jwks.json
NEXA_ENV=development|staging|production
```

---

**End of document. Implementation may begin.**
