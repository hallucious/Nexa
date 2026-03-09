from typing import Dict, Any


class ProviderRegistry:
    """
    Registry mapping provider_id -> provider implementation.

    Providers must expose:
        execute(request) -> ProviderResult
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {}

    def register(self, provider_id: str, provider: Any) -> None:
        """
        Register a provider implementation.
        """
        if provider_id in self._providers:
            raise ValueError(f"Provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def resolve(self, provider_id: str) -> Any:
        """
        Resolve provider implementation by id.
        """
        if provider_id not in self._providers:
            raise KeyError(f"Provider not found: {provider_id}")
        return self._providers[provider_id]

    def list_providers(self):
        """
        Return list of registered provider ids.
        """
        return list(self._providers.keys())
