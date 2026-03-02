from pathlib import Path

from src.engine.environment_fingerprint import compute_dependency_fingerprint


def test_dependency_fingerprint_deterministic(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("a==1\nb==2\n", encoding="utf-8")
    fp1 = compute_dependency_fingerprint(repo_root=tmp_path)
    fp2 = compute_dependency_fingerprint(repo_root=tmp_path)
    assert fp1 == fp2


def test_dependency_fingerprint_order_invariant(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("b==2\na==1\n", encoding="utf-8")
    fp1 = compute_dependency_fingerprint(repo_root=tmp_path)
    (tmp_path / "requirements.txt").write_text("a==1\nb==2\n", encoding="utf-8")
    fp2 = compute_dependency_fingerprint(repo_root=tmp_path)
    assert fp1 == fp2


def test_dependency_fingerprint_changes_on_content(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("a==1\n", encoding="utf-8")
    fp1 = compute_dependency_fingerprint(repo_root=tmp_path)
    (tmp_path / "requirements.txt").write_text("a==2\n", encoding="utf-8")
    fp2 = compute_dependency_fingerprint(repo_root=tmp_path)
    assert fp1 != fp2


def test_dependency_fingerprint_missing_is_deterministic(tmp_path: Path):
    fp1 = compute_dependency_fingerprint(repo_root=tmp_path)
    fp2 = compute_dependency_fingerprint(repo_root=tmp_path)
    assert fp1 == fp2
