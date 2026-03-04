from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class NodeTrace:
    events: List[str] = field(default_factory=list)


@dataclass
class NodeResult:
    node_id: str
    output: Any
    artifacts: List[Any] = field(default_factory=list)
    trace: NodeTrace = field(default_factory=NodeTrace)


class NodeExecutionRuntime:
    def __init__(self, provider_execution):
        self.provider_execution = provider_execution

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        node_id = node.get("id", "unknown")
        trace = NodeTrace()

        trace.events.append("pre_plugins")

        prompt_template = node.get("prompt", "")
        rendered_prompt = prompt_template.format(**state) if prompt_template else ""
        trace.events.append("prompt_render")

        provider_result = self.provider_execution.execute(rendered_prompt)
        trace.events.append("provider_execute")

        output = provider_result.get("output")

        trace.events.append("post_plugins")

        return NodeResult(
            node_id=node_id,
            output=output,
            artifacts=[],
            trace=trace,
        )