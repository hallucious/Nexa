import pytest


class _FakeResolver:
    def __init__(self):
        self.called = False

    class _Config:
        config_id = "ec_testhash"
        version = "1.0.0"
        config_schema_version = "1"
        label = None
        inputs = {}
        pre_plugins = []
        prompt_ref = None
        provider_ref = None
        post_plugins = []
        validation_rules = []
        output_mapping = {}
        policy = {}
        runtime_config = {}

    def resolve(self, node):
        self.called = True
        return self._Config()


class _FakeNodeResult:
    def __init__(self, node_id):
        self.node_id = node_id
        self.output = {"ok": True}
        self.artifacts = []
        self.trace = None


class _FakeNodeRuntime:
    def __init__(self):
        self.last_node = None

    def execute(self, node, state):
        self.last_node = node
        return _FakeNodeResult(getattr(node, "config_id", None) or node.get("id"))


def test_step128_execution_config_ref_bridge():
    from src.engine.graph_execution_runtime import GraphExecutionRuntime

    runtime = _FakeNodeRuntime()
    resolver = _FakeResolver()
    engine = GraphExecutionRuntime(runtime, node_spec_resolver=resolver)

    circuit = {
        "nodes": [
            {
                "id": "n1",
                "execution_config_ref": "ec_testhash"
            }
        ],
        "edges": []
    }

    result = engine.execute(circuit, state={})

    assert resolver.called is True
    assert result.trace.node_sequence == ["n1"]
    assert runtime.last_node.config_id == "ec_testhash"
