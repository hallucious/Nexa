from src.engine.engine import Engine
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.engine.types import NodeStatus


class _FakeProvider:
    def execute(self, prompt: str):
        return {"output": {"answer": "ok", "prompt": prompt}, "trace": {"provider": "fake"}}


def test_step116_engine_delegates_to_node_runtime_when_no_handler(tmp_path):
    runtime = NodeExecutionRuntime(provider_execution=_FakeProvider(), observability_file=str(tmp_path / "obs.jsonl"))

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={},  # no handler => should delegate
        node_runtime=runtime,
    )

    trace = eng.execute(revision_id="rev116")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].output_snapshot == {"answer": "ok", "prompt": ""}  # entry input is empty => prompt ''
