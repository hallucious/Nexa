from src.engine.environment_fingerprint import compute_environment_fingerprint

def test_environment_fingerprint_deterministic():
    fp1, _ = compute_environment_fingerprint("a","b","c")
    fp2, _ = compute_environment_fingerprint("a","b","c")
    assert fp1 == fp2

def test_environment_fingerprint_changes():
    fp1, _ = compute_environment_fingerprint("a","b","c")
    fp2, _ = compute_environment_fingerprint("x","b","c")
    assert fp1 != fp2