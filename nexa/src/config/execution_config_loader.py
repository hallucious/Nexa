from pathlib import Path
from typing import Any, Dict
import yaml

from src.config.execution_config_registry import ExecutionConfigRegistry
from src.config.execution_config_schema_validator import (
    ExecutionConfigSchemaValidationError,
    ExecutionConfigSchemaValidator,
)


def load_execution_configs(config_dir: str) -> ExecutionConfigRegistry:
    registry = ExecutionConfigRegistry()

    path = Path(config_dir)

    if not path.exists():
        raise FileNotFoundError(config_dir)

    for file in sorted(path.glob("*.yaml")):
        with open(file, "r", encoding="utf-8") as f:
            loaded: Any = yaml.safe_load(f)

        try:
            config: Dict[str, Any] = ExecutionConfigSchemaValidator(loaded).validate()
            registry.register(config)
        except ExecutionConfigSchemaValidationError as exc:
            raise ExecutionConfigSchemaValidationError(f"{file}: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"{file}: {exc}") from exc

    return registry