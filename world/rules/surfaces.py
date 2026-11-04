"""Shared snapshot/restore support for multi-surface deterministic writes (D-10).

Reward claims, purchases, sales, registration, exam settlement, and inventory
plans all follow one order: parse, validate, compute replacement values, then
apply every write inside one ``transaction.atomic()`` block. On any exception
the database rolls back; Evennia's in-process attribute/trait caches must be
restored to their pre-operation values so no caller serves a stale read.

The same module owns the engine-cache recovery those failure paths need
(:func:`flush_idmapper_cache`, :func:`flush_orphan_instances`,
:func:`flush_instance`): a rolled-back write also leaves the idmapper and
every room's contents cache disagreeing with the database.
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


def persisted_hp(entity: Any) -> float:
    """Read entity's persisted HP record directly without materializing TraitHandler.

    Evennia's ``TraitHandler.get`` constructs a ``Trait`` from persisted ``_SaverDict``
    and constructor validation calls ``trait_data.update(...)``, which saves the
    Attribute on read. To ensure pure, side-effect-free reads that never modify
    Attribute records or trigger saves, read the persisted trait mapping directly.
    Fails closed to 0.0 on missing or unreadable records.
    """
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return 0.0
    traits = attributes.get("traits", category="traits")
    if not isinstance(traits, Mapping):
        return 0.0
    record = traits.get("hp")
    if not isinstance(record, Mapping):
        return 0.0
    if "current" in record:
        try:
            return float(record["current"])
        except (ValueError, TypeError):  # observability: ignore R2: malformed persisted numeric record fails closed to 0.0
            return 0.0
    try:
        return float(record.get("base", 0) + record.get("mod", 0)) * float(
            record.get("mult", 1)
        )
    except (ValueError, TypeError):  # observability: ignore R2: unparseable gauge expression fails closed to 0.0
        return 0.0


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


def _refresh_contents_cache(container: Any) -> None:
    """Re-read one container's contents cache from the database.

    Best-effort: a refresh failure on a rollback path is logged and never
    masks the operation failure that opened the compensation.
    """
    try:
        container.contents_cache.init()
    except Exception as error:  # observability: ignore R2: the warn below is this handler's facade event
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={
                "stage": "contents_cache",
                "obj": str(getattr(container, "pk", container)),
            },
        )


def flush_idmapper_cache() -> None:
    """Flush the shared idmapper caches without replacing their dictionaries.

    Evennia's ``flush_cache()`` rebuilds each ``__instance_cache__`` mapping.
    ``ContentsHandler`` captures that mapping by reference when a room's
    contents cache is first built, so a rebuild detaches every existing handler
    from the live idmapper permanently: ``contents_cache.get()`` then falls
    back to a database read and logs ``contents cache failed for <room>`` on
    every call. Mutating the same mapping in place applies Evennia's identical
    ``at_idmapper_flush`` filter while keeping those handles live. Instances a
    rolled-back transaction deleted in memory are evicted unconditionally: the
    rollback restored their rows, so the stale deletion must not survive.
    """
    import gc

    from evennia.utils.idmapper.models import SharedMemoryModel

    def leaf_classes(cls: type) -> Any:
        subclasses = cls.__subclasses__()
        if subclasses:
            for subclass in subclasses:
                yield from leaf_classes(subclass)
        else:
            yield cls

    for cls in leaf_classes(SharedMemoryModel):
        cache = getattr(getattr(cls, "__dbclass__", None), "__instance_cache__", None)
        if cache is None:
            continue
        for key in list(cache.keys()):
            instance = cache.get(key)
            if (
                instance is None
                or getattr(instance, "_is_deleted", False)
                or instance.at_idmapper_flush()
            ):
                cache.pop(key, None)
    gc.collect()


def flush_instance(instance: Any) -> None:
    """Force one cached instance out of the idmapper and refresh its room.

    ``delete()`` evicts only when ``at_idmapper_flush()`` returns True, which
    ``TypedObject`` refuses while the object holds an NAttribute, and a row a
    rolled-back transaction created leaves no in-process trace to evict it. The
    room's contents cache keeps the evicted primary key otherwise, so it is
    re-read from the rolled-back rows here.
    """
    container = getattr(instance, "location", None)
    instance.flush_from_cache(force=True)
    if container is not None:
        _refresh_contents_cache(container)


def flush_orphan_instances() -> None:
    """Evict every cached instance whose row a rollback removed.

    Evennia's idmapper is not transaction-aware: a stage that *creates*
    objects inside a transaction has no pre-operation snapshot to restore, so
    the row disappears while the instance and its room's cached primary key
    stay in process. A later row reusing that primary key would otherwise be
    served as the stale object, and every contents read would log a cache
    failure. This runs only on failure paths, where the cache is bounded by
    what the failed operation touched.
    """
    from evennia.objects.models import ObjectDB

    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is None:
        return
    containers: dict[int, Any] = {}
    for key, instance in list(cache.items()):
        if key is None or getattr(instance, "_is_deleted", False):
            continue
        if ObjectDB.objects.filter(pk=key).exists():
            continue
        container = getattr(instance, "location", None)
        if container is not None:
            containers[id(container)] = container
        instance.flush_from_cache(force=True)
    for container in containers.values():
        _refresh_contents_cache(container)