from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.contracts.savefile_loader import load_savefile_from_path
from src.contracts.savefile_provider_builder import build_provider_registry_from_savefile
from src.contracts.savefile_validator import validate_savefile


def is_savefile_contract(circuit_path: str) -> bool:
    try:
        data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    required = {"meta", "circuit", "resources", "state", "ui"}
    return required.issubset(set(data.keys()))


def execute_savefile(
    circuit_path: str,
    *,
    input_overrides: Mapping[str, Any] | None = None,
    run_id: str = "cli",
):
    savefile = load_savefile_from_path(circuit_path)

    if input_overrides:
        savefile.state.input.update(dict(input_overrides))

    validate_savefile(savefile)
    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)
    trace = executor.execute(savefile, run_id=run_id)
    return savefile, trace
