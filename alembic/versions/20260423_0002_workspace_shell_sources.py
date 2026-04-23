"""workspace shell sources 0002

Revision ID: 20260423_0002
Revises: 20260423_0001
Create Date: 2026-04-23 00:10:00
"""
from __future__ import annotations

from alembic import op

from src.server.migration_foundation import build_workspace_shell_sources_migration

revision = "20260423_0002"
down_revision = "20260423_0001"
branch_labels = None
depends_on = None


_STATEMENTS = build_workspace_shell_sources_migration().steps[0].statements


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Downgrade is not supported for workspace shell source persistence migration.")
