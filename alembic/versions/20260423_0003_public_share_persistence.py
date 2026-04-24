"""public share persistence 0003

Revision ID: 20260423_0003
Revises: 20260423_0002
Create Date: 2026-04-23 00:20:00
"""
from __future__ import annotations

from alembic import op

from src.server.migration_foundation import build_public_share_persistence_migration

revision = "20260423_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


_STATEMENTS = build_public_share_persistence_migration().steps[0].statements


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Downgrade is not supported for public share persistence migration.")
