from pathlib import Path
from src.engine.plugin_registry_fingerprint import compute_plugin_registry_fingerprint

def test_plugin_registry_order_invariant(tmp_path: Path):
    p1 = tmp_path / "a.py"
    p2 = tmp_path / "b.py"
    p1.write_text("x", encoding="utf-8")
    p2.write_text("y", encoding="utf-8")

    plugins1 = {"A": p1, "B": p2}
    plugins2 = {"B": p2, "A": p1}

    fp1 = compute_plugin_registry_fingerprint(plugins=plugins1)
    fp2 = compute_plugin_registry_fingerprint(plugins=plugins2)

    assert fp1 == fp2

def test_plugin_registry_change_detected(tmp_path: Path):
    p1 = tmp_path / "a.py"
    p1.write_text("x", encoding="utf-8")
    plugins = {"A": p1}
    fp1 = compute_plugin_registry_fingerprint(plugins=plugins)

    p1.write_text("z", encoding="utf-8")
    fp2 = compute_plugin_registry_fingerprint(plugins=plugins)

    assert fp1 != fp2
