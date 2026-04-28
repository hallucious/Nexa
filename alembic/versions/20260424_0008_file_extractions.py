"""Add file extraction status and event tables.

Revision ID: 20260424_0008
Revises: 20260424_0007
Create Date: 2026-04-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260424_0008"
down_revision = "20260424_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_extractions",
        sa.Column("extraction_id", sa.Text(), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Text(), nullable=False),
        sa.Column("extraction_state", sa.Text(), nullable=False),
        sa.Column("source_document_type", sa.Text(), nullable=True),
        sa.Column("source_object_ref", sa.Text(), nullable=True),
        sa.Column("text_artifact_ref", sa.Text(), nullable=True),
        sa.Column("extracted_text_char_count", sa.Integer(), nullable=True),
        sa.Column("text_preview", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("rejection_reason_code", sa.Text(), nullable=True),
        sa.Column("extractor_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_file_extractions_workspace_id", "file_extractions", ["workspace_id"])
    op.create_index("idx_file_extractions_upload_id", "file_extractions", ["upload_id"])
    op.create_index("idx_file_extractions_extraction_state", "file_extractions", ["extraction_state"])
    op.create_index("idx_file_extractions_updated_at", "file_extractions", ["updated_at"])

    op.create_table(
        "file_extraction_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("extraction_id", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_ref", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_file_extraction_events_extraction_id", "file_extraction_events", ["extraction_id"])
    op.create_index("idx_file_extraction_events_workspace_id", "file_extraction_events", ["workspace_id"])
    op.create_index("idx_file_extraction_events_upload_id", "file_extraction_events", ["upload_id"])
    op.create_index("idx_file_extraction_events_created_at", "file_extraction_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_file_extraction_events_created_at", table_name="file_extraction_events")
    op.drop_index("idx_file_extraction_events_upload_id", table_name="file_extraction_events")
    op.drop_index("idx_file_extraction_events_workspace_id", table_name="file_extraction_events")
    op.drop_index("idx_file_extraction_events_extraction_id", table_name="file_extraction_events")
    op.drop_table("file_extraction_events")
    op.drop_index("idx_file_extractions_updated_at", table_name="file_extractions")
    op.drop_index("idx_file_extractions_extraction_state", table_name="file_extractions")
    op.drop_index("idx_file_extractions_upload_id", table_name="file_extractions")
    op.drop_index("idx_file_extractions_workspace_id", table_name="file_extractions")
    op.drop_table("file_extractions")
