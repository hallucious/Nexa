from __future__ import annotations

from typing import Any

from src.server.fastapi_binding_models import FastApiRouteDependencies


# ``engine`` is intentionally typed as ``Any`` here so importing this module does
# not force optional SQLAlchemy availability in non-Postgres environments.
def build_postgres_dependencies(engine: Any) -> FastApiRouteDependencies:
    """Return the initial Postgres-backed dependency bundle.

    This batch keeps route-provider wiring intentionally conservative.
    The engine-backed readiness path is now real, while higher-level row/store
    bindings can be added in later batches without reopening bootstrap.
    """

    _ = engine
    return FastApiRouteDependencies()
