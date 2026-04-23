from __future__ import annotations

from src.server import (
    AuthorizationGate,
    AuthorizationInput,
    ClerkAuthAdapter,
    EngineLaunchAdapter,
    RequestAuthResolver,
    RunAuthorizationContext,
    WorkspaceAuthorizationContext,
    build_engine_auth_context_refs,
    describe_request_auth_context,
)


def test_clerk_auth_adapter_normalizes_identity_and_session_without_provider_shapes_leaking() -> None:
    request_auth = ClerkAuthAdapter.build_request_auth_context(
        headers={
            "Authorization": "Bearer secret-token",
            "X-Request-Id": "req-123",
            "User-Agent": "pytest",
            "X-Forwarded-For": "127.0.0.1",
        },
        session_claims={
            "sub": "user_123",
            "sid": "sess_456",
            "email": "user@example.com",
            "name": "Test User",
            "org_id": "org_primary",
            "org_ids": ["org_primary", "org_secondary"],
            "org_role": "reviewer",
            "roles": ["editor"],
            "iat": 100,
            "exp": 200,
        },
        now_epoch_s=150,
    )

    assert request_auth.is_authenticated is True
    assert request_auth.auth_context_ref == "authctx:clerk:sess_456:user_123"
    assert request_auth.authorization_scheme == "bearer"
    assert request_auth.bearer_token_present is True
    assert request_auth.requested_by_user_ref == "user_123"
    assert request_auth.authenticated_identity is not None
    assert request_auth.authenticated_identity.organization_refs == ("org_primary", "org_secondary")
    assert request_auth.authenticated_identity.role_refs == ("reviewer", "editor")
    assert request_auth.session_context is not None
    assert request_auth.session_context.is_valid is True


def test_request_auth_resolver_returns_unauthenticated_context_without_claims() -> None:
    request_auth = RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-anon"},
        session_claims=None,
        now_epoch_s=100,
    )

    assert request_auth.is_authenticated is False
    assert request_auth.auth_context_ref == "authctx:anonymous"
    assert request_auth.authorization_scheme == "bearer"
    assert request_auth.bearer_token_present is True
    assert request_auth.requested_by_user_ref is None


def test_workspace_authorization_gate_allows_owner_and_blocks_viewer_for_launch() -> None:
    workspace = WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
        reviewer_user_refs=("user-reviewer",),
    )

    owner_decision = AuthorizationGate.authorize_workspace_scope(
        AuthorizationInput(
            user_id="user-owner",
            workspace_id="ws-001",
            requested_action="launch",
        ),
        workspace,
    )
    viewer_decision = AuthorizationGate.authorize_workspace_scope(
        AuthorizationInput(
            user_id="user-viewer",
            workspace_id="ws-001",
            requested_action="launch",
        ),
        workspace,
    )

    assert owner_decision.allowed is True
    assert owner_decision.resolved_role == "owner"
    assert viewer_decision.allowed is False
    assert viewer_decision.reason_code == "authorization.role_insufficient"


def test_run_authorization_gate_allows_run_owner_and_workspace_admin_role_context() -> None:
    workspace = WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
    )
    run_context = RunAuthorizationContext(
        run_id="run-001",
        workspace_context=workspace,
        run_owner_user_ref="user-runner",
    )

    run_owner_decision = AuthorizationGate.authorize_run_scope(
        AuthorizationInput(
            user_id="user-runner",
            workspace_id="ws-001",
            run_id="run-001",
            requested_action="result",
        ),
        run_context,
    )
    admin_decision = AuthorizationGate.authorize_run_scope(
        AuthorizationInput(
            user_id="user-admin",
            workspace_id="ws-001",
            run_id="run-001",
            requested_action="manage",
            role_context=("admin",),
        ),
        run_context,
    )

    assert run_owner_decision.allowed is True
    assert run_owner_decision.resolved_role == "run_owner"
    assert admin_decision.allowed is True
    assert admin_decision.resolved_role == "admin"


def test_engine_launch_adapter_can_consume_normalized_request_auth_context_only() -> None:
    request_auth = ClerkAuthAdapter.build_request_auth_context(
        headers={"Authorization": "Bearer token"},
        session_claims={"sub": "user_123", "sid": "sess_456", "exp": 500},
        now_epoch_s=100,
    )
    auth_refs = build_engine_auth_context_refs(request_auth)
    request = EngineLaunchAdapter.build_request(
        run_request_id="req-001",
        workspace_ref="ws-123",
        target_type="working_save",
        target_ref="ws-123",
        input_payload={"question": "hello"},
        auth_context_ref=auth_refs["auth_context_ref"],
        requested_by_user_ref=auth_refs["requested_by_user_ref"],
    )
    description = describe_request_auth_context(request_auth)

    assert request.auth_context_ref == "authctx:clerk:sess_456:user_123"
    assert request.requested_by_user_ref == "user_123"
    assert description["identity"]["user_id"] == "user_123"
    assert description["session"]["session_id"] == "sess_456"
    assert description["bearer_token_present"] is True
