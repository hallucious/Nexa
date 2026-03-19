
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class PluginResolutionResult:
    found: List[str]
    missing_required: List[str]
    missing_optional: List[str]
    version_mismatch: List[str]


def _load_plugin_metadata(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Best-effort metadata loader.

    Compatibility rule:
    - v1 plugins may exist as a bare folder with no plugin.json
    - v2 plugins may include plugin.json and will be validated when present
    """
    meta_file = plugin_dir / "plugin.json"
    if not meta_file.exists():
        return None

    data = json.loads(meta_file.read_text(encoding="utf-8"))

    required_fields = ["plugin_id", "version", "entrypoint", "type"]
    for field in required_fields:
        if field not in data:
            raise RuntimeError(f"Missing field '{field}' in {meta_file}")

    if data["plugin_id"] != plugin_dir.name:
        raise RuntimeError(
            f"plugin_id mismatch: {data['plugin_id']} != {plugin_dir.name}"
        )

    return data


def scan_plugins_dir(plugins_dir: Path) -> Dict[str, Dict[str, Any]]:
    if not plugins_dir.exists():
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for p in plugins_dir.iterdir():
        if not p.is_dir():
            continue

        metadata = _load_plugin_metadata(p)
        if metadata is None:
            metadata = {
                "plugin_id": p.name,
                "version": None,
                "entrypoint": None,
                "type": "legacy",
            }

        result[p.name] = metadata

    return result


def resolve_plugins(plugin_refs, plugins_dir: Path) -> PluginResolutionResult:
    available = scan_plugins_dir(plugins_dir)

    found: List[str] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []
    version_mismatch: List[str] = []

    for ref in plugin_refs:
        pid = ref.get("plugin_id")
        required = ref.get("required", True)
        expected_version = ref.get("version")

        if pid not in available:
            if required:
                missing_required.append(pid)
            else:
                missing_optional.append(pid)
            continue

        actual_version = available[pid].get("version")

        # Backward compatibility:
        # If plugin metadata is absent (legacy folder-only plugin), do not fail version match.
        if expected_version and actual_version is not None and expected_version != actual_version:
            version_mismatch.append(f"{pid}:{expected_version}!={actual_version}")
            continue

        found.append(pid)

    return PluginResolutionResult(
        found=found,
        missing_required=missing_required,
        missing_optional=missing_optional,
        version_mismatch=version_mismatch,
    )
