"""Acceptance-time hunt target provisioning through the ambient population owner.

Design D-Q3: the quest layer never creates, moves, or deletes an individual
itself. A regional species hunt's acceptance guarantee is obtained here — the
map layer's own ensure API — which decides legality under habitat, authored
placement capacity, ownership markers, and current site state.

The guarantee is about *ordinary-eligible* targets (the countable variants that
are ordinary baseline variants; design D-Q2). Availability counts every living
individual the region's bookkeeping holds, whatever owner created it — ambient,
site, quest, or otherwise — because all of them are reachable targets a player
can defeat. Only the *provisioning* half is restricted to the ambient owner's
own footprint: it tops the region's authored ambient population up from the
maintained ``quantity`` towards the authored ``capacity`` ceiling of each
covered coordinate, through the ambient branch's own creation primitive, so the
individuals carry the ambient ownership marker and are reconciled by that same
owner afterwards.

Three boundaries are pinned here:

* **Nothing is rebuilt, moved, or deleted.** A coordinate already holding
  ``capacity`` ambient individuals is skipped, an already-sufficient region
  creates nothing at all, and no foreign-owned, site-owned, or quest-owned
  individual is ever touched.
* **No site is recovered early.** Sites are a source of living targets only
  through the individuals they already hold; the world clock alone decides a
  cleared site's authored in-game recovery (``world.maps.monster_sites``).
* **Feasibility is decided before anything is created.** When the region's
  authored ambient footprint cannot legally supply the shortfall, a named
  refusal is returned and no individual is created, so a failed acceptance can
  never leave a partial target arrangement.

The caller's transaction owns durability. This module writes the wilderness
script's in-process bookkeeping as it creates, which a database rollback does
not reach, so it also publishes the matching snapshot/restore pair
(:func:`snapshot_provisioning_surfaces` /
:func:`restore_provisioning_surfaces`) for the acceptance owner that owns the
transaction that can fail.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from evennia.contrib.grid.wilderness.wilderness import WildernessScript

from typeclasses.monsters import Monster
from world.lore.monster_placement import AMBIENT_PLACEMENT_REGISTRY, AmbientPlacementRule
from world.maps.wilderness_population import (
    _population_key,
    _spawn_species_individual,
    _stored_hp,
    species_rule_for_coordinates,
)
from world.maps.wilderness_provider import (
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    is_footprint_cell,
    region_for_coordinates,
)
from world.observability import log_info, log_warn

#: The closed refusal vocabulary. ``world_unavailable`` means no world is
#: provisioned yet, ``no_ambient_rule`` that the region has no authored ambient
#: placement at all, ``no_eligible_variant`` that the region's authored ambient
#: variants carry none of the hunt's ordinary countable variants, and
#: ``capacity_exhausted`` that the authored capacity that may legally be added
#: is smaller than the shortfall.
PROVISION_WORLD_UNAVAILABLE = "world_unavailable"
PROVISION_NO_AMBIENT_RULE = "no_ambient_rule"
PROVISION_NO_ELIGIBLE_VARIANT = "no_eligible_variant"
PROVISION_CAPACITY_EXHAUSTED = "capacity_exhausted"


@dataclass(frozen=True, slots=True)
class HuntProvisionResult:
    """One provisioning decision: what was created, or the named refusal."""

    created: tuple[int, ...]
    required: int
    available: int
    reason: str | None = None

    @property
    def satisfied(self) -> bool:
        """Whether the guarantee holds (nothing created counts as satisfied)."""
        return self.reason is None


@dataclass(frozen=True, slots=True)
class ProvisioningSnapshot:
    """The in-process wilderness surfaces a rolled-back provisioning touched."""

    wilderness: Any
    itemcoordinates: dict
    rooms: tuple[Any, ...]

    def restore(self) -> None:
        """Put the snapshotted surfaces back, best-effort and idempotently.

        The database rows are already restored by the caller's rollback; this
        only reconciles the process caches Evennia's idmapper and the
        wilderness script keep outside the transaction: the ambient owner's
        bookkeeping, the rooms a provisioned individual was attached to, and any
        cached instance whose row no longer exists.
        """
        try:
            self.wilderness.db.itemcoordinates = dict(self.itemcoordinates)
        except Exception as error:  # observability: ignore R2: the warn below is this handler's facade event
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "key": "wilderness_itemcoordinates",
                    "obj": str(getattr(self.wilderness, "pk", None)),
                },
            )
        for room in self.rooms:
            try:
                contents = getattr(room, "contents_cache", None)
                if contents is not None:
                    contents.init()
            except Exception as error:  # observability: ignore R2: the warn below is this handler's facade event
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "key": "contents_cache",
                        "obj": str(getattr(room, "pk", room)),
                    },
                )
        _discard_orphan_instances()


def _wilderness() -> Any | None:
    """The live wilderness script, or ``None`` before the world is provisioned.

    Discovered at call time rather than captured at import, mirroring the same
    helper in ``world.maps.monster_sites``: a quest acceptance can run before
    ``sync_wilderness`` has built the world, and that must refuse rather than
    raise.
    """
    return WildernessScript.objects.filter(db_key=WILDERNESS_NAME).first()


def snapshot_provisioning_surfaces() -> ProvisioningSnapshot | None:
    """Snapshot the wilderness surfaces acceptance provisioning may write.

    A read-only whole-value snapshot: the ambient owner's bookkeeping plus the
    rooms a provisioning attach could touch. ``None`` when no world exists, in
    which case nothing can be provisioned either.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return None
    return ProvisioningSnapshot(
        wilderness=wilderness,
        itemcoordinates=dict(wilderness.db.itemcoordinates or {}),
        rooms=tuple((wilderness.db.rooms or {}).values()),
    )


def restore_provisioning_surfaces(snapshot: ProvisioningSnapshot | None) -> None:
    """Restore a snapshot taken by :func:`snapshot_provisioning_surfaces`."""
    if snapshot is not None:
        snapshot.restore()


def _discard_orphan_instances() -> None:
    """Evict cached instances whose rows a rollback removed.

    Evennia's idmapper is not transaction-aware and this module *creates*
    individuals inside the caller's transaction, so a rollback leaves the
    created instances cached while their rows are gone; a later row reusing such
    a primary key would otherwise be served as the stale object. The failure path
    is bounded — everything cached then is what the failed acceptance touched —
    so a straight sweep of the shared instance cache is exact and cheap.
    """
    from evennia.objects.models import ObjectDB

    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is None:
        return
    for key, instance in list(cache.items()):
        if key is None or getattr(instance, "_is_deleted", False):
            continue
        if not ObjectDB.objects.filter(pk=key).exists():
            instance.flush_from_cache(force=True)


def _living_region_individuals(
    wilderness: Any, region_key: str
) -> dict[tuple[int, int], list[Monster]]:
    """The region's living individuals, grouped by the cell they occupy.

    One pass over the ambient owner's own bookkeeping: every wilderness monster
    is registered there by its owner, so the count covers ambient-, site-,
    quest-, and foreign-owned individuals alike. Unreadable HP is treated as
    "not a guaranteed living target" and never mutated.
    """
    grouped: dict[tuple[int, int], list[Monster]] = {}
    for obj, coordinates in list((wilderness.db.itemcoordinates or {}).items()):
        if not isinstance(obj, Monster):
            continue
        if (
            not isinstance(coordinates, (tuple, list))
            or len(coordinates) != 2
            or any(
                isinstance(axis, bool) or not isinstance(axis, int)
                for axis in coordinates
            )
        ):
            continue
        cell = (coordinates[0], coordinates[1])
        if region_for_coordinates(*cell) != region_key:
            continue
        try:
            living = _stored_hp(obj) > 0
        except Exception:  # observability: ignore R2: an individual whose stored HP cannot be read is not a guaranteed living target; it is skipped, never mutated
            continue
        if living:
            grouped.setdefault(cell, []).append(obj)
    return grouped


def _candidate_cells(
    region_key: str, rule: AmbientPlacementRule
) -> tuple[tuple[int, int], ...]:
    """Every walkable cell the region's authored ambient rule legally covers.

    Enumerated from the bounded map extent in one deterministic ascending order
    — pure integer arithmetic plus the provider's footprint rule, one bounded
    scan of 224x224 cells and no database read — and independent of whether a
    room happens to be materialized there: the authored capacity is per covered
    coordinate, so a region nobody has walked through yet still has exactly the
    capacity its author gave it. Cells inside the contract-pinned hunting band,
    or covered by any other ambient branch, keep their own branch and are never
    provisioned into.
    """
    cells: list[tuple[int, int]] = []
    for x in range(WILDERNESS_MAX_X + 1):
        for y in range(WILDERNESS_MAX_Y + 1):
            if region_for_coordinates(x, y) != region_key:
                continue
            if is_footprint_cell((x, y)):
                continue
            if species_rule_for_coordinates(x, y) != rule:
                continue
            cells.append((x, y))
    return tuple(cells)


def _emit_unavailable(
    region_key: str,
    species_key: str,
    ordinary_variant_keys: tuple[str, ...],
    required: int,
    available: int,
    reason: str,
) -> None:
    """Record a refused guarantee immediately (the acceptance then rolls back).

    Scheduled directly rather than on commit: this path always ends in a
    rejected acceptance whose transaction rollback would discard an on-commit
    callback, and no persistent state changed on it.
    """
    log_warn(
        "hunt_targets_unavailable",
        context={
            "region": region_key,
            "species": species_key,
            "variant": ordinary_variant_keys,
            "required": required,
            "available": available,
            "reason": reason,
        },
    )


def _emit_provisioned(
    region_key: str,
    species_key: str,
    ordinary_variant_keys: tuple[str, ...],
    required: int,
    available: int,
    created: tuple[int, ...],
) -> None:
    """Record created targets on the enclosing durable commit."""
    frozen = {
        "region": region_key,
        "species": species_key,
        "variant": ordinary_variant_keys,
        "required": required,
        "available": available,
        "created": created,
    }
    transaction.on_commit(lambda: log_info("hunt_targets_provisioned", context=frozen))


def ensure_hunt_targets(
    region_key: str,
    species_key: str,
    ordinary_variant_keys: tuple[str, ...],
    needed: int,
    *,
    wilderness: Any | None = None,
) -> HuntProvisionResult:
    """Guarantee enough reachable, living ordinary-eligible targets in a region.

    Returns the created identities when it had to provision, an empty ``created``
    tuple when the region already held enough, or a named refusal when the
    region's authored ambient placement cannot legally supply the shortfall. The
    refusal creates nothing, so a caller that wraps this in its own transaction
    has nothing to undo on that path.
    """
    if needed <= 0:
        return HuntProvisionResult((), needed, 0, None)
    ordinary = tuple(dict.fromkeys(ordinary_variant_keys))
    if not ordinary:
        _emit_unavailable(
            region_key,
            species_key,
            ordinary,
            needed,
            0,
            PROVISION_NO_ELIGIBLE_VARIANT,
        )
        return HuntProvisionResult((), needed, 0, PROVISION_NO_ELIGIBLE_VARIANT)
    world = _wilderness() if wilderness is None else wilderness
    if world is None:
        _emit_unavailable(
            region_key, species_key, ordinary, needed, 0, PROVISION_WORLD_UNAVAILABLE
        )
        return HuntProvisionResult((), needed, 0, PROVISION_WORLD_UNAVAILABLE)

    living = _living_region_individuals(world, region_key)
    eligible = frozenset(ordinary)
    available = sum(
        1
        for members in living.values()
        for member in members
        if member.species_key == species_key and member.variant_key in eligible
    )
    if available >= needed:
        # The guarantee already holds: nothing is rebuilt, moved, or created.
        return HuntProvisionResult((), needed, available, None)

    rule = AMBIENT_PLACEMENT_REGISTRY.get(region_key)
    if rule is None:
        _emit_unavailable(
            region_key, species_key, ordinary, needed, available, PROVISION_NO_AMBIENT_RULE
        )
        return HuntProvisionResult((), needed, available, PROVISION_NO_AMBIENT_RULE)
    creatable = tuple(key for key in rule.variant_keys if key in eligible)
    if not creatable:
        _emit_unavailable(
            region_key,
            species_key,
            ordinary,
            needed,
            available,
            PROVISION_NO_ELIGIBLE_VARIANT,
        )
        return HuntProvisionResult((), needed, available, PROVISION_NO_ELIGIBLE_VARIANT)

    candidates = _candidate_cells(region_key, rule)
    headroom = {
        cell: max(0, rule.capacity - len(living.get(cell, ())))
        for cell in candidates
    }
    deficit = needed - available
    if sum(headroom.values()) < deficit:
        _emit_unavailable(
            region_key,
            species_key,
            ordinary,
            needed,
            available,
            PROVISION_CAPACITY_EXHAUSTED,
        )
        return HuntProvisionResult((), needed, available, PROVISION_CAPACITY_EXHAUSTED)

    created: list[int] = []
    cursor = 0
    remaining = deficit
    for cell in candidates:
        take = min(headroom[cell], remaining)
        for _ in range(take):
            individual = _spawn_species_individual(
                world, cell, creatable[cursor % len(creatable)], _population_key(*cell)
            )
            created.append(individual.pk)
            cursor += 1
        remaining -= take
        if remaining == 0:
            break
    identities = tuple(created)
    _emit_provisioned(
        region_key, species_key, ordinary, needed, available, identities
    )
    return HuntProvisionResult(identities, needed, available, None)
