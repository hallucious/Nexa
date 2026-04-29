from __future__ import annotations

from src.plugins.contracts.builder_types import PluginBuilderRequest
from src.plugins.contracts.common_enums import (
    BUILDER_MODE_BUILD_AND_REGISTER,
    BUILDER_MODE_CREATE_NEW,
    BUILDER_MODE_REVIEW_EXISTING,
    BUILDER_MODE_UPDATE_CANDIDATE,
    BUILDER_MODES,
    SOURCE_TYPE_EXISTING_CANDIDATE,
    SOURCE_TYPE_EXISTING_REGISTRY_ENTRY,
    require_known_value,
)


def normalize_builder_mode(mode: str) -> str:
    return require_known_value(str(mode or "").strip(), allowed=BUILDER_MODES, field_name="builder mode")


def validate_builder_request_mode(request: PluginBuilderRequest) -> None:
    mode = normalize_builder_mode(request.mode)
    if mode == BUILDER_MODE_CREATE_NEW and request.builder_spec is None:
        raise ValueError("create_new mode requires builder_spec")
    if mode == BUILDER_MODE_UPDATE_CANDIDATE and not request.existing_candidate_ref:
        raise ValueError("update_candidate mode requires existing_candidate_ref")
    if mode == BUILDER_MODE_REVIEW_EXISTING and not request.existing_registry_ref:
        raise ValueError("review_existing mode requires existing_registry_ref")
    if mode == BUILDER_MODE_BUILD_AND_REGISTER and request.registration_request is not None and not request.registration_request.requested:
        raise ValueError("build_and_register mode requires requested registration")


def source_type_required_for_existing_ref(source_type: str) -> bool:
    return source_type in {SOURCE_TYPE_EXISTING_CANDIDATE, SOURCE_TYPE_EXISTING_REGISTRY_ENTRY}


__all__ = [
    "normalize_builder_mode",
    "source_type_required_for_existing_ref",
    "validate_builder_request_mode",
]
