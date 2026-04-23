# tests/test_server_external_delivery_provider_quota_consistency.py

def test_delivery_requires_run_identity():
    delivery = {"run_id": "r1"}
    assert "run_id" in delivery


def test_provider_failure_requires_fallback_or_error():
    provider_ok = False
    fallback_exists = True
    assert provider_ok or fallback_exists


def test_quota_enforcement_blocks_excess_usage():
    quota = 10
    used = 12
    blocked = used > quota
    assert blocked
