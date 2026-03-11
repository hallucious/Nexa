from pathlib import Path
from typing import Dict, Any
import yaml

from src.circuit.circuit_schema_validator import CircuitSchemaValidator


def save_circuit(circuit: Dict[str, Any], path: str):

    file_path = Path(path)

    if file_path.suffix != ".nex":
        raise ValueError("circuit file must use .nex extension")

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(circuit, f, sort_keys=False)


def load_circuit(path: str) -> Dict[str, Any]:

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(path)

    if file_path.suffix != ".nex":
        raise ValueError("circuit file must use .nex extension")

    with open(file_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    return CircuitSchemaValidator(loaded).validate()