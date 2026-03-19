from __future__ import annotations

import json
from dataclasses import asdict

from src.contracts.nex_format import NexCircuit


def serialize_nex(circuit: NexCircuit) -> dict:
    """Convert NexCircuit dataclass into JSON-serializable dict"""
    return asdict(circuit)


def save_nex_file(circuit: NexCircuit, file_path: str) -> None:
    """Save NexCircuit to .nex file (JSON format)"""
    data = serialize_nex(circuit)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
