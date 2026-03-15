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
    # Python version (major.minor)
    vi = sys.version_info
    python_version = f"{vi.major}.{vi.minor}"

    # Nexa root: src/cli/nexa_cli.py → ../../.. → project root
    nexa_root = Path(__file__).resolve().parent.parent.parent

    # Installed providers: count *_provider.py files under src/providers/
    providers_dir = nexa_root / "src" / "providers"
    if providers_dir.is_dir():
        providers_installed = len(list(providers_dir.glob("*_provider.py")))
    else:
        providers_installed = 0

    # Registered plugins: use plugin registry
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


def run_command(args):
    runner = CircuitRunner()

    initial_state = load_cli_state(args.state, args.var)
    started_at = time.time()

    result = runner.run(Path(args.circuit), state=initial_state)

    ended_at = time.time()

    final_state = result.get("state", {})
    summary = build_execution_summary(
        initial_state=initial_state,
        final_state=final_state,
        started_at=started_at,
        ended_at=ended_at,
    )

    payload = {
        "result": result,
        "summary": summary,
    }

    if args.out:
        save_output(payload, args.out)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    metrics = result.get("metrics", {})
    circuit = result.get("circuit", {"id": None, "nodes": []})

    record = build_success_observability_record(
        args=args,
        circuit=circuit,
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
