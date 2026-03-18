from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.circuit.circuit_runner import CircuitRunner
from src.engine.run_comparator import RunComparator

OBSERVABILITY_FILE = Path("OBSERVABILITY.jsonl")


def build_parser():
    parser = argparse.ArgumentParser("nexa")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("circuit")
    run_parser.add_argument("--configs")
    run_parser.add_argument("--plugins")
    run_parser.add_argument("--state")
    run_parser.add_argument("--var", action="append", default=[])
    run_parser.add_argument("--summary", action="store_true")
    run_parser.add_argument("--out", "--output", dest="out")
    run_parser.add_argument("--error-out")
    run_parser.add_argument("--observability-out")

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("run_a")
    compare_parser.add_argument("run_b")

    sub.add_parser("info")

    task_parser = sub.add_parser("task")
    task_sub = task_parser.add_subparsers(dest="task_command")

    tgen = task_sub.add_parser("generate")
    tgen.add_argument("feature", help="Feature name (e.g. execution_diff)")
    tgen.add_argument("--base", type=int, default=180, help="Base step number")

    tprompt = task_sub.add_parser("prompt")
    tprompt.add_argument("feature", help="Feature name")
    tprompt.add_argument("step_id", help="Step ID or 1-based index (e.g. Step180 or 1)")
    tprompt.add_argument("--base", type=int, default=180, help="Base step number")

    diff_parser = sub.add_parser("diff")
    diff_parser.add_argument("left", help="Path to left run snapshot JSON file")
    diff_parser.add_argument("right", help="Path to right run snapshot JSON file")
    diff_parser.add_argument("--json", action="store_true", dest="output_json", help="Output diff as JSON")
    diff_parser.add_argument("--regression", action="store_true", dest="regression_mode", help="Run regression detection mode")

    return parser


def _parse_inline_vars(var_items):
    state = {}

    for item in var_items or []:
        if "=" not in item:
            raise ValueError("invalid --var format")
        key, value = item.split("=", 1)
        state[key] = value

    return state


def load_cli_state(state_path=None, var_items=None):
    state = {}

    if state_path is not None:
        with open(state_path, "r", encoding="utf-8") as f:
            state.update(json.load(f))

    state.update(_parse_inline_vars(var_items))
    return state


def save_output(payload, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def build_execution_summary(initial_state, final_state, started_at, ended_at):
    initial_keys = set(initial_state.keys())
    final_keys = set(final_state.keys())
    produced_keys = sorted(final_keys - initial_keys)

    return {
        "initial_state_keys": len(initial_keys),
        "final_state_keys": len(final_keys),
        "node_outputs": len(produced_keys),
        "produced_keys": produced_keys,
        "execution_time_ms": round((ended_at - started_at) * 1000, 1),
    }


def build_error_payload(exc, args):
    return {
        "status": "error",
        "error_type": type(exc).__name__,
        "message": str(exc),
        "command": getattr(args, "command", None),
        "circuit": getattr(args, "circuit", None),
        "configs": getattr(args, "configs", None),
        "plugins": getattr(args, "plugins", None),
    }


def print_error_payload(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def append_observability_record(record):
    OBSERVABILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OBSERVABILITY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


def build_success_observability_record(args, circuit, metrics, started_at, ended_at):
    return {
        "timestamp": started_at,
        "command": getattr(args, "command", None),
        "circuit_path": getattr(args, "circuit", None),
        "circuit_id": circuit.get("id"),
        "status": "success",
        "success": True,
        "execution_time_ms": round((ended_at - started_at) * 1000, 1),
        "node_count": len(circuit.get("nodes", [])),
        "executed_nodes": metrics.get("executed_nodes"),
        "wave_count": metrics.get("wave_count"),
        "plugin_calls": metrics.get("plugin_calls"),
        "provider_calls": metrics.get("provider_calls"),
        "error_type": None,
        "error_message": None,
    }


def build_failure_observability_record(args, exc):
    return {
        "timestamp": time.time(),
        "command": getattr(args, "command", None),
        "circuit_path": getattr(args, "circuit", None),
        "circuit_id": None,
        "status": "error",
        "success": False,
        "execution_time_ms": None,
        "node_count": None,
        "executed_nodes": None,
        "wave_count": None,
        "plugin_calls": None,
        "provider_calls": None,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def get_system_info() -> dict:
    """Collect Nexa system information for the info command."""
    vi = sys.version_info
    python_version = f"{vi.major}.{vi.minor}"

    nexa_root = Path(__file__).resolve().parent.parent.parent

    providers_dir = nexa_root / "src" / "providers"
    if providers_dir.is_dir():
        providers_installed = len(list(providers_dir.glob("*_provider.py")))
    else:
        providers_installed = 0

    from src.platform.plugin_registry import ids as plugin_ids
    plugins_registered = len(plugin_ids())

    return {
        "python_version": python_version,
        "nexa_root": str(nexa_root),
        "providers_installed": providers_installed,
        "plugins_registered": plugins_registered,
    }


def info_command() -> int:
    """Print Nexa system information."""
    info = get_system_info()

    print("Nexa System Info")
    print("----------------")
    print(f"Python Version: {info['python_version']}")
    print(f"Nexa Root Path: {info['nexa_root']}")
    print(f"Providers Installed: {info['providers_installed']}")
    print(f"Plugins Registered: {info['plugins_registered']}")

    return 0


def _load_run_snapshot(path: str) -> dict:
    """Load a run snapshot JSON file and return it as a dict.

    Raises SystemExit(1) with a message on any input error so that
    diff_command can treat all error paths uniformly.
    """
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error: cannot read file {path}: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(data, dict):
        print(
            f"Error: {path} must contain a JSON object (dict), "
            f"got {type(data).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return data


def diff_command(args) -> int:
    """Execute the diff command: compare two run snapshot JSON files."""
    import json as _json
    from src.engine.execution_diff_engine import compare_runs
    from src.engine.execution_diff_formatter import format_diff, format_diff_json

    left_run = _load_run_snapshot(args.left)
    right_run = _load_run_snapshot(args.right)

    diff = compare_runs(left_run, right_run)

    # Regression mode
    if getattr(args, "regression_mode", False):
        from src.engine.execution_regression_detector import detect_regressions
        from src.engine.execution_regression_formatter import (
            format_regression,
            format_regression_json,
        )

        regression_result = detect_regressions(diff)

        if getattr(args, "output_json", False):
            print(_json.dumps(format_regression_json(regression_result), indent=2))
        else:
            print(format_regression(regression_result))
    else:
        # Normal diff mode
        if getattr(args, "output_json", False):
            print(_json.dumps(format_diff_json(diff), indent=2))
        else:
            print(format_diff(diff))

    return 0


def _execution_config_search_candidates(circuit_path: str):
    circuit = Path(circuit_path).resolve()
    yield circuit.parent / "execution_configs"
    yield Path.cwd() / "execution_configs"


def resolve_execution_config_dir(circuit_path: str, cli_configs: str | None = None) -> Path:
    if cli_configs:
        path = Path(cli_configs).resolve()
        if not path.exists():
            raise FileNotFoundError(cli_configs)
        return path

    for candidate in _execution_config_search_candidates(circuit_path):
        if candidate.exists():
            return candidate

    searched = [str(path) for path in _execution_config_search_candidates(circuit_path)]
    raise FileNotFoundError(
        "execution config directory not found. searched: " + ", ".join(searched)
    )


def run_command(args):
    from src.config.execution_config_loader import load_execution_configs
    from src.contracts.provider_contract import ProviderRequest, ProviderResult
    from src.circuit.circuit_io import load_circuit
    from src.engine.node_execution_runtime import NodeExecutionRuntime
    from src.platform.provider_executor import ProviderExecutor
    from src.platform.provider_registry import ProviderRegistry

    class EchoProvider:
        def execute(self, request: ProviderRequest) -> ProviderResult:
            return ProviderResult(
                output=request.prompt,
                raw_text=request.prompt,
                structured=None,
                artifacts=[],
                trace={"provider": "echo"},
                error=None,
            )

    provider_registry = ProviderRegistry()
    provider_registry.register("echo", EchoProvider())
    executor = ProviderExecutor(provider_registry)
    runtime = NodeExecutionRuntime(provider_executor=executor)

    config_dir = resolve_execution_config_dir(args.circuit, args.configs)
    config_registry = load_execution_configs(str(config_dir))

    runner = CircuitRunner(runtime, config_registry)

    initial_state = load_cli_state(args.state, args.var)
    if not initial_state:
        initial_state = {"message": "Hello Nexa"}

    started_at = time.time()
    circuit = load_circuit(args.circuit)
    final_state = runner.execute(circuit, initial_state)
    ended_at = time.time()

    summary = build_execution_summary(
        initial_state=initial_state,
        final_state=final_state,
        started_at=started_at,
        ended_at=ended_at,
    )

    payload = {
        "result": {"state": final_state},
        "summary": summary,
    }

    if args.out:
        save_output(payload, args.out)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    metrics = runtime.get_metrics()
    circuit_meta = {"id": circuit.get("id"), "nodes": circuit.get("nodes", [])}

    record = build_success_observability_record(
        args=args,
        circuit=circuit_meta,
        metrics=metrics,
        started_at=started_at,
        ended_at=ended_at,
    )
    append_observability_record(record)

    if args.observability_out:
        save_output(record, args.observability_out)

    return 0


def compare_command(args):
    with open(args.run_a, "r", encoding="utf-8") as f:
        run_a = json.load(f)

    with open(args.run_b, "r", encoding="utf-8") as f:
        run_b = json.load(f)

    result = RunComparator.compare(run_a, run_b)

    print(result["diff_text"])

    reg = result["regression_report"]
    print()
    print("Regression Summary")
    print("------------------")
    print("Highest Severity:", reg.highest_severity)
    print("Total Regressions:", reg.total_regressions)

    return 0


def task_command(args) -> int:
    """Route nexa task subcommands to the claude_task_generator."""
    from src.devtools.claude_task_generator.cli import cmd_generate, cmd_prompt

    task_cmd = getattr(args, "task_command", None)

    if task_cmd == "generate":
        return cmd_generate(args.feature, base_number=args.base)

    if task_cmd == "prompt":
        return cmd_prompt(args.feature, args.step_id, base_number=args.base)

    # No task subcommand given — print help
    print("Usage: nexa task <generate|prompt> ...")
    return 1



def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        try:
            return run_command(args)
        except Exception as exc:
            payload = build_error_payload(exc, args)
            print_error_payload(payload)

            failure_record = build_failure_observability_record(args=args, exc=exc)
            append_observability_record(failure_record)

            if getattr(args, "error_out", None):
                save_output(payload, args.error_out)

            return 1

    if args.command == "compare":
        return compare_command(args)

    if args.command == "info":
        return info_command()

    if args.command == "diff":
        return diff_command(args)

    if args.command == "task":
        return task_command(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
