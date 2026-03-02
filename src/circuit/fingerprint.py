import hashlib
from typing import Dict, Any
from .canonicalize import canonicalize_definition


def compute_circuit_fingerprint(data: Dict[str, Any]) -> str:
    canonical = canonicalize_definition(data)
    return hashlib.sha256(canonical.encode()).hexdigest()
