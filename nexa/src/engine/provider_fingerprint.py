import hashlib
import json
from typing import Dict, Any

def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def compute_provider_fingerprint(*, config: Dict[str, Any]) -> str:
    allowed_keys = {
        "provider",
        "model",
        "endpoint",
        "temperature",
        "max_tokens",
        "adapter_version",
    }

    filtered = {}
    for k, v in config.items():
        if k in allowed_keys and v is not None:
            filtered[k] = v

    canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
    return _sha256_hex(canonical)
