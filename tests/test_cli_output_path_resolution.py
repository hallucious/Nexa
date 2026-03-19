from pathlib import Path

from src.cli.nexa_cli import resolve_output_path


def test_resolve_output_path_filename_only_goes_to_nex_runs(tmp_path: Path):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    resolved = resolve_output_path('run_a.json', str(nex_path))

    assert resolved == nex_dir / 'runs' / 'run_a.json'
    assert (nex_dir / 'runs').exists()


def test_resolve_output_path_custom_path_is_preserved(tmp_path: Path):
    nex_dir = tmp_path / "examples" / "real_ai_bug_autopsy"
    nex_dir.mkdir(parents=True)
    nex_path = nex_dir / "run_a.nex"
    nex_path.write_text('id: x\n', encoding='utf-8')

    resolved = resolve_output_path('outputs/run_a.json', str(nex_path))

    assert resolved == Path('outputs/run_a.json')
