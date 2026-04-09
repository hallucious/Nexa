from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ProviderError:
    """Provider execution error surface."""
    type: str
    message: str
    retryable: bool = False


@dataclass
class ProviderRequest:
    """Standard request passed from runtime to provider."""
    provider_id: str
    prompt: str
    context: Dict[str, Any]
    options: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class ProviderResult:
    """Standard result returned from provider to runtime."""
    output: Any
    raw_text: Optional[str]
    structured: Optional[Dict[str, Any]]
    artifacts: List[Any]
    trace: Dict[str, Any]
    error: Optional[ProviderError]
    stream: Optional[Dict[str, Any]] = None
