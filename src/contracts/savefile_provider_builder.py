from src.platform.provider_registry import ProviderRegistry
from src.contracts.savefile_format import Savefile

def build_provider_registry_from_savefile(savefile: Savefile) -> ProviderRegistry:
    registry = ProviderRegistry()

    for provider_id, provider_resource in savefile.resources.providers.items():
        provider_type = provider_resource.type

        if provider_type == "openai":
            from src.providers.openai_provider import OpenAIProvider
            provider_instance = OpenAIProvider(
                model=provider_resource.model,
                config=provider_resource.config
            )

        elif provider_type == "anthropic":
            from src.providers.anthropic_provider import AnthropicProvider
            provider_instance = AnthropicProvider(
                model=provider_resource.model,
                config=provider_resource.config
            )

        elif provider_type == "test":
            provider_instance = _create_test_provider()

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        registry.register(provider_id, provider_instance)

    return registry


def _create_test_provider():
    from src.contracts.provider_contract import ProviderResult

    class TestProvider:
        def execute(self, request):
            return ProviderResult(
                output=f"[TEST] {request.prompt}",
                raw_text=f"[TEST] {request.prompt}",
                structured=None,
                artifacts=[],
                trace={"provider": "test"},
                error=None
            )

    return TestProvider()
