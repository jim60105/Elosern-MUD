"""The all-or-nothing item-use rollback journal (design D3).

Part of the ``world.rules.items`` package: the pre-write snapshot/restore
machinery every settlement runs through, kept byte-identical to the shipped
single-module journal — the capture ordering and per-surface best-effort
restore are the load-bearing half of the item-use transaction contract.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from world.observability import log_warn
from world.quests.transitions import restore_quest_log, snapshot_quest_log
from world.rules.clock import (
    _flush_deleted_instance,
    _refresh_advance_entity_caches,
)
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)


#: Every ``sexual_state``-category attribute the sexual surface writes,
#: snapshotted per touched entity by the journal. The handler-published state
#: lives in ``sexual_traits`` (category ``traits``); the climax pipeline
#: additionally stages ``pending_climax_extension`` — which
#: ``apply_pleasure_gain`` may write for a target mid-climax — plus the
#: identity/experience and per-turn fields that share the category. Capturing
#: the whole category (mirroring the shipped round-touched sexual surface)
#: keeps a rolled-back settlement byte-identical on every writer surface,
#: including the ``pending_climax_extension`` a handler-read-only rollback
#: test would otherwise leave behind as a phantom extension.
_SEXUAL_STATE_KEYS = (
    "virgin",
    "experience_types",
    "climax_turns",
    "pending_climax_extension",
)


def _entity_identity(entity: Any) -> tuple[str, int]:
    """Key one captured journal record by the entity's own identity.

    Primary key plus ``str`` identity: the assert on restore may only write a
    record back to the entity it came from, and an unsaved/pk-less entity
    still keys distinctly through ``id()``.
    """
    pk = getattr(entity, "pk", None) or getattr(entity, "id", None)
    if pk is None:
        return ("id", id(entity))
    return ("pk", int(pk))


@dataclass
class _EntitySnapshot:
    """The per-entity half of the rollback journal (design D3).

    Traits, buffs, and the full sexual surface for one touched entity — the
    surfaces every effect family can write on anyone the plan steps on.
    Restore asserts the identity of the entity it writes back to.
    """

    entity: Any
    traits: tuple[bool, Any] | None = None
    buffs: tuple[bool, Any] | None = None
    sexual_traits: tuple[bool, Any] | None = None
    sexual_state: dict[str, tuple[bool, Any]] = field(default_factory=dict)

    @classmethod
    def capture(cls, entity: Any) -> "_EntitySnapshot":
        """Snapshot this entity's writable surfaces, pre-write."""
        return cls(
            entity=entity,
            traits=snapshot_traits(entity),
            buffs=attribute_snapshot(entity, "buffs"),
            sexual_traits=attribute_snapshot(
                entity, "sexual_traits", category="traits"
            ),
            sexual_state={
                key: attribute_snapshot(entity, key, category="sexual_state")
                for key in _SEXUAL_STATE_KEYS
            },
        )

    def restore(self) -> None:
        """Write this entity's snapshot back, best-effort per surface."""
        entity = self.entity
        if self.traits is not None:
            restore_traits(entity, self.traits)
        if self.buffs is not None:
            restore_attribute_best_effort(entity, "buffs", self.buffs)
        if self.sexual_traits is not None:
            restore_attribute_best_effort(
                entity, "sexual_traits", self.sexual_traits, category="traits"
            )
        for key, surface in self.sexual_state.items():
            if surface is None:
                continue
            existed, value = surface
            if not existed:
                # The settlement (or the climax pipeline) created the
                # attribute after capture: the pre-write state was its
                # absence, so removal — not a value write — is the restore.
                try:
                    entity.attributes.remove(key, category="sexual_state")
                except Exception as error:
                    log_warn(
                        "rollback_restore_failed",
                        exc=error,
                        context={
                            "stage": "item_journal_attribute_remove",
                            "obj": str(entity),
                            "key": key,
                        },
                    )
                continue
            restore_attribute_best_effort(
                entity, key, surface, category="sexual_state"
            )
        try:
            entity.__dict__.pop("sexual", None)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "item_journal_sexual_cache",
                    "obj": str(entity),
                    "key": "sexual",
                },
            )


@dataclass
class ItemTouchedJournal:
    """Pre-write snapshots of every surface an item-use settlement may touch.

    Multi-entity since add-item-effect-targeting (design D3): ``entities``
    holds one per-entity record — traits, buffs, and the sexual surface —
    keyed by entity identity and captured for **every** entity the plan
    touches, the actor included, through the same capture path (no special
    case). Only the actor consumes, so the actor-owned surfaces (inventory,
    quest log, the deleted-mirror instance, and the contents-cache re-seed)
    are captured once, actor-only — a per-target capture would invite a
    restore that writes inventory onto a companion.

    The resolver captures this before any write (a lazy per-target capture
    taken after an earlier target's write cannot restore state that earlier
    step's cascade touched — pleasure moves four sexual values at once) and
    hands it to the caller on success, so an outer combat transaction whose
    later phase fails can restore the trait, inventory, quest-progress, buff,
    sexual, and mirror/contents/idmapper caches the resolver committed.
    Restoration is best-effort per surface with a logged diagnostic and is
    safe to run twice (idempotent value writes). The buff surface restores
    through the attribute handler, which Evennia's ``BuffHandler`` re-reads on
    every access, so live handler reads recover together with persistence.
    **The in-process cache drop runs per captured entity, not only the
    actor**: ``restore_traits`` alone clears only the trait cache, while
    ``_refresh_advance_entity_caches`` additionally pops the memoized
    ``entity.sexual`` handler off ``entity.__dict__`` — skipping the drop for
    a companion would roll back stored sexual state while leaving a stale
    in-memory ``companion.sexual`` readable in the same process.
    """

    actor: Any
    entities: dict[tuple[str, int], "_EntitySnapshot"] = field(default_factory=dict)
    inventory: tuple[bool, Any] | None = None
    quest_log: tuple[bool, Any] | None = None
    mirror: Any | None = None
    mirror_pk: int | None = None

    @classmethod
    def capture(cls, actor: Any, targets: Sequence[Any] = ()) -> "ItemTouchedJournal":
        """Snapshot every surface one settlement may reach, pre-write.

        ``targets`` is every entity the plan will step on; the actor is
        captured through the same per-entity path as any target (the plan
        steps the actor for self-scoped effects, so the actor is normally in
        ``targets`` already; dedup keeps one record either way).
        """
        journal = cls(
            actor=actor,
            inventory=attribute_snapshot(actor, "inventory"),
            quest_log=snapshot_quest_log(actor),
        )
        for entity in dict.fromkeys((actor, *targets)):
            journal.entities[_entity_identity(entity)] = _EntitySnapshot.capture(entity)
        return journal

    def note_mirror(self, mirror: Any) -> None:
        """Record the live mirror instance before its deletion."""
        self.mirror = mirror
        self.mirror_pk = mirror.id

    def restore(self) -> None:
        """Restore every snapshotted surface after a rolled-back settlement."""
        for identity, record in self.entities.items():
            entity = record.entity
            if _entity_identity(entity) != identity:
                # Identity assert (design Risks): a record may only be
                # written back to the entity it came from. A mismatch means
                # the journal data itself was corrupted (a crossed pairing);
                # writing either entity's snapshot onto the other would be a
                # silent data-destroying "fix", so the record is skipped with
                # a loud diagnostic instead.
                log_warn(
                    "rollback_restore_failed",
                    context={
                        "stage": "item_journal_identity",
                        "obj": str(entity),
                        "key": str(identity),
                    },
                )
                continue
            record.restore()
            try:
                _refresh_advance_entity_caches(entity)
            except Exception as error:
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "item_journal_entity_caches",
                        "obj": str(entity),
                        "key": "traits",
                    },
                )
        actor = self.actor
        if self.inventory is not None:
            restore_attribute_best_effort(actor, "inventory", self.inventory)
        if self.quest_log is not None:
            restore_quest_log(actor, self.quest_log)
        if self.mirror is not None:
            try:
                _flush_deleted_instance(self.mirror)
            except Exception as error:
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "item_journal_mirror_flush",
                        "obj": str(actor),
                        "key": str(self.mirror_pk),
                    },
                )
        try:
            contents_cache = getattr(actor, "contents_cache", None)
            if contents_cache is not None:
                contents_cache.init()
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "item_journal_contents_cache",
                    "obj": str(actor),
                    "key": "contents_cache",
                },
            )
