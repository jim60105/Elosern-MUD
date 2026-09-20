"""The closed freeform scale tables and their fail-closed loaders.

The canonical table, the YAML-validated cast-scale set, and the
proficiency-anchored ladder all load at import time, exactly as the original
single module loaded them (lines 44-200 of the former flat module).
"""

from collections.abc import Sequence
from math import isfinite
from typing import Any

from ._constants import FREEFORM_CAST_SCALE_COUNT, PROGRESSION_YAML

# The fixed canonical freeform scale table (freeform-casting spec): exact
# (scale, label) pairs in ascending order. A table that deviates in any value
# or label pairing fails closed at load — no consumer may ever run a different
# set.
FREEFORM_CANONICAL_SCALES: tuple[tuple[float, str], ...] = (
    (0.25, "1/4"),
    (0.5, "1/2"),
    (1.0, "1"),
    (2.0, "2"),
    (4.0, "4"),
)


def _load_freeform_cast_scales(
    raw: Any,
) -> tuple[tuple[float, str], ...]:
    """Load and fail-closed validate the closed freeform scale table.

    The table must carry exactly ``FREEFORM_CAST_SCALE_COUNT`` entries, each
    an object with a finite positive ``scale`` and a non-empty string
    ``label``; scales must be unique and strictly ascending, labels unique,
    and exactly one entry must carry ``scale == 1.0``. The parsed table must
    then equal the canonical ``FREEFORM_CANONICAL_SCALES`` set exactly — any
    deviation in a scale value or its label pairing raises a named
    ``ValueError`` before any consumer can read a partial or deviant set.
    """
    entries = raw.get("freeform_cast_scales")
    if not isinstance(entries, list) or len(entries) != FREEFORM_CAST_SCALE_COUNT:
        raise ValueError(
            "freeform_cast_scales must be a list of exactly "
            f"{FREEFORM_CAST_SCALE_COUNT} entries"
        )
    parsed: list[tuple[float, str]] = []
    seen_scales: set[float] = set()
    seen_labels: set[str] = set()
    has_one = False
    previous = 0.0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"scale", "label"}:
            raise ValueError(
                f"freeform_cast_scales entry {index} must be {{scale, label}}"
            )
        scale = entry["scale"]
        label = entry["label"]
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise ValueError(
                f"freeform_cast_scales entry {index} scale must be numeric"
            )
        scale = float(scale)
        if not isfinite(scale) or scale <= 0:
            raise ValueError(
                f"freeform_cast_scales entry {index} scale must be finite and positive"
            )
        if scale in seen_scales:
            raise ValueError(
                f"freeform_cast_scales entry {index} duplicates scale {scale:g}"
            )
        if scale <= previous:
            raise ValueError(
                "freeform_cast_scales must be strictly ascending, entry "
                f"{index} has scale {scale:g}"
            )
        if not isinstance(label, str) or not label.strip():
            raise ValueError(
                f"freeform_cast_scales entry {index} label must be non-empty"
            )
        if label in seen_labels:
            raise ValueError(
                f"freeform_cast_scales entry {index} duplicates label {label!r}"
            )
        if scale == 1.0:
            has_one = True
        seen_scales.add(scale)
        seen_labels.add(label)
        parsed.append((scale, label))
        previous = scale
    if not has_one:
        raise ValueError("freeform_cast_scales must contain exactly one 1.0 entry")
    canonical = tuple(parsed)
    if canonical != FREEFORM_CANONICAL_SCALES:
        raise ValueError(
            "freeform_cast_scales must equal the canonical set "
            f"{FREEFORM_CANONICAL_SCALES!r}, got {canonical!r}"
        )
    return canonical


# The closed freeform-casting scale set: ascending ``(scale, label)`` pairs
# shared by the resolver gate, the preview, the wire validator, and the text
# command. Never hard-code the set anywhere else.
FREEFORM_CAST_SCALES: tuple[tuple[float, str], ...] = _load_freeform_cast_scales(
    PROGRESSION_YAML
)
# Canonical table membership (the closed wire-level scale set). NOT the
# actor's entitlement: which rungs one may actually cast derives from
# :func:`freeform_scales_for` (the ladder).
FREEFORM_SCALE_VALUES = tuple(scale for scale, _ in FREEFORM_CAST_SCALES)
FREEFORM_SCALE_LABELS = frozenset(label for _, label in FREEFORM_CAST_SCALES)


def _load_freeform_scale_ladder(
    raw: Any, canonical: tuple[tuple[float, str], ...]
) -> tuple[tuple[float, int], ...]:
    """Load and fail-closed validate the proficiency-anchored scale ladder.

    Each rung is ``{scale, min_level}``: the scale must be a canonical table
    member, ``min_level`` an int >= 0, and both sequences strictly ascending
    starting at level 0 (the entry rung is unconditional for an entitled
    actor). A ladder deviating in any way fails at import.
    """
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("freeform_scale_ladder must be a non-empty sequence")
    canonical_values = {scale for scale, _ in canonical}
    parsed: list[tuple[float, int]] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict) or set(entry) != {"scale", "min_level"}:
            raise ValueError(
                "freeform_scale_ladder entries must name exactly scale and "
                f"min_level, got {entry!r} at index {index}"
            )
        scale, min_level = entry["scale"], entry["min_level"]
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not isfinite(scale)
            or scale <= 0
            or float(scale) not in canonical_values
        ):
            raise ValueError(
                f"freeform_scale_ladder scale {scale!r} is not a canonical "
                "positive finite scale at index "
                f"{index}"
            )
        if isinstance(min_level, bool) or not isinstance(min_level, int) or min_level < 0:
            raise ValueError(
                f"freeform_scale_ladder min_level must be an int >= 0, got "
                f"{min_level!r} at index {index}"
            )
        if parsed:
            if float(scale) <= parsed[-1][0]:
                raise ValueError("freeform_scale_ladder scales must ascend")
            if min_level <= parsed[-1][1]:
                raise ValueError("freeform_scale_ladder levels must ascend")
        parsed.append((float(scale), min_level))
    if parsed[0][1] != 0:
        raise ValueError("freeform_scale_ladder must start at min_level 0")
    return tuple(parsed)


# The proficiency ladder (use-driven-progression D5): ascending
# ``(scale, min_level)`` rungs an entitled actor unlocks through the CAST
# SKILL's own proficiency. Never hard-coded anywhere else.
FREEFORM_SCALE_LADDER: tuple[tuple[float, int], ...] = _load_freeform_scale_ladder(
    PROGRESSION_YAML["freeform_scale_ladder"], FREEFORM_CAST_SCALES
)
