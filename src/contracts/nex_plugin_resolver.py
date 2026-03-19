from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path


@dataclass
class PluginResolutionResult:
    found: List[str]
    missing_required: List[str]
    missing_optional: List[str]
    version_mismatch: List[str]


def scan_plugins_dir(plugins_dir: Path) -> Dict[str, Path]:
    if not plugins_dir.exists():
        return {}
    return {p.name: p for p in plugins_dir.iterdir() if p.is_dir()}


def resolve_plugins(plugin_refs, plugins_dir: Path) -> PluginResolutionResult:
    available = scan_plugins_dir(plugins_dir)

    found = []
    missing_required = []
    missing_optional = []
    version_mismatch = []

    for ref in plugin_refs:
        pid = ref.get("plugin_id")
        required = ref.get("required", True)

        if pid in available:
            found.append(pid)
        else:
            if required:
                missing_required.append(pid)
            else:
                missing_optional.append(pid)

    return PluginResolutionResult(
        found=found,
        missing_required=missing_required,
        missing_optional=missing_optional,
        version_mismatch=version_mismatch,
    )
