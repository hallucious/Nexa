import hashlib
from typing import Dict, Any
from .canonicalize import canonicalize_definition


def compute_circuit_fingerprint(data: Dict[str, Any]) -> str:
    canonical = canonicalize_definition(data)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _normalize_execution_surface(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    surface: Dict[str, Any] = {}

    if "circuit" in data or "resources" in data or "execution_configs" in data or "configs" in data:
        circuit = data.get("circuit") if isinstance(data.get("circuit"), dict) else {}
        surface["circuit"] = {
            "nodes": circuit.get("nodes", data.get("nodes", [])),
            "edges": circuit.get("edges", data.get("edges", [])),
            "entry": circuit.get("entry", data.get("entry")),
            "outputs": circuit.get("outputs", data.get("outputs", [])),
        }
        if isinstance(data.get("resources"), dict):
            surface["resources"] = data.get("resources")
        if isinstance(data.get("execution_configs"), dict):
            surface["execution_configs"] = data.get("execution_configs")
        elif isinstance(data.get("configs"), dict):
            surface["configs"] = data.get("configs")
        return surface

    surface["circuit"] = {
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "entry": data.get("entry"),
        "outputs": data.get("outputs", []),
    }
    if isinstance(data.get("resources"), dict):
        surface["resources"] = data.get("resources")
    if isinstance(data.get("execution_configs"), dict):
        surface["execution_configs"] = data.get("execution_configs")
    elif isinstance(data.get("configs"), dict):
        surface["configs"] = data.get("configs")
    return surface


def compute_execution_surface_fingerprint(data: Dict[str, Any]) -> str:
    canonical = canonicalize_definition(_normalize_execution_surface(data))
    return hashlib.sha256(canonical.encode()).hexdigest()
