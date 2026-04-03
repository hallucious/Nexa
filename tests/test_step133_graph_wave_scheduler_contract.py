import threading
import time

from src.engine.compiled_resource_graph import compile_execution_config_to_graph
from src.engine.graph_scheduler import GraphScheduler


def test_step133_graph_scheduler_builds_parallel_wave_from_shared_dependency():
    config = {
        "prompt": {
            "prompt_id": "main",
            "inputs": {"question": "input.question"},
        },
        "plugins": [
            {
                "plugin_id": "translate",
                "inputs": {"text": "prompt.main.rendered"},
                "output_fields": ["result"],
            },
            {
                "plugin_id": "sentiment",
                "inputs": {"text": "prompt.main.rendered"},
                "output_fields": ["score"],
            },
        ],
    }

    graph = compile_execution_config_to_graph(config)
    scheduler = GraphScheduler(graph)

    waves = scheduler.build_waves()

    assert len(waves) == 2
    assert waves[0].resource_ids == ["prompt.main"]
    assert waves[1].resource_ids == ["plugin.sentiment", "plugin.translate"]


def test_step133_graph_scheduler_executes_all_resources_in_wave_order():
    config = {
        "plugins": [
            {
                "plugin_id": "search",
                "inputs": {"query": "input.query"},
                "output_fields": ["result"],
            },
            {
                "plugin_id": "rank",
                "inputs": {"text": "plugin.search.result"},
                "output_fields": ["result"],
            },
        ],
    }

    graph = compile_execution_config_to_graph(config)
    scheduler = GraphScheduler(graph)
    execution_order = []

    result = scheduler.execute(lambda resource_id: execution_order.append(resource_id) or resource_id)

    assert [wave.resource_ids for wave in result.waves] == [
        ["plugin.search"],
        ["plugin.rank"],
    ]
    assert execution_order == ["plugin.search", "plugin.rank"]
    assert result.resource_results["plugin.search"] == "plugin.search"
    assert result.resource_results["plugin.rank"] == "plugin.rank"

def test_step133_graph_scheduler_executes_same_wave_resources_in_parallel():
    config = {
        "prompt": {
            "prompt_id": "main",
            "inputs": {"question": "input.question"},
        },
        "plugins": [
            {
                "plugin_id": "translate",
                "inputs": {"text": "prompt.main.rendered"},
                "output_fields": ["result"],
            },
            {
                "plugin_id": "sentiment",
                "inputs": {"text": "prompt.main.rendered"},
                "output_fields": ["score"],
            },
        ],
    }

    graph = compile_execution_config_to_graph(config)
    scheduler = GraphScheduler(graph)
    barrier = threading.Barrier(2)
    seen = []

    def executor(resource_id: str):
        seen.append(resource_id)
        if resource_id.startswith("plugin."):
            barrier.wait(timeout=1.0)
            time.sleep(0.01)
        return resource_id

    result = scheduler.execute(executor, max_workers=2)

    assert result.resource_results["prompt.main"] == "prompt.main"
    assert result.resource_results["plugin.sentiment"] == "plugin.sentiment"
    assert result.resource_results["plugin.translate"] == "plugin.translate"
    assert seen[0] == "prompt.main"
    assert set(seen[1:]) == {"plugin.sentiment", "plugin.translate"}
