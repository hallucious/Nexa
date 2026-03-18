import copy

from src.engine.execution_config_hash import (
    canonicalize_execution_config_json,
    compute_execution_config_hash,
    generate_execution_config_id,
)


def test_step121_hash_ignores_human_metadata_and_version():
    base = {
        "config_schema_version": "1",
        "prompt_ref": "prompt.basic.v1",
        "provider_ref": "openai.gpt4",
        "pre_plugins": [],
        "post_plugins": [],
        "validation_rules": [],
        "output_mapping": {},
        "policy": {},
        "runtime_config": {
            "execution": {"temperature": 0.2},
            "metadata": {"note": "baseline"},
        },
        "config_id": "ec_old",
        "label": "old label",
        "version": "1.0.0",
    }
    other = copy.deepcopy(base)
    other["config_id"] = "ec_new"
    other["label"] = "new label"
    other["version"] = "9.9.9"
    other["runtime_config"]["metadata"]["note"] = "changed"

    assert compute_execution_config_hash(base) == compute_execution_config_hash(other)
    assert generate_execution_config_id(base) == generate_execution_config_id(other)


def test_step121_hash_changes_when_execution_meaning_changes():
    base = {
        "prompt_ref": "prompt.basic.v1",
        "provider_ref": "openai.gpt4",
        "runtime_config": {"execution": {"temperature": 0.2}},
    }
    changed = copy.deepcopy(base)
    changed["runtime_config"]["execution"]["temperature"] = 0.8

    assert compute_execution_config_hash(base) != compute_execution_config_hash(changed)


def test_step121_canonical_json_is_stable_for_key_order_and_nulls():
    a = {
        "provider_ref": "openai.gpt4",
        "prompt_ref": "prompt.basic.v1",
        "runtime_config": {"execution": {"temperature": 0.2}, "metadata": {"note": "x"}},
        "label": "x",
        "notes": None,
    }
    b = {
        "label": "y",
        "runtime_config": {"metadata": {"note": "y"}, "execution": {"temperature": 0.2}},
        "prompt_ref": "prompt.basic.v1",
        "provider_ref": "openai.gpt4",
        "created_at": "today",
    }

    assert canonicalize_execution_config_json(a) == canonicalize_execution_config_json(b)
