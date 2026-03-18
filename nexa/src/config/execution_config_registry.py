from typing import Dict


class ExecutionConfigRegistry:
    """
    Registry for execution configs.

    Maps:
        config_id -> execution_config
    """

    def __init__(self):
        self._configs: Dict[str, dict] = {}

    def register(self, config: dict):
        if "config_id" not in config:
            raise ValueError("execution config must contain config_id")

        config_id = config["config_id"]

        if config_id in self._configs:
            raise ValueError(f"execution config already registered: {config_id}")

        self._configs[config_id] = config

    def get(self, config_id: str) -> dict:
        if config_id not in self._configs:
            raise KeyError(f"execution config not found: {config_id}")

        return self._configs[config_id]

    def list_configs(self):
        return list(self._configs.keys())