from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from src.server.aws_secrets_manager_models import AwsSecretWriteReceipt, AwsSecretsManagerBindingConfig


def create_boto3_secrets_manager_client(config: AwsSecretsManagerBindingConfig) -> Any:
    import boto3

    session = boto3.session.Session()
    return session.client("secretsmanager", region_name=config.region_name)


class AwsSecretsManagerSecretAuthority:
    @staticmethod
    def build_secret_name(
        workspace_id: str,
        provider_key: str,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> str:
        resolved = config or AwsSecretsManagerBindingConfig()
        return resolved.provider_secret_template.format(
            prefix=resolved.secret_name_prefix.strip("/"),
            workspace_id=workspace_id,
            provider_key=provider_key,
        )

    @staticmethod
    def _build_tags(
        workspace_id: str,
        provider_key: str,
        metadata: Mapping[str, Any],
        config: AwsSecretsManagerBindingConfig,
    ) -> list[dict[str, str]]:
        tags = dict(config.default_tags)
        tags.setdefault("workspace_id", workspace_id)
        tags.setdefault("provider_key", provider_key)
        requested_by = str(metadata.get("requested_by_user_id") or "").strip()
        if requested_by:
            tags.setdefault("requested_by_user_id", requested_by)
        return [{"Key": str(key), "Value": str(value)} for key, value in sorted(tags.items()) if str(key).strip()]

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        response = getattr(exc, "response", None)
        if isinstance(response, Mapping):
            error = response.get("Error")
            if isinstance(error, Mapping) and error.get("Code") == "ResourceNotFoundException":
                return True
        return exc.__class__.__name__ == "ResourceNotFoundException"

    @classmethod
    def write_workspace_provider_secret(
        cls,
        *,
        client: Any,
        workspace_id: str,
        provider_key: str,
        secret_value: str,
        metadata: Mapping[str, Any],
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> AwsSecretWriteReceipt:
        resolved = config or AwsSecretsManagerBindingConfig()
        secret_name = cls.build_secret_name(workspace_id, provider_key, resolved)
        description = f"Nexa managed provider credential for workspace {workspace_id} / provider {provider_key}"
        secret_arn: Optional[str] = None
        version_id: Optional[str] = None
        was_created = False
        try:
            described = client.describe_secret(SecretId=secret_name)
            secret_arn = str(described.get("ARN") or "").strip() or None
            rotated = client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
            version_id = str(rotated.get("VersionId") or "").strip() or None
            secret_arn = secret_arn or (str(rotated.get("ARN") or "").strip() or None)
        except Exception as exc:  # pragma: no cover - exercised via fake client
            if not cls._is_not_found_error(exc):
                raise
            created = client.create_secret(
                Name=secret_name,
                SecretString=secret_value,
                Description=description,
                Tags=cls._build_tags(workspace_id, provider_key, metadata, resolved),
                **({"KmsKeyId": resolved.kms_key_id} if resolved.kms_key_id else {}),
            )
            secret_arn = str(created.get("ARN") or "").strip() or None
            version_id = str(created.get("VersionId") or "").strip() or None
            was_created = True
        secret_ref = f"{resolved.ref_scheme}://{secret_name}"
        secret_version_ref = f"{secret_ref}#version:{version_id}" if version_id else None
        last_rotated_at = str(metadata.get("now_iso") or metadata.get("updated_at") or "").strip() or None
        return AwsSecretWriteReceipt(
            secret_name=secret_name,
            secret_arn=secret_arn,
            secret_ref=secret_ref,
            secret_version_ref=secret_version_ref,
            last_rotated_at=last_rotated_at,
            was_created=was_created,
        )

    @classmethod
    def build_secret_writer(
        cls,
        *,
        client: Any,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> Callable[[str, str, str, Mapping[str, Any]], Mapping[str, Any]]:
        resolved = config or AwsSecretsManagerBindingConfig()

        def _writer(workspace_id: str, provider_key: str, secret_value: str, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
            receipt = cls.write_workspace_provider_secret(
                client=client,
                workspace_id=workspace_id,
                provider_key=provider_key,
                secret_value=secret_value,
                metadata=metadata,
                config=resolved,
            )
            return {
                "secret_ref": receipt.secret_ref,
                "secret_version_ref": receipt.secret_version_ref,
                "last_rotated_at": receipt.last_rotated_at,
                "secret_name": receipt.secret_name,
                "secret_arn": receipt.secret_arn,
                "secret_authority": "aws_secrets_manager",
                "was_created": receipt.was_created,
            }

        return _writer
