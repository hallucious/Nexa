"""Add provider_cost_catalog for canonical provider/model cost access.

Revision ID: 20260424_0006
Revises: 20260424_0005
Create Date: 2026-04-24 00:06:00

This migration adds the durable provider/model catalog table needed by
Batch 2B provider-core work. The table stores model-level plan access
and relative cost ratios without storing provider secrets.
"""
from __future__ import annotations

from alembic import op

revision = "20260424_0006"
down_revision = "20260424_0005"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS provider_cost_catalog (
        provider_model_key TEXT PRIMARY KEY,
        provider_key TEXT NOT NULL,
        provider_family TEXT NOT NULL,
        model_ref TEXT NOT NULL,
        model_display_name TEXT NOT NULL,
        tier TEXT NOT NULL,
        plan_availability JSONB NOT NULL,
        default_for_plans JSONB,
        cost_ratio NUMERIC NOT NULL,
        pricing_unit TEXT NOT NULL DEFAULT 'relative_unit',
        lifecycle_state TEXT NOT NULL DEFAULT 'active',
        updated_at TIMESTAMPTZ
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_provider_cost_catalog_provider_key ON provider_cost_catalog (provider_key);",
    "CREATE INDEX IF NOT EXISTS idx_provider_cost_catalog_tier ON provider_cost_catalog (tier);",
    "CREATE INDEX IF NOT EXISTS idx_provider_cost_catalog_lifecycle_state ON provider_cost_catalog (lifecycle_state);",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_provider_cost_catalog_lifecycle_state;")
    op.execute("DROP INDEX IF EXISTS idx_provider_cost_catalog_tier;")
    op.execute("DROP INDEX IF EXISTS idx_provider_cost_catalog_provider_key;")
    op.execute("DROP TABLE IF EXISTS provider_cost_catalog;")
