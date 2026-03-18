import pytest

from src.platform.plugin_auto_loader import (
    PluginAutoLoaderError,
    _validate_plugin,
)


def test_plugin_callable_short_form():
    def plugin_fn():
        return {"ok": True}

    plugin = _validate_plugin("test.plugin", plugin_fn, "test.py")

    assert plugin.plugin_id == "test.plugin"
    assert plugin.version == "1.0.0"
    assert plugin.description == ""
    assert callable(plugin)
    assert plugin() == {"ok": True}


def test_plugin_dict_form():
    def plugin_fn():
        return {"ok": True}

    plugin = _validate_plugin(
        "test.plugin",
        {
            "callable": plugin_fn,
            "version": "2.0.0",
            "description": "test plugin",
        },
        "test.py",
    )

    assert plugin.plugin_id == "test.plugin"
    assert plugin.version == "2.0.0"
    assert plugin.description == "test plugin"
    assert callable(plugin)
    assert plugin() == {"ok": True}


def test_plugin_invalid_callable():
    with pytest.raises(PluginAutoLoaderError):
        _validate_plugin(
            "test.plugin",
            {"callable": "not callable"},
            "test.py",
        )