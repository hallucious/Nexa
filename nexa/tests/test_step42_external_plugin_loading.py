from __future__ import annotations

from pathlib import Path

from src.platform.external_loader import load_external_injections


def test_step42_external_plugin_loading_injects_providers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugins_dir = repo / "plugins"
    plugins_dir.mkdir(parents=True)

    (repo / "src").mkdir()
    (repo / "tests").mkdir()

    # External plugin module.
    (plugins_dir / "myprov.py").write_text(
        """PLUGIN_ID = 'myprov'
def register(*, providers, plugins, context):
    providers['demo'] = object()
""",
        encoding="utf-8",
    )

    ctx, prov, plg = load_external_injections(repo, plugins_dir=plugins_dir)
    assert 'demo' in prov
    assert ctx == {}
    assert plg == {}


def test_step42_external_plugin_loading_rejects_conflicts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugins_dir = repo / "plugins"
    plugins_dir.mkdir(parents=True)

    (repo / "src").mkdir()
    (repo / "tests").mkdir()

    (plugins_dir / "a.py").write_text(
        """def register(*, providers, plugins, context):
    providers['demo'] = 1
""",
        encoding="utf-8",
    )
    (plugins_dir / "b.py").write_text(
        """def register(*, providers, plugins, context):
    providers['demo'] = 2
""",
        encoding="utf-8",
    )

    try:
        load_external_injections(repo, plugins_dir=plugins_dir)
        assert False, "Expected conflict error"
    except ValueError as e:
        assert "override existing providers key" in str(e)
