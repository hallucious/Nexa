from __future__ import annotations

from src.server.provider_catalog_runtime import (
    default_provider_model_catalog_rows,
    evaluate_provider_model_access_for_artifact,
    extract_provider_model_requirements,
    provider_catalog_rows_from_model_catalog,
    provider_cost_catalog_rows_from_model_catalog,
    resolve_default_model_for_provider,
    resolve_provider_model_access,
    resolve_provider_model_cost,
)


def _source_with_provider(provider: str = "openai", model: str | None = "gpt-4o") -> dict:
    execution_provider = {"provider_id": f"{provider}:default", "prompt_ref": "prompt.main"}
    if model is not None:
        execution_provider["model"] = model
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "commit_snapshot", "commit_id": "snap-provider-catalog"},
        "circuit": {
            "nodes": [
                {
                    "node_id": "n-provider",
                    "kind": "provider",
                    "resource_ref": {"provider": provider, "prompt": "prompt.main"},
                    "execution": {"provider": execution_provider},
                }
            ],
            "edges": [],
            "entry": "n-provider",
            "outputs": [{"name": "result", "source": "state.working.result"}],
        },
        "resources": {
            "prompts": {"prompt.main": {"template": "Hello"}},
            "providers": {provider: {"provider_family": provider, "display_name": provider.title()}},
            "plugins": {},
        },
        "state": {"input": {}, "working": {}, "memory": {}},
    }


def test_default_provider_model_catalog_matches_batch_2b_baseline() -> None:
    rows = default_provider_model_catalog_rows()

    provider_model_keys = {row["provider_model_key"] for row in rows}
    assert provider_model_keys == {
        "anthropic:claude-haiku-3",
        "anthropic:claude-sonnet-4",
        "openai:gpt-4o",
    }

    provider_rows = provider_catalog_rows_from_model_catalog(rows)
    provider_keys = {row["provider_key"] for row in provider_rows}
    assert provider_keys == {"anthropic", "openai"}

    anthropic = next(row for row in provider_rows if row["provider_key"] == "anthropic")
    assert anthropic["default_model_ref"] == "claude-haiku-3"
    assert set(anthropic["allowed_model_refs"]) == {"claude-haiku-3", "claude-sonnet-4"}


def test_plan_access_follows_initial_saas_model_policy() -> None:
    free_haiku = resolve_provider_model_access(
        provider_key="anthropic",
        model_ref="claude-haiku-3",
        plan_key="free",
    )
    assert free_haiku.allowed is True

    free_gpt = resolve_provider_model_access(
        provider_key="openai",
        model_ref="gpt-4o",
        plan_key="free",
    )
    assert free_gpt.allowed is False
    assert free_gpt.reason_code == "provider_model_access.plan_not_allowed"

    pro_gpt = resolve_provider_model_access(
        provider_key="openai",
        model_ref="gpt-4o",
        plan_key="pro",
    )
    assert pro_gpt.allowed is True
    assert pro_gpt.cost_ratio == 3.0


def test_default_model_and_cost_lookup_are_model_level() -> None:
    default_free = resolve_default_model_for_provider("anthropic", plan_key="free")
    assert default_free is not None
    assert default_free.model_ref == "claude-haiku-3"

    cost = resolve_provider_model_cost(provider_key="openai", model_ref="gpt-4o")
    assert cost is not None
    assert cost.provider_model_key == "openai:gpt-4o"
    assert cost.cost_ratio == 3.0

    cost_rows = provider_cost_catalog_rows_from_model_catalog()
    assert any(row["provider_model_key"] == "openai:gpt-4o" and row["cost_ratio"] == 3.0 for row in cost_rows)


def test_extract_and_evaluate_artifact_provider_requirements() -> None:
    requirements = extract_provider_model_requirements(_source_with_provider("openai", "gpt-4o"))
    assert len(requirements) == 1
    assert requirements[0].provider_key == "openai"
    assert requirements[0].model_ref == "gpt-4o"

    decisions = evaluate_provider_model_access_for_artifact(
        source_payload=_source_with_provider("openai", "gpt-4o"),
        plan_key="free",
    )
    assert len(decisions) == 1
    assert decisions[0].allowed is False
    assert decisions[0].reason_code == "provider_model_access.plan_not_allowed"




def test_provider_cost_catalog_has_dedicated_incremental_migration() -> None:
    from pathlib import Path

    migration_text = Path("alembic/versions/20260424_0006_provider_cost_catalog.py").read_text()

    assert "CREATE TABLE IF NOT EXISTS provider_cost_catalog" in migration_text
    assert "provider_model_key TEXT PRIMARY KEY" in migration_text
    assert "cost_ratio NUMERIC" in migration_text
    assert "idx_provider_cost_catalog_provider_key" in migration_text
