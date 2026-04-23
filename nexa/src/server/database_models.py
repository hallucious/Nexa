from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

ServerPersistenceMode = Literal["mutable_projection", "append_only"]
MigrationDialect = Literal["postgresql"]

_ALLOWED_PERSISTENCE_MODES = {"mutable_projection", "append_only"}
_ALLOWED_SSL_MODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}


@dataclass(frozen=True)
class PostgresConnectionSettings:
    host: str
    port: int
    database_name: str
    username: str
    password_env_var: str = "NEXA_SERVER_DB_PASSWORD"
    ssl_mode: str = "require"
    application_name: str = "nexa_server"
    connect_timeout_s: int = 10
    schema_name: str = "public"

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("PostgresConnectionSettings.host must be non-empty")
        if self.port <= 0:
            raise ValueError("PostgresConnectionSettings.port must be > 0")
        if not self.database_name:
            raise ValueError("PostgresConnectionSettings.database_name must be non-empty")
        if not self.username:
            raise ValueError("PostgresConnectionSettings.username must be non-empty")
        if not self.password_env_var:
            raise ValueError("PostgresConnectionSettings.password_env_var must be non-empty")
        if self.ssl_mode not in _ALLOWED_SSL_MODES:
            raise ValueError(f"Unsupported ssl_mode: {self.ssl_mode}")
        if not self.application_name:
            raise ValueError("PostgresConnectionSettings.application_name must be non-empty")
        if self.connect_timeout_s <= 0:
            raise ValueError("PostgresConnectionSettings.connect_timeout_s must be > 0")
        if not self.schema_name:
            raise ValueError("PostgresConnectionSettings.schema_name must be non-empty")


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    sql_type: str
    nullable: bool = False
    default_sql: Optional[str] = None
    is_primary_key: bool = False
    reference_table: Optional[str] = None
    reference_column: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ColumnSpec.name must be non-empty")
        if not self.sql_type:
            raise ValueError("ColumnSpec.sql_type must be non-empty")
        if self.reference_table and not self.reference_column:
            raise ValueError("ColumnSpec.reference_column must be set when reference_table is provided")
        if self.reference_column and not self.reference_table:
            raise ValueError("ColumnSpec.reference_table must be set when reference_column is provided")

    @property
    def sql_definition(self) -> str:
        parts = [self.name, self.sql_type]
        if self.is_primary_key:
            parts.append("PRIMARY KEY")
        if not self.nullable and not self.is_primary_key:
            parts.append("NOT NULL")
        if self.default_sql is not None:
            parts.append(f"DEFAULT {self.default_sql}")
        if self.reference_table and self.reference_column:
            parts.append(f"REFERENCES {self.reference_table} ({self.reference_column})")
        return " ".join(parts)


@dataclass(frozen=True)
class IndexSpec:
    name: str
    columns: tuple[str, ...]
    unique: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("IndexSpec.name must be non-empty")
        if not self.columns:
            raise ValueError("IndexSpec.columns must be non-empty")
        for item in self.columns:
            if not item:
                raise ValueError("IndexSpec.columns must not contain empty values")


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    indexes: tuple[IndexSpec, ...] = ()
    persistence_mode: ServerPersistenceMode = "mutable_projection"
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("TableSpec.name must be non-empty")
        if not self.columns:
            raise ValueError("TableSpec.columns must be non-empty")
        if self.persistence_mode not in _ALLOWED_PERSISTENCE_MODES:
            raise ValueError(f"Unsupported persistence_mode: {self.persistence_mode}")

        column_names = [column.name for column in self.columns]
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"Duplicate column names are not allowed in table {self.name}")

        index_names = [index.name for index in self.indexes]
        if len(index_names) != len(set(index_names)):
            raise ValueError(f"Duplicate index names are not allowed in table {self.name}")

        for index in self.indexes:
            for column_name in index.columns:
                if column_name not in column_names:
                    raise ValueError(
                        f"Index {index.name} references unknown column {column_name!r} in table {self.name}"
                    )

    @property
    def primary_key_columns(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns if column.is_primary_key)


@dataclass(frozen=True)
class SchemaFamily:
    family_name: str
    tables: tuple[TableSpec, ...]
    purpose: str
    persistence_mode: ServerPersistenceMode

    def __post_init__(self) -> None:
        if not self.family_name:
            raise ValueError("SchemaFamily.family_name must be non-empty")
        if not self.tables:
            raise ValueError("SchemaFamily.tables must be non-empty")
        if not self.purpose:
            raise ValueError("SchemaFamily.purpose must be non-empty")
        if self.persistence_mode not in _ALLOWED_PERSISTENCE_MODES:
            raise ValueError(f"Unsupported persistence_mode: {self.persistence_mode}")
        for table in self.tables:
            if table.persistence_mode != self.persistence_mode:
                raise ValueError(
                    f"SchemaFamily {self.family_name} mixes persistence modes: {table.name} has {table.persistence_mode}"
                )


@dataclass(frozen=True)
class MigrationStep:
    step_id: str
    description: str
    statements: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("MigrationStep.step_id must be non-empty")
        if not self.description:
            raise ValueError("MigrationStep.description must be non-empty")
        if not self.statements:
            raise ValueError("MigrationStep.statements must be non-empty")
        for statement in self.statements:
            if not statement.strip():
                raise ValueError("MigrationStep.statements must not contain empty SQL")


@dataclass(frozen=True)
class MigrationScript:
    migration_id: str
    dialect: MigrationDialect
    summary: str
    schema_families: tuple[SchemaFamily, ...]
    steps: tuple[MigrationStep, ...]

    def __post_init__(self) -> None:
        if not self.migration_id:
            raise ValueError("MigrationScript.migration_id must be non-empty")
        if self.dialect != "postgresql":
            raise ValueError(f"Unsupported migration dialect: {self.dialect}")
        if not self.summary:
            raise ValueError("MigrationScript.summary must be non-empty")
        if not self.schema_families:
            raise ValueError("MigrationScript.schema_families must be non-empty")
        if not self.steps:
            raise ValueError("MigrationScript.steps must be non-empty")
