from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.contracts.nex_format import NexCircuit


def serialize_nex(circuit: NexCircuit) -> dict:
    """Convert legacy NexCircuit dataclass into JSON-serializable dict.

    Note:
        This serializer is for the legacy ``NexCircuit`` JSON contract only.
        It is not the canonical executable savefile writer; canonical savefiles
        must use ``src.contracts.savefile_serializer``.
    """
    return asdict(circuit)


def save_nex_file(circuit: NexCircuit, file_path: str) -> None:
    """Save legacy NexCircuit to a ``.nex`` JSON file."""
    path = Path(file_path)
    if path.suffix != ".nex":
        raise ValueError("legacy NexCircuit files must use .nex extension")

    data = serialize_nex(circuit)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
