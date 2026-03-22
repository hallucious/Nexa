from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False

from src.circuit.circuit_runner import CircuitRunner
from src.engine.run_comparator import RunComparator

OBSERVABILITY_FILE = Path("OBSERVABILITY.jsonl")


class _GenerateTextProviderAdapter:
    """Compatibility adapter: wrap providers exposing generate_text(...) so they
    can be used through the runtime ProviderExecutor execute(request) contract.
    """

    def __init__(self, provider, provider_name: str | None = None) -> None:
        self.provider = provider
        self.provider_name = provider_name or type(provider).__name__

    def execute(self, request):
        from src.contracts.provider_contract import ProviderResult

        options = dict(getattr(request, 'options', {}) or {})
        kwargs = {
            'prompt': request.prompt,
            'temperature': options.get('temperature', 0.0),
            'max_output_tokens': options.get('max_output_tokens', options.get('max_tokens', 1024)),
        }
        if 'instructions' in options and options.get('instructions') is not None:
            kwargs['instructions'] = options.get('instructions')
        if 'timeout_sec' in options and options.get('timeout_sec') is not None:
            kwargs['timeout_sec'] = options.get('timeout_sec')

        result = self.provider.generate_text(**kwargs)

        if isinstance(result, ProviderResult):
            return result

        if isinstance(result, tuple) and len(result) == 3:
            text, raw, err = result
            trace = {'provider': self.provider_name}
            if isinstance(raw, dict):
                trace.update({'raw': raw})
            if err is not None:
                from src.contracts.provider_contract import ProviderError
                return ProviderResult(
                    output=text,
                    raw_text=str(text) if text is not None else None,
                    structured=None,
                    artifacts=[],
                    trace=trace,
                    error=ProviderError(type='provider_internal_error', message=str(err), retryable=False),
                )
            return ProviderResult(
                output=text,
                raw_text=str(text) if text is not None else None,
                structured=None,
                artifacts=[],
                trace=trace,
                error=None,
            )

        return result


def _safe_register(registry, provider_id: str, provider) -> bool:
    try:
        registry.register(provider_id, provider)
        return True
    except ValueError:
        return False


def _maybe_register_real_providers(provider_registry):
    """Best-effort registration of real AI providers.

    Returns a list of provider ids that were newly registered. This function is
    intentionally tolerant: missing env vars, optional dependencies, or import
    failures should never break the CLI.
    """
    load_dotenv()

    registered: list[str] = []
    first_real_alias: str | None = None

    def add_aliases(alias_map):
        nonlocal first_real_alias
        for alias, provider in alias_map:
            if _safe_register(provider_registry, alias, provider):
                registered.append(alias)
                if alias != 'ai' and first_real_alias is None:
                    first_real_alias = alias

    openai_key = (os.environ.get('OPENAI_API_KEY') or '').strip()
    if openai_key:
        try:
            from src.providers.gpt_provider import GPTProvider
            provider = _GenerateTextProviderAdapter(GPTProvider.from_env(), provider_name='openai')
            add_aliases([('gpt', provider), ('openai', provider)])
        except Exception:
            pass

    anthropic_key = (os.environ.get('ANTHROPIC_API_KEY') or '').strip()
    if anthropic_key:
        try:
            from src.providers.claude_provider import ClaudeProvider
            provider = _GenerateTextProviderAdapter(ClaudeProvider.from_env(), provider_name='anthropic')
            add_aliases([('claude', provider), ('anthropic', provider)])
        except Exception:
            pass

    gemini_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if gemini_key:
        try:
            from src.providers.gemini_provider import GeminiProvider
            provider = _GenerateTextProviderAdapter(GeminiProvider.from_env(), provider_name='gemini')
            add_aliases([('gemini', provider)])
        except Exception:
            pass

    pplx_key = ((os.environ.get('PPLX_API_KEY') or '') or (os.environ.get('PERPLEXITY_API_KEY') or '')).strip()
    if pplx_key:
        try:
            if not os.environ.get('PPLX_API_KEY') and os.environ.get('PERPLEXITY_API_KEY'):
                os.environ['PPLX_API_KEY'] = os.environ['PERPLEXITY_API_KEY']
            from src.providers.perplexity_provider import PerplexityProvider
            provider = _GenerateTextProviderAdapter(PerplexityProvider.from_env(), provider_name='perplexity')
            add_aliases([('perplexity', provider), ('pplx', provider)])
        except Exception:
            pass

    if first_real_alias is not None:
        try:
            provider = provider_registry.resolve(first_real_alias)
            if _safe_register(provider_registry, 'ai', provider):
                registered.append('ai')
        except Exception:
            pass

    return registered


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

    export_parser = sub.add_parser("export")
    export_parser.add_argument("input", help="Path to run result JSON file")
    export_parser.add_argument("--out", required=True, help="Path to audit pack zip output")

    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("input", help="Path to audit pack zip file")
    replay_parser.add_argument("--strict", action="store_true", help="Return non-zero on any non-determinism")

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


def resolve_output_path(out_path: str, circuit_path: str) -> Path:
    p = Path(out_path)

    if p.parent == Path("."):
        nex_dir = Path(circuit_path).resolve().parent
        runs_dir = nex_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        return runs_dir / p.name

    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _to_json_safe(value):
    if is_dataclass(value):
        return _to_json_safe(asdict(value))

    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]

    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _to_json_safe(value.model_dump())

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _to_json_safe(value.to_dict())

    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def save_output(payload, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_to_json_safe(payload), f, indent=2, ensure_ascii=False)


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
    info = get_system_info()

    print("Nexa System Info")
    print("----------------")
    print(f"Python Version: {info['python_version']}")
    print(f"Nexa Root Path: {info['nexa_root']}")
    print(f"Providers Installed: {info['providers_installed']}")
    print(f"Plugins Registered: {info['plugins_registered']}")

    return 0


def _load_run_snapshot(path: str) -> dict:
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


def _normalize_run_output_to_snapshot(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return raw

    if any(key in raw for key in ("nodes", "artifacts", "context")):
        return raw

    result = raw.get("result") or {}
    state = result.get("state") or {}
    replay_payload = raw.get("replay_payload") or {}
    expected_outputs = replay_payload.get("expected_outputs") or {}

    nodes: dict[str, dict] = {}
    context: dict[str, object] = {}

    for node_id, node_data in state.items():
        if not isinstance(node_data, dict):
            continue

        node_output = node_data.get("output")
        nodes[node_id] = {
            "status": "success" if "error" not in node_data else "failure",
            "output": node_output,
        }
        context[f"{node_id}.output"] = node_output

    for output_key, output_value in expected_outputs.items():
        context[f"output.{output_key}"] = output_value

    return {
        "run_id": (
            raw.get("run_id")
            or result.get("execution_id")
            or replay_payload.get("execution_id")
            or "unknown-run"
        ),
        "nodes": nodes,
        "artifacts": {},
        "context": context,
    }


def diff_command(args) -> int:
    import json as _json
    from src.engine.execution_diff_engine import compare_runs
    from src.engine.execution_diff_formatter import format_diff, format_diff_json

    left_run_raw = _load_run_snapshot(args.left)
    right_run_raw = _load_run_snapshot(args.right)

    left_run = _normalize_run_output_to_snapshot(left_run_raw)
    right_run = _normalize_run_output_to_snapshot(right_run_raw)

    diff = compare_runs(left_run, right_run)

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


def _is_savefile_contract(circuit_path: str) -> bool:
    """Return True if the .nex file matches the savefile-native contract."""
    try:
        with open(circuit_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    required = {"meta", "circuit", "resources", "state", "ui"}
    return required.issubset(set(data.keys()))


def _extract_savefile_metrics(trace) -> dict:
    executed_nodes = len(getattr(trace, "node_results", {}) or {})
    provider_calls = 0
    plugin_calls = 0
    for result in (getattr(trace, "node_results", {}) or {}).values():
        trace_data = getattr(result, "trace", {}) or {}
        if trace_data.get("provider_type") or trace_data.get("provider"):
            provider_calls += 1
        else:
            plugin_calls += 1

    return {
        "executed_nodes": executed_nodes,
        "wave_count": None,
        "plugin_calls": plugin_calls,
        "provider_calls": provider_calls,
    }


def _savefile_payload(savefile, trace, started_at, ended_at):
    summary = build_execution_summary(
        initial_state=getattr(savefile.state, "input", {}) or {},
        final_state=getattr(trace, "final_state", {}) or {},
        started_at=started_at,
        ended_at=ended_at,
    )

    expected_outputs = {}
    for node_id, result in (getattr(trace, "node_results", {}) or {}).items():
        expected_outputs[node_id] = {
            "status": getattr(result, "status", None),
            "output": getattr(result, "output", None),
            "error": getattr(result, "error", None),
            "artifacts": getattr(result, "artifacts", []),
            "trace": getattr(result, "trace", {}),
        }

    replay_payload = {
        "execution_id": getattr(trace, "run_id", "unknown-execution"),
        "node_order": [node.id for node in savefile.circuit.nodes],
        "circuit": _to_json_safe({
            "id": savefile.meta.name,
            "nodes": [{"id": node.id} for node in savefile.circuit.nodes],
        }),
        "execution_configs": {},
        "input_state": getattr(savefile.state, "input", {}) or {},
        "expected_outputs": expected_outputs,
    }

    return {
        "result": {
            "state": getattr(trace, "final_state", {}) or {},
            "status": getattr(trace, "status", None),
            "node_results": expected_outputs,
            "artifacts": getattr(trace, "all_artifacts", []),
        },
        "summary": summary,
        "replay_payload": replay_payload,
    }


def _run_savefile_command(args):
    from src.contracts.savefile_loader import load_savefile_from_path
    from src.contracts.savefile_validator import validate_savefile
    from src.contracts.savefile_provider_builder import build_provider_registry_from_savefile
    from src.contracts.savefile_executor_aligned import SavefileExecutor

    started_at = time.time()
    savefile = load_savefile_from_path(args.circuit)

    cli_state = load_cli_state(args.state, args.var)
    if cli_state:
        savefile.state.input.update(cli_state)

    validate_savefile(savefile)
    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)
    trace = executor.execute(savefile, run_id=f"savefile-{int(started_at)}")
    ended_at = time.time()

    payload = _savefile_payload(savefile, trace, started_at, ended_at)

    if args.out:
        out_path = resolve_output_path(args.out, args.circuit)
        save_output(payload, out_path)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    metrics = _extract_savefile_metrics(trace)
    circuit_meta = {"id": savefile.meta.name, "nodes": [{"id": node.id} for node in savefile.circuit.nodes]}
    record = build_success_observability_record(
        args=args,
        circuit=circuit_meta,
        metrics=metrics,
        started_at=started_at,
        ended_at=ended_at,
    )
    append_observability_record(record)

    if args.observability_out:
        observability_out = Path(args.observability_out)
        if observability_out.parent != Path("."):
            observability_out.parent.mkdir(parents=True, exist_ok=True)
        save_output(record, observability_out)

    return 0


def run_command(args):
    if _is_savefile_contract(args.circuit):
        return _run_savefile_command(args)

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
    _maybe_register_real_providers(provider_registry)
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

    replay_payload = {
        "execution_id": circuit.get("id", "unknown-execution"),
        "node_order": [node.get("id") for node in circuit.get("nodes", []) if node.get("id")],
        "circuit": circuit,
        "execution_configs": dict(getattr(config_registry, "_configs", {})),
        "input_state": initial_state,
        "expected_outputs": {
            node.get("id"): final_state.get(node.get("id"))
            for node in circuit.get("nodes", [])
            if node.get("id") in final_state
        },
    }

    payload = {
        "result": {"state": final_state},
        "summary": summary,
        "replay_payload": replay_payload,
    }

    if args.out:
        out_path = resolve_output_path(args.out, args.circuit)
        save_output(payload, out_path)
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
        observability_out = Path(args.observability_out)
        if observability_out.parent != Path("."):
            observability_out.parent.mkdir(parents=True, exist_ok=True)
        save_output(record, observability_out)

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


def export_command(args) -> int:
    from src.engine.execution_audit_pack import ExecutionAuditPackBuilder

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print(f"Error: {args.input} must contain a JSON object", file=sys.stderr)
        return 1

    ExecutionAuditPackBuilder.export(payload, args.out)
    print(json.dumps({"status": "ok", "output": args.out}, indent=2, ensure_ascii=False))
    return 0


def replay_command(args) -> int:
    from src.engine.audit_replay import replay_audit_pack

    try:
        result = replay_audit_pack(args.input)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result["status"] == "PASS":
        print("PASS: deterministic execution confirmed")
        return 0

    print("FAIL: non-determinism detected")
    for diff in result.get("differences", []):
        print(f"- {diff}")

    return 1 if getattr(args, "strict", False) else 0


def task_command(args) -> int:
    from src.devtools.claude_task_generator.cli import cmd_generate, cmd_prompt

    task_cmd = getattr(args, "task_command", None)

    if task_cmd == "generate":
        return cmd_generate(args.feature, base_number=args.base)

    if task_cmd == "prompt":
        return cmd_prompt(args.feature, args.step_id, base_number=args.base)

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
                error_out = Path(args.error_out)
                if error_out.parent != Path("."):
                    error_out.parent.mkdir(parents=True, exist_ok=True)
                save_output(payload, error_out)

            return 1

    if args.command == "compare":
        return compare_command(args)

    if args.command == "info":
        return info_command()

    if args.command == "diff":
        return diff_command(args)

    if args.command == "task":
        return task_command(args)

    if args.command == "export":
        return export_command(args)

    if args.command == "replay":
        return replay_command(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
