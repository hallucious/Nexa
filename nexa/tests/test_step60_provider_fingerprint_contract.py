from src.engine.provider_fingerprint import compute_provider_fingerprint

def test_provider_fingerprint_deterministic():
    config = {
        "provider": "openai",
        "model": "gpt-4.1",
        "temperature": 0.7,
    }
    fp1 = compute_provider_fingerprint(config=config)
    fp2 = compute_provider_fingerprint(config=config)
    assert fp1 == fp2

def test_provider_fingerprint_order_invariant():
    c1 = {"provider": "openai", "model": "gpt-4.1"}
    c2 = {"model": "gpt-4.1", "provider": "openai"}
    assert compute_provider_fingerprint(config=c1) == compute_provider_fingerprint(config=c2)

def test_provider_fingerprint_changes_on_model():
    c1 = {"provider": "openai", "model": "gpt-4.1"}
    c2 = {"provider": "openai", "model": "gpt-4.2"}
    assert compute_provider_fingerprint(config=c1) != compute_provider_fingerprint(config=c2)

def test_provider_fingerprint_changes_on_temperature():
    c1 = {"provider": "openai", "model": "gpt-4.1", "temperature": 0.5}
    c2 = {"provider": "openai", "model": "gpt-4.1", "temperature": 0.9}
    assert compute_provider_fingerprint(config=c1) != compute_provider_fingerprint(config=c2)
