from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

from src.storage.lifecycle_api import (
    create_serialized_circuit_execution_payload,
    create_serialized_execution_artifact_components,
    create_serialized_savefile_execution_payload,
)

try:
    from dotenv import load_dotenv
    DOTENV_INSTALLED = True
except ModuleNotFoundError:
    DOTENV_INSTALLED = False

    def load_dotenv(*args, **kwargs):
        return False

from src.circuit.circuit_runner import CircuitRunner
from src.cli.savefile_runtime import execute_savefile, is_savefile_contract
from src.engine.run_comparator import RunComparator
from src.providers.env_diagnostics import publish_dotenv_status
from src.utils.nexa_config import get_observability_path


OBSERVABILITY_FILE = Path(get_observability_path())


from src.platform.provider_executor import GenerateTextProviderBridge


class _GenerateTextProviderAdapter(GenerateTextProviderBridge):
    """Backward-compatible alias for the shared generate_text bridge."""

    pass


def _safe_register(registry, provider_id: str, provider) -> bool:
    try:
        registry.register(provider_id, provider)
        return True
    except ValueError:
        return False


def _find_repo_root_from_path(start: "Path | None") -> "Path | None":
    """Walk upward from *start* to find the repo root.

    A directory is considered the repo root when it contains both src/
    and examples/.  Returns None if not found or if *start* is None.
    """
    if start is None:
        return None
    try:
        current = Path(start).resolve()
    except Exception:
        return None
    for candidate in [current, *current.parents]:
        if (candidate / "src").exists() and (candidate / "examples").exists():
            return candidate
    return None


def _find_repo_root_from_cwd() -> "Path | None":
    """Walk up from cwd looking for the repo root (has both 'src' and 'examples')."""
    return _find_repo_root_from_path(Path.cwd())


def _load_env_for_args(args) -> "str | None":
    """Load the first .env found in the standard search order.

    Search order:
      1. cwd/.env
      2. repo root/.env  (detected by walking up from cwd)
      3. repo root/.env  (detected by walking up from args.circuit)
      4. circuit/savefile parent dir/.env (if args.circuit is set)
      5. plain load_dotenv() fallback (searches standard locations)

    Duplicate resolved paths are skipped.
    Returns the path of the .env that was loaded, or None if only the
    fallback was used (or dotenv is not installed).
    """
    candidates = [Path.cwd() / ".env"]

    cwd_root = _find_repo_root_from_cwd()
    if cwd_root is not None:
        candidates.append(cwd_root / ".env")

    circuit = getattr(args, "circuit", None)
    if circuit:
        try:
            circuit_path = Path(circuit).expanduser().resolve()
        except Exception:
            circuit_path = None

        if circuit_path is not None:
            circuit_root = _find_repo_root_from_path(circuit_path.parent)
            if circuit_root is not None:
                candidates.append(circuit_root / ".env")
            candidates.append(circuit_path.parent / ".env")

    seen: set = set()
    for path in candidates:
        try:
            rp = path.resolve()
        except Exception:
            continue
        if rp in seen:
            continue
        seen.add(rp)
        if rp.exists():
            load_dotenv(dotenv_path=rp)
            return str(rp)

    load_dotenv()
    return None


def _maybe_register_real_providers(provider_registry):
    """Best-effort registration of real AI providers.

    Returns a list of provider ids that were newly registered. This function is
    intentionally tolerant: missing env vars, optional dependencies, or import
    failures should never break the CLI.
    """

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

    savefile_parser = sub.add_parser("savefile")
    savefile_sub = savefile_parser.add_subparsers(dest="savefile_command")

    savefile_new = savefile_sub.add_parser("new")
    savefile_new.add_argument("output", help="Path to output .nex savefile")
    savefile_new.add_argument("--name", help="Savefile name (defaults to output stem)")
    savefile_new.add_argument("--version", default="1.0.0", help="Savefile version")
    savefile_new.add_argument("--description", help="Optional savefile description")
    savefile_new.add_argument("--entry", default="node1", help="Entry node id")
    savefile_new.add_argument(
        "--template",
        choices=["plugin", "ai"],
        help="Named savefile template to create (preferred over manual node-type selection)",
    )
    savefile_new.add_argument(
        "--node-type",
        choices=["plugin", "ai"],
        default="plugin",
        help="Template node type for the minimal savefile (legacy fallback; prefer --template)",
    )
    savefile_new.add_argument("--plugin-id", default="plugin.main", help="Plugin resource id for plugin template")
    savefile_new.add_argument(
        "--plugin-entry",
        default="plugins.example.run",
        help="Plugin entry path for plugin template",
    )
    savefile_new.add_argument("--prompt-id", default="prompt.main", help="Prompt resource id for ai template")
    savefile_new.add_argument(
        "--prompt-template",
        default="You are a helpful assistant.",
        help="Prompt template for ai template",
    )
    savefile_new.add_argument("--provider-id", default="provider.main", help="Provider resource id for ai template")
    savefile_new.add_argument("--provider-type", default="openai", help="Provider type for ai template")
    savefile_new.add_argument("--provider-model", default="gpt-4o-mini", help="Provider model for ai template")
    savefile_new.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

    savefile_validate = savefile_sub.add_parser("validate")
    savefile_validate.add_argument("input", help="Path to input .nex savefile")

    savefile_info = savefile_sub.add_parser("info")
    savefile_info.add_argument("input", help="Path to input .nex savefile")

    savefile_set_name = savefile_sub.add_parser("set-name")
    savefile_set_name.add_argument("input", help="Path to input .nex savefile")
    savefile_set_name.add_argument("--name", required=True, help="New savefile name")

    savefile_set_entry = savefile_sub.add_parser("set-entry")
    savefile_set_entry.add_argument("input", help="Path to input .nex savefile")
    savefile_set_entry.add_argument("--entry", required=True, help="New entry node id")

    savefile_set_description = savefile_sub.add_parser("set-description")
    savefile_set_description.add_argument("input", help="Path to input .nex savefile")
    savefile_set_description.add_argument("--description", required=True, help="New savefile description")

    savefile_template = savefile_sub.add_parser("template")
    savefile_template_sub = savefile_template.add_subparsers(dest="savefile_template_command")
    savefile_template_sub.add_parser("list")

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


def _canonical_output_path(out_path: str, circuit_path: str) -> Path:
    """Return the intended output path before deduplication suffix is applied.

    This mirrors resolve_output_path's directory routing logic but skips
    _deduplicate_output_path, so callers can check whether the file already
    exists *before* resolve_output_path is called.
    """
    p = Path(out_path).expanduser()
    if p.parent == Path('.'):
        circuit_dir = Path(circuit_path).expanduser().resolve().parent
        return (circuit_dir / "runs" / p.name).resolve()
    return p.resolve()


def _deduplicate_output_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}__{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def resolve_output_path(out_path: str, circuit_path: str) -> Path:
    p = Path(out_path).expanduser()

    if p.parent == Path('.'):
        circuit_dir = Path(circuit_path).expanduser().resolve().parent
        target_dir = circuit_dir / "runs"
        target_dir.mkdir(parents=True, exist_ok=True)
        resolved = (target_dir / p.name).resolve()
    else:
        resolved = p.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return _deduplicate_output_path(resolved)


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
    import os as _os
    _configured = globals().get("OBSERVABILITY_FILE")
    if _configured is None:
        _path = get_observability_path()
    else:
        _path = str(_configured)
    _dir = _os.path.dirname(_os.path.abspath(_path))
    _os.makedirs(_dir, exist_ok=True)
    with open(_path, "a", encoding="utf-8") as f:
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

    from src.platform.plugin_discovery import load_platform_plugin_manifests

    try:
        plugins_registered = len(load_platform_plugin_manifests(nexa_root))
    except Exception:
        # Keep `nexa info` resilient even if plugin manifests are temporarily
        # invalid or incomplete; detailed validation belongs elsewhere.
        plugins_registered = 0

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


def _savefile_template_registry() -> list[dict]:
    return [
        {
            "name": "plugin",
            "description": "Minimal canonical savefile with one plugin node.",
            "node_type": "plugin",
            "defaults": {
                "entry": "node1",
                "plugin_id": "plugin.main",
                "plugin_entry": "plugins.example.run",
            },
            "options": ["--plugin-id", "--plugin-entry"],
        },
        {
            "name": "ai",
            "description": "Minimal canonical savefile with one AI node.",
            "node_type": "ai",
            "defaults": {
                "entry": "node1",
                "prompt_id": "prompt.main",
                "prompt_template": "You are a helpful assistant.",
                "provider_id": "provider.main",
                "provider_type": "openai",
                "provider_model": "gpt-4o-mini",
            },
            "options": [
                "--prompt-id",
                "--prompt-template",
                "--provider-id",
                "--provider-type",
                "--provider-model",
            ],
        },
    ]


def savefile_template_list_command(args) -> int:
    templates = _savefile_template_registry()
    payload = {
        "status": "ok",
        "template_count": len(templates),
        "templates": templates,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0

def _build_new_savefile(args):
    from src.contracts.savefile_factory import make_minimal_savefile

    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("savefile output must use .nex extension")

    name = args.name or output_path.stem

    template_name = args.template or args.node_type

    ui_metadata = {
        "created_by": "nexa savefile new",
        "template": template_name,
    }

    if template_name == "plugin":
        return make_minimal_savefile(
            name=name,
            version=args.version,
            description=args.description,
            entry=args.entry,
            node_type="plugin",
            resource_ref={"plugin": args.plugin_id},
            plugins={args.plugin_id: {"entry": args.plugin_entry}},
            ui_metadata=ui_metadata,
        )

    return make_minimal_savefile(
        name=name,
        version=args.version,
        description=args.description,
        entry=args.entry,
        node_type="ai",
        resource_ref={"prompt": args.prompt_id, "provider": args.provider_id},
        prompts={args.prompt_id: {"template": args.prompt_template}},
        providers={
            args.provider_id: {
                "type": args.provider_type,
                "model": args.provider_model,
                "config": {},
            }
        },
        ui_metadata=ui_metadata,
    )


def savefile_new_command(args) -> int:
    from src.contracts.savefile_serializer import save_savefile_file
    from src.contracts.savefile_validator import validate_savefile

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    savefile = _build_new_savefile(args)
    validate_savefile(savefile)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_savefile_file(savefile, str(output_path))

    payload = {
        "status": "ok",
        "output": str(output_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
        "node_type": savefile.circuit.nodes[0].type,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_validate_command(args) -> int:
    from src.contracts.savefile_loader import load_savefile_from_path
    from src.contracts.savefile_validator import validate_savefile

    input_path = Path(args.input)
    if input_path.suffix != ".nex":
        raise ValueError("savefile input must use .nex extension")

    savefile = load_savefile_from_path(str(input_path))
    warnings = validate_savefile(savefile) or []

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
        "node_count": len(savefile.circuit.nodes),
        "warnings": warnings,
        "warning_count": len(warnings),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_info_command(args) -> int:
    from src.contracts.savefile_loader import load_savefile_from_path

    input_path = Path(args.input)
    if input_path.suffix != ".nex":
        raise ValueError("savefile input must use .nex extension")

    savefile = load_savefile_from_path(str(input_path))

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "version": savefile.meta.version,
        "description": savefile.meta.description,
        "entry": savefile.circuit.entry,
        "node_count": len(savefile.circuit.nodes),
        "edge_count": len(savefile.circuit.edges),
        "prompt_count": len(savefile.resources.prompts),
        "provider_count": len(savefile.resources.providers),
        "plugin_count": len(savefile.resources.plugins),
        "state_input_key_count": len(savefile.state.input),
        "state_working_key_count": len(savefile.state.working),
        "state_memory_key_count": len(savefile.state.memory),
        "ui_layout_key_count": len(savefile.ui.layout),
        "ui_metadata_key_count": len(savefile.ui.metadata),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _load_editable_savefile(input_value: str):
    from src.contracts.savefile_loader import load_savefile_from_path

    input_path = Path(input_value)
    if input_path.suffix != ".nex":
        raise ValueError("savefile input must use .nex extension")

    savefile = load_savefile_from_path(str(input_path))
    return input_path, savefile


def _persist_edited_savefile(savefile, input_path: Path) -> None:
    from src.contracts.savefile_serializer import save_savefile_file
    from src.contracts.savefile_validator import validate_savefile

    validate_savefile(savefile)
    save_savefile_file(savefile, str(input_path))



def savefile_set_name_command(args) -> int:
    input_path, savefile = _load_editable_savefile(args.input)
    savefile.meta.name = args.name
    _persist_edited_savefile(savefile, input_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_set_entry_command(args) -> int:
    input_path, savefile = _load_editable_savefile(args.input)
    savefile.circuit.entry = args.entry
    _persist_edited_savefile(savefile, input_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_set_description_command(args) -> int:
    input_path, savefile = _load_editable_savefile(args.input)
    savefile.meta.description = args.description
    _persist_edited_savefile(savefile, input_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
        "description": savefile.meta.description,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
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


def _snapshot_from_execution_record_payload(execution_record: dict) -> dict | None:
    if not isinstance(execution_record, dict) or not execution_record:
        return None

    meta = execution_record.get("meta") if isinstance(execution_record.get("meta"), dict) else {}
    run_id = meta.get("run_id") or "unknown-run"

    artifact_map: dict[str, dict] = {}
    artifacts_section = execution_record.get("artifacts") if isinstance(execution_record.get("artifacts"), dict) else {}
    for item in artifacts_section.get("artifact_refs", []):
        if not isinstance(item, dict) or not item.get("artifact_id"):
            continue
        artifact_map[str(item["artifact_id"])] = {
            "hash": item.get("hash"),
            "kind": item.get("artifact_type"),
        }

    nodes: dict[str, dict] = {}
    context: dict[str, object] = {}
    node_results = execution_record.get("node_results") if isinstance(execution_record.get("node_results"), dict) else {}
    for item in node_results.get("results", []):
        if not isinstance(item, dict) or not item.get("node_id"):
            continue
        node_id = str(item["node_id"])
        output_preview = item.get("output_preview")
        artifact_ids = item.get("artifact_refs") if isinstance(item.get("artifact_refs"), list) else []
        nodes[node_id] = {
            "status": item.get("status"),
            "output": output_preview,
            "artifacts": {artifact_id: artifact_map[artifact_id] for artifact_id in artifact_ids if artifact_id in artifact_map},
        }
        context[f"{node_id}.output"] = output_preview

    outputs = execution_record.get("outputs") if isinstance(execution_record.get("outputs"), dict) else {}
    for item in outputs.get("final_outputs", []):
        if not isinstance(item, dict) or not item.get("output_ref"):
            continue
        context[f"output.{item['output_ref']}"] = item.get("value_payload")

    if not nodes and not context and not artifact_map:
        return None

    return {
        "run_id": run_id,
        "nodes": nodes,
        "artifacts": artifact_map,
        "context": context,
    }


def _normalize_run_output_to_snapshot(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return raw

    if isinstance(raw.get("nodes"), dict) and not any(
        key in raw for key in (
            "result",
            "replay_payload",
            "execution_record",
            "execution_record_reference_contract",
            "summary",
            "trace",
            "primary_trace_ref",
        )
    ):
        return {
            "run_id": raw.get("run_id") or "unknown-run",
            "nodes": raw.get("nodes") or {},
            "artifacts": raw.get("artifacts") if isinstance(raw.get("artifacts"), dict) else {},
            "context": raw.get("context") if isinstance(raw.get("context"), dict) else {},
        }

    components = create_serialized_execution_artifact_components(raw)
    execution_record = components.get("execution_record")
    snapshot = _snapshot_from_execution_record_payload(execution_record)
    if snapshot is not None:
        return snapshot

    result = raw.get("result") or {}
    state = result.get("state") or {}
    replay_payload = components.get("replay_payload") if isinstance(components.get("replay_payload"), dict) else {}
    expected_outputs = replay_payload.get("expected_outputs") if isinstance(replay_payload.get("expected_outputs"), dict) else {}

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
            components.get("run_id")
            or raw.get("run_id")
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
    return create_serialized_savefile_execution_payload(
        savefile,
        trace,
        started_at=started_at,
        ended_at=ended_at,
    )


def _run_savefile_command(args):
    started_at = time.time()
    cli_state = load_cli_state(args.state, args.var)
    savefile, trace = execute_savefile(
        args.circuit,
        input_overrides=cli_state or None,
        run_id=f"savefile-{int(started_at)}",
    )
    ended_at = time.time()

    payload = _savefile_payload(savefile, trace, started_at, ended_at)

    if args.out:
        file_already_existed = _canonical_output_path(args.out, args.circuit).exists()
        out_path = resolve_output_path(args.out, args.circuit)
        save_output(payload, out_path)
        if file_already_existed:
            print(
                f"Info: output already existed; wrote new file to {out_path}",
                file=sys.stderr,
            )
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

    from src.platform.execution_config_registry import load_execution_configs
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
    final_state = asyncio.run(runner.execute_async(circuit, initial_state))
    ended_at = time.time()

    payload = create_serialized_circuit_execution_payload(
        circuit,
        final_state,
        initial_state=initial_state,
        execution_configs=dict(getattr(config_registry, "_configs", {})),
        started_at=started_at,
        ended_at=ended_at,
        trace={"events": []},
        artifacts=[],
    )

    if args.out:
        file_already_existed = _canonical_output_path(args.out, args.circuit).exists()
        out_path = resolve_output_path(args.out, args.circuit)
        save_output(payload, out_path)
        if file_already_existed:
            print(
                f"Info: output already existed; wrote new file to {out_path}",
                file=sys.stderr,
            )
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

    _load_env_for_args(args)

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

    if args.command == "savefile":
        try:
            if getattr(args, "savefile_command", None) == "new":
                return savefile_new_command(args)
            if getattr(args, "savefile_command", None) == "validate":
                return savefile_validate_command(args)
            if getattr(args, "savefile_command", None) == "info":
                return savefile_info_command(args)
            if getattr(args, "savefile_command", None) == "set-name":
                return savefile_set_name_command(args)
            if getattr(args, "savefile_command", None) == "set-entry":
                return savefile_set_entry_command(args)
            if getattr(args, "savefile_command", None) == "set-description":
                return savefile_set_description_command(args)
            if getattr(args, "savefile_command", None) == "template":
                if getattr(args, "savefile_template_command", None) == "list":
                    return savefile_template_list_command(args)
            parser.print_help()
            return 1
        except Exception as exc:
            payload = {
                "status": "error",
                "error_type": type(exc).__name__,
                "message": str(exc),
                "command": "savefile",
                "subcommand": getattr(args, "savefile_command", None),
                "output": getattr(args, "output", None),
                "input": getattr(args, "input", None),
            }
            print_error_payload(payload)
            return 1

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
