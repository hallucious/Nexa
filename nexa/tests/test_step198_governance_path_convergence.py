from src.circuit.circuit_runner import CircuitRunner
from src.engine.engine import Engine


class _SimpleRegistry:
    def __init__(self, configs=None):
        self._configs = configs or {}

    def get(self, config_id):
        return self._configs.get(config_id)

    def register(self, config):
        self._configs[config["config_id"]] = config


class _SimpleRuntime:
    def __init__(self, outputs=None):
        self._outputs = outputs or {}

    def execute_by_config_id(self, registry, config_id, state):
        class R:
            def __init__(self, output):
                self.output = output

        return R(self._outputs.get(config_id, f"out:{config_id}"))


def _registry():
    registry = _SimpleRegistry()
    registry.register({"config_id": "cfg.a"})
    return registry


def _valid_circuit():
    return {"id": "tc", "nodes": [{"id": "n_a", "execution_config_ref": "cfg.a"}]}


def test_step198_circuit_governance_exposes_engine_shaped_meta():
    runner = CircuitRunner(_SimpleRuntime({"cfg.a": "ok"}), _registry())
    result = runner.execute(_valid_circuit(), {})

    engine_meta = result.governance.to_engine_meta()

    assert set(engine_meta.keys()) == {"pre_validation", "post_validation", "decision"}
    assert engine_meta["pre_validation"]["structural"]["performed"] is True
    assert engine_meta["pre_validation"]["determinism"]["performed"] is False
    assert engine_meta["post_validation"]["performed"] is True
    assert engine_meta["post_validation"]["strict_mode"] is False
    assert engine_meta["decision"]["pre"]["value"] == "CONTINUE"
    assert engine_meta["decision"]["post"]["value"] in {"ACCEPT", "WARN"}


def test_step198_circuit_to_dict_preserves_legacy_fields_and_adds_decision_block():
    runner = CircuitRunner(_SimpleRuntime({"cfg.a": "ok"}), _registry())
    result = runner.execute(_valid_circuit(), {})

    payload = result.governance.to_dict()

    assert "pre_decision" in payload
    assert "post_decision" in payload
    assert "decision" in payload
    assert payload["decision"]["pre"]["value"] == payload["pre_decision"]["value"]
    assert payload["decision"]["post"]["value"] == payload["post_decision"]["value"]


def test_step198_engine_and_circuit_governance_share_same_decision_shape_on_success():
    engine = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": lambda state: {"ok": True}},
    )
    engine_trace = engine.execute(revision_id="step198")

    runner = CircuitRunner(_SimpleRuntime({"cfg.a": "ok"}), _registry())
    circuit_result = runner.execute(_valid_circuit(), {})
    circuit_meta = circuit_result.governance.to_engine_meta()

    assert set(engine_trace.meta["decision"].keys()) == {"pre", "post"}
    assert engine_trace.meta["decision"].keys() == circuit_meta["decision"].keys()
    assert engine_trace.meta["pre_validation"]["structural"].keys() == circuit_meta["pre_validation"]["structural"].keys()
    assert engine_trace.meta["post_validation"].keys() == circuit_meta["post_validation"].keys()
    assert engine_trace.meta["decision"]["pre"]["value"] == circuit_meta["decision"]["pre"]["value"] == "CONTINUE"
