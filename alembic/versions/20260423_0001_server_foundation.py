"""server foundation 0001

Revision ID: 20260423_0001
Revises: 
Create Date: 2026-04-23 00:00:00
"""
from __future__ import annotations

from alembic import op

from src.server.migration_foundation import build_initial_server_migration

revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None


_STATEMENTS = build_initial_server_migration().steps[0].statements


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


# The initial foundation migration is additive-only in this batch.
def downgrade() -> None:
    raise RuntimeError("Downgrade is not supported for the initial server foundation migration.")
