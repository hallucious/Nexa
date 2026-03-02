import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_dependency_fingerprint(*, repo_root: Path) -> str:
    req = repo_root / "requirements.txt"
    if not req.exists():
        return _sha256_hex("")

    raw = req.read_text(encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        lines.append(s)

    lines.sort()
    canonical = "\n".join(lines)
    return _sha256_hex(canonical)


def compute_environment_fingerprint(
    dependency_fingerprint: str = "",
    plugin_registry_fingerprint: str = "",
    provider_fingerprint: str = "",
    *,
    repo_root: Optional[Path] = None,
) -> Tuple[str, Dict[str, str]]:
    # Backward compatible: if repo_root is provided and dependency_fingerprint is empty,
    # compute it from requirements.txt.
    if repo_root is not None and dependency_fingerprint == "":
        dependency_fingerprint = compute_dependency_fingerprint(repo_root=repo_root)

    payload: Dict[str, str] = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependency_fingerprint": dependency_fingerprint,
        "plugin_registry_fingerprint": plugin_registry_fingerprint,
        "provider_fingerprint": provider_fingerprint,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_hex(canonical), payload
