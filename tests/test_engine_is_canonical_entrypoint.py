from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path


def test_engine_cli_importable():
    mod = importlib.import_module("src.engine.cli")
    assert mod is not None


def test_public_cli_entrypoint_is_nexa_cli():
    project_root = Path(__file__).resolve().parents[1]
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    launcher = (project_root / "nexa.py").read_text(encoding="utf-8")

    assert 'nexa = "src.cli.nexa_cli:main"' in pyproject
    assert 'from src.cli.nexa_cli import main' in launcher


def test_engine_cli_is_compatibility_wrapper_for_public_cli():
    mod = importlib.import_module("src.engine.cli")
    assert getattr(mod, "CANONICAL_PUBLIC_CLI") == "src.cli.nexa_cli:main"


def test_engine_does_not_import_legacy():
    """Engine must remain isolated from any legacy or pipeline modules."""
    engine_pkg = importlib.import_module("src.engine")
    for _, modname, _ in pkgutil.walk_packages(engine_pkg.__path__, engine_pkg.__name__ + "."):
        mod = importlib.import_module(modname)
        try:
            src = inspect.getsource(mod)
        except (OSError, TypeError):
            continue
        assert "src.legacy" not in src, f"Engine must not depend on legacy: {modname}"
        assert "src.pipeline" not in src, f"Engine must not depend on pipeline: {modname}"
        assert "src.gates" not in src, f"Engine must not depend on gates: {modname}"


def test_legacy_pipeline_package_is_absent():
    """Legacy src.pipeline package must be gone — engine is the only entrypoint."""
    try:
        importlib.import_module("src.pipeline")
        raise AssertionError("src.pipeline must not exist after legacy removal")
    except ModuleNotFoundError:
        pass  # expected
