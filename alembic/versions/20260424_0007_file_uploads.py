"""Add file upload quarantine and event tables.

Revision ID: 20260424_0007
Revises: 20260424_0006
Create Date: 2026-04-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260424_0007"
down_revision = "20260424_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_uploads",
        sa.Column("upload_id", sa.Text(), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("object_ref", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("declared_mime_type", sa.Text(), nullable=False),
        sa.Column("declared_size_bytes", sa.Integer(), nullable=False),
        sa.Column("upload_state", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("rejection_reason_code", sa.Text(), nullable=True),
        sa.Column("observed_mime_type", sa.Text(), nullable=True),
        sa.Column("observed_size_bytes", sa.Integer(), nullable=True),
        sa.Column("extracted_text_char_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_file_uploads_workspace_id", "file_uploads", ["workspace_id"])
    op.create_index("idx_file_uploads_upload_state", "file_uploads", ["upload_state"])
    op.create_index("idx_file_uploads_updated_at", "file_uploads", ["updated_at"])
    op.create_index("idx_file_uploads_expires_at", "file_uploads", ["expires_at"])

    op.create_table(
        "file_upload_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("upload_id", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_ref", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_file_upload_events_upload_id", "file_upload_events", ["upload_id"])
    op.create_index("idx_file_upload_events_workspace_id", "file_upload_events", ["workspace_id"])
    op.create_index("idx_file_upload_events_created_at", "file_upload_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_file_upload_events_created_at", table_name="file_upload_events")
    op.drop_index("idx_file_upload_events_workspace_id", table_name="file_upload_events")
    op.drop_index("idx_file_upload_events_upload_id", table_name="file_upload_events")
    op.drop_table("file_upload_events")
    op.drop_index("idx_file_uploads_expires_at", table_name="file_uploads")
    op.drop_index("idx_file_uploads_updated_at", table_name="file_uploads")
    op.drop_index("idx_file_uploads_upload_state", table_name="file_uploads")
    op.drop_index("idx_file_uploads_workspace_id", table_name="file_uploads")
    op.drop_table("file_uploads")
