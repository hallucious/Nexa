from __future__ import annotations

import os


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_observability_path() -> str:
    return _env_first(
        "NEXA_OBSERVABILITY_PATH",
        "HAI_OBSERVABILITY_PATH",
        default="OBSERVABILITY.jsonl",
    )


def get_observability_filename() -> str:
    # run_dir-based observability writers still choose the directory separately.
    return "OBSERVABILITY.jsonl"


def is_observability_enabled(raw: dict | None = None) -> bool:
    try:
        if isinstance(raw, dict) and raw.get("observability_enabled") is True:
            return True
    except Exception:
        pass
    return _is_truthy(
        _env_first("NEXA_OBSERVABILITY", "HAI_OBSERVABILITY", default="")
    )


def get_safe_mode_enabled() -> bool:
    return _is_truthy(_env_first("NEXA_SAFE_MODE", "HAI_SAFE_MODE", default="0"))


def get_safe_mode_link_mode() -> str:
    return _env_first(
        "NEXA_SAFE_MODE_LINK_MODE",
        "HAI_SAFE_MODE_LINK_MODE",
        default="OFF",
    ).strip().upper()


def get_safe_mode_strict_recovery_enabled() -> bool:
    return _is_truthy(
        _env_first(
            "NEXA_SAFE_MODE_STRICT_RECOVERY",
            "HAI_SAFE_MODE_STRICT_RECOVERY",
            default="0",
        )
    )


def get_safe_mode_reason_override() -> str:
    return _env_first("NEXA_SAFE_MODE_REASON", "HAI_SAFE_MODE_REASON", default="")
