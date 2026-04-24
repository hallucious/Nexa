"""Create provider catalog surface table family."""

from __future__ import annotations

from alembic import op

from src.server.migration_foundation import build_catalog_surfaces_migration

revision = "20260423_0004"
down_revision = "20260423_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    migration = build_catalog_surfaces_migration()
    bind = op.get_bind()
    for statement in migration.steps[0].statements:
        if statement.lstrip().startswith("--"):
            continue
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX IF EXISTS idx_provider_catalog_entries_lifecycle_state")
    bind.exec_driver_sql("DROP INDEX IF EXISTS idx_provider_catalog_entries_provider_family")
    bind.exec_driver_sql("DROP TABLE IF EXISTS provider_catalog_entries")
