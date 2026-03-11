from pathlib import Path
from typing import Dict, Any
import yaml

from src.config.execution_config_registry import ExecutionConfigRegistry


def load_execution_configs(config_dir: str) -> ExecutionConfigRegistry:

    registry = ExecutionConfigRegistry()

    path = Path(config_dir)

    if not path.exists():
        raise FileNotFoundError(config_dir)

    for file in path.glob("*.yaml"):

        with open(file, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = yaml.safe_load(f)

        if "config_id" not in config:
            raise ValueError(f"config missing config_id: {file}")

        registry.register(config)

    return registry