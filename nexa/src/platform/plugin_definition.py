from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class PluginDefinition:
    plugin_id: str
    version: str
    description: str
    callable: Callable[..., Any]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.callable(*args, **kwargs)