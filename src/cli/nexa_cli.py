from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass, replace
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

    for path_arg in (getattr(args, "circuit", None), getattr(args, "artifact", None)):
        if not path_arg:
            continue
        try:
            resolved_path = Path(path_arg).expanduser().resolve()
        except Exception:
            resolved_path = None

        if resolved_path is not None:
            resolved_parent = resolved_path.parent if resolved_path.suffix else resolved_path
            resolved_root = _find_repo_root_from_path(resolved_parent)
            if resolved_root is not None:
                candidates.append(resolved_root / ".env")
            candidates.append(resolved_parent / ".env")

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

    savefile_commit = savefile_sub.add_parser("commit")
    savefile_commit.add_argument("input", help="Path to input .nex savefile")
    savefile_commit.add_argument("output", help="Path to output .nex commit snapshot")
    savefile_commit.add_argument("--commit-id", required=True, help="Commit Snapshot identifier")
    savefile_commit.add_argument("--parent-commit-id", help="Optional parent commit id")
    savefile_commit.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

    savefile_checkout = savefile_sub.add_parser("checkout")
    savefile_checkout.add_argument("input", help="Path to input .nex commit snapshot")
    savefile_checkout.add_argument("output", help="Path to output .nex working save")
    savefile_checkout.add_argument("--working-save-id", help="Optional Working Save identifier override")
    savefile_checkout.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

    savefile_upgrade = savefile_sub.add_parser("upgrade")
    savefile_upgrade.add_argument("input", help="Path to legacy input .nex savefile")
    savefile_upgrade.add_argument("output", help="Path to output public working save")
    savefile_upgrade.add_argument("--working-save-id", help="Optional Working Save identifier override")
    savefile_upgrade.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

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

    savefile_share = savefile_sub.add_parser("share")
    savefile_share_sub = savefile_share.add_subparsers(dest="savefile_share_command")

    savefile_share_export = savefile_share_sub.add_parser("export")
    savefile_share_export.add_argument("input", help="Path to input public .nex artifact")
    savefile_share_export.add_argument("output", help="Path to output public link-share payload")
    savefile_share_export.add_argument("--share-id", help="Optional share identifier override")
    savefile_share_export.add_argument("--title", help="Optional share title override")
    savefile_share_export.add_argument("--summary", help="Optional share summary override")
    savefile_share_export.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

    savefile_share_info = savefile_share_sub.add_parser("info")
    savefile_share_info.add_argument("input", help="Path to input public link-share payload")

    savefile_share_import = savefile_share_sub.add_parser("import")
    savefile_share_import.add_argument("input", help="Path to input public link-share payload")
    savefile_share_import.add_argument("output", help="Path to output imported public .nex artifact")
    savefile_share_import.add_argument("--force", action="store_true", help="Overwrite output file if it already exists")

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

    design_parser = sub.add_parser("design")
    design_parser.add_argument("request_text", help="Natural-language Designer AI request")
    design_parser.add_argument(
        "--save",
        "--working-save-ref",
        dest="working_save_ref",
        help="Working save reference for an existing draft context",
    )
    design_parser.add_argument(
        "--artifact",
        help="Optional .nex artifact path used to build Designer session state context",
    )
    design_parser.add_argument(
        "--backend",
        help="Optional semantic backend preset (for example: claude, gpt, gemini, perplexity)",
    )
    design_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Emit structured JSON instead of only the rendered preview",
    )
    design_parser.add_argument(
        "--out",
        help="Optional path to save the structured Designer proposal payload as JSON",
    )

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

def _build_new_working_save(args):
    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("savefile output must use .nex extension")

    name = args.name or output_path.stem
    template_name = args.template or args.node_type

    from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
    from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
    from src.storage.legacy_savefile_bridge import default_working_save_id

    ui_metadata = {
        "created_by": "nexa savefile new",
        "template": template_name,
    }

    if template_name == "plugin":
        return WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version=args.version,
                storage_role="working_save",
                working_save_id=default_working_save_id(name, fallback=output_path.stem),
                name=name,
                description=args.description,
            ),
            circuit=CircuitModel(
                entry=args.entry,
                nodes=[
                    {
                        "id": args.entry,
                        "type": "plugin",
                        "resource_ref": {"plugin": args.plugin_id},
                        "inputs": {},
                        "outputs": {"result": "output.value"},
                    }
                ],
                edges=[],
                outputs=[{"name": "result", "node_id": args.entry, "path": "output.value"}],
            ),
            resources=ResourcesModel(
                prompts={},
                providers={},
                plugins={args.plugin_id: {"entry": args.plugin_entry}},
            ),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata=ui_metadata),
        )

    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version=args.version,
            storage_role="working_save",
            working_save_id=default_working_save_id(name, fallback=output_path.stem),
            name=name,
            description=args.description,
        ),
        circuit=CircuitModel(
            entry=args.entry,
            nodes=[
                {
                    "id": args.entry,
                    "type": "ai",
                    "resource_ref": {"prompt": args.prompt_id, "provider": args.provider_id},
                    "inputs": {},
                    "outputs": {"result": "output.value"},
                }
            ],
            edges=[],
            outputs=[{"name": "result", "node_id": args.entry, "path": "output.value"}],
        ),
        resources=ResourcesModel(
            prompts={args.prompt_id: {"template": args.prompt_template}},
            providers={
                args.provider_id: {
                    "type": args.provider_type,
                    "model": args.provider_model,
                    "config": {},
                }
            },
            plugins={},
        ),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=ui_metadata),
    )


def _read_json_object(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(".nex root must be a JSON object")
    return data


def _is_public_nex_payload(data: dict) -> bool:
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    return meta.get("storage_role") in {"working_save", "commit_snapshot"}


def _is_public_nex_link_share_payload(data: dict) -> bool:
    from src.storage.share_api import is_public_nex_link_share_payload

    return is_public_nex_link_share_payload(data)


def _load_public_nex_artifact(input_path: Path):
    from src.storage.nex_api import load_nex

    loaded = load_nex(input_path)
    if loaded.parsed_model is None:
        blocking_messages = [finding.message for finding in loaded.findings if getattr(finding, "blocking", False)]
        detail = blocking_messages[0] if blocking_messages else f"public .nex artifact could not be loaded ({loaded.load_status})"
        raise ValueError(detail)
    return loaded


def _load_public_nex_link_share(input_path: Path) -> dict:
    from src.storage.nex_api import load_nex
    from src.storage.share_api import load_public_nex_link_share

    share_payload = load_public_nex_link_share(input_path)
    loaded = load_nex(share_payload["artifact"])
    if loaded.parsed_model is None:
        blocking_messages = [finding.message for finding in loaded.findings if getattr(finding, "blocking", False)]
        detail = blocking_messages[0] if blocking_messages else f"public link share artifact could not be loaded ({loaded.load_status})"
        raise ValueError(detail)
    return {"share_payload": share_payload, "loaded": loaded}


def _load_cli_savefile_source(input_value: str):
    from src.contracts.savefile_loader import load_savefile_from_path

    input_path = Path(input_value)
    if input_path.suffix not in {".nex", ".json"}:
        raise ValueError("savefile input must use .nex extension unless it is a public link-share payload")
    if input_path.suffix == ".json" and not input_path.exists():
        raise ValueError(
            "savefile input must use .nex extension unless it is an existing public link-share payload"
        )

    raw_data = _read_json_object(input_path)
    if _is_public_nex_link_share_payload(raw_data):
        share_source = _load_public_nex_link_share(input_path)
        return {
            "mode": "public_share",
            "input_path": input_path,
            "raw_data": raw_data,
            "share_payload": share_source["share_payload"],
            "loaded": share_source["loaded"],
        }
    if _is_public_nex_payload(raw_data):
        if input_path.suffix != ".nex":
            raise ValueError("public .nex artifact input must use .nex extension")
        return {
            "mode": "public",
            "input_path": input_path,
            "raw_data": raw_data,
            "loaded": _load_public_nex_artifact(input_path),
        }

    if input_path.suffix != ".nex":
        raise ValueError("savefile input must use .nex extension unless it is a public link-share payload")

    return {
        "mode": "legacy",
        "input_path": input_path,
        "raw_data": raw_data,
        "savefile": load_savefile_from_path(str(input_path)),
    }


def _blocking_validation_messages(report) -> list[str]:
    findings = getattr(report, "findings", []) or []
    return [finding.message for finding in findings if getattr(finding, "blocking", False)]


def _public_artifact_payload(loaded, *, input_path: Path) -> dict:
    parsed = loaded.parsed_model
    if parsed is None:
        raise ValueError("public .nex artifact is not loadable")

    meta = getattr(parsed, "meta", None)
    circuit = getattr(parsed, "circuit", None)
    resources = getattr(parsed, "resources", None)
    state = getattr(parsed, "state", None)
    ui = getattr(parsed, "ui", None)
    canonical_ref = getattr(meta, "working_save_id", None) or getattr(meta, "commit_id", None)
    payload = {
        "status": "ok",
        "input": str(input_path),
        "storage_role": loaded.storage_role,
        "load_status": loaded.load_status,
        "name": getattr(meta, "name", None),
        "version": getattr(meta, "format_version", None),
        "description": getattr(meta, "description", None),
        "entry": getattr(circuit, "entry", None),
        "node_count": len(getattr(circuit, "nodes", []) or []),
        "edge_count": len(getattr(circuit, "edges", []) or []),
        "prompt_count": len(getattr(resources, "prompts", {}) or {}),
        "provider_count": len(getattr(resources, "providers", {}) or {}),
        "plugin_count": len(getattr(resources, "plugins", {}) or {}),
        "state_input_key_count": len(getattr(state, "input", {}) or {}),
        "state_working_key_count": len(getattr(state, "working", {}) or {}),
        "state_memory_key_count": len(getattr(state, "memory", {}) or {}),
        "ui_layout_key_count": len(getattr(ui, "layout", {}) or {}) if ui is not None else 0,
        "ui_metadata_key_count": len(getattr(ui, "metadata", {}) or {}) if ui is not None else 0,
        "finding_count": len(getattr(loaded, "findings", []) or []),
        "blocking_count": sum(1 for finding in (getattr(loaded, "findings", []) or []) if getattr(finding, "blocking", False)),
        "canonical_ref": canonical_ref,
    }
    if getattr(loaded, "migration_notes", None):
        payload["migration_notes"] = list(loaded.migration_notes or [])
    return payload


def _public_share_payload(share_payload: dict, loaded, *, input_path: Path) -> dict:
    payload = _public_artifact_payload(loaded, input_path=input_path)
    share = share_payload.get("share", {}) if isinstance(share_payload.get("share"), dict) else {}
    lifecycle = share.get("lifecycle", {}) if isinstance(share.get("lifecycle"), dict) else {}
    payload.update({
        "input_mode": "public_link_share",
        "share_id": share.get("share_id"),
        "share_path": share.get("share_path"),
        "share_title": share.get("title"),
        "share_summary": share.get("summary"),
        "viewer_capabilities": share.get("viewer_capabilities", []),
        "operation_capabilities": share.get("operation_capabilities", []),
        "lifecycle_state": lifecycle.get("state"),
        "created_at": lifecycle.get("created_at"),
        "updated_at": lifecycle.get("updated_at"),
        "expires_at": lifecycle.get("expires_at"),
        "issued_by_user_ref": lifecycle.get("issued_by_user_ref"),
    })
    return payload


def _persist_public_working_save(model, input_path: Path) -> None:
    from src.storage.nex_api import validate_working_save
    from src.storage.serialization import save_nex_artifact_file

    report = validate_working_save(model)
    blocking_messages = _blocking_validation_messages(report)
    if blocking_messages:
        raise ValueError(blocking_messages[0])
    save_nex_artifact_file(model, input_path)


def savefile_new_command(args) -> int:
    from src.storage.nex_api import validate_working_save
    from src.storage.serialization import save_nex_artifact_file

    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("savefile output must use .nex extension")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    working_save = _build_new_working_save(args)
    report = validate_working_save(working_save)
    blocking_messages = _blocking_validation_messages(report)
    if blocking_messages:
        raise ValueError(blocking_messages[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_nex_artifact_file(working_save, output_path)

    payload = {
        "status": "ok",
        "output": str(output_path),
        "storage_role": "working_save",
        "canonical_ref": working_save.meta.working_save_id,
        "name": working_save.meta.name,
        "entry": working_save.circuit.entry,
        "node_type": str((working_save.circuit.nodes or [{}])[0].get("type") or ""),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_validate_command(args) -> int:
    from src.contracts.savefile_validator import validate_savefile
    from src.storage.nex_api import validate_commit_snapshot, validate_working_save

    loaded_source = _load_cli_savefile_source(args.input)
    input_path = loaded_source["input_path"]

    if loaded_source["mode"] in {"public", "public_share"}:
        loaded = loaded_source["loaded"]
        parsed = loaded.parsed_model
        if loaded.storage_role == "working_save":
            report = validate_working_save(parsed)
        else:
            report = validate_commit_snapshot(parsed)
        blocking_messages = _blocking_validation_messages(report)
        payload = {
            "status": "ok" if not blocking_messages else "error",
            "input": str(input_path),
            "storage_role": loaded.storage_role,
            "name": getattr(getattr(parsed, "meta", None), "name", None),
            "entry": getattr(getattr(parsed, "circuit", None), "entry", None),
            "node_count": len(getattr(getattr(parsed, "circuit", None), "nodes", []) or []),
            "result": getattr(report, "result", None),
            "warnings": [getattr(finding, "message", "") for finding in (getattr(report, "findings", []) or []) if not getattr(finding, "blocking", False)],
            "warning_count": getattr(report, "warning_count", 0),
            "blocking_count": getattr(report, "blocking_count", 0),
            "canonical_ref": getattr(getattr(parsed, "meta", None), "working_save_id", None) or getattr(getattr(parsed, "meta", None), "commit_id", None),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if not blocking_messages else 1

    savefile = loaded_source["savefile"]
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
    loaded_source = _load_cli_savefile_source(args.input)
    input_path = loaded_source["input_path"]

    if loaded_source["mode"] == "public":
        payload = _public_artifact_payload(loaded_source["loaded"], input_path=input_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if loaded_source["mode"] == "public_share":
        payload = _public_share_payload(loaded_source["share_payload"], loaded_source["loaded"], input_path=input_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    savefile = loaded_source["savefile"]

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
    source = _load_cli_savefile_source(input_value)
    if source["mode"] == "public_share":
        raise ValueError("savefile edit commands do not modify public link shares; import or checkout first")
    if source["mode"] == "public":
        loaded = source["loaded"]
        if loaded.storage_role != "working_save":
            raise ValueError("savefile edit commands only support working_save artifacts")
        return source["input_path"], loaded.parsed_model, "public"
    return source["input_path"], source["savefile"], "legacy"


def _persist_edited_savefile(savefile, input_path: Path, mode: str) -> None:
    if mode == "public":
        _persist_public_working_save(savefile, input_path)
        return

    from src.contracts.savefile_serializer import save_savefile_file
    from src.contracts.savefile_validator import validate_savefile

    validate_savefile(savefile)
    save_savefile_file(savefile, str(input_path))



def _load_commit_source(input_value: str):
    from src.storage.legacy_savefile_bridge import working_save_model_from_legacy_savefile

    source = _load_cli_savefile_source(input_value)
    if source["mode"] == "public_share":
        raise ValueError("savefile commit does not accept public link shares directly; import the shared artifact first")
    if source["mode"] == "public":
        loaded = source["loaded"]
        if loaded.storage_role != "working_save":
            raise ValueError("savefile commit only supports working_save artifacts")
        return source["input_path"], loaded.parsed_model, "public"
    return source["input_path"], working_save_model_from_legacy_savefile(source["savefile"]), "legacy"



def _load_checkout_source(input_value: str):
    source = _load_cli_savefile_source(input_value)
    if source["mode"] not in {"public", "public_share"}:
        raise ValueError("savefile checkout only supports public commit_snapshot artifacts or public link shares")
    if source["mode"] == "public_share":
        from src.storage.share_api import ensure_public_nex_link_share_operation_allowed

        ensure_public_nex_link_share_operation_allowed(source["share_payload"], "checkout_working_copy")
    loaded = source["loaded"]
    if loaded.storage_role != "commit_snapshot":
        raise ValueError("savefile checkout only supports commit_snapshot artifacts")
    resolved_mode = "public_commit_snapshot" if source["mode"] == "public" else "public_share"
    return source["input_path"], loaded.parsed_model, resolved_mode



def savefile_checkout_command(args) -> int:
    from src.storage.lifecycle_api import create_working_save_from_commit_snapshot
    from src.storage.nex_api import validate_working_save
    from src.storage.serialization import save_nex_artifact_file

    input_path, commit_snapshot, source_mode = _load_checkout_source(args.input)
    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("working save output must use .nex extension")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    working_save = create_working_save_from_commit_snapshot(
        commit_snapshot,
        working_save_id=getattr(args, "working_save_id", None),
    )
    report = validate_working_save(working_save)
    blocking_messages = _blocking_validation_messages(report)
    if blocking_messages:
        raise ValueError(blocking_messages[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_nex_artifact_file(working_save, output_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "output": str(output_path),
        "input_mode": source_mode,
        "storage_role": "working_save",
        "canonical_ref": working_save.meta.working_save_id,
        "working_save_id": working_save.meta.working_save_id,
        "source_commit_id": commit_snapshot.meta.commit_id,
        "name": working_save.meta.name,
        "entry": working_save.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_upgrade_command(args) -> int:
    from src.storage.legacy_savefile_bridge import working_save_model_from_legacy_savefile
    from src.storage.nex_api import validate_working_save
    from src.storage.serialization import save_nex_artifact_file

    source = _load_cli_savefile_source(args.input)
    if source["mode"] != "legacy":
        raise ValueError("savefile upgrade only supports legacy savefiles; public artifacts or shares are already role-aware")

    input_path = source["input_path"]
    working_save = working_save_model_from_legacy_savefile(
        source["savefile"],
        working_save_id=getattr(args, "working_save_id", None),
    )
    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("working save output must use .nex extension")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    report = validate_working_save(working_save)
    blocking_messages = _blocking_validation_messages(report)
    if blocking_messages:
        raise ValueError(blocking_messages[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_nex_artifact_file(working_save, output_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "output": str(output_path),
        "input_mode": "legacy",
        "storage_role": "working_save",
        "canonical_ref": working_save.meta.working_save_id,
        "working_save_id": working_save.meta.working_save_id,
        "name": working_save.meta.name,
        "entry": working_save.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_share_export_command(args) -> int:
    from src.storage.share_api import describe_public_nex_link_share, save_public_nex_link_share_file

    source = _load_cli_savefile_source(args.input)
    if source["mode"] not in {"public", "public_share"}:
        raise ValueError("savefile share export only supports public .nex artifacts or existing public link shares")

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    model_or_data = source["share_payload"]["artifact"] if source["mode"] == "public_share" else source["loaded"].parsed_model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = save_public_nex_link_share_file(
        model_or_data,
        output_path,
        share_id=getattr(args, "share_id", None),
        title=getattr(args, "title", None),
        summary=getattr(args, "summary", None),
    )
    descriptor = describe_public_nex_link_share(written)
    payload = {
        "status": "ok",
        "input": str(source["input_path"]),
        "output": str(written),
        "input_mode": source["mode"],
        "share_id": descriptor.share_id,
        "share_path": descriptor.share_path,
        "storage_role": descriptor.storage_role,
        "canonical_ref": descriptor.canonical_ref,
        "title": descriptor.title,
        "summary": descriptor.summary,
        "viewer_capabilities": list(descriptor.viewer_capabilities),
        "operation_capabilities": list(descriptor.operation_capabilities),
        "lifecycle_state": descriptor.lifecycle_state,
        "created_at": descriptor.created_at,
        "updated_at": descriptor.updated_at,
        "expires_at": descriptor.expires_at,
        "issued_by_user_ref": descriptor.issued_by_user_ref,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_share_info_command(args) -> int:
    loaded_source = _load_cli_savefile_source(args.input)
    if loaded_source["mode"] != "public_share":
        raise ValueError("savefile share info only supports public link-share payloads")
    payload = _public_share_payload(loaded_source["share_payload"], loaded_source["loaded"], input_path=loaded_source["input_path"])
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_share_import_command(args) -> int:
    from src.storage.serialization import save_nex_artifact_file

    loaded_source = _load_cli_savefile_source(args.input)
    if loaded_source["mode"] != "public_share":
        raise ValueError("savefile share import only supports public link-share payloads")

    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("share import output must use .nex extension")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    from src.storage.share_api import ensure_public_nex_link_share_operation_allowed

    ensure_public_nex_link_share_operation_allowed(loaded_source["share_payload"], "import_copy")

    parsed_model = loaded_source["loaded"].parsed_model
    if parsed_model is None:
        raise ValueError("public link share artifact is not loadable")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_nex_artifact_file(parsed_model, output_path)
    share = loaded_source["share_payload"].get("share", {}) if isinstance(loaded_source["share_payload"].get("share"), dict) else {}
    payload = {
        "status": "ok",
        "input": str(loaded_source["input_path"]),
        "output": str(output_path),
        "input_mode": "public_share",
        "share_id": share.get("share_id"),
        "storage_role": loaded_source["loaded"].storage_role,
        "canonical_ref": getattr(getattr(parsed_model, "meta", None), "working_save_id", None) or getattr(getattr(parsed_model, "meta", None), "commit_id", None),
        "name": getattr(getattr(parsed_model, "meta", None), "name", None),
        "entry": getattr(getattr(parsed_model, "circuit", None), "entry", None),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def savefile_commit_command(args) -> int:
    from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
    from src.storage.serialization import save_nex_artifact_file

    input_path, working_save, source_mode = _load_commit_source(args.input)
    output_path = Path(args.output)
    if output_path.suffix != ".nex":
        raise ValueError("commit snapshot output must use .nex extension")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists: {output_path}")

    snapshot = create_commit_snapshot_from_working_save(
        working_save,
        commit_id=args.commit_id,
        parent_commit_id=getattr(args, "parent_commit_id", None),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_nex_artifact_file(snapshot, output_path)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "output": str(output_path),
        "input_mode": source_mode,
        "storage_role": "commit_snapshot",
        "canonical_ref": snapshot.meta.commit_id,
        "commit_id": snapshot.meta.commit_id,
        "source_working_save_id": snapshot.meta.source_working_save_id,
        "name": snapshot.meta.name,
        "entry": snapshot.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_set_name_command(args) -> int:
    input_path, savefile, mode = _load_editable_savefile(args.input)
    if mode == "public":
        if not args.name.strip():
            raise ValueError("Working Save name must be a non-empty string")
        savefile = replace(savefile, meta=replace(savefile.meta, name=args.name))
    else:
        savefile.meta.name = args.name
    _persist_edited_savefile(savefile, input_path, mode)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_set_entry_command(args) -> int:
    input_path, savefile, mode = _load_editable_savefile(args.input)
    if mode == "public":
        node_ids = {str(node.get("id") or node.get("node_id") or "") for node in savefile.circuit.nodes}
        if args.entry not in node_ids:
            raise ValueError(f"Entry node '{args.entry}' not found in nodes")
        savefile = replace(savefile, circuit=replace(savefile.circuit, entry=args.entry))
    else:
        savefile.circuit.entry = args.entry
    _persist_edited_savefile(savefile, input_path, mode)

    payload = {
        "status": "ok",
        "input": str(input_path),
        "name": savefile.meta.name,
        "entry": savefile.circuit.entry,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0



def savefile_set_description_command(args) -> int:
    input_path, savefile, mode = _load_editable_savefile(args.input)
    if mode == "public":
        savefile = replace(savefile, meta=replace(savefile.meta, description=args.description))
    else:
        savefile.meta.description = args.description
    _persist_edited_savefile(savefile, input_path, mode)

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
            "validation_status": item.get("validation_status"),
            "validation_reason_codes": item.get("validation_reason_codes") if isinstance(item.get("validation_reason_codes"), list) else [],
            "artifact_schema_version": item.get("artifact_schema_version"),
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
        typed_artifact_ids = item.get("typed_artifact_refs") if isinstance(item.get("typed_artifact_refs"), list) else []
        merged_artifact_ids = [artifact_id for artifact_id in [*artifact_ids, *typed_artifact_ids] if artifact_id in artifact_map]
        nodes[node_id] = {
            "status": item.get("status"),
            "output": output_preview,
            "artifacts": {artifact_id: artifact_map[artifact_id] for artifact_id in merged_artifact_ids if artifact_id in artifact_map},
            "verifier_status": item.get("verifier_status"),
            "verifier_reason_codes": item.get("verifier_reason_codes") if isinstance(item.get("verifier_reason_codes"), list) else [],
            "typed_artifact_refs": typed_artifact_ids,
        }
        context[f"{node_id}.output"] = output_preview

    outputs = execution_record.get("outputs") if isinstance(execution_record.get("outputs"), dict) else {}
    for item in outputs.get("final_outputs", []):
        if not isinstance(item, dict) or not item.get("output_ref"):
            continue
        context[f"output.{item['output_ref']}"] = item.get("value_payload")

    if not nodes and not context and not artifact_map:
        return None

    observability_payload = execution_record.get("observability") if isinstance(execution_record.get("observability"), dict) else {}
    observability = {}
    if observability_payload.get("verifier_summary") is not None:
        observability["verifier_summary"] = observability_payload.get("verifier_summary")

    return {
        "run_id": run_id,
        "nodes": nodes,
        "artifacts": artifact_map,
        "context": context,
        "observability": observability,
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
            "observability": raw.get("observability") if isinstance(raw.get("observability"), dict) else {},
        }

    explicit_execution_record = raw.get("execution_record") if isinstance(raw.get("execution_record"), dict) else {}
    snapshot = _snapshot_from_execution_record_payload(explicit_execution_record)
    if snapshot is not None:
        return snapshot

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
        "observability": {},
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

    if _is_public_nex_link_share_payload(data):
        return True

    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    if meta.get("storage_role") in {"working_save", "commit_snapshot"}:
        return True

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


def _savefile_payload(
    savefile,
    trace,
    started_at,
    ended_at,
    *,
    storage_role: str | None = None,
    canonical_ref: str | None = None,
    working_save_id: str | None = None,
    commit_id: str | None = None,
    source_share_id: str | None = None,
):
    payload = create_serialized_savefile_execution_payload(
        savefile,
        trace,
        started_at=started_at,
        ended_at=ended_at,
        storage_role=storage_role,
        canonical_ref=canonical_ref,
        working_save_id=working_save_id,
        commit_id=commit_id,
    )
    if storage_role is not None:
        payload["storage_role"] = storage_role
    if canonical_ref is not None:
        payload["canonical_ref"] = canonical_ref
    if source_share_id is not None:
        payload["source_share_id"] = source_share_id
        payload.setdefault("source_artifact", {})["share_id"] = source_share_id
        payload.setdefault("replay_payload", {}).setdefault("source_artifact", {})["share_id"] = source_share_id
    return payload


def _run_savefile_command(args):
    started_at = time.time()
    cli_state = load_cli_state(args.state, args.var)
    execution_context, trace = execute_savefile(
        args.circuit,
        input_overrides=cli_state or None,
        run_id=f"savefile-{int(started_at)}",
    )
    ended_at = time.time()

    payload = _savefile_payload(
        execution_context.savefile,
        trace,
        started_at,
        ended_at,
        storage_role=execution_context.storage_role,
        canonical_ref=execution_context.canonical_ref,
        working_save_id=execution_context.working_save_id,
        commit_id=execution_context.commit_id,
        source_share_id=getattr(execution_context, "share_id", None),
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

    metrics = _extract_savefile_metrics(trace)
    savefile = execution_context.savefile
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


def _load_designer_cli_artifact(artifact_path: str | None):
    if not artifact_path:
        return None
    from src.storage.validators.shared_validator import load_nex

    loaded = load_nex(artifact_path)
    if loaded.parsed_model is None:
        blocking_messages = [finding.message for finding in loaded.findings if getattr(finding, "blocking", False)]
        detail = "; ".join(blocking_messages) if blocking_messages else f"load_status={loaded.load_status}"
        raise ValueError(f"Unable to load Designer artifact context from {artifact_path}: {detail}")
    return loaded.parsed_model



def design_command(args) -> int:
    from src.designer.proposal_flow import DesignerProposalFlow
    from src.designer.request_normalizer import DesignerRequestNormalizer
    from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder

    artifact = _load_designer_cli_artifact(getattr(args, "artifact", None))
    has_existing_target = bool(getattr(args, "working_save_ref", None) or artifact is not None)
    session_state_card = DesignerSessionStateCardBuilder().build(
        request_text=args.request_text,
        artifact=artifact,
        session_id=None,
        target_scope_mode="existing_circuit" if has_existing_target else "new_circuit",
    )

    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset=getattr(args, "backend", None),
        semantic_backend_preset_use_env=bool(getattr(args, "backend", None)),
        use_llm_semantic_interpreter=bool(getattr(args, "backend", None)),
        llm_backend_required=bool(getattr(args, "backend", None)),
    )
    flow = DesignerProposalFlow(normalizer=normalizer)
    bundle = flow.propose(
        args.request_text,
        working_save_ref=getattr(args, "working_save_ref", None),
        session_state_card=session_state_card,
    )

    payload = {
        "status": "ok",
        "command": "design",
        "request_text": bundle.request_text,
        "target_working_save_ref": bundle.target_working_save_ref,
        "rendered_preview": bundle.rendered_preview,
        "bundle": _to_json_safe(bundle),
    }

    if getattr(args, "out", None):
        out_path = Path(args.out)
        if out_path.parent != Path('.'):
            out_path.parent.mkdir(parents=True, exist_ok=True)
        save_output(payload, out_path)

    if getattr(args, "output_json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(bundle.rendered_preview)
    return 0



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
            if getattr(args, "savefile_command", None) == "commit":
                return savefile_commit_command(args)
            if getattr(args, "savefile_command", None) == "checkout":
                return savefile_checkout_command(args)
            if getattr(args, "savefile_command", None) == "upgrade":
                return savefile_upgrade_command(args)
            if getattr(args, "savefile_command", None) == "set-name":
                return savefile_set_name_command(args)
            if getattr(args, "savefile_command", None) == "set-entry":
                return savefile_set_entry_command(args)
            if getattr(args, "savefile_command", None) == "set-description":
                return savefile_set_description_command(args)
            if getattr(args, "savefile_command", None) == "template":
                if getattr(args, "savefile_template_command", None) == "list":
                    return savefile_template_list_command(args)
            if getattr(args, "savefile_command", None) == "share":
                if getattr(args, "savefile_share_command", None) == "export":
                    return savefile_share_export_command(args)
                if getattr(args, "savefile_share_command", None) == "info":
                    return savefile_share_info_command(args)
                if getattr(args, "savefile_share_command", None) == "import":
                    return savefile_share_import_command(args)
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

    if args.command == "design":
        try:
            return design_command(args)
        except Exception as exc:
            payload = {
                "status": "error",
                "error_type": type(exc).__name__,
                "message": str(exc),
                "command": "design",
                "request_text": getattr(args, "request_text", None),
                "working_save_ref": getattr(args, "working_save_ref", None),
                "artifact": getattr(args, "artifact", None),
                "backend": getattr(args, "backend", None),
            }
            print_error_payload(payload)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
