from __future__ import annotations

from src.server.database_models import ColumnSpec, IndexSpec, MigrationScript, MigrationStep, SchemaFamily, TableSpec
from src.server.migration_foundation import render_postgres_schema_statements, validate_schema_families

GDPR_USER_DELETION_AUDIT_SCHEMA_FAMILY = "gdpr_user_deletion_audit"
GDPR_USER_DELETION_AUDIT_TABLE = "user_deletion_audit"
GDPR_USER_DELETION_AUDIT_MIGRATION_ID = "server_foundation_gdpr_user_deletion_audit"


def build_gdpr_user_deletion_audit_schema_family() -> SchemaFamily:
    """Build the permanent audit schema family for GDPR deletion events.

    ``user_deletion_audit`` is Category D permanent audit. It is therefore
    modeled as append-only schema: insert new audit rows, never update/delete
    existing audit evidence. The table supports both completed deletion audit
    records and denied-route audit events, so deletion_request_id and user_ref
    are nullable while audit_event_id remains the immutable row identity.
    """

    return SchemaFamily(
        family_name=GDPR_USER_DELETION_AUDIT_SCHEMA_FAMILY,
        purpose=(
            "Permanent append-only audit rows for GDPR/user deletion requests, "
            "denials, outcomes, and immutable-history preservation evidence."
        ),
        persistence_mode="append_only",
        tables=(
            TableSpec(
                name=GDPR_USER_DELETION_AUDIT_TABLE,
                persistence_mode="append_only",
                description=(
                    "Category D permanent audit table for GDPR deletion route denials, "
                    "successful deletion outcomes, and failed deletion outcomes."
                ),
                columns=(
                    ColumnSpec("audit_event_id", "TEXT", is_primary_key=True),
                    ColumnSpec("deletion_request_id", "TEXT", nullable=True),
                    ColumnSpec("user_ref", "TEXT", nullable=True),
                    ColumnSpec("requested_by_ref", "TEXT", nullable=True),
                    ColumnSpec("status", "TEXT", nullable=True),
                    ColumnSpec("reason", "TEXT", nullable=True),
                    ColumnSpec("event_type", "TEXT", nullable=True),
                    ColumnSpec("recorded_at", "TEXT"),
                    ColumnSpec("audit_payload", "JSONB"),
                ),
                indexes=(
                    IndexSpec("idx_user_deletion_audit_deletion_request_id", ("deletion_request_id",)),
                    IndexSpec("idx_user_deletion_audit_user_ref", ("user_ref",)),
                    IndexSpec("idx_user_deletion_audit_requested_by_ref", ("requested_by_ref",)),
                    IndexSpec("idx_user_deletion_audit_recorded_at", ("recorded_at",)),
                    IndexSpec("idx_user_deletion_audit_event_type", ("event_type",)),
                ),
            ),
        ),
    )


def build_gdpr_user_deletion_audit_migration() -> MigrationScript:
    """Build the migration fragment for the GDPR deletion audit table."""

    schema_family = build_gdpr_user_deletion_audit_schema_family()
    validate_schema_families((schema_family,))
    statements = render_postgres_schema_statements((schema_family,))
    return MigrationScript(
        migration_id=GDPR_USER_DELETION_AUDIT_MIGRATION_ID,
        dialect="postgresql",
        summary=(
            "Add Category D permanent user_deletion_audit rows for GDPR deletion "
            "route denials, deletion outcomes, and immutable-history preservation evidence."
        ),
        schema_families=(schema_family,),
        steps=(
            MigrationStep(
                step_id="create_user_deletion_audit",
                description="Create the append-only GDPR user deletion audit table and indexes.",
                statements=statements,
            ),
        ),
    )


__all__ = [
    "GDPR_USER_DELETION_AUDIT_MIGRATION_ID",
    "GDPR_USER_DELETION_AUDIT_SCHEMA_FAMILY",
    "GDPR_USER_DELETION_AUDIT_TABLE",
    "build_gdpr_user_deletion_audit_migration",
    "build_gdpr_user_deletion_audit_schema_family",
]
