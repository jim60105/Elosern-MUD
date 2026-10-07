"""JSON conversion for arbitrary persistent state (gm-portal-s3-runtime-state).

Every value a runtime reader exposes passes through :func:`json_value`. The
conversion is total — it never raises and never writes — so one unreprable leaf
can never take down a whole inventory (design §3):

- Evennia entities become ``{"$ref": "#123", "typeclass": ..., "key": ...}``.
- Values that cannot be represented become
  ``{"$unserializable": "<type name>", "repr": "<repr, 200 chars>"}``.
- Containers recurse; a cycle is reported as one bounded marker instead of
  being traversed forever.

Nothing here repairs, normalizes, or persists inspected state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set as AbstractSet
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

#: The bounded ``repr`` length of an unconvertible value (design §2).
MAX_REPR_CHARS = 200

_ENTITY_TYPES: tuple[type, ...] | None = None


def entity_types() -> tuple[type, ...]:
    """The Evennia entity models a value can reference, imported lazily."""
    global _ENTITY_TYPES
    if _ENTITY_TYPES is None:
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        from evennia.scripts.models import ScriptDB

        _ENTITY_TYPES = (ObjectDB, AccountDB, ScriptDB)
    return _ENTITY_TYPES


def bounded_repr(value: Any) -> str:
    """``repr(value)`` clipped to :data:`MAX_REPR_CHARS`, never raising."""
    try:
        text = repr(value)
    except Exception:  # observability: ignore R2: an unreprable value is the fact being reported
        text = f"<unreprable {type(value).__name__}>"
    return text[:MAX_REPR_CHARS]


def entity_ref(value: Any) -> dict[str, Any] | None:
    """The ``$ref`` projection of an Evennia entity, else ``None``.

    An ObjectDB reference keeps exactly the specified ``$ref``/``typeclass``/
    ``key`` shape, because that is the one the raw-object route can resolve. An
    AccountDB or ScriptDB reference carries an extra ``model`` discriminator:
    their primary keys live in different tables, so a console must not send
    them to the ObjectDB route where an unrelated row could share the number.
    """
    if isinstance(value, entity_types()):
        reference = {
            "$ref": f"#{value.pk}",
            "typeclass": str(getattr(value, "db_typeclass_path", "") or ""),
            "key": str(getattr(value, "db_key", "") or ""),
        }
        model = _model_name(value)
        if model != "object":
            reference["model"] = model
        return reference
    return None


def _model_name(value: Any) -> str:
    """The stored-table family of an entity reference."""
    from evennia.accounts.models import AccountDB
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB

    if isinstance(value, ObjectDB):
        return "object"
    if isinstance(value, AccountDB):
        return "account"
    if isinstance(value, ScriptDB):
        return "script"
    return "object"


def unserializable(value: Any) -> dict[str, str]:
    """The ``$unserializable`` marker for a value JSON cannot carry."""
    return {"$unserializable": type(value).__name__, "repr": bounded_repr(value)}


def json_value(value: Any, _seen: frozenset[int] = frozenset()) -> Any:
    """Return a JSON-serialisable projection of ``value``.

    Scalars pass through (a non-finite float becomes an ``$unserializable``
    marker, because neither JSON nor ``json.dumps`` may emit it), references
    become ``$ref``, and everything else recurses until a marker is reached.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # inf/nan are not representable JSON; report them rather than emit them.
        if value != value or value in (float("inf"), float("-inf")):
            return unserializable(value)
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return unserializable(value)
    reference = entity_ref(value)
    if reference is not None:
        return reference
    # Evennia returns stored containers as ``_SaverList``/``_SaverDict``/
    # ``_SaverSet`` wrappers (``MutableSequence``/``MutableMapping``/
    # ``MutableSet``), never the concrete builtins, so the ABCs are the only
    # correct test here; a concrete ``isinstance`` would mark every stored
    # container as unserializable.
    if isinstance(value, Mapping):
        if id(value) in _seen:
            return unserializable(value)
        inner = _seen | {id(value)}
        return {str(key): json_value(item, inner) for key, item in value.items()}
    if isinstance(value, (Sequence, AbstractSet)) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        if id(value) in _seen:
            return unserializable(value)
        inner = _seen | {id(value)}
        return [json_value(item, inner) for item in value]
    return unserializable(value)


__all__ = [
    "MAX_REPR_CHARS",
    "bounded_repr",
    "entity_ref",
    "entity_types",
    "json_value",
    "unserializable",
]
