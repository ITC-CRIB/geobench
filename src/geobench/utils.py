"""Utilities module."""

import os
import re
import unicodedata
from typing import Any


def is_empty(value: Any) -> bool:
    """Return whether a value is considered empty.

    A value is considered empty if it is None, a blank string, or an empty
    dictionary, list, or set.

    Args:
        value: Value to check.

    Returns:
        True if the value is considered empty; otherwise False.
    """
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, (dict, list, set)) and not value)
    )


def prune_dict(value: dict) -> dict:
    """Return a dictionary with empty values removed.

    Nested dictionaries are recursively pruned.

    Args:
        value: Dictionary to prune.

    Returns:
        Dictionary without empty values.
    """
    return {
        key: prune_dict(val) if isinstance(val, dict) else val
        for key, val in value.items()
        if not is_empty(val)
    }


def serialize_dict(value: dict) -> dict:
    """Return a serialized representation of a dictionary.

    Empty values are removed, and callable values are replaced with
    their function names. Nested dictionaries are recursively serialized.

    Args:
        value: Dictionary to serialize.

    Returns:
        Serialized dictionary.
    """
    out = {}
    for key, val in prune_dict(value).items():
        if callable(val):
            outval = val.__name__
        elif isinstance(val, dict):
            outval = serialize_dict(val)
        else:
            outval = val
        out[key] = outval
    return out


def slugify(value: str) -> str:
    """Return a normalized slug from a string.

    Non-ASCII characters are transliterated where possible, and
    non-word characters are replaced with underscores.

    Args:
        value: String to slugify.

    Returns:
        Normalized slug.
    """
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^\w]", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def is_filename(value: str) -> bool:
    """Return whether a value appears to be a filename.

    The filename must contain a non-empty extension after the last
    period. Directory components are ignored.

    Args:
        value: Path or filename to check.

    Returns:
        True if the value appears to be a filename; otherwise False.
    """
    return bool(re.match(r"^.+\.[^.]+$", os.path.basename(value)))


def get_abs_path(path: str, root: str | None = None) -> str:
    """Return normalized absolute path.

    Args:
        path: Path.
        root: Optional root path.

    Returns:
        Normalized absolute path.
    """
    path = path or ""
    if not os.path.isabs(path):
        if root:
            return get_abs_path(os.path.join(root, path))
        else:
            return os.path.abspath(path or os.getcwd())
    return os.path.normpath(path)
