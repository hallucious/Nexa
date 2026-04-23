from __future__ import annotations

VALID_SEVERITIES = {"HIGH", "MEDIUM", "LOW"}
SUPPORTED_VERSION = "1.0"


class PolicyConfigError(Exception):
    pass


def validate_policy_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise PolicyConfigError("Config must be a JSON object")

    version = config.get("version")
    if version != SUPPORTED_VERSION:
        raise PolicyConfigError(f"Unsupported or missing version: {version}")

    overrides = config.get("overrides", {})

    if not isinstance(overrides, dict):
        raise PolicyConfigError("overrides must be a dictionary")

    for k, v in overrides.items():
        if not isinstance(k, str):
            raise PolicyConfigError("reason_code must be string")
        if v not in VALID_SEVERITIES:
            raise PolicyConfigError(f"Invalid severity for {k}: {v}")

    return overrides
