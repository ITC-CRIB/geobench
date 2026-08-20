"""Utilities module."""

from typing import Any


def is_empty(val: Any) -> bool:
    return (
        val is None
        or (isinstance(val, str) and not val.strip())
        or (isinstance(val, (dict, list, set)) and not val)
    )


def prune_dict(val: dict) -> dict:
    return {
        key: prune_dict(val) if isinstance(val, dict) else val
        for key, val in val.items()
        if not is_empty(val)
    }
