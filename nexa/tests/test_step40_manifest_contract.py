from __future__ import annotations

from pathlib import Path

import pytest

from src.platform.plugin_discovery import discover_platform_plugins, load_platform_plugin_manifests


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        if (parent / "src").exists() and (parent / "tests").exists():
            return parent
    return Path.cwd()


def test_step40_all_manifests_load_and_validate() -> None:
    repo = _repo_root()
    manifests = load_platform_plugin_manifests(repo)

    manifest_ids = {m.plugin_id for m in manifests}
    discovered_ids = {p.plugin_id for p in discover_platform_plugins(repo)}
    assert manifest_ids == discovered_ids


def test_step40_duplicate_injection_rejected() -> None:
    # Lightweight unit-style test for uniqueness rule.
    repo = _repo_root()
    manifests = load_platform_plugin_manifests(repo)
    inject_pairs = [(m.inject_target, m.inject_key) for m in manifests if m.inject_target != "providers"]
    assert len(inject_pairs) == len(set(inject_pairs))
