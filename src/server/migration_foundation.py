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


def _schema_family_by_name(schema_families: tuple[SchemaFamily, ...], family_name: str) -> SchemaFamily:
    for family in schema_families:
        if family.family_name == family_name:
            return family
    raise ValueError(f"Unknown schema family: {family_name}")


def build_initial_server_migration() -> MigrationScript:
    schema_families = get_server_schema_families()
    validate_schema_families(schema_families)
    statements = render_postgres_schema_statements(schema_families)
    return MigrationScript(
        migration_id="server_foundation_0001",
        dialect="postgresql",
        summary=(
            "Initial PostgreSQL foundation for workspace continuity, workspace shell artifact sources, run continuity, "
            "managed provider bindings, provider probe history, provider catalog surfaces, public-share persistence, workspace feedback, onboarding state, "
            "artifact index, trace event index, and artifact lineage links."
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


def build_workspace_shell_sources_migration() -> MigrationScript:
    schema_families = get_server_schema_families()
    validate_schema_families(schema_families)
    workspace_shell_sources = _schema_family_by_name(schema_families, "workspace_shell_sources")
    statements = render_postgres_schema_statements((workspace_shell_sources,))
    return MigrationScript(
        migration_id="server_foundation_0002_workspace_shell_sources",
        dialect="postgresql",
        summary=(
            "Add PostgreSQL-backed workspace shell artifact source persistence so workspace shell draft, "
            "commit, checkout, import, and starter-template flows resolve through durable current artifacts."
        ),
        schema_families=(workspace_shell_sources,),
        steps=(
            MigrationStep(
                step_id="server_foundation_0002_create_workspace_shell_sources",
                description="Create the workspace shell artifact source table family and indexes.",
                statements=statements,
            ),
        ),
    )


def build_public_share_persistence_migration() -> MigrationScript:
    schema_families = get_server_schema_families()
    validate_schema_families(schema_families)
    public_share_persistence = _schema_family_by_name(schema_families, "public_share_persistence")
    statements = render_postgres_schema_statements((public_share_persistence,))
    return MigrationScript(
        migration_id="server_foundation_0003_public_share_persistence",
        dialect="postgresql",
        summary=(
            "Add PostgreSQL-backed public-share payload, governance action report, and saved-share persistence "
            "so catalog, issuer-management, and saved-share product flows resolve through durable rows."
        ),
        schema_families=(public_share_persistence,),
        steps=(
            MigrationStep(
                step_id="server_foundation_0003_create_public_share_persistence",
                description="Create the public-share payload, governance action report, and saved-share table families and indexes.",
                statements=statements,
            ),
        ),
    )



def build_catalog_surfaces_migration() -> MigrationScript:
    schema_families = get_server_schema_families()
    validate_schema_families(schema_families)
    catalog_surfaces = _schema_family_by_name(schema_families, "catalog_surfaces")
    statements = render_postgres_schema_statements((catalog_surfaces,))
    return MigrationScript(
        migration_id="server_foundation_0004_catalog_surfaces",
        dialect="postgresql",
        summary=(
            "Add PostgreSQL-backed provider catalog surface rows while target catalogs resolve from canonical workspace artifact sources, "
            "closing remaining provider-catalog and target-catalog dependency seams."
        ),
        schema_families=(catalog_surfaces,),
        steps=(
            MigrationStep(
                step_id="server_foundation_0004_create_catalog_surfaces",
                description="Create the provider catalog surface table family and indexes.",
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
