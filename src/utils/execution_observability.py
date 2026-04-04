import json
import os
import time
from typing import Dict, Any

from src.utils.nexa_config import get_observability_path


def _ensure_file():
    path = get_observability_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass


def _now_ts():
    return int(time.time() * 1000)


def write_execution_record(record: Dict[str, Any]) -> None:
    _ensure_file()
    with open(get_observability_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_success_record(
    circuit_path: str,
    circuit_id: str,
    metrics: Dict[str, Any],
    execution_time_ms: int
) -> Dict[str, Any]:

    return {
        "timestamp": _now_ts(),
        "circuit_path": circuit_path,
        "circuit_id": circuit_id,
        "execution_time_ms": execution_time_ms,
        "node_count": metrics.get("node_count", 0),
        "executed_nodes": metrics.get("executed_nodes", 0),
        "wave_count": metrics.get("wave_count", 0),
        "plugin_calls": metrics.get("plugin_calls", 0),
        "provider_calls": metrics.get("provider_calls", 0),
        "status": "success",
        "success": True,
        "error_type": None,
        "error_message": None,
    }


def build_failure_record(
    circuit_path: str,
    circuit_id: str,
    error: Exception
) -> Dict[str, Any]:

    return {
        "timestamp": _now_ts(),
        "circuit_path": circuit_path,
        "circuit_id": circuit_id,
        "execution_time_ms": None,
        "node_count": None,
        "executed_nodes": None,
        "wave_count": None,
        "plugin_calls": None,
        "provider_calls": None,
        "status": "failure",
        "success": False,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }