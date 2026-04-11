from __future__ import annotations

from src.server.database_foundation import get_server_schema_families
from src.server.database_models import MigrationScript, MigrationStep, SchemaFamily, TableSpec


def _render_table_statement(table: TableSpec) -> str:
    column_lines = [f"    {column.sql_definition}" for column in table.columns]
    body = ",\n".join(column_lines)
    return f"CREATE TABLE IF NOT EXISTS {table.name} (\n{body}\n);"


def _render_index_statement(table: TableSpec, *, index_name: str, columns: tuple[str, ...], unique: bool) -> str:
    uniqueness = "UNIQUE " if unique else ""
    joined_columns = ", ".join(columns)
    return f"CREATE {uniqueness}INDEX IF NOT EXISTS {index_name} ON {table.name} ({joined_columns});"


def render_postgres_schema_statements(schema_families: tuple[SchemaFamily, ...]) -> tuple[str, ...]:
    statements: list[str] = []
    for family in schema_families:
        statements.append(f"-- family: {family.family_name} [{family.persistence_mode}]")
        for table in family.tables:
            statements.append(_render_table_statement(table))
            for index in table.indexes:
                statements.append(
                    _render_index_statement(
                        table,
                        index_name=index.name,
                        columns=index.columns,
                        unique=index.unique,
                    )
                )
    return tuple(statements)


def validate_schema_families(schema_families: tuple[SchemaFamily, ...]) -> None:
    family_names = [family.family_name for family in schema_families]
    if len(family_names) != len(set(family_names)):
        raise ValueError("Duplicate schema family names are not allowed")

    table_names: list[str] = []
    index_names: list[str] = []
    for family in schema_families:
        for table in family.tables:
            table_names.append(table.name)
            for index in table.indexes:
                index_names.append(index.name)
    if len(table_names) != len(set(table_names)):
        raise ValueError("Duplicate table names are not allowed across schema families")
    if len(index_names) != len(set(index_names)):
        raise ValueError("Duplicate index names are not allowed across schema families")


def build_initial_server_migration() -> MigrationScript:
    schema_families = get_server_schema_families()
    validate_schema_families(schema_families)
    statements = render_postgres_schema_statements(schema_families)
    return MigrationScript(
        migration_id="server_foundation_0001",
        dialect="postgresql",
        summary=(
            "Initial PostgreSQL foundation for workspace continuity, run continuity, "
            "onboarding state, artifact index, trace event index, and artifact lineage links."
        ),
        schema_families=schema_families,
        steps=(
            MigrationStep(
                step_id="server_foundation_0001_create_tables_and_indexes",
                description="Create the initial server persistence table families and indexes.",
                statements=statements,
            ),
        ),
    )


def build_migration_file_text(migration: MigrationScript) -> str:
    parts = [f"-- migration_id: {migration.migration_id}", f"-- summary: {migration.summary}"]
    for step in migration.steps:
        parts.append(f"\n-- step: {step.step_id}")
        parts.append(f"-- description: {step.description}")
        parts.extend(step.statements)
    return "\n".join(parts) + "\n"
