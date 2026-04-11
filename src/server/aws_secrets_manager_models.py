from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class AwsSecretsManagerBindingConfig:
    region_name: str = "us-east-1"
    secret_name_prefix: str = "nexa"
    provider_secret_template: str = "{prefix}/{workspace_id}/providers/{provider_key}"
    kms_key_id: Optional[str] = None
    default_tags: Mapping[str, str] = field(default_factory=dict)
    ref_scheme: str = "aws-secretsmanager"

    def __post_init__(self) -> None:
        if not str(self.region_name).strip():
            raise ValueError("AwsSecretsManagerBindingConfig.region_name must be non-empty")
        if not str(self.secret_name_prefix).strip():
            raise ValueError("AwsSecretsManagerBindingConfig.secret_name_prefix must be non-empty")
        if not str(self.provider_secret_template).strip():
            raise ValueError("AwsSecretsManagerBindingConfig.provider_secret_template must be non-empty")
        if not str(self.ref_scheme).strip():
            raise ValueError("AwsSecretsManagerBindingConfig.ref_scheme must be non-empty")


@dataclass(frozen=True)
class AwsSecretWriteReceipt:
    secret_name: str
    secret_arn: Optional[str]
    secret_ref: str
    secret_version_ref: Optional[str]
    last_rotated_at: Optional[str]
    was_created: bool
