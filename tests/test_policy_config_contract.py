import pytest

from src.contracts.policy_config_contract import (
    validate_policy_config,
    PolicyConfigError,
)


def test_valid_config():
    cfg = {
        "version": "1.0",
        "overrides": {"NODE_SUCCESS_TO_FAILURE": "MEDIUM"},
    }
    result = validate_policy_config(cfg)
    assert result["NODE_SUCCESS_TO_FAILURE"] == "MEDIUM"


def test_invalid_version():
    with pytest.raises(PolicyConfigError):
        validate_policy_config({"version": "2.0"})


def test_invalid_severity():
    with pytest.raises(PolicyConfigError):
        validate_policy_config(
            {
                "version": "1.0",
                "overrides": {"X": "INVALID"},
            }
        )


def test_overrides_not_dict():
    with pytest.raises(PolicyConfigError):
        validate_policy_config(
            {
                "version": "1.0",
                "overrides": [],
            }
        )
