from pathlib import Path

from src.cli.nexa_cli import resolve_output_path


def test_resolve_output_path_filename_only_goes_to_circuit_runs_dir(tmp_path: Path, monkeypatch):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    monkeypatch.chdir(tmp_path)

    resolved = resolve_output_path('run_a.json', str(nex_path))

    assert resolved == (nex_dir / 'runs' / 'run_a.json').resolve()
    assert resolved.parent == (nex_dir / 'runs').resolve()


def test_resolve_output_path_custom_path_is_preserved(tmp_path: Path, monkeypatch):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    monkeypatch.chdir(tmp_path)

    resolved = resolve_output_path('outputs/run_a.json', str(nex_path))

    assert resolved == (tmp_path / 'outputs' / 'run_a.json').resolve()
    assert (tmp_path / 'outputs').exists()


def test_resolve_output_path_avoids_overwriting_existing_file(tmp_path: Path, monkeypatch):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    monkeypatch.chdir(tmp_path)

    runs_dir = nex_dir / 'runs'
    runs_dir.mkdir(parents=True, exist_ok=True)
    existing = runs_dir / 'run_a.json'
    existing.write_text('{}', encoding='utf-8')

    resolved = resolve_output_path('run_a.json', str(nex_path))

    assert resolved == (runs_dir / 'run_a__1.json').resolve()


def test_resolve_output_path_uses_next_available_suffix(tmp_path: Path, monkeypatch):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    monkeypatch.chdir(tmp_path)

    runs_dir = nex_dir / 'runs'
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / 'run_a.json').write_text('{}', encoding='utf-8')
    (runs_dir / 'run_a__1.json').write_text('{}', encoding='utf-8')

    resolved = resolve_output_path('run_a.json', str(nex_path))

    assert resolved == (runs_dir / 'run_a__2.json').resolve()
