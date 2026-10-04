"""Deterministic bounded rendering of the StoryDirector context frame.

The frame is the only dynamic part of the director prompt: the bounded
candidate/request context the deterministic narrative core hands to the
generative layer. Rendering is a pure function of the context mapping, so the
same context always produces byte-identical text, and every nested value is
bounded before serialization so no input can build an unbounded prompt.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

# Bounds on one rendered frame. They mirror the narrative-side context bounds;
# the copy here is defensive so the prompt builder alone cannot be driven
# unbounded by a caller.
MAX_FRAME_CHARACTERS = 6000
MAX_STRING_CHARACTERS = 300
MAX_SEQUENCE_ITEMS = 16
MAX_MAPPING_KEYS = 24

_EMPTY = ""


def _bound(value: Any, *, depth: int = 0) -> Any:
    """Return a deterministically bounded, plain-JSON copy of ``value``."""
    if depth > 6:
        return _EMPTY
    if isinstance(value, str):
        return value[:MAX_STRING_CHARACTERS]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, Mapping):
        bounded: dict[str, Any] = {}
        for key in sorted(value, key=str)[:MAX_MAPPING_KEYS]:
            bounded[str(key)[:MAX_STRING_CHARACTERS]] = _bound(
                value[key], depth=depth + 1
            )
        return bounded
    if isinstance(value, Sequence):
        return [_bound(item, depth=depth + 1) for item in list(value)[:MAX_SEQUENCE_ITEMS]]
    return _EMPTY


def render_director_frame(context: Mapping[str, Any]) -> str:
    """Serialize one bounded director context into a stable prompt frame."""
    if not isinstance(context, Mapping):
        raise TypeError("director context must be a mapping")
    bounded = _bound(dict(context))
    text = json.dumps(
        bounded, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if len(text) > MAX_FRAME_CHARACTERS:
        # A pathological context still yields a bounded, valid frame: the
        # deterministic narrative side never depends on frame content.
        text = text[:MAX_FRAME_CHARACTERS]
    return text
