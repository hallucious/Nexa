from __future__ import annotations

import pytest

from src.circuit.node_execution import run_node_stages


def test_run_node_stages_subcircuit_uses_runner_and_binds_outputs() -> None:
    calls = []

    def _runner(*, node_id, child_circuit_ref, child_input, runtime_policy, node_raw):
        calls.append({
            "node_id": node_id,
            "child_circuit_ref": child_circuit_ref,
            "child_input": child_input,
            "runtime_policy": runtime_policy,
        })
        return {
            "status": "success",
            "output": {
                "result": f"review:{child_input['question']}",
                "confidence": 0.8,
            },
        }

    out = run_node_stages(
        node_id="review_stage",
        node_raw={
            "kind": "subcircuit",
            "execution": {
                "subcircuit": {
                    "child_circuit_ref": "internal:review_bundle",
                    "input_mapping": {
                        "question": "input.question",
                        "draft": "node.draft.output.result",
                    },
                    "output_binding": {
                        "result": "child.output.result",
                        "confidence": "child.output.confidence",
                    },
                    "runtime_policy": {"max_child_depth": 2},
                }
            },
        },
        input_payload={
            "input": {"question": "What is safer?"},
            "__node_outputs__": {"draft": {"result": "Draft A"}},
            "__subcircuit_runner__": _runner,
        },
        handler=lambda *_args, **_kwargs: {"unused": True},
    )

    assert out == {"result": "review:What is safer?", "confidence": 0.8}
    assert calls == [
        {
            "node_id": "review_stage",
            "child_circuit_ref": "internal:review_bundle",
            "child_input": {"question": "What is safer?", "draft": "Draft A"},
            "runtime_policy": {"max_child_depth": 2},
        }
    ]


def test_run_node_stages_subcircuit_raises_on_child_failure() -> None:
    def _runner(**_kwargs):
        return {"status": "failure", "error": "Child subcircuit execution failed"}

    with pytest.raises(RuntimeError, match="Child subcircuit execution failed"):
        run_node_stages(
            node_id="review_stage",
            node_raw={
                "kind": "subcircuit",
                "execution": {
                    "subcircuit": {
                        "child_circuit_ref": "internal:review_bundle",
                        "input_mapping": {"question": "input.question"},
                        "output_binding": {"result": "child.output.result"},
                    }
                },
            },
            input_payload={
                "input": {"question": "What is safer?"},
                "__subcircuit_runner__": _runner,
            },
            handler=lambda *_args, **_kwargs: {"unused": True},
        )


def test_run_node_stages_subcircuit_rejects_invalid_binding_target() -> None:
    with pytest.raises(ValueError, match="Invalid subcircuit output binding target"):
        run_node_stages(
            node_id="review_stage",
            node_raw={
                "kind": "subcircuit",
                "execution": {
                    "subcircuit": {
                        "child_circuit_ref": "internal:review_bundle",
                        "input_mapping": {"question": "input.question"},
                        "output_binding": {"result": "provider.output"},
                    }
                },
            },
            input_payload={"input": {"question": "Q"}},
            handler=lambda *_args, **_kwargs: {"unused": True},
        )


def test_run_node_stages_subcircuit_raises_when_child_output_missing() -> None:
    def _runner(**_kwargs):
        return {"status": "success", "output": {"other": 1}}

    with pytest.raises(KeyError, match="Missing child output for binding"):
        run_node_stages(
            node_id="review_stage",
            node_raw={
                "kind": "subcircuit",
                "execution": {
                    "subcircuit": {
                        "child_circuit_ref": "internal:review_bundle",
                        "input_mapping": {"question": "input.question"},
                        "output_binding": {"result": "child.output.result"},
                    }
                },
            },
            input_payload={
                "input": {"question": "Q"},
                "__subcircuit_runner__": _runner,
            },
            handler=lambda *_args, **_kwargs: {"unused": True},
        )
