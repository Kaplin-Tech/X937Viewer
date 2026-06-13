"""Moov-compatible JSON serialization.

Output matches moov-io/imagecashletter's JSON encoding of an ICL file:
camelCase keys in Go struct order, amounts as integer cents, dates as
RFC-3339 strings, empty repeated groups as ``null``, image bytes as base64.
"""

from __future__ import annotations

import base64
import json
from typing import Union

from .parser import X937File

# repeated groups that Moov serializes as null when empty
_NULL_WHEN_EMPTY = {
    "checkDetailAddendumA", "checkDetailAddendumB", "checkDetailAddendumC",
    "returnDetailAddendumA", "returnDetailAddendumB", "returnDetailAddendumC",
    "returnDetailAddendumD",
    "imageViewDetail", "imageViewData", "imageViewAnalysis",
}

# repeated groups that Moov omits entirely when empty
_OMIT_WHEN_EMPTY = {
    "checks", "returns", "credits", "creditItems", "routingNumberSummary",
}


def _transform(value, key=None):
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii") if value else ""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in _OMIT_WHEN_EMPTY and not v:
                continue
            if k in _NULL_WHEN_EMPTY and not v:
                out[k] = None
                continue
            out[k] = _transform(v, k)
        return out
    if isinstance(value, list):
        return [_transform(v) for v in value]
    return value


def to_json_obj(f: Union[X937File, dict]) -> dict:
    """Return a plain JSON-serializable dict mirroring Moov's output."""
    data = f.data if isinstance(f, X937File) else f
    return _transform(data)


def to_json(f: Union[X937File, dict], indent: int = 4) -> str:
    return json.dumps(to_json_obj(f), indent=indent)


def write_json(f: Union[X937File, dict], path: str, indent: int = 4) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_json(f, indent=indent))
        fh.write("\n")
