from __future__ import annotations

from src.server.gdpr_deletion_schema import GDPR_USER_DELETION_AUDIT_MIGRATION_ID
from src.server.migration_foundation import (
    build_all_server_migrations,
    build_gdpr_user_deletion_audit_migration,
    build_incremental_server_migrations,
    build_migration_file_text,
)


def test_gdpr_user_deletion_audit_migration_is_registered_in_migration_foundation() -> None:
    migration = build_gdpr_user_deletion_audit_migration()

    assert migration.migration_id == GDPR_USER_DELETION_AUDIT_MIGRATION_ID
    assert migration.schema_families[0].tables[0].name == "user_deletion_audit"

    text = build_migration_file_text(migration)
    assert "CREATE TABLE IF NOT EXISTS user_deletion_audit" in text
    assert "audit_event_id TEXT PRIMARY KEY" in text
    assert "CREATE INDEX IF NOT EXISTS idx_user_deletion_audit_event_type" in text


def test_incremental_server_migrations_include_gdpr_audit_after_existing_fragments() -> None:
    migration_ids = [migration.migration_id for migration in build_incremental_server_migrations()]

    assert migration_ids[-1] == GDPR_USER_DELETION_AUDIT_MIGRATION_ID
    assert len(migration_ids) == len(set(migration_ids))


def test_all_server_migrations_include_initial_and_gdpr_audit_registration() -> None:
    migration_ids = [migration.migration_id for migration in build_all_server_migrations()]

    assert migration_ids[0] == "server_foundation_0001"
    assert GDPR_USER_DELETION_AUDIT_MIGRATION_ID in migration_ids
    assert len(migration_ids) == len(set(migration_ids))
