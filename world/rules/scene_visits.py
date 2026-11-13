"""The per-character record of entered scene archetypes: one writer, one reader.

``entered-archetype-record`` (gallery window programme, stage 3): the gallery's
scene category lists only the archetypes the live character has entered, so the
fact is written by this one deterministic module at the room-entry seam that
already ensures the scene asset, per character. The writer never raises and a
recording failure never blocks the move (design D1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from world.observability import log_info, log_warn

#: The stored envelope's shape version (design D1).
SCHEMA_VERSION = 1

#: The character attribute holding the record (design D1).
ENTERED_ARCHETYPES_ATTRIBUTE = "entered_scene_archetypes"

_RECORD_KEYS = frozenset({"schema_version", "archetypes"})


class SceneEntryRecordError(ValueError):
    """A stored scene-entry record is not a valid schema-1 envelope."""


def _validated_archetypes(stored: Any) -> list[str]:
    """Return a copy of one stored envelope's archetype keys, or raise."""

    if not isinstance(stored, Mapping) or set(stored) != _RECORD_KEYS:
        raise SceneEntryRecordError("unexpected envelope shape")
    version = stored["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise SceneEntryRecordError("unsupported schema version")
    archetypes = stored["archetypes"]
    # A stored list comes back from the Attribute handler as Evennia's own
    # saver sequence, so the shape check accepts any non-text sequence.
    if not isinstance(archetypes, Sequence) or isinstance(archetypes, (str, bytes)):
        raise SceneEntryRecordError("archetypes is not a sequence of keys")
    for key in archetypes:
        if not isinstance(key, str) or not key:
            raise SceneEntryRecordError("archetype key is not a non-empty string")
    return list(archetypes)


def _write_record(character: Any, record: dict[str, Any]) -> None:
    """Persist ``record`` onto ``character`` (the injectable write seam)."""

    character.attributes.add(ENTERED_ARCHETYPES_ATTRIBUTE, record)


def record_scene_entry(character: Any, archetype: Any) -> None:
    """Record one entered scene archetype for a ``PlayerCharacter`` (never raises).

    A no-op for a non-``PlayerCharacter``, a missing or unregistered archetype,
    a corrupt pre-existing record (logged, never overwritten), and an archetype
    that is already recorded. The save sits in its own savepoint with a
    best-effort cache restore, so a persistence failure is contained instead of
    poisoning the caller's movement (design D1).
    """

    try:
        from typeclasses.characters import PlayerCharacter

        if not isinstance(character, PlayerCharacter):
            return
        from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

        if not isinstance(archetype, str) or archetype not in SCENE_ARCHETYPE_REGISTRY:
            return
        stored = character.attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE)
        if stored is None:
            recorded: list[str] = []
        else:
            try:
                recorded = _validated_archetypes(stored)
            except SceneEntryRecordError as error:
                log_warn(
                    "scene_entry_record_corrupt",
                    exc=error,
                    context={"char": character.pk, "key": ENTERED_ARCHETYPES_ATTRIBUTE},
                )
                return
        if archetype in recorded:
            return
        updated = {
            "schema_version": SCHEMA_VERSION,
            "archetypes": sorted({*recorded, archetype}),
        }
        from django.db import transaction

        from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

        snapshot = attribute_snapshot(character, ENTERED_ARCHETYPES_ATTRIBUTE)
        try:
            with transaction.atomic():
                _write_record(character, updated)
        except Exception as error:
            restore_attribute_best_effort(character, ENTERED_ARCHETYPES_ATTRIBUTE, snapshot)
            log_warn(
                "scene_entry_record_failed",
                exc=error,
                context={"char": character.pk, "archetype": archetype},
            )
            return
        log_info(
            "scene_entry_recorded",
            context={"char": character.pk, "archetype": archetype},
        )
    except Exception as error:
        log_warn(
            "scene_entry_record_failed",
            exc=error,
            context={"char": getattr(character, "pk", None), "archetype": archetype},
        )


def entered_archetypes(character: Any) -> tuple[str, ...]:
    """The registered archetypes ``character`` has entered, in registry order.

    Tolerant, non-mutating read: a missing or corrupt record yields ``()``, and
    a recorded key the registry no longer declares is omitted while the stored
    record stays untouched (design D1/D2).
    """

    try:
        attributes = getattr(character, "attributes", None)
        if attributes is None:
            return ()
        stored = attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE)
        if stored is None:
            return ()
        try:
            recorded = _validated_archetypes(stored)
        except SceneEntryRecordError as error:
            log_warn(
                "scene_entry_record_corrupt",
                exc=error,
                context={
                    "char": getattr(character, "pk", None),
                    "key": ENTERED_ARCHETYPES_ATTRIBUTE,
                },
            )
            return ()
        from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

        registered = set(recorded)
        return tuple(key for key in SCENE_ARCHETYPE_REGISTRY if key in registered)
    except Exception as error:
        log_warn(
            "scene_entry_record_failed",
            exc=error,
            context={
                "char": getattr(character, "pk", None),
                "key": ENTERED_ARCHETYPES_ATTRIBUTE,
                "scope": "read",
            },
        )
        return ()
