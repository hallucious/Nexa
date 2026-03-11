import argparse
import json
from typing import Any

from src.config.execution_config_loader import load_execution_configs
from src.circuit.circuit_io import load_circuit
from src.circuit.circuit_runner import CircuitRunner


def build_runtime() -> Any:
    """
    Runtime construction entrypoint.

    Step144에서는 CLI 설치/실행 구조를 먼저 고정한다.
    실제 provider/plugin wiring은 이후 단계에서 확장한다.
    """
    raise NotImplementedError(
        "CLI runtime bootstrap is not configured yet. "
        "Connect ProviderRegistry/ProviderExecutor/NodeExecutionRuntime in the next step."
    )


def run_command(args):
    registry = load_execution_configs(args.configs)
    circuit = load_circuit(args.circuit)
    runtime = build_runtime()

    runner = CircuitRunner(runtime, registry)
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