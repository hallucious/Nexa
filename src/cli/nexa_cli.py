import argparse
import json

from src.config.execution_config_loader import load_execution_configs
from src.circuit.circuit_io import load_circuit
from src.circuit.circuit_runner import CircuitRunner

from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor
from src.engine.node_execution_runtime import NodeExecutionRuntime


def build_runtime():
    """
    Build default Nexa runtime for CLI execution.

    Step145에서는 CLI가 실제 엔진 객체를 생성할 수 있도록
    최소 wiring만 연결한다.
    """

    provider_registry = ProviderRegistry()
    provider_executor = ProviderExecutor(provider_registry)

    runtime = NodeExecutionRuntime(
        provider_executor=provider_executor
    )

    return runtime


def run_command(args):
    execution_registry = load_execution_configs(args.configs)
    circuit = load_circuit(args.circuit)
    runtime = build_runtime()

    runner = CircuitRunner(runtime, execution_registry)
    result = runner.execute(circuit, {})

    print(json.dumps(result, indent=2, ensure_ascii=False))


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