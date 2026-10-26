"""Shared snapshot/restore support for multi-surface deterministic writes (D-10).

Reward claims, purchases, sales, registration, exam settlement, and inventory
plans all follow one order: parse, validate, compute replacement values, then
apply every write inside one ``transaction.atomic()`` block. On any exception
the database rolls back; Evennia's in-process attribute/trait caches must be
restored to their pre-operation values so no caller serves a stale read.
"""

from copy import deepcopy
from typing import Any, Mapping

from world.observability import log_warn


def attribute_snapshot(obj: Any, key: str, category: str | None = None) -> tuple[bool, Any]:
    """Return ``(existed, deepcopy-of-value)`` for one attribute."""
    exists = obj.attributes.has(key, category=category)
    value = (
        deepcopy(obj.attributes.get(key, category=category))
        if exists
        else None
    )
    return exists, value


def restore_attribute(
    obj: Any,
    key: str,
    snapshot: tuple[bool, Any],
    category: str | None = None,
) -> None:
    """Restore one pre-operation attribute value."""
    existed, value = snapshot
    if existed:
        obj.attributes.add(key, deepcopy(value), category=category)
    else:
        obj.attributes.remove(key, category=category)


def restore_attribute_best_effort(
    obj: Any,
    key: str,
    snapshot: tuple[bool, Any],
    category: str | None = None,
) -> None:
    """Restore one attribute, degrading to a cache reset when the write fails."""
    try:
        restore_attribute(obj, key, snapshot, category)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:  # observability: ignore R2: cache invalidation is best-effort; the restore failure itself is logged below
            pass
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "attribute", "obj": str(obj), "key": key, "category": category},
        )


def snapshot_attributes(obj: Any, keys: tuple[str, ...]) -> dict[str, tuple[bool, Any]]:
    return {key: attribute_snapshot(obj, key) for key in keys}


def restore_attributes(obj: Any, snapshots: Mapping[str, tuple[bool, Any]]) -> None:
    for key, snapshot in snapshots.items():
        restore_attribute_best_effort(obj, key, snapshot)


def snapshot_traits(obj: Any) -> tuple[bool, Any]:
    """Snapshot the raw trait-storage attribute (merit/level writes occur there)."""
    return attribute_snapshot(obj, "traits", category="traits")


def restore_traits(obj: Any, snapshot: tuple[bool, Any]) -> None:
    """Restore the trait attribute and refresh the TraitHandler caches."""
    restore_attribute_best_effort(obj, "traits", snapshot, category="traits")
    try:
        obj.traits.trait_data = obj.attributes.get(
            "traits", default={}, category="traits"
        )
        obj.traits._cache.clear()
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "trait_caches", "obj": str(obj), "key": "traits"},
        )


def read_counter_trait(obj: Any, key: str) -> int:
    """Read one counter trait's integer current value (`guild_merit`)."""
    return int(obj.traits[key].current)


def write_counter_trait(obj: Any, key: str, value: int) -> None:
    """Set one counter trait's integer current value."""
    obj.traits[key].current = int(value)


def restore_component_state(
    obj: Any, snapshots: Mapping[str, tuple[bool, Any]]
) -> None:
    """Restore one host's pre-batch attributes and rebuild its component caches.

    A rolled-back transaction restores the durable rows, but every attribute the
    batch wrote stays readable in process: the ``Attribute`` rows themselves are
    idmapper instances whose ``db_value`` the write already replaced, so
    resetting the handler lookup cache alone would re-serve the rolled-back
    values (see ``fix-clock-rollback-cache-sync``). Writing the snapshot back
    through the handler makes those instances agree with the database again.

    The component handler is then rebuilt from the restored ``component_names``
    attribute, so a slot the batch added or removed is no longer cached. Both
    the attribute and the tag cache are dropped first, and the component handler
    is re-initialized through the typeclass's own ``at_init`` (the engine's
    documented cache-rebuild path) instead of reaching into its internals.

    Every step is best-effort: a restore failure is logged and never masks the
    original exception.
    """
    restore_attributes(obj, snapshots)
    for stage, step in (
        ("attribute_cache", obj.attributes.reset_cache),
        ("tag_cache", obj.tags.reset_cache),
        ("component_cache", obj.at_init),
    ):
        try:
            step()
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={"stage": stage, "obj": str(obj)},
            )