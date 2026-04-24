from __future__ import annotations

import base64

from collections.abc import Callable, Mapping
from typing import Any, Optional

from src.server.aws_secrets_manager_models import AwsSecretWriteReceipt, AwsSecretsManagerBindingConfig


def create_boto3_secrets_manager_client(config: AwsSecretsManagerBindingConfig) -> Any:
    import boto3

    session = boto3.session.Session()
    return session.client("secretsmanager", region_name=config.region_name)


class AwsSecretsManagerSecretAuthority:
    @staticmethod
    def secret_name_from_ref(secret_ref: str, config: AwsSecretsManagerBindingConfig | None = None) -> str:
        resolved = config or AwsSecretsManagerBindingConfig()
        prefix = f"{resolved.ref_scheme}://"
        normalized = str(secret_ref or "").strip()
        if not normalized.startswith(prefix):
            raise ValueError("aws_secret.secret_ref_invalid")
        secret_name = normalized[len(prefix):].strip()
        if not secret_name:
            raise ValueError("aws_secret.secret_name_missing")
        return secret_name

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
    def read_secret_metadata(
        cls,
        *,
        client: Any,
        secret_ref: Optional[str] = None,
        secret_name: Optional[str] = None,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> Optional[Mapping[str, Any]]:
        resolved = config or AwsSecretsManagerBindingConfig()
        resolved_secret_name = str(secret_name or "").strip()
        if not resolved_secret_name and secret_ref is not None:
            resolved_secret_name = cls.secret_name_from_ref(secret_ref, resolved)
        if not resolved_secret_name:
            raise ValueError("aws_secret.secret_name_missing")
        try:
            described = client.describe_secret(SecretId=resolved_secret_name)
        except Exception as exc:  # pragma: no cover - exercised via fake client
            if cls._is_not_found_error(exc):
                return None
            raise
        last_rotated = described.get("LastRotatedDate") or described.get("LastChangedDate")
        if hasattr(last_rotated, "isoformat"):
            last_rotated = last_rotated.isoformat()
        return {
            "secret_name": resolved_secret_name,
            "secret_arn": str(described.get("ARN") or "").strip() or None,
            "secret_ref": f"{resolved.ref_scheme}://{resolved_secret_name}",
            "last_rotated_at": str(last_rotated or "").strip() or None,
            "secret_authority": "aws_secrets_manager",
        }

    @classmethod
    def read_secret_value(
        cls,
        *,
        client: Any,
        secret_ref: Optional[str] = None,
        secret_name: Optional[str] = None,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> Optional[str]:
        resolved = config or AwsSecretsManagerBindingConfig()
        resolved_secret_name = str(secret_name or '').strip()
        if not resolved_secret_name and secret_ref is not None:
            resolved_secret_name = cls.secret_name_from_ref(secret_ref, resolved)
        if not resolved_secret_name:
            raise ValueError('aws_secret.secret_name_missing')
        try:
            secret_value = client.get_secret_value(SecretId=resolved_secret_name)
        except Exception as exc:  # pragma: no cover - exercised via fake client
            if cls._is_not_found_error(exc):
                return None
            raise
        secret_string = secret_value.get('SecretString')
        if secret_string is not None:
            return str(secret_string)
        secret_binary = secret_value.get('SecretBinary')
        if secret_binary is None:
            return None
        if isinstance(secret_binary, str):
            try:
                decoded = base64.b64decode(secret_binary)
            except Exception:
                return secret_binary
            return decoded.decode('utf-8', errors='replace')
        if isinstance(secret_binary, (bytes, bytearray)):
            return bytes(secret_binary).decode('utf-8', errors='replace')
        return str(secret_binary)

    @classmethod
    def build_secret_value_reader(
        cls,
        *,
        client: Any,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> Callable[[str], Optional[str]]:
        resolved = config or AwsSecretsManagerBindingConfig()

        def _reader(secret_ref: str) -> Optional[str]:
            return cls.read_secret_value(client=client, secret_ref=secret_ref, config=resolved)

        return _reader

    @classmethod
    def build_secret_metadata_reader(
        cls,
        *,
        client: Any,
        config: AwsSecretsManagerBindingConfig | None = None,
    ) -> Callable[[str], Optional[Mapping[str, Any]]]:
        resolved = config or AwsSecretsManagerBindingConfig()

        def _reader(secret_ref: str) -> Optional[Mapping[str, Any]]:
            return cls.read_secret_metadata(client=client, secret_ref=secret_ref, config=resolved)

        return _reader

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
