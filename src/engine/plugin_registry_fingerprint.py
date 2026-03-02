import hashlib
from pathlib import Path
from typing import Dict

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def compute_plugin_registry_fingerprint(*, plugins: Dict[str, Path]) -> str:
    entries = []
    for plugin_id, path in plugins.items():
        if not path.exists():
            continue
        content = path.read_bytes()
        file_hash = _sha256_hex(content)
        entries.append(f"{plugin_id}:{file_hash}")
    entries.sort()
    joined = "\n".join(entries).encode()
    return _sha256_hex(joined)
