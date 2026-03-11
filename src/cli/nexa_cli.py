import argparse
import json
from pathlib import Path

from src.config.execution_config_loader import load_execution_configs
from src.circuit.circuit_io import load_circuit
from src.circuit.circuit_runner import CircuitRunner

from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor
from src.platform.plugin_auto_loader import load_plugin_registry
from src.engine.node_execution_runtime import NodeExecutionRuntime


def build_runtime(plugin_dir="plugins"):
    provider_registry = ProviderRegistry()
    provider_executor = ProviderExecutor(provider_registry)
    plugin_registry = load_plugin_registry(plugin_dir)

    runtime = NodeExecutionRuntime(
        provider_executor=provider_executor,
        plugin_registry=plugin_registry,
    )

    return runtime


def load_cli_state(state_file=None, variables=None):
    state = {}

    if state_file:
        with open(state_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            raise ValueError("CLI state file must contain a JSON object")

        state.update(loaded)

    for item in variables or []:
        if "=" not in item:
            raise ValueError(f"invalid --var format: {item}")

        key, value = item.split("=", 1)
        key = key.strip()

        if not key:
            raise ValueError(f"invalid --var key: {item}")

        state[key] = value

    return state


def save_output(result, out_file):
    path = Path(out_file)

    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def run_command(args):
    execution_registry = load_execution_configs(args.configs)
    circuit = load_circuit(args.circuit)
    runtime = build_runtime(args.plugins)
    input_state = load_cli_state(args.state, args.var)

    runner = CircuitRunner(runtime, execution_registry)
    result = runner.execute(circuit, input_state)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.out:
        save_output(result, args.out)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="nexa",
        description="Nexa workflow engine CLI",
    )

    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run")

    run_parser.add_argument(
        "circuit",
        help=".nex circuit file",
    )

    run_parser.add_argument(
        "--configs",
        default="configs",
        help="execution config directory",
    )

    run_parser.add_argument(
        "--plugins",
        default="plugins",
        help="plugin directory",
    )

    run_parser.add_argument(
        "--state",
        help="JSON file containing initial execution state",
    )

    run_parser.add_argument(
        "--var",
        action="append",
        default=[],
        help='inline state variable, e.g. --var question="What is Nexa?"',
    )

    run_parser.add_argument(
        "--out",
        help="write execution result to JSON file",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()