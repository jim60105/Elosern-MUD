"""Immutable reusable scenes and complete typed dialogue line models.

This module is part of the pure data layer in ``world.lore``. It defines the
immutable building blocks of authored scenes (Speech, Narration, Scene) along
with UTF-8 wire/budget serialization checks and invariant validation.

Invariants enforced here:
- Speech: speaker in {"actor", "host"}, text 1..2000 code points.
- Narration: text 1..2000 code points, no speaker.
- Scene: 1..32 lines, total text <= 16000 code points, canonical UTF-8 JSON <= 8192 bytes.
- Formal scenes start with a complete actor Speech line.
- Revisions are explicit nonempty ASCII tokens <= 32 chars.
- Static scene IDs match ``[a-z][a-z0-9_.-]{0,95}``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Literal

MAX_LINE_CODE_POINTS = 2000
MAX_SCENE_LINES = 32
MAX_SCENE_CODE_POINTS = 16000
MAX_SCENE_CANONICAL_BYTES = 8192
MAX_REVISION_ASCII_CHARS = 32
MAX_STATIC_SCENE_ID_CHARS = 96

STATIC_SCENE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,95}\Z")
REVISION_PATTERN = re.compile(r"^[!-~]{1,32}\Z")


@dataclass(frozen=True)
class Speech:
    """A line of spoken dialogue delivered by actor or host."""

    speaker: Literal["actor", "host"]
    text: str

    def __post_init__(self) -> None:
        if self.speaker not in ("actor", "host"):
            raise ValueError(f"Speech speaker must be 'actor' or 'host', got {self.speaker!r}")
        if not isinstance(self.text, str) or not (1 <= len(self.text) <= MAX_LINE_CODE_POINTS):
            raise ValueError(
                f"Speech text must be a string of 1..{MAX_LINE_CODE_POINTS} code points"
            )


@dataclass(frozen=True)
class Narration:
    """A line of narrative/stage-direction prose without a speaker."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not (1 <= len(self.text) <= MAX_LINE_CODE_POINTS):
            raise ValueError(
                f"Narration text must be a string of 1..{MAX_LINE_CODE_POINTS} code points"
            )


SceneLine = Speech | Narration


def canonical_utf8_json_bytes(obj: object) -> bytes:
    """Serialize an object to canonical UTF-8 JSON bytes."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def line_to_dict(line: SceneLine) -> dict[str, str]:
    """Convert a SceneLine to its exact wire/payload dictionary form."""
    if isinstance(line, Speech):
        return {"kind": "speech", "speaker": line.speaker, "text": line.text}
    if isinstance(line, Narration):
        return {"kind": "narration", "text": line.text}
    raise TypeError(f"Unknown scene line type: {type(line)!r}")


def scene_to_dict(scene: Scene) -> dict[str, object]:
    """Convert a Scene to its wire/payload dictionary form."""
    return {
        "scene_id": scene.scene_id,
        "revision": scene.revision,
        "lines": [line_to_dict(line) for line in scene.lines],
    }


def scene_canonical_bytes(scene: Scene) -> int:
    """Return the byte length of the canonical UTF-8 JSON wire form of the scene."""
    return len(canonical_utf8_json_bytes(scene_to_dict(scene)))


@dataclass(frozen=True)
class Scene:
    """An immutable, reusable authored scene."""

    scene_id: str
    revision: str
    lines: tuple[SceneLine, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scene_id, str) or not self.scene_id:
            raise ValueError("Scene scene_id must be a nonempty string")
        if not isinstance(self.revision, str) or not REVISION_PATTERN.match(self.revision):
            raise ValueError(
                f"Scene revision must be a nonempty ASCII token <= {MAX_REVISION_ASCII_CHARS} chars, got {self.revision!r}"
            )
        if not isinstance(self.lines, tuple):
            raise TypeError("Scene lines must be a tuple of SceneLine instances")
        if not (1 <= len(self.lines) <= MAX_SCENE_LINES):
            raise ValueError(
                f"Scene must have 1..{MAX_SCENE_LINES} lines, got {len(self.lines)}"
            )
        total_code_points = 0
        for idx, line in enumerate(self.lines):
            if not isinstance(line, (Speech, Narration)):
                raise TypeError(f"Scene line {idx} is not Speech or Narration: {line!r}")
            total_code_points += len(line.text)
        if total_code_points > MAX_SCENE_CODE_POINTS:
            raise ValueError(
                f"Scene total code points ({total_code_points}) exceeds limit of {MAX_SCENE_CODE_POINTS}"
            )
        canon_bytes = scene_canonical_bytes(self)
        if canon_bytes > MAX_SCENE_CANONICAL_BYTES:
            raise ValueError(
                f"Scene canonical UTF-8 JSON bytes ({canon_bytes}) exceeds limit of {MAX_SCENE_CANONICAL_BYTES}"
            )
