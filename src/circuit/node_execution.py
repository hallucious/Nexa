from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol, Union
from src.utils.observability import is_observability_enabled, make_event, emit_event


class Stage(str, Enum):
    PRE = "pre"
    CORE = "core"
    POST = "post"


PreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
CoreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
PostHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]

StagedHandler = Dict[str, Any]  # keys: pre/core/post


def is_staged_handler(obj: Any) -> bool:
    return isinstance(obj, dict) and any(k in obj for k in ("pre", "core", "post"))


def _merge(base: Dict[str, Any], patch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not patch:
        return dict(base)
    merged = dict(base)
    merged.update(patch)
    return merged


class PromptSpecLike(Protocol):
    prompt_id: str
    version: str

    def validate(self, variables: Dict[str, Any]) -> None: ...
    def render(self, *, variables: Dict[str, Any]) -> str: ...
    @property
    def prompt_hash(self) -> str: ...


class PromptRegistryLike(Protocol):
    def get(self, prompt_id: str) -> PromptSpecLike: ...


def _resolve_prompt_variables(*, node_raw: Dict[str, Any], input_payload: Dict[str, Any]) -> Dict[str, Any]:
    variables: Dict[str, Any] = {}
    nr_vars = node_raw.get("prompt_variables")
    if isinstance(nr_vars, dict):
        variables.update(nr_vars)

    in_vars = input_payload.get("prompt_variables")
    if isinstance(in_vars, dict):
        variables.update(in_vars)

    return variables


def _inject_rendered_prompt(
    *,
    node_raw: Dict[str, Any],
    core_input: Dict[str, Any],
    prompt_registry: Optional[PromptRegistryLike],
) -> Dict[str, Any]:
    prompt_id = node_raw.get("prompt_id")
    if not prompt_id:
        return core_input

    if not isinstance(prompt_id, str):
        raise TypeError("node_raw.prompt_id must be a string")

    if prompt_registry is None:
        raise ValueError("prompt_id is set but prompt_registry is not provided")

    spec = prompt_registry.get(prompt_id)
    variables = _resolve_prompt_variables(node_raw=node_raw, input_payload=core_input)

    spec.validate(variables)
    rendered = spec.render(variables=variables)
    meta = {
        "prompt_id": spec.prompt_id,
        "version": spec.version,
        "prompt_hash": spec.prompt_hash,
    }

    injected = dict(core_input)
    injected["__rendered_prompt__"] = rendered
    injected["__prompt_meta__"] = meta
    return injected




def _obs_ctx(input_payload: Dict[str, Any], node_raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ctx = input_payload.get("__obs_ctx__")
    if isinstance(ctx, dict):
        return ctx
    ctx = node_raw.get("__obs_ctx__")
    if isinstance(ctx, dict):
        return ctx
    return None
def run_node_stages(
    *,
    node_id: str,
    node_raw: Dict[str, Any],
    input_payload: Dict[str, Any],
    handler: Union[CoreHandler, StagedHandler],
    prompt_registry: Optional[PromptRegistryLike] = None,
) -> Dict[str, Any]:
    pre_fn: Optional[PreHandler] = None
    core_fn: Optional[CoreHandler] = None
    post_fn: Optional[PostHandler] = None

    if callable(handler):
        core_fn = handler  # type: ignore[assignment]
    elif is_staged_handler(handler):
        pre_fn = handler.get("pre")
        core_fn = handler.get("core")
        post_fn = handler.get("post")
    else:
        raise TypeError("Unsupported handler type for circuit execution")

    core_input = dict(input_payload)
    obs_enabled = is_observability_enabled(node_raw)
    ctx = _obs_ctx(core_input, node_raw) if obs_enabled else None

    # PRE
    if obs_enabled and ctx is not None:
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='pre', event='node.stage.enter'))
    if pre_fn is not None:
        pre_patch = pre_fn(node_id, node_raw, dict(core_input))
        core_input = _merge(core_input, pre_patch)

    if obs_enabled and ctx is not None:
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='pre', event='node.stage.exit', success=True))
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='core', event='node.stage.enter'))

    # PROMPT (Core-input injection)
    core_input = _inject_rendered_prompt(node_raw=node_raw, core_input=core_input, prompt_registry=prompt_registry)

    # CORE
    if core_fn is None:
        raise ValueError("Staged handler missing 'core'")
    core_output = core_fn(node_id, node_raw, dict(core_input))

    if obs_enabled and ctx is not None:
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='core', event='node.stage.exit', success=True))
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='post', event='node.stage.enter'))

    # POST
    final_output = dict(core_output)
    if post_fn is not None:
        post_patch = post_fn(node_id, node_raw, dict(final_output))
        final_output = _merge(final_output, post_patch)

    if obs_enabled and ctx is not None:
        emit_event(make_event(run_id=str(ctx.get('run_id','run-unknown')), circuit_id=str(ctx.get('circuit_id','c-unknown')), node_id=node_id, stage='post', event='node.stage.exit', success=True))

    return final_output
