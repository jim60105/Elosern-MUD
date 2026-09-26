"""Structured, server-authored beats for one settled ordinary combat round.

Design §10.1 of
``docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md``
(change ``combat-beats-panel``) asks for beats the WebClient can play without
parsing narrative prose. This module owns the rules side:

- :func:`capture_round_hp` reads every roster participant's stored HP through
  the same ``stored_gauge_pair`` source the combat panel uses, so a beat's
  ``hp_after`` is true stored HP (``disguised_stats`` is never consulted).
- :class:`RoundRecord` freezes one settled round: its own ``EventLog``s, the
  roster-key → dbref identities, and each participant's stored HP before and
  after the round.
- :func:`build_combat_beats` derives the bounded beat list from those
  structured event records alone — never by parsing prose — and projects each
  damage beat's ``hp_after`` with the knockout floor.

The projection is checked against the recorded end-of-round HP. Any HP change
inside the round that carries no ``damage`` entry (a ``heal``/``self_heal``
line, a drain ``gauge_transfer``, a ``damage_divert``, a silent unattributed
upkeep or regeneration tick, an item heal, a counterattack) makes the last
projected value disagree with the recorded one, so that round raises
:class:`CombatBeatsError` and the panel falls back to the common unavailable
form. Widening the projection needs a spec change.

Every error carries a stable snake_case code as its first argument so the
presentation layer can log a bounded reason: ``too_many_beats``,
``beat_text_too_long``, ``round_id_too_long``, ``unknown_damage_target``,
``damage_amount_invalid``, ``hp_mismatch``.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from evennia.utils.ansi import strip_ansi

from world.rules.event_log import EventEntry, EventLog, render_entry_text


# The closed beat-kind set (design D5). A kind joins this set only through a
# change to the ``webclient-combat-beats`` capability's derivation requirement.
BEAT_KINDS = ("roll", "damage", "target_defeated", "other")

# Entry kinds that map to themselves; every other entry kind maps to ``other``.
_MAPPED_KINDS = frozenset({"roll", "damage", "target_defeated"})

# Bounds (design D8). Nothing is ever truncated: past a bound the round is
# unavailable, because truncation would break the last-``hp_after`` check.
MAX_BEATS = 64
MAX_BEAT_TEXT = 256
MAX_ROUND_ID = 160


class CombatBeatsError(ValueError):
    """One settled round cannot be projected into a bounded beat list."""


@dataclass(frozen=True)
class RoundRecord:
    """One settled ordinary round, frozen for one presentation publication.

    Attributes:
        session_id: The combat session's opaque identifier.
        number: The round number after the round (``rounds_elapsed``).
        logs: The round's OWN event logs, in resolution order. A terminal
            settlement's defeat-aftermath logs are not part of the round and
            must not be passed here.
        identities: Roster key → dbref for every participant of the round.
        hp_before: dbref → stored HP before the round.
        hp_after: dbref → stored HP at the committed end of the round, read
            before any terminal settlement.
    """

    session_id: str
    number: int
    logs: tuple[EventLog, ...]
    identities: Mapping[str, int]
    hp_before: Mapping[int, int]
    hp_after: Mapping[int, int]

    @property
    def round_id(self) -> str:
        """The stable ``"<session_id>/<round number>"`` round identity."""
        return f"{self.session_id}/{self.number}"


@dataclass(frozen=True)
class CombatBeat:
    """One ordered, renderable beat of a settled round."""

    seq: int
    action: int
    kind: str
    actor: str | None
    target: str | None
    amount: int | None
    hp_after: int | None
    text: str


@dataclass(frozen=True)
class CombatBeatsView:
    """The complete frozen beat list of one settled round."""

    round: str
    beats: tuple[CombatBeat, ...]


def capture_round_hp(battlefield: Any) -> tuple[dict[str, int], dict[int, int]]:
    """Read the roster's identities and stored HP at one round boundary.

    Returns ``(identities, hp)`` where ``identities`` maps every roster key to
    its dbref and ``hp`` maps every dbref to its stored current HP. Both terms
    come from :func:`world.rules.action.stored_gauge_pair`, the same read-only
    true-HP source the combat panel's participant rows use (it clamps negative
    stored HP to zero, which is the projection's own floor for a lethal
    overkill).
    """
    # Function-local import (the ``combat_view`` precedent): the action package
    # reaches the Evennia dice contrib, which is not importable while the
    # input-function module is still being collected at startup.
    from world.rules.action import stored_gauge_pair

    identities: dict[str, int] = {}
    hp: dict[int, int] = {}
    for key, entity in battlefield.roster.items():
        dbref = int(entity.pk)
        identities[str(key)] = dbref
        hp[dbref] = stored_gauge_pair(entity, "hp")[0]
    return identities, hp


def _code_points(value: str) -> int:
    return sum(1 for _ in value)


def _identity_of(identities: Mapping[str, int], key: str | None) -> str | None:
    """The opaque catalog key of ``key`` when it names a participant, else None."""
    if key is None or key not in identities:
        return None
    # Local import: the art view reaches the dialogue and roster read models,
    # which the round transaction does not otherwise need.
    from world.rules.art_view import portrait_catalog_key

    return portrait_catalog_key(identities[key])


def _knockout_floors(record: RoundRecord) -> dict[int, int]:
    """The per-dbref projection floor: 1 for a knocked-out target, else 0."""
    floors = {dbref: 0 for dbref in record.identities.values()}
    for event_log in record.logs:
        for entry in event_log.entries:
            if entry.kind != "target_knocked_out":
                continue
            dbref = record.identities.get(entry.target)
            if dbref is not None:
                floors[dbref] = 1
    return floors


def _damage_amount(entry: EventEntry) -> int:
    amount = entry.data.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise CombatBeatsError("damage_amount_invalid")
    return amount


def _beat(seq: int, action: int, entry: EventEntry, record: RoundRecord,
          projected: dict[int, int], floors: dict[int, int]) -> CombatBeat:
    """Build one beat, projecting HP for a ``damage`` entry."""
    kind = entry.kind if entry.kind in _MAPPED_KINDS else "other"
    actor = _identity_of(record.identities, entry.actor)
    target = _identity_of(record.identities, entry.target)
    amount: int | None = None
    hp_after: int | None = None
    if kind == "damage":
        if entry.target is None or entry.target not in record.identities:
            raise CombatBeatsError("unknown_damage_target")
        dbref = record.identities[entry.target]
        if dbref not in projected:
            raise CombatBeatsError("hp_mismatch")
        amount = _damage_amount(entry)
        projected[dbref] = max(floors.get(dbref, 0), projected[dbref] - amount)
        hp_after = projected[dbref]
    text = strip_ansi(render_entry_text(entry))
    if _code_points(text) > MAX_BEAT_TEXT:
        raise CombatBeatsError("beat_text_too_long")
    return CombatBeat(
        seq=seq,
        action=action,
        kind=kind,
        actor=actor,
        target=target,
        amount=amount,
        hp_after=hp_after,
        text=text,
    )


def build_combat_beats(record: RoundRecord) -> CombatBeatsView:
    """Derive the bounded beat list of one settled round, or raise.

    Beats come only from ``record.logs`` in log order and then entry order, so
    the entry kinds map to the closed set in order and each beat carries the
    0-based ordinal of its source log as ``action``. ``amount`` and
    ``hp_after`` are set on ``damage`` beats only.

    Raises :class:`CombatBeatsError` when a bound is exceeded, when a
    ``damage`` beat names a target that is not a round participant, or when the
    projected HP disagrees with the recorded end-of-round HP.
    """
    round_id = record.round_id
    if _code_points(round_id) > MAX_ROUND_ID:
        raise CombatBeatsError("round_id_too_long")
    floors = _knockout_floors(record)
    projected = {int(dbref): int(hp) for dbref, hp in record.hp_before.items()}
    beats: list[CombatBeat] = []
    damaged: set[int] = set()
    for action, event_log in enumerate(record.logs):
        for entry in event_log.entries:
            if len(beats) >= MAX_BEATS:
                raise CombatBeatsError("too_many_beats")
            beat = _beat(len(beats), action, entry, record, projected, floors)
            if beat.kind == "damage":
                damaged.add(record.identities[entry.target])
            beats.append(beat)
    for dbref in damaged:
        recorded = record.hp_after.get(dbref)
        if recorded is None or projected.get(dbref) != int(recorded):
            raise CombatBeatsError("hp_mismatch")
    return CombatBeatsView(round=round_id, beats=tuple(beats))


__all__ = [
    "BEAT_KINDS",
    "MAX_BEATS",
    "MAX_BEAT_TEXT",
    "MAX_ROUND_ID",
    "CombatBeat",
    "CombatBeatsError",
    "CombatBeatsView",
    "RoundRecord",
    "build_combat_beats",
    "capture_round_hp",
]
