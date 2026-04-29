from __future__ import annotations

from src.server.gdpr_deletion_schema import (
    GDPR_USER_DELETION_AUDIT_MIGRATION_ID,
    GDPR_USER_DELETION_AUDIT_TABLE,
    build_gdpr_user_deletion_audit_migration,
    build_gdpr_user_deletion_audit_schema_family,
)
from src.server.migration_foundation import render_postgres_schema_statements, validate_schema_families


def test_gdpr_user_deletion_audit_schema_is_append_only_and_permanent_audit_ready() -> None:
    family = build_gdpr_user_deletion_audit_schema_family()

    assert family.family_name == "gdpr_user_deletion_audit"
    assert family.persistence_mode == "append_only"
    assert len(family.tables) == 1
    table = family.tables[0]
    assert table.name == GDPR_USER_DELETION_AUDIT_TABLE
    assert table.persistence_mode == "append_only"
    assert table.primary_key_columns == ("audit_event_id",)
    column_names = {column.name for column in table.columns}
    assert {
        "audit_event_id",
        "deletion_request_id",
        "user_ref",
        "requested_by_ref",
        "status",
        "reason",
        "event_type",
        "recorded_at",
        "audit_payload",
    }.issubset(column_names)
    assert {index.name for index in table.indexes} >= {
        "idx_user_deletion_audit_deletion_request_id",
        "idx_user_deletion_audit_user_ref",
        "idx_user_deletion_audit_requested_by_ref",
        "idx_user_deletion_audit_recorded_at",
        "idx_user_deletion_audit_event_type",
    }


def test_gdpr_user_deletion_audit_migration_renders_table_and_indexes() -> None:
    migration = build_gdpr_user_deletion_audit_migration()

    assert migration.migration_id == GDPR_USER_DELETION_AUDIT_MIGRATION_ID
    assert migration.dialect == "postgresql"
    assert len(migration.steps) == 1
    statements = migration.steps[0].statements
    rendered = "\n".join(statements)
    assert "CREATE TABLE IF NOT EXISTS user_deletion_audit" in rendered
    assert "audit_event_id TEXT PRIMARY KEY" in rendered
    assert "audit_payload JSONB NOT NULL" in rendered
    assert "CREATE INDEX IF NOT EXISTS idx_user_deletion_audit_deletion_request_id" in rendered
    assert "CREATE INDEX IF NOT EXISTS idx_user_deletion_audit_recorded_at" in rendered


def test_gdpr_user_deletion_audit_schema_validates_standalone() -> None:
    family = build_gdpr_user_deletion_audit_schema_family()

    validate_schema_families((family,))
    statements = render_postgres_schema_statements((family,))

    assert statements[0] == "-- family: gdpr_user_deletion_audit [append_only]"
    assert any("user_deletion_audit" in statement for statement in statements)
