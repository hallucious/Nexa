"""Add run_submissions table for async queue substrate.

Revision ID: 20260424_0005
Revises: 20260423_0004
Create Date: 2026-04-24 00:00:00

run_submissions is the durable Category C operational truth table that
bridges accepted run requests and Redis queue transport.
It enables Redis-loss recovery by ensuring every accepted run has a
Postgres record before queue enqueue occurs.
"""
from __future__ import annotations

from alembic import op

revision = "20260424_0005"
down_revision = "20260423_0004"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS run_submissions (
        submission_id          TEXT PRIMARY KEY,
        run_id                 TEXT NOT NULL,
        workspace_id           TEXT NOT NULL,
        run_request_id         TEXT NOT NULL,
        submitter_user_ref     TEXT NOT NULL,
        target_type            TEXT NOT NULL,
        target_ref             TEXT NOT NULL,
        provider_id            TEXT,
        model_id               TEXT,
        priority               TEXT NOT NULL DEFAULT 'normal',
        mode                   TEXT NOT NULL DEFAULT 'standard',
        submission_status      TEXT NOT NULL DEFAULT 'submitted',
        queue_name             TEXT,
        queue_job_id           TEXT,
        worker_attempt_number  INTEGER NOT NULL DEFAULT 0,
        submitted_at           TEXT NOT NULL,
        queued_at              TEXT,
        claimed_at             TEXT,
        terminal_at            TEXT,
        expires_at             TEXT,
        failure_reason         TEXT,
        created_at             TEXT NOT NULL,
        updated_at             TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_run_submissions_run_id ON run_submissions (run_id);",
    "CREATE INDEX IF NOT EXISTS idx_run_submissions_workspace_id ON run_submissions (workspace_id);",
    "CREATE INDEX IF NOT EXISTS idx_run_submissions_submission_status ON run_submissions (submission_status);",
    "CREATE INDEX IF NOT EXISTS idx_run_submissions_submitted_at ON run_submissions (submitted_at);",
    "CREATE INDEX IF NOT EXISTS idx_run_submissions_expires_at ON run_submissions (expires_at);",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_run_submissions_run_request_id ON run_submissions (run_request_id);",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS run_submissions;")
