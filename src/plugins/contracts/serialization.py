from __future__ import annotations

import json
import types
from collections.abc import Mapping as AbcMapping, Sequence as AbcSequence
from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

T = TypeVar("T")


def dataclass_to_payload(value: Any) -> Any:
    """Convert dataclass-based Plugin Builder contracts into JSON-safe payloads."""

    if is_dataclass(value):
        return {field.name: dataclass_to_payload(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, AbcMapping):
        return {str(key): dataclass_to_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [dataclass_to_payload(item) for item in value]
    if isinstance(value, list):
        return [dataclass_to_payload(item) for item in value]
    return value


def dataclass_to_json(value: Any, *, sort_keys: bool = True) -> str:
    return json.dumps(dataclass_to_payload(value), ensure_ascii=False, sort_keys=sort_keys)


def dataclass_from_payload(cls: type[T], payload: Mapping[str, Any]) -> T:
    """Reconstruct a dataclass contract from a JSON-safe payload.

    The contract modules use ``from __future__ import annotations``, so raw
    ``field.type`` values may be strings. Resolve annotations through
    ``get_type_hints`` before coercion so nested dataclasses are restored rather
    than left as plain dictionaries.
    """

    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass type")
    type_hints = get_type_hints(cls)
    values: dict[str, Any] = {}
    for field in fields(cls):
        if field.name not in payload:
            continue
        annotation = type_hints.get(field.name, field.type)
        values[field.name] = _coerce_value(annotation, payload[field.name])
    return cls(**values)  # type: ignore[misc,call-arg]


def _coerce_value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(annotation)
    args = get_args(annotation)

    if _is_union_annotation(origin):
        non_none_args = tuple(item for item in args if item is not type(None))
        for item_type in non_none_args:
            try:
                return _coerce_value(item_type, value)
            except Exception:
                continue
        return value

    if origin is tuple and args:
        item_type = args[0]
        if isinstance(value, AbcSequence) and not isinstance(value, (str, bytes, bytearray)):
            return tuple(_coerce_value(item_type, item) for item in value)
        return ()

    if origin is list and args:
        item_type = args[0]
        if isinstance(value, AbcSequence) and not isinstance(value, (str, bytes, bytearray)):
            return [_coerce_value(item_type, item) for item in value]
        return []

    if _is_mapping_origin(origin):
        return dict(value) if isinstance(value, AbcMapping) else {}

    if isinstance(annotation, type) and is_dataclass(annotation) and isinstance(value, AbcMapping):
        return dataclass_from_payload(annotation, value)

    return value


def _is_union_annotation(origin: Any) -> bool:
    return origin in {Union, types.UnionType}


def _is_mapping_origin(origin: Any) -> bool:
    if origin is None:
        return False
    try:
        return issubclass(origin, AbcMapping)
    except TypeError:
        return False


class JsonPayloadMixin:
    def as_payload(self) -> dict[str, Any]:
        payload = dataclass_to_payload(self)
        return dict(payload) if isinstance(payload, AbcMapping) else {}

    def to_json(self) -> str:
        return dataclass_to_json(self)


__all__ = [
    "JsonPayloadMixin",
    "dataclass_from_payload",
    "dataclass_to_json",
    "dataclass_to_payload",
]
