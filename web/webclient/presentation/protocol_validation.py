"""Shared protocol-validation helpers for the presentation and actions layers.

Three validator pairs were duplicated between surfaces and had started to
drift (webclient-presentation-push-factory): the creation draft surface
(``presentation/creation.py``) and the creation submit surface
(``actions/creation_actions.py``) each validate the background text and the
affinity-element list; the local-map and exploration surfaces each require
the exit-ref and node-id shapes. The shared mechanism lives here once, with
each site's observable deviation kept as a parameter — the error class, the
empty-value normalization, and the global over-bound check — so no surface's
accept/reject set or message text changes.
"""

from typing import Any

from web.webclient.presentation.affordances import (
    MAX_EXIT_REF_CHARS,
    MAX_NODE_ID_CHARS,
)
from world.lore.elements import ELEMENT_REGISTRY
from world.rules.character_creation import max_affinity_elements

__all__ = [
    "require_exit_ref",
    "require_node_id_shape",
    "validate_affinity_elements",
    "validate_background",
]


def require_exit_ref(
    value: Any, field: str, error_cls: type[Exception]
) -> str:
    """Require an exit reference of the bounded ASCII shape.

    Byte-identical between the local-map and exploration surfaces; moved
    wholesale (design D3).
    """
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_EXIT_REF_CHARS:
        raise error_cls(
            f"{field} must be 1..{MAX_EXIT_REF_CHARS} ASCII characters"
        )
    if not value.isascii():
        raise error_cls(f"{field} must be ASCII")
    return value


def require_node_id_shape(
    value: Any, field: str, error_cls: type[Exception], max_chars: int
) -> str:
    """Require the common node-ID shape (an over-bound-free string) only.

    Deliberately NOT unified with the per-surface decode hop: exploration
    wraps a ``KnowledgeError`` from ``decode_node`` into a
    ``ProtocolValidationError`` while local_map lets it escape — an
    observable divergence pinned by the existing panel tests. Do not unify.
    """
    if not isinstance(value, str) or len(value) > max_chars:
        raise error_cls(f"{field} exceeds the maximum node-ID length")
    return value


def validate_background(
    value: Any, error_cls: type[Exception], max_length: int
) -> str | None:
    """Validate one nullable bounded background text field.

    A missing or blank value normalizes to ``None``; a non-string or
    over-bound value rejects. The bound is supplied per surface so the
    persona-field contract keeps its single authority at each site.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise error_cls("background must be text or null")
    text = value.strip()
    if not text:
        return None
    if sum(1 for _ in text) > max_length:
        raise error_cls("background exceeds its bound")
    return text


def validate_affinity_elements(
    value: Any,
    race_key: str,
    error_cls: type[Exception],
    *,
    empty_as_none: bool,
    global_bound: int | None = None,
) -> list[str] | None:
    """Validate one affinity set against the race-dependent maximum.

    The union of the two creation surfaces' behaviors (design D2):
    ``empty_as_none`` selects the ``None`` normalization — the submit surface
    passes ``None`` through as neutral, the draft surface normalizes to
    ``[]`` — and ``global_bound`` replicates the draft surface's extra over-
    bound check the submit surface deliberately lacks. Passing ``None`` (the
    default) keeps the submit surface's exact accept/reject set; a list
    (``list[str]``) is always returned so each surface maps to its own return
    shape.
    """
    if value is None:
        return None if empty_as_none else []
    if not isinstance(value, list):
        raise error_cls("affinity_elements must be a list or null")
    if global_bound is not None and len(value) > global_bound:
        raise error_cls("affinity_elements exceeds its bound")
    if race_key == "elf" and value:
        raise error_cls(
            "an elf must not supply affinity_elements; the subrace is the authority"
        )
    maximum = max_affinity_elements(race_key)
    if len(value) > maximum:
        raise error_cls(
            f"affinity_elements exceeds the {race_key} maximum of {maximum}"
        )
    checked: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or entry not in ELEMENT_REGISTRY:
            raise error_cls(f"unknown affinity element {entry!r}")
        if entry in checked:
            raise error_cls(f"duplicate affinity element {entry!r}")
        checked.append(entry)
    return checked