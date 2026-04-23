from __future__ import annotations

from src.contracts.savefile_factory import make_minimal_savefile
from src.contracts.savefile_serializer import serialize_savefile


def make_demo_savefile(*, name: str = "demo"):
    return make_minimal_savefile(
        name=name,
        version="2.0.0",
        description="minimal savefile",
        entry="node1",
        node_type="ai",
        resource_ref={
            "prompt": "prompt.main",
            "provider": "provider.main",
        },
        inputs={"text": "state.input.text"},
        outputs={"answer": "state.working.answer"},
        prompts={"prompt.main": {"template": "Answer {{text}}"}},
        providers={
            "provider.main": {
                "type": "openai",
                "model": "gpt-5",
                "config": {},
            }
        },
        state_input={"text": "hello"},
    )


def make_demo_savefile_payload(*, name: str = "demo"):
    return serialize_savefile(make_demo_savefile(name=name))
