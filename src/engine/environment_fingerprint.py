import hashlib
import json
import platform
import sys

def compute_environment_fingerprint(
    dependency_fingerprint: str = "",
    plugin_registry_fingerprint: str = "",
    provider_fingerprint: str = "",
):
    payload = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependency_fingerprint": dependency_fingerprint,
        "plugin_registry_fingerprint": plugin_registry_fingerprint,
        "provider_fingerprint": provider_fingerprint,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest(), payload