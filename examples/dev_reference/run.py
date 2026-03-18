"""
DEV REFERENCE ONLY

This script demonstrates direct NodeExecutionRuntime usage.

It is NOT part of the official Nexa execution path.

Use CLI instead:

    nexa run examples/hello_world.nex
"""

"""
examples/dev_reference/run.py

Minimal Nexa runtime execution example.

Demonstrates:
  - constructing a NodeExecutionRuntime with an echo provider
  - executing a single node with an inline execution config
  - reading artifact output
  - inspecting the execution trace
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when run directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.provider_contract import ProviderRequest, ProviderResult
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry


# ---------------------------------------------------------------------------
# Echo provider — returns the input prompt unchanged (no external API needed)
# ---------------------------------------------------------------------------

class EchoProvider:
    """Deterministic provider for local examples and testing."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            output=request.prompt,
            raw_text=request.prompt,
            structured=None,
            artifacts=[],
            trace={"provider": "echo", "prompt_len": len(request.prompt)},
            error=None,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    # 1. Register the echo provider
    registry = ProviderRegistry()
    registry.register("echo", EchoProvider())
    executor = ProviderExecutor(registry)

    # 2. Build the runtime
    runtime = NodeExecutionRuntime(provider_executor=executor)

    # 3. Define an inline execution config for a single node
    execution_config = {
        "config_id": "hello_node",
        "node_id": "hello_node",
        "provider": {
            "provider_id": "echo",
            "inputs": {"prompt": "input.message"},
        },
        "runtime_config": {
            "return_raw_output": True,
            "write_observability": False,
        },
    }

    initial_state = {"message": "Hello from Nexa!"}

    # 4. Execute the node
    result = runtime.execute(execution_config, initial_state)

    # 5. Print output
    print("=== Nexa Dev Reference Example ===")
    print()
    print(f"Node:   {result.node_id}")
    print(f"Output: {result.output}")
    print()

    # 6. Print artifact
    if result.artifacts:
        art = result.artifacts[0]
        print("--- Artifact ---")
        print(f"  type:          {art.type}")
        print(f"  name:          {art.name}")
        print(f"  data:          {art.data}")
        print(f"  producer_node: {art.producer_node}")
        print()

    # 7. Print execution trace
    print("--- Execution Trace ---")
    for event in result.trace.events:
        print(f"  {event}")
    print()

    print("Done.")


if __name__ == "__main__":
    run()