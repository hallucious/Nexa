from __future__ import annotations

import pytest

from src.server import AwsSecretsManagerBindingConfig, AwsSecretsManagerSecretAuthority, FastApiRouteDependencies, create_fastapi_app

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient


class ResourceNotFoundException(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "ResourceNotFoundException"}}


class FakeSecretsManagerClient:
    def __init__(self, existing_names: tuple[str, ...] = ()) -> None:
        self.secrets = {
            name: {"arn": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{name}", "versions": ["v1"]}
            for name in existing_names
        }
        self.created: list[dict] = []
        self.rotated: list[dict] = []

    def describe_secret(self, SecretId: str):
        if SecretId not in self.secrets:
            raise ResourceNotFoundException()
        return {"ARN": self.secrets[SecretId]["arn"], "Name": SecretId}

    def create_secret(self, Name: str, SecretString: str, Description: str, Tags=None, KmsKeyId=None):
        self.secrets[Name] = {
            "arn": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{Name}",
            "versions": ["v1"],
        }
        payload = {
            "Name": Name,
            "SecretString": SecretString,
            "Description": Description,
            "Tags": Tags,
            "KmsKeyId": KmsKeyId,
        }
        self.created.append(payload)
        return {"ARN": self.secrets[Name]["arn"], "Name": Name, "VersionId": "v1"}

    def put_secret_value(self, SecretId: str, SecretString: str):
        versions = self.secrets[SecretId]["versions"]
        version = f"v{len(versions) + 1}"
        versions.append(version)
        self.rotated.append({"SecretId": SecretId, "SecretString": SecretString, "VersionId": version})
        return {"ARN": self.secrets[SecretId]["arn"], "Name": SecretId, "VersionId": version}


def test_aws_secrets_manager_binding_creates_secret_and_returns_canonical_refs() -> None:
    client = FakeSecretsManagerClient()
    receipt = AwsSecretsManagerSecretAuthority.write_workspace_provider_secret(
        client=client,
        workspace_id="ws-001",
        provider_key="openai",
        secret_value="super-secret",
        metadata={"requested_by_user_id": "user-owner", "now_iso": "2026-04-11T12:06:00+00:00"},
        config=AwsSecretsManagerBindingConfig(region_name="us-east-1"),
    )

    assert receipt.was_created is True
    assert receipt.secret_ref == "aws-secretsmanager://nexa/ws-001/providers/openai"
    assert receipt.secret_version_ref == "aws-secretsmanager://nexa/ws-001/providers/openai#version:v1"
    assert client.created[0]["SecretString"] == "super-secret"


def test_aws_secrets_manager_binding_rotates_existing_secret() -> None:
    client = FakeSecretsManagerClient(existing_names=("nexa/ws-001/providers/openai",))
    receipt = AwsSecretsManagerSecretAuthority.write_workspace_provider_secret(
        client=client,
        workspace_id="ws-001",
        provider_key="openai",
        secret_value="rotated-secret",
        metadata={"requested_by_user_id": "user-owner", "now_iso": "2026-04-11T12:07:00+00:00"},
        config=AwsSecretsManagerBindingConfig(region_name="us-east-1"),
    )

    assert receipt.was_created is False
    assert receipt.secret_version_ref == "aws-secretsmanager://nexa/ws-001/providers/openai#version:v2"
    assert client.rotated[0]["SecretString"] == "rotated-secret"


def test_fastapi_provider_binding_route_can_use_aws_secrets_manager_writer() -> None:
    client = FakeSecretsManagerClient()
    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: __import__("src.server", fromlist=["WorkspaceAuthorizationContext"]).WorkspaceAuthorizationContext(
            workspace_id="ws-001", owner_user_ref="user-owner", collaborator_user_refs=("user-collab",), viewer_user_refs=("user-viewer",)
        ) if workspace_id == "ws-001" else None,
        provider_catalog_rows_provider=lambda: ({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
        workspace_provider_binding_rows_provider=lambda workspace_id: (),
        workspace_provider_binding_row_provider=lambda workspace_id, provider_key: None,
        binding_id_factory=lambda: "binding-001",
        now_iso_provider=lambda: "2026-04-11T12:06:00+00:00",
        aws_secrets_manager_client_provider=lambda: client,
        aws_secrets_manager_config=AwsSecretsManagerBindingConfig(region_name="us-east-1"),
    )
    app = create_fastapi_app(dependencies=deps)
    web = TestClient(app)
    response = web.put(
        "/api/workspaces/ws-001/provider-bindings/openai",
        headers={
            "Authorization": "Bearer token",
            "X-Nexa-Session-Claims": '{"sub":"user-owner","sid":"sess-001","exp":4102444800,"roles":["admin"]}',
        },
        json={"display_name": "OpenAI GPT", "secret_value": "aws-secret", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding"]["secret_ref"] == "aws-secretsmanager://nexa/ws-001/providers/openai"
    assert payload["binding"]["secret_version_ref"].endswith("#version:v1")
    assert client.created[0]["SecretString"] == "aws-secret"
