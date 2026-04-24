from __future__ import annotations

from typing import Any, Optional

from src.server.aws_secrets_manager_binding import AwsSecretsManagerSecretAuthority
from src.server.aws_secrets_manager_models import AwsSecretsManagerBindingConfig
from src.server.provider_health_api import SecretMetadataReader
from src.server.provider_probe_api import ProviderProbeRunner
from src.server.provider_probe_runtime import build_provider_probe_runner


def resolve_managed_secret_metadata_reader(
    *,
    secret_metadata_reader: Optional[SecretMetadataReader] = None,
    aws_secrets_manager_client: Any = None,
    aws_secrets_manager_config: AwsSecretsManagerBindingConfig | None = None,
) -> Optional[SecretMetadataReader]:
    if secret_metadata_reader is not None:
        return secret_metadata_reader
    if aws_secrets_manager_client is None:
        return None
    config = aws_secrets_manager_config or AwsSecretsManagerBindingConfig()
    return AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=aws_secrets_manager_client,
        config=config,
    )


def resolve_provider_probe_runner(
    *,
    probe_runner: Optional[ProviderProbeRunner] = None,
    aws_secrets_manager_client: Any = None,
    aws_secrets_manager_config: AwsSecretsManagerBindingConfig | None = None,
) -> ProviderProbeRunner:
    if probe_runner is not None:
        return probe_runner
    if aws_secrets_manager_client is None:
        return build_provider_probe_runner(secret_value_reader=None)
    config = aws_secrets_manager_config or AwsSecretsManagerBindingConfig()
    return build_provider_probe_runner(
        secret_value_reader=AwsSecretsManagerSecretAuthority.build_secret_value_reader(
            client=aws_secrets_manager_client,
            config=config,
        )
    )
