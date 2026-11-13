"""The per-character met-person record: one writer, one tolerant reader.

Design ``openspec/changes/met-person-record/design.md`` (D1-D3): each character
owns at most one entry per named NPC, keyed by that NPC's portrait stable key
(:func:`world.art.subjects.character_subject_for`), holding the NPC identity,
the interaction place and the time of the last interaction. Exactly this module
writes the record; presentation reads it through :func:`met_people` and never
mutates it.

The place of an interaction is the settlement whose map holds the room, else
the wilderness region of the cell; an instance room resolves one level through
its origin room, and a district is never a place. Reads skip entries whose NPC
no longer exists or no longer carries the recorded stable key; the writer drops
them on its next write, so no cleanup job exists.

Lookups read their owning module (``world.maps.map_data``,
``world.maps.wilderness_provider``, ``world.lore.*``) at call time, never a
module-level binding, so a republished map world or a rebinding test fixture is
observed without an import cycle back into the map package.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from world.observability import log_info, log_warn

#: The stored envelope's shape version (design D1).
SCHEMA_VERSION = 1

#: The character attribute holding the record, uncategorized (design D1).
MET_PEOPLE_ATTRIBUTE = "met_people"

#: Place-key prefixes; the value after the colon is the settlement map id or
#: the wilderness region key (design D2).
PLACE_SETTLEMENT = "settlement"
PLACE_REGION = "region"

_RECORD_KEYS = frozenset({"schema_version", "seq", "entries"})
_ENTRY_KEYS = frozenset({"npc", "place", "tick", "seq"})


class MetPeopleRecordError(ValueError):
    """A stored met-person record is not a valid schema-1 envelope."""


@dataclass(frozen=True)
class MetPerson:
    """One named NPC the character has interacted with.

    ``npc`` is the live typeclass object resolved at read time; ``place`` is
    the derived place key (``settlement:<map id>`` or ``region:<region key>``)
    and ``seq`` is the record counter value of the last interaction, which
    makes recency ordering total even when two ticks are equal.
    """

    stable_key: str
    npc: Any
    place: str | None
    tick: int
    seq: int


def _is_count(value: Any) -> bool:
    """Whether ``value`` is an exact non-negative integer (booleans reject)."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_record(value: Any) -> dict[str, Any]:
    """Return a fresh, strictly validated copy of one stored envelope.

    Raises :class:`MetPeopleRecordError` for any shape deviation; the caller
    logs and refuses to overwrite the corrupt value (the precedent is
    :func:`world.rules.map_knowledge.record_arrival`).
    """

    if not isinstance(value, Mapping):
        raise MetPeopleRecordError("met-person record is not an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise MetPeopleRecordError(
            f"met-person record has unknown schema version {value.get('schema_version')!r}"
        )
    if set(value) != _RECORD_KEYS:
        raise MetPeopleRecordError(
            f"met-person record has invalid top-level keys {set(value)!r}"
        )
    sequence = value.get("seq")
    if not _is_count(sequence):
        raise MetPeopleRecordError("met-person record has a non-integer sequence")
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, Mapping):
        raise MetPeopleRecordError("met-person record has no entries mapping")

    entries: dict[str, dict[str, Any]] = {}
    for stable_key, entry in raw_entries.items():
        if not isinstance(stable_key, str) or not stable_key:
            raise MetPeopleRecordError(f"invalid met-person stable key {stable_key!r}")
        if not isinstance(entry, Mapping) or set(entry) != _ENTRY_KEYS:
            raise MetPeopleRecordError(
                f"met-person entry {stable_key!r} is not an entry object"
            )
        identifier = entry.get("npc")
        place = entry.get("place")
        tick = entry.get("tick")
        entry_sequence = entry.get("seq")
        if not _is_count(identifier):
            raise MetPeopleRecordError(
                f"met-person entry {stable_key!r} has a non-integer npc identity"
            )
        if place is not None and (not isinstance(place, str) or not place):
            raise MetPeopleRecordError(
                f"met-person entry {stable_key!r} has a non-text place"
            )
        if not _is_count(tick):
            raise MetPeopleRecordError(
                f"met-person entry {stable_key!r} has a non-integer tick"
            )
        # An entry's sequence is the record counter value of its last
        # interaction, so it can never exceed the record's own counter: a
        # larger one would let a later write stamp a smaller, newer value.
        if (
            not _is_count(entry_sequence)
            or entry_sequence < 1
            or entry_sequence > sequence
        ):
            raise MetPeopleRecordError(
                f"met-person entry {stable_key!r} has an out-of-range sequence"
            )
        entries[stable_key] = {
            "npc": identifier,
            "place": place,
            "tick": tick,
            "seq": entry_sequence,
        }
    return {"schema_version": SCHEMA_VERSION, "seq": sequence, "entries": entries}


def _live_entries(
    entries: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[Any, dict[str, Any]]]:
    """Resolve every entry's NPC in one query and keep only live named ones.

    "Gone" (design D3) means the dbid no longer resolves or the object no
    longer yields the recorded stable key; both the read and the write path
    drop such entries through this single rule.
    """

    from evennia.objects.objects import ObjectDB

    from world.art.subjects import ArtSubjectError, character_subject_for

    identifiers = {entry["npc"] for entry in entries.values()}
    if not identifiers:
        return {}
    live = {obj.pk: obj for obj in ObjectDB.objects.filter(id__in=identifiers)}
    kept: dict[str, tuple[Any, dict[str, Any]]] = {}
    for stable_key, entry in entries.items():
        obj = live.get(entry["npc"])
        if obj is None:
            continue
        # A malformed portrait policy means the NPC is no longer a named
        # subject: the entry is simply not live.
        try:
            subject = character_subject_for(obj)
        except ArtSubjectError:  # observability: ignore R2: a malformed policy reads as no subject
            continue
        if subject is None or subject.key != stable_key:
            continue
        kept[stable_key] = (obj, dict(entry))
    return kept


def _recording_owner(actor: Any) -> Any | None:
    """The character whose record an interaction by ``actor`` belongs to.

    A possessed companion's interaction belongs to the owning character when
    the two-way possession binding and the party binding agree; a mismatch, a
    stale binding, or any non-player actor records nothing (design D2 step 1).
    """

    from typeclasses.characters import PlayerCharacter

    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    owner = actor
    if possessed_by is not None:
        from world.rules.party import bound_owner_of

        owner = bound_owner_of(actor)
        if owner is None or type(possessed_by) is not int or owner.pk != possessed_by:
            return None
    return owner if isinstance(owner, PlayerCharacter) else None


def _current_tick() -> int:
    """The world tick of the interaction, or 0 when the clock does not exist."""

    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return int(clock.tick) if clock is not None else 0


def interaction_place(location: Any) -> str | None:
    """The place key of one room, or ``None`` when no place is derivable.

    A grid room inside a published settlement graph is that settlement; a
    terrain room is its wilderness region; an instance room resolves one level
    through its origin room. Districts are never consulted (design D2).
    """

    if location is None:
        return None

    from typeclasses.rooms import GridRoom, InstanceRoom, TerrainRoom

    if isinstance(location, InstanceRoom):
        origin = location.origin_room
        if origin is None or isinstance(origin, InstanceRoom):
            return None
        return interaction_place(origin)

    if isinstance(location, GridRoom):
        from world.maps import map_data

        xyz = location.xyz
        if not xyz or xyz[2] not in map_data.SETTLEMENT_GRAPHS:
            return None
        return f"{PLACE_SETTLEMENT}:{xyz[2]}"

    if isinstance(location, TerrainRoom):
        coordinates = location.coordinates
        if coordinates is None:
            return None
        from world.maps import wilderness_provider

        return f"{PLACE_REGION}:{wilderness_provider.region_for_coordinates(*coordinates)}"

    return None


def place_label(place: str | None) -> str:
    """The player-facing label of one place key (design D2).

    A settlement resolves through the anchor whose wilderness gateway targets
    that map, exactly as the area map's title does, and otherwise names the map
    key. A region resolves through the published region registry and otherwise
    names the region key. A string with no known prefix is returned unchanged,
    and an absent place has no label.
    """

    if not isinstance(place, str) or not place:
        return ""
    prefix, _separator, key = place.partition(":")
    if prefix == PLACE_SETTLEMENT:
        from world.lore import anchors, wilderness_entry

        for entry in wilderness_entry.WILDERNESS_ENTRY_REGISTRY.values():
            if any(gate.z_map_key == key for gate in entry.gates):
                anchor = anchors.anchors().get(entry.anchor_key)
                if anchor is not None:
                    return anchor.display_name_zh
        return key
    if prefix == PLACE_REGION:
        from world.lore import wilderness_regions

        region = wilderness_regions.regions().get(key)
        return region.display_name_zh if region is not None else key
    return place


def record_person_interaction(actor: Any, npc: Any) -> None:
    """Record one interaction with named NPC ``npc`` for ``actor``'s owner.

    No-op (and never raises) for a non-player actor, a mismatched possession
    binding, an NPC without a named portrait policy, a corrupt pre-existing
    record, or a room with no derivable place when the NPC has no entry yet.
    A corrupt record is logged and never overwritten (design D2).
    """

    try:
        owner = _recording_owner(actor)
        if owner is None:
            return

        from world.art.subjects import ArtSubjectError, character_subject_for

        # A malformed portrait policy means the NPC is not a named subject, so
        # the interaction records nothing.
        try:
            subject = character_subject_for(npc)
        except ArtSubjectError:  # observability: ignore R2: a malformed policy reads as no subject
            return
        if subject is None:
            return

        stored = owner.attributes.get(MET_PEOPLE_ATTRIBUTE)
        if stored is None:
            record: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "seq": 0,
                "entries": {},
            }
        else:
            try:
                record = _validate_record(stored)
            except MetPeopleRecordError as error:
                log_warn(
                    "met_people_record_corrupt",
                    exc=error,
                    context={"char": owner.pk, "key": MET_PEOPLE_ATTRIBUTE},
                )
                return

        entries = {
            stable_key: entry
            for stable_key, (_obj, entry) in _live_entries(record["entries"]).items()
        }
        place = interaction_place(actor.location)
        existing = entries.get(subject.key)
        if existing is None and place is None:
            return

        sequence = record["seq"] + 1
        tick = _current_tick()
        if existing is None:
            entries[subject.key] = {
                "npc": npc.pk,
                "place": place,
                "tick": tick,
                "seq": sequence,
            }
        else:
            existing["npc"] = npc.pk
            existing["tick"] = tick
            existing["seq"] = sequence
            if place is not None and place != existing["place"]:
                existing["place"] = place

        updated: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "seq": sequence,
            "entries": entries,
        }
        from django.db import transaction

        from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

        snapshot = attribute_snapshot(owner, MET_PEOPLE_ATTRIBUTE)
        try:
            with transaction.atomic():
                owner.attributes.add(MET_PEOPLE_ATTRIBUTE, updated)
        except Exception as error:
            restore_attribute_best_effort(owner, MET_PEOPLE_ATTRIBUTE, snapshot)
            log_warn(
                "met_person_record_failed",
                exc=error,
                context={"char": owner.pk, "npc": npc.pk, "place": place},
            )
            return
        log_info(
            "met_person_recorded",
            context={"char": owner.pk, "npc": npc.pk, "place": place},
        )
    except Exception as error:
        log_warn(
            "met_person_record_failed",
            exc=error,
            context={"npc": getattr(npc, "pk", None)},
        )


def met_people(character: Any) -> tuple[MetPerson, ...]:
    """The character's recorded named NPCs, newest interaction first.

    Tolerant read: a missing or corrupt record yields ``()``, and an entry is
    omitted when its NPC is gone or no longer carries the recorded stable key
    (design D3). Ordering is total: sequence descending, then stable key.
    """

    if character is None:
        return ()
    try:
        stored = character.attributes.get(MET_PEOPLE_ATTRIBUTE)
        if stored is None:
            return ()
        try:
            record = _validate_record(stored)
        except MetPeopleRecordError as error:
            log_warn(
                "met_people_record_corrupt",
                exc=error,
                context={"char": getattr(character, "pk", None), "key": MET_PEOPLE_ATTRIBUTE},
            )
            return ()
        people = [
            MetPerson(
                stable_key=stable_key,
                npc=obj,
                place=entry["place"],
                tick=entry["tick"],
                seq=entry["seq"],
            )
            for stable_key, (obj, entry) in _live_entries(record["entries"]).items()
        ]
        return tuple(sorted(people, key=lambda person: (-person.seq, person.stable_key)))
    except Exception as error:
        log_warn(
            "met_people_read_failed",
            exc=error,
            context={"char": getattr(character, "pk", None), "key": MET_PEOPLE_ATTRIBUTE},
        )
        return ()
