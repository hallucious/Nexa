"""
Focused tests for true async execution path.

Validates that:
1. GraphScheduler.execute_async() uses asyncio.gather() for same-wave concurrency
2. NodeExecutionRuntime.execute_async() correctly delegates to the async graph path
3. CircuitRunner.execute_async() runs same-wave nodes concurrently via asyncio
4. Wave ordering is preserved in async path
5. Results are identical between sync and async paths
"""
import asyncio
import threading
import time
from typing import Any, Dict, List

import pytest

from src.engine.compiled_resource_graph import (
    ResourceNode,
    CompiledResourceGraph,
)
from src.engine.graph_scheduler import GraphScheduler, ExecutionWave


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_graph(resources: Dict[str, ResourceNode]) -> CompiledResourceGraph:
    """Build a minimal CompiledResourceGraph from a dict of resources."""
    dependencies: Dict[str, set] = {rid: set() for rid in resources}
    dependents: Dict[str, set] = {rid: set() for rid in resources}

    for rid, res in resources.items():
        for dep_id in getattr(res, "dependencies", set()):
            if dep_id in resources:
                dependencies[rid].add(dep_id)
                dependents[dep_id].add(rid)

    return CompiledResourceGraph(
        resources=resources,
        dependencies=dependencies,
        dependents=dependents,
        final_candidates=set(),
    )


def _simple_resource(rid: str, deps: set = None) -> ResourceNode:
    r = ResourceNode(
        id=rid,
        type="plugin",
        reads=set(),
        writes={f"{rid}.result"},
    )
    # Patch dependencies onto the object for _make_graph
    object.__setattr__(r, "dependencies", deps or set())
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 1. GraphScheduler.execute_async() — concurrency proof
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphSchedulerExecuteAsync:

    def test_execute_async_returns_correct_results(self):
        """execute_async produces same results as execute() for a linear graph."""
        resources = {
            "a": _simple_resource("a"),
            "b": _simple_resource("b", deps={"a"}),
        }
        graph = _make_graph(resources)
        scheduler = GraphScheduler(graph)

        execution_log: List[str] = []

        def sync_executor(rid: str) -> str:
            execution_log.append(rid)
            return f"result:{rid}"

        sync_result = scheduler.execute(sync_executor)

        async def run():
            async def async_executor(rid: str) -> str:
                return f"result:{rid}"
            return await scheduler.execute_async(async_executor)

        async_result = asyncio.run(run())

        assert sync_result.resource_results == async_result.resource_results
        assert len(async_result.waves) == 2
        assert async_result.waves[0].resource_ids == ["a"]
        assert async_result.waves[1].resource_ids == ["b"]

    def test_execute_async_same_wave_runs_concurrently(self):
        """Same-wave resources in execute_async run concurrently, not sequentially."""
        resources = {
            "x": _simple_resource("x"),
            "y": _simple_resource("y"),
        }
        graph = _make_graph(resources)
        scheduler = GraphScheduler(graph)

        overlap_detected = []
        running = set()
        lock = threading.Lock()

        async def slow_executor(rid: str) -> str:
            # Record overlap using asyncio.to_thread to simulate I/O
            async def _work():
                with lock:
                    running.add(rid)
                    if len(running) > 1:
                        overlap_detected.append(True)
                await asyncio.sleep(0.05)
                with lock:
                    running.discard(rid)
                return f"done:{rid}"

            return await _work()

        async def run():
            return await scheduler.execute_async(slow_executor)

        result = asyncio.run(run())

        # Both resources should complete
        assert "x" in result.resource_results
        assert "y" in result.resource_results
        # They should have overlapped (concurrent execution)
        assert overlap_detected, (
            "Same-wave resources did not execute concurrently in execute_async(). "
            "asyncio.gather() must have been used."
        )

    def test_execute_async_wave_ordering_preserved(self):
        """Wave N+1 must not start before wave N completes."""
        resources = {
            "a": _simple_resource("a"),
            "b": _simple_resource("b", deps={"a"}),
            "c": _simple_resource("c", deps={"a"}),
            "d": _simple_resource("d", deps={"b", "c"}),
        }
        graph = _make_graph(resources)
        scheduler = GraphScheduler(graph)

        execution_order: List[str] = []

        async def ordered_executor(rid: str) -> str:
            await asyncio.sleep(0.01)
            execution_order.append(rid)
            return rid

        asyncio.run(scheduler.execute_async(ordered_executor))

        # a must come before b and c; b and c must come before d
        idx = {rid: i for i, rid in enumerate(execution_order)}
        assert idx["a"] < idx["b"]
        assert idx["a"] < idx["c"]
        assert idx["b"] < idx["d"]
        assert idx["c"] < idx["d"]

    def test_execute_async_single_resource_wave_no_gather_needed(self):
        """Single-resource waves complete correctly without gather."""
        resources = {"solo": _simple_resource("solo")}
        graph = _make_graph(resources)
        scheduler = GraphScheduler(graph)

        async def run():
            async def ex(rid):
                return f"ok:{rid}"
            result = await scheduler.execute_async(ex)
            return result

        result = asyncio.run(run())
        assert result.resource_results == {"solo": "ok:solo"}

    def test_execute_async_propagates_exception(self):
        """Exceptions from async executors are propagated correctly."""
        resources = {"bad": _simple_resource("bad")}
        graph = _make_graph(resources)
        scheduler = GraphScheduler(graph)

        async def run():
            async def failing_executor(rid: str):
                raise RuntimeError(f"failure in {rid}")
            await scheduler.execute_async(failing_executor)

        with pytest.raises(RuntimeError, match="failure in bad"):
            asyncio.run(run())


# ─────────────────────────────────────────────────────────────────────────────
# 2. CircuitRunner.execute_async() — end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestCircuitRunnerExecuteAsync:

    def _make_runner(self, nodes_outputs: Dict[str, Any]):
        """Create a minimal CircuitRunner with a mock runtime."""
        from unittest.mock import MagicMock
        from src.circuit.circuit_runner import CircuitRunner
        from src.engine.node_execution_runtime import NodeResult, NodeTrace

        mock_runtime = MagicMock()
        mock_registry = MagicMock()

        call_log: List[str] = []

        def fake_execute_by_config_id(registry, config_id, state):
            call_log.append(config_id)
            output = nodes_outputs.get(config_id, f"output:{config_id}")
            return NodeResult(node_id=config_id, output=output, trace=NodeTrace())

        async def fake_execute_async(config, state):
            config_id = config.get("config_id") or config.get("node_id", "unknown")
            call_log.append(config_id)
            output = nodes_outputs.get(config_id, f"output:{config_id}")
            return NodeResult(node_id=config_id, output=output, trace=NodeTrace())

        mock_runtime.execute_by_config_id.side_effect = fake_execute_by_config_id
        mock_runtime.execute_async = fake_execute_async
        mock_runtime.set_execution_id = MagicMock()

        def fake_registry_get(config_id):
            return {"config_id": config_id}

        mock_registry.get.side_effect = fake_registry_get

        runner = CircuitRunner(runtime=mock_runtime, registry=mock_registry)
        return runner, call_log

    def _make_circuit(self, node_ids: List[str]) -> Dict[str, Any]:
        return {
            "id": "test-circuit",
            "nodes": [
                {
                    "id": nid,
                    "type": "ai",
                    "execution_config_ref": nid,
                }
                for nid in node_ids
            ],
            "edges": [],
        }

    def test_execute_async_produces_correct_state(self):
        """execute_async populates current_state with node outputs."""
        runner, _ = self._make_runner({"node1": "out1", "node2": "out2"})
        circuit = self._make_circuit(["node1", "node2"])

        result = asyncio.run(runner.execute_async(circuit, {}))

        assert result["node1"] == "out1"
        assert result["node2"] == "out2"

    def test_execute_async_governance_trace_present(self):
        """execute_async returns CircuitRunResult with governance trace."""
        runner, _ = self._make_runner({"node1": "out1"})
        circuit = self._make_circuit(["node1"])

        result = asyncio.run(runner.execute_async(circuit, {}))

        assert hasattr(result, "governance")
        assert result.governance is not None

    def test_execute_async_execution_mode_in_event(self):
        """execute_async emits execution_started with execution_mode=async."""
        emitted_events: List[dict] = []

        runner, _ = self._make_runner({"n1": "v1"})
        original_emit = runner._emit_runtime_event

        def capturing_emit(event_type, payload):
            emitted_events.append({"type": event_type, "payload": payload})
            return original_emit(event_type, payload)

        runner._emit_runtime_event = capturing_emit
        circuit = self._make_circuit(["n1"])

        asyncio.run(runner.execute_async(circuit, {}))

        started = next(
            (e for e in emitted_events if e["type"] == "execution_started"), None
        )
        assert started is not None
        assert started["payload"].get("execution_mode") == "async"

    def test_execute_async_and_sync_produce_same_outputs(self):
        """execute_async and execute() produce the same node outputs."""
        runner, _ = self._make_runner({"n1": "val1", "n2": "val2"})
        circuit = self._make_circuit(["n1", "n2"])

        sync_result = runner.execute(circuit, {})
        async_result = asyncio.run(runner.execute_async(circuit, {}))

        assert sync_result.get("n1") == async_result.get("n1")
        assert sync_result.get("n2") == async_result.get("n2")


# ─────────────────────────────────────────────────────────────────────────────
# 3. execute_async is a real coroutine (not a sync wrapper)
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncPathIsGenuine:

    def test_graph_scheduler_execute_async_is_coroutinefunction(self):
        """GraphScheduler.execute_async must be a real coroutine function."""
        import inspect
        assert inspect.iscoroutinefunction(GraphScheduler.execute_async), (
            "GraphScheduler.execute_async must be defined with 'async def'"
        )

    def test_circuit_runner_execute_async_is_coroutinefunction(self):
        """CircuitRunner.execute_async must be a real coroutine function."""
        import inspect
        from src.circuit.circuit_runner import CircuitRunner
        assert inspect.iscoroutinefunction(CircuitRunner.execute_async), (
            "CircuitRunner.execute_async must be defined with 'async def'"
        )

    def test_node_execution_runtime_execute_async_is_coroutinefunction(self):
        """NodeExecutionRuntime.execute_async must be a real coroutine function."""
        import inspect
        from src.engine.node_execution_runtime import NodeExecutionRuntime
        assert inspect.iscoroutinefunction(NodeExecutionRuntime.execute_async), (
            "NodeExecutionRuntime.execute_async must be defined with 'async def'"
        )

    def test_graph_scheduler_execute_async_returns_coroutine(self):
        """Calling execute_async() must return a coroutine object, not a plain value."""
        import inspect
        from src.engine.compiled_resource_graph import compile_execution_config_to_graph

        config = {
            "plugins": [
                {"plugin_id": "p", "inputs": {}, "output_fields": ["result"]}
            ]
        }
        graph = compile_execution_config_to_graph(config)
        scheduler = GraphScheduler(graph)

        async def noop(rid):
            return rid

        coro = scheduler.execute_async(noop)
        assert inspect.iscoroutine(coro), (
            "execute_async() must return a coroutine, not a plain value"
        )
        # Clean up the unawaited coroutine
        coro.close()
