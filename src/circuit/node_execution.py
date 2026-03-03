from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol, Union


class Stage(str, Enum):
    PRE = "pre"
    CORE = "core"
    POST = "post"


# Circuit-stage handler signatures:
# - pre:  (node_id, node_raw, input_payload) -> patch (merged into input)
# - core: (node_id, node_raw, input_payload) -> output_payload
# - post: (node_id, node_raw, core_output)  -> patch (merged into core output)
PreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
CoreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
PostHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


PipelineHandler = Dict[str, Any]  # keys: pre/core/post


def is_pipeline_handler(obj: Any) -> bool:
    return isinstance(obj, dict) and any(k in obj for k in ("pre", "core", "post"))


def _merge(base: Dict[str, Any], patch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not patch:
        return dict(base)
    merged = dict(base)
    merged.update(patch)
    return merged


@dataclass
class StageRunReport:
    ran_pre: bool
    ran_core: bool
    ran_post: bool


class PromptSpecLike(Protocol):
    prompt_id: str
    version: str

    def validate(self, variables: Dict[str, Any]) -> None: ...
    def render(self, variables: Dict[str, Any]) -> str: ...
    def prompt_hash(self) -> str: ...


class PromptRegistryLike(Protocol):
    def get(self, prompt_id: str) -> PromptSpecLike: ...


def _resolve_prompt_variables(
    *, node_raw: Dict[str, Any], input_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Resolve variables for prompt rendering.

    Rule (v1, minimal):
    - Start from node_raw["prompt_variables"] if present (dict).
    - Overlay input_payload["prompt_variables"] if present (dict).
    - No implicit extraction from input_payload keys (keeps behavior explicit/stable).
    """
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
    """If node_raw declares prompt_id, render the prompt deterministically and inject.

    Injected keys (v1):
    - __rendered_prompt__: str
    - __prompt_meta__: {prompt_id, version, prompt_hash}
    """
    prompt_id = node_raw.get("prompt_id")
    if not prompt_id:
        return core_input

    if not isinstance(prompt_id, str):
        raise TypeError("node_raw.prompt_id must be a string")

    if prompt_registry is None:
        raise ValueError("prompt_id is set but prompt_registry is not provided")

    spec = prompt_registry.get(prompt_id)
    variables = _resolve_prompt_variables(node_raw=node_raw, input_payload=core_input)

    # Contract enforcement: validate → render (deterministic)
    spec.validate(variables)
    rendered = spec.render(variables)
    meta = {
        "prompt_id": spec.prompt_id,
        "version": spec.version,
        "prompt_hash": spec.prompt_hash(),
    }

    injected = dict(core_input)
    injected["__rendered_prompt__"] = rendered
    injected["__prompt_meta__"] = meta
    return injected


def run_node_pipeline(
    *,
    node_id: str,
    node_raw: Dict[str, Any],
    input_payload: Dict[str, Any],
    handler: Union[CoreHandler, PipelineHandler],
    prompt_registry: Optional[PromptRegistryLike] = None,
) -> Dict[str, Any]:
    """Run a node under mandatory Pre → Core → Post stages.

    Enforcement:
    - If handler is callable: treated as CORE only; PRE/POST are no-ops.
    - If handler is pipeline dict: PRE/CORE/POST are executed in order (if present).
    - Prompt rendering is Core-input injection only (PROMPT-CONTRACT v1.0.0):
        * node_raw["prompt_id"] activates prompt rendering via prompt_registry.
        * rendered prompt and prompt_meta are injected into core input.
    """
    pre_fn: Optional[PreHandler] = None
    core_fn: Optional[CoreHandler] = None
    post_fn: Optional[PostHandler] = None

    if callable(handler):
        core_fn = handler  # type: ignore[assignment]
    elif is_pipeline_handler(handler):
        pre_fn = handler.get("pre")
        core_fn = handler.get("core")
        post_fn = handler.get("post")
    else:
        raise TypeError("Unsupported handler type for circuit execution")

    # PRE
    core_input = dict(input_payload)
    if pre_fn is not None:
        pre_patch = pre_fn(node_id, node_raw, dict(core_input))
        core_input = _merge(core_input, pre_patch)

    # PROMPT (Core-input injection; explicit + deterministic)
    core_input = _inject_rendered_prompt(
        node_raw=node_raw, core_input=core_input, prompt_registry=prompt_registry
    )

    # CORE (required)
    if core_fn is None:
        raise ValueError("Pipeline handler missing 'core'")
    core_output = core_fn(node_id, node_raw, dict(core_input))

    # POST
    final_output = dict(core_output)
    if post_fn is not None:
        post_patch = post_fn(node_id, node_raw, dict(final_output))
        final_output = _merge(final_output, post_patch)

    return final_output
