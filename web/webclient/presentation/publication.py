"""Content-aware publication primitives for the version-1 OOB protocol.

This module owns the three pieces the coordinator needs to publish only what
actually changed, without ever serializing or hashing a whole presentation:

* :func:`json_value_equal` compares two validated JSON values structurally.
* :func:`copy_json_value` produces an owned plain-JSON tree.
* :class:`PublicationReceipt` reports what one publication did.

Comparison semantics follow JSON, not Python: ``None``, ``bool``, number,
string, list and object are the six categories. A boolean is never equal to a
number even though ``True == 1`` in Python; integers and finite floats share one
number category, so ``1`` and ``1.0`` compare equal. Object key order is
irrelevant and only the key set plus per-key values are compared; list order is
significant and lists compare length first. Anything outside the six categories
compares unequal, so an unexpected object can never masquerade as unchanged.

Owned-value semantics: a value is *owned* when it is a fresh plain-JSON tree
that nothing else holds a reference to. The coordinator copies only values it
newly adopts into the published baseline (:func:`copy_json_value` at adoption
time, before the first frame is sent) and keeps every unchanged baseline value
by reference. That is why a presenter mutating a nested list it returned earlier
can never corrupt the baseline, and why a suppressed publication costs no copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping

__all__ = [
    "PreparedFrame",
    "PublicationCompletion",
    "PublicationKind",
    "PublicationReceipt",
    "copy_json_value",
    "json_value_equal",
]

#: The three publication outcomes a receipt can report.
PublicationKind = Literal["snapshot", "delta", "unchanged"]

_MISSING = object()


@dataclass(frozen=True)
class PreparedFrame:
    """One exact transport frame of a prepared logical publication.

    ``command`` is the Evennia OOB message name the frame travels under:
    ``ui_snapshot``/``ui_update`` for an intact logical document, or
    ``ui_publication_part`` for one bounded part of an oversized one.
    ``canonical`` holds the reusable canonical UTF-8 JSON bytes of the whole
    logical document only on an intact frame; a part frame owns no
    whole-document bytes (its wire envelope carries base64 chunks instead).
    """

    command: str
    envelope: dict[str, Any]
    canonical: bytes | None = None


def _category(value: Any) -> str:
    """Return the JSON category of ``value``.

    ``bool`` is checked before the number category on purpose: Python's
    ``bool`` is an ``int`` subclass, and the wire contract keeps the two
    categories distinct.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "unsupported"


def json_value_equal(old: Any, new: Any) -> bool:
    """Whether two JSON values are equal under the publication contract.

    The walk visits only the compared values; it never serializes, sorts or
    hashes the whole presentation. Nested objects and lists recurse with the
    same category rules.
    """
    old_category = _category(old)
    if old_category != _category(new):
        return False
    if old_category == "null":
        return True
    if old_category in ("bool", "string"):
        return old == new
    if old_category == "number":
        # JSON has one number type: 1 and 1.0 are the same value. A finite
        # float and an int compare numerically; NaN can never be equal, which
        # the plain ``==`` already answers False for.
        return old == new
    if old_category == "list":
        if len(old) != len(new):
            return False
        return all(json_value_equal(left, right) for left, right in zip(old, new))
    if old_category == "object":
        if set(old) != set(new):
            return False
        return all(json_value_equal(old[key], new[key]) for key in old)
    return False


def copy_json_value(value: Any) -> Any:
    """Return an owned plain-JSON copy of ``value``.

    Dictionaries and lists are rebuilt recursively, tuples become lists, and the
    scalars are returned as-is (they are immutable). An object that is not a
    JSON value raises ``TypeError``: a presenter returning one is a defect that
    must fail preflight, never a silent alias into the published baseline.
    """
    category = _category(value)
    if category == "null":
        return None
    if category in ("bool", "number", "string"):
        return value
    if category == "list":
        return [copy_json_value(item) for item in value]
    if category == "object":
        return {str(key): copy_json_value(item) for key, item in value.items()}
    raise TypeError(
        "presentation values must be plain JSON; got %s" % type(value).__name__
    )


@dataclass(frozen=True)
class PublicationReceipt:
    """What one publication actually did, returned once the batch has sent.

    Attributes:
        epoch: The presentation epoch the publication ran under.
        revision: The revision the client can now hold: the revision of the
            last logical publication that sent, or the current committed
            revision when nothing was sent.
        kind: ``snapshot``, ``delta`` or ``unchanged``.
        published: Whether any presentation frame was sent.
    """

    epoch: str
    revision: int
    kind: PublicationKind
    published: bool


@dataclass(frozen=True)
class PublicationCompletion:
    """One dispatcher-owned action result published with a presentation.

    The dispatcher normalizes the adapter outcome into ``result`` (an owned
    plain-JSON mapping it never mutates again) and supplies ``envelope`` to
    build the exact ``ui_action_result`` for the revision the coordinator
    actually publishes. ``envelope`` is an immutable closure over that owned
    result, so the envelope the coordinator prevalidates is byte-identical to
    the one it sends after the presentation frames.

    Attributes:
        request_id: The admitted request this result answers.
        result: The owned normalized result mapping.
        envelope: ``(epoch, revision) -> ui_action_result envelope``.
    """

    request_id: str
    result: Mapping[str, Any]
    envelope: Callable[[str, int], dict[str, Any]]
