"""Turn a CycleRecord into plain JSON-safe data and back.

Used by storage (encrypted blob per user) and by the app sync API. Driven by the
dataclass type hints, so new fields round-trip without extra code. Sets are
written as sorted lists so output is stable.
"""

from __future__ import annotations

import types
import typing
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from .models import CycleRecord


def to_data(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_data(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted((to_data(v) for v in value), key=str)
    if isinstance(value, (list, tuple)):
        return [to_data(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_data(v) for k, v in value.items()}
    return value


def from_data(tp: Any, data: Any) -> Any:
    if data is None:
        return None
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        inner = [a for a in args if a is not type(None)]
        return from_data(inner[0], data)
    if origin in (list, tuple):
        return [from_data(args[0], v) for v in data]
    if origin in (set, frozenset):
        return {from_data(args[0], v) for v in data}
    if origin is dict:
        return {k: from_data(args[1], v) for k, v in data.items()}
    if is_dataclass(tp):
        hints = typing.get_type_hints(tp)
        kwargs = {f.name: from_data(hints[f.name], data[f.name]) for f in fields(tp) if f.name in data}
        return tp(**kwargs)
    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(data)
    if tp is datetime:
        return datetime.fromisoformat(data)
    if tp is date:
        return date.fromisoformat(data)
    return data


def record_to_data(record: CycleRecord) -> dict:
    return to_data(record)


def record_from_data(data: dict) -> CycleRecord:
    return from_data(CycleRecord, data)
