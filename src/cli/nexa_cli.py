import argparse
import json
import sys
import time
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


def build_execution_summary(initial_state, final_state, started_at, ended_at):
    initial_keys = set(initial_state.keys())
    final_keys = set(final_state.keys())
    produced_keys = sorted(final_keys - initial_keys)

    summary = {
        "initial_state_keys": len(initial_state),
        "final_state_keys": len(final_state),
        "node_outputs": len(produced_keys),
        "produced_keys": produced_keys,
        "execution_time_ms": round((ended_at - started_at) * 1000.0, 3),
    }
    return summary


def print_summary(summary):
    print("\n[execution summary]")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def build_error_payload(exc, args):
    payload = {
        "status": "error",
        "error_type": type(exc).__name__,
        "message": str(exc),
        "command": getattr(args, "command", None),
    }

    if hasattr(args, "circuit"):
        payload["circuit"] = args.circuit
    if hasattr(args, "configs"):
        payload["configs"] = args.configs
    if hasattr(args, "plugins"):
        payload["plugins"] = args.plugins

    return payload


def print_error_payload(payload):
    print("[nexa error]", file=sys.stderr)
    print(json.dumps(payload, indent=2, ensure_ascii=False), file=sys.stderr)


def run_command(args):
    execution_registry = load_execution_configs(args.configs)
    circuit = load_circuit(args.circuit)
    runtime = build_runtime(args.plugins)
    input_state = load_cli_state(args.state, args.var)

    runner = CircuitRunner(runtime, execution_registry)

    started_at = time.perf_counter()
    result = runner.execute(circuit, input_state)
    ended_at = time.perf_counter()

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.out:
        save_output(result, args.out)

    if args.summary:
        summary = build_execution_summary(
            initial_state=input_state,
            final_state=result,
            started_at=started_at,
            ended_at=ended_at,
        )
        print_summary(summary)

    return 0


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

    run_parser.add_argument(
        "--summary",
        action="store_true",
        help="print execution summary and basic metrics",
    )

    run_parser.add_argument(
        "--error-out",
        help="write structured error payload to JSON file on failure",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return 0

    try:
        return run_command(args)
    except Exception as exc:
        payload = build_error_payload(exc, args)
        print_error_payload(payload)

        if getattr(args, "error_out", None):
            save_output(payload, args.error_out)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())