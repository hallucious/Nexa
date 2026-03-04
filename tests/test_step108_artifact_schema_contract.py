from src.engine.node_execution_runtime import NodeExecutionRuntime, Artifact
from pathlib import Path


class DummyProviderExecution:
    def execute(self, prompt):
        return {
            "output": f"echo:{prompt}",
            "trace": {"provider": "dummy"}
        }


def test_step108_artifact_schema(tmp_path):
    obs = tmp_path / "OBSERVABILITY.jsonl"

    runtime = NodeExecutionRuntime(
        provider_execution=DummyProviderExecution(),
        observability_file=str(obs),
    )

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert len(result.artifacts) == 1

    art = result.artifacts[0]
    assert isinstance(art, Artifact)
    assert art.type == "provider_output"
    assert art.name == "primary_output"
    assert art.producer_node == "n1"