from __future__ import annotations

import importlib
import inspect
import pkgutil


def test_engine_cli_importable():
    mod = importlib.import_module("src.engine.cli")
    assert mod is not None


def test_pipeline_cli_is_shim():
    mod = importlib.import_module("src.pipeline.cli")
    src = inspect.getsource(mod)
    assert "src.legacy.pipeline.cli" in src


def test_engine_does_not_import_legacy():
    engine_pkg = importlib.import_module("src.engine")
    for _, modname, _ in pkgutil.walk_packages(engine_pkg.__path__, engine_pkg.__name__ + "."):
        mod = importlib.import_module(modname)
        try:
            src = inspect.getsource(mod)
        except (OSError, TypeError):
            continue
        assert "src.legacy" not in src, f"Engine must not depend on legacy: {modname}"
