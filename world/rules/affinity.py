"""Hidden NPC-to-player affinity: records, handler, and the sole writer (affinity-system).

Every NPC holds one affinity record per player it has interacted with, stored
as serialized data on the NPC's ``relations_data`` attribute through the
``RelationHandler`` mounted on ``LivingEntity.relations``. ``apply_affinity_change``
is the only function that writes affinity values; callers (talk, trade, guild)
invoke it inside their own all-or-nothing commits and restore the host's
``relations_data`` surface on failure. Reads never materialize a record, so a
mere look can never create one.
"""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.observability import log_warn
from world.rules.affinity_config import AffinityStage, get_config
from world.rules.clock import CLOCK_YAML

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

NATURAL_CAP = 99

AFFINITY_DAILY_CAP_HINT = "（今天你們之間的交流已經夠多了，她看起來有些疲憊。）"


class AffinitySource(StrEnum):
    """The closed set of affinity gain sources."""

    TALK = "talk"
    TRADE = "trade"
    GUILD = "guild"
    AI_DIALOGUE = "ai_dialogue"
    QUEST_COMPLETION = "quest_completion"
    FRIENDLY_FIRE = "friendly_fire"
    SEXUAL_FORCED = "sexual_forced"


@dataclass(frozen=True)
class AffinityRecord:
    """One NPC-to-player affinity record (value, cap, daily budget counters).

    ``daily_gain`` counts the capped positive deltas applied since the world-day
    tick stored in ``daily_tick``; a future cap-break event only raises ``cap``.
    """

    value: int = 0
    cap: int = NATURAL_CAP
    daily_gain: int = 0
    daily_tick: int = 0

    def to_storage(self) -> dict[str, int]:
        """Serialize into a JSON-safe storage dict."""
        return {
            "value": self.value,
            "cap": self.cap,
            "daily_gain": self.daily_gain,
            "daily_tick": self.daily_tick,
        }

    @classmethod
    def from_storage(cls, data: Any) -> "AffinityRecord":
        """Tolerantly parse one storage dict (quest-record idiom, D-7).

        Missing fields take defaults; type-violating or negative fields reset
        the whole record to a fresh default and log the recovery. This never
        raises, so a corrupted record can never crash a look or a conversation.
        """
        if not isinstance(data, dict):
            try:
                data = dict(data)
            except (TypeError, ValueError):
                log_warn(
                    "affinity_relations_record_reset",
                    context={"reason": "record is not a mapping"},
                )
                return cls()
        fields = {}
        for field, default in (
            ("value", 0),
            ("cap", NATURAL_CAP),
            ("daily_gain", 0),
            ("daily_tick", 0),
        ):
            if field not in data:
                fields[field] = default
                continue
            value = data[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                _recover(f"record field {field!r} is not a non-negative integer")
                return cls()
            fields[field] = value
        return cls(**fields)


def _recover(reason: str) -> None:
    log_warn("affinity_relations_record_reset", context={"reason": reason})


class RelationHandler:
    """Per-NPC affinity store keyed by player primary key.

    Reads return defaults without persisting anything; ``has_record`` is the
    only way to distinguish a stored record from a default.
    """

    def __init__(self, npc: Any) -> None:
        self.npc = npc

    def _container(self) -> dict[str, Any]:
        """A fresh copy of the persisted per-player dict, or ``{}``."""
        raw = self.npc.db.relations_data or None
        if raw is None:
            return {}
        if not hasattr(raw, "items"):
            log_warn(
                "affinity_relations_data_not_mapping",
                context={"npc": str(self.npc), "key": "relations_data"},
            )
            return {}
        return {str(key): value for key, value in dict(raw).items()}

    def _load(self, player: Any) -> AffinityRecord | None:
        """Parse the stored record for ``player``, or ``None`` when absent."""
        entry = self._container().get(str(player.pk))
        if entry is None:
            return None
        return AffinityRecord.from_storage(entry)

    def _save(self, player: Any, record: AffinityRecord) -> None:
        """Persist one record; assigns a fresh dict so Evennia saves it."""
        container = self._container()
        container[str(player.pk)] = record.to_storage()
        self.npc.db.relations_data = container

    def has_record(self, player: Any) -> bool:
        """Whether a stored record exists for ``player`` (no materialization)."""
        return str(player.pk) in self._container()

    def affinity_for(self, player: Any) -> int:
        """The hidden value for ``player``, or 0 when no record exists."""
        record = self._load(player)
        return record.value if record is not None else 0

    def cap_for(self, player: Any) -> int:
        """The record's natural cap for ``player``, or the default when absent."""
        record = self._load(player)
        return record.cap if record is not None else NATURAL_CAP

    def stage_for(self, player: Any) -> AffinityStage:
        """The resolved stage for ``player`` (defaults for recordless players)."""
        record = self._load(player)
        value = record.value if record is not None else 0
        return get_config().stage_for_value(value)


@dataclass(frozen=True)
class AffinityChangeOutcome:
    """The structured result of one affinity write, for caller feedback.

    ``delta_used`` is the actually applied amount (0 when rejected, capped out,
    or at the natural cap); ``budget_capped`` means the daily budget limited or
    blocked the delta; ``source_rejected`` means the source or owner was
    invalid and nothing was written; ``auto_leave_notification`` carries the
    party auto-leave line when a negative delta ended a companion party -- the
    caller sends it only after its own transaction commits (the writer never
    notifies).
    """

    delta_used: int
    applied: bool
    budget_capped: bool
    source_rejected: bool
    auto_leave_notification: str | None = None

    @classmethod
    def rejected(cls) -> "AffinityChangeOutcome":
        return cls(
            delta_used=0,
            applied=False,
            budget_capped=False,
            source_rejected=True,
        )


def run_auto_leave_recheck(npc: Any, player: Any) -> str | None:
    """The wired party auto-leave rule, run after every negative delta.

    When ``npc`` is a bound companion of ``player`` and its affinity toward
    the player dropped below the invite threshold, the party ends through the
    sole-writer ``leave_party`` and the notification line is returned for the
    caller to send only after its own transaction commits. Returns ``None``
    when no party ends. Deterministic and side-effect free for non-companions.
    A failed leave raises so the caller's transaction rolls back the whole
    negative-delta operation -- "affinity below threshold but still bound" is
    unreachable.
    """
    from world.rules.affinity_config import get_config
    from world.rules.party import AUTO_LEAVE_MESSAGE, is_companion, leave_party

    if not is_companion(npc, player):
        return None
    if npc.relations.affinity_for(player) >= get_config().invite_threshold:
        return None
    leave_party(npc, player, reason="affinity_below_threshold")
    return AUTO_LEAVE_MESSAGE


def _current_day() -> int:
    from world.rules.clock import get_world_clock

    return int(get_world_clock().tick // _DAY_SECONDS)


def apply_affinity_change(
    npc: Any, player: Any, source: Any, delta: int
) -> AffinityChangeOutcome:
    """The sole affinity writer: apply ``delta`` from a closed source set.

    An unknown source or a non-NPC owner is rejected without writing. Capped
    positive sources share the daily budget (lazily reset by world day before
    budgeting) and clamp to the record's cap; ``quest_completion`` bypasses the
    budget. Negative deltas never reset or restore budget, floor at 0, and
    always run the auto-leave recheck hook.
    """
    if isinstance(delta, bool) or not isinstance(delta, int):
        return AffinityChangeOutcome.rejected()
    if isinstance(source, str):
        try:
            source = AffinitySource(source)
        except ValueError:  # observability: ignore R2: an unknown source is a validation rejection surfaced to the caller as a rejected outcome
            return AffinityChangeOutcome.rejected()
    elif not isinstance(source, AffinitySource):
        return AffinityChangeOutcome.rejected()

    from typeclasses.npcs import NPC

    if not isinstance(npc, NPC):
        return AffinityChangeOutcome.rejected()

    handler = npc.relations
    record = handler._load(player) or AffinityRecord()
    if delta < 0:
        new_value = max(record.value + delta, 0)
        applied = new_value - record.value
        notification = None
        with transaction.atomic():
            if applied != 0:
                handler._save(player, replace(record, value=new_value))
            try:
                notification = run_auto_leave_recheck(npc, player)
            except Exception:
                # A failed auto-leave must roll back the whole negative-delta
                # operation: restore the in-process surface explicitly (the
                # savepoint restores the database writes) and propagate so
                # callers see the operation fail.
                handler._save(player, record)
                raise
        return AffinityChangeOutcome(
            delta_used=applied,
            applied=applied != 0,
            budget_capped=False,
            source_rejected=False,
            auto_leave_notification=notification,
        )

    capped = source is not AffinitySource.QUEST_COMPLETION
    reset_tick = False
    if capped:
        day = _current_day()
        if record.daily_tick != day:
            record = replace(record, daily_gain=0, daily_tick=day)
            reset_tick = True
    headroom = max(record.cap - record.value, 0)
    applied = 0
    budget_capped = False
    if capped:
        remaining = max(
            get_config().daily_interaction_cap - record.daily_gain, 0
        )
        applied = min(delta, remaining, headroom)
        budget_capped = remaining < delta and applied < delta
    else:
        applied = min(delta, headroom)
    if applied > 0:
        updated = replace(record, value=record.value + applied)
        if capped:
            updated = replace(updated, daily_gain=updated.daily_gain + applied)
        handler._save(player, updated)
    elif capped and reset_tick:
        # Persist the lazy day reset even when the delta applies zero, so the
        # record's budget metadata never trails the current world day while no
        # budget is consumed (daily_gain stays 0).
        handler._save(player, record)
    return AffinityChangeOutcome(
        delta_used=applied,
        applied=applied != 0,
        budget_capped=budget_capped,
        source_rejected=False,
    )


def raise_affinity_cap(npc: Any, player: Any, new_cap: int) -> bool:
    """Raise a record's ``cap`` monotonically; the sole cap writer (affinity-cap-break D1).

    Only this function mutates a record's ``cap``. For a player without a
    record it first creates a fresh record (value 0, cap 99) so a milestone can
    never silently fail on a recordless bound companion, then raises it. It
    raises only when ``new_cap`` is strictly greater than the current cap,
    leaves the value and the daily-gain fields untouched, runs no daily-budget
    logic and no auto-leave hook, and returns whether the cap changed.
    """
    from typeclasses.npcs import NPC

    if isinstance(new_cap, bool) or not isinstance(new_cap, int):
        return False
    if not isinstance(npc, NPC):
        return False

    handler = npc.relations
    record = handler._load(player) or AffinityRecord()
    if new_cap <= record.cap:
        return False
    handler._save(player, replace(record, cap=new_cap))
    return True


def restore_relations_surfaces(snapshots: dict[int, Any]) -> None:
    """Restore in-process ``relations_data`` surfaces after a rolled-back round.

    The idmapper attribute cache is not transaction-aware: a rolled-back
    ``relations_data`` write still leaves the post-write value readable
    in-process. Callers that snapshot the records before an atomic block
    invoke this helper in the failure path so readers never observe the
    rolled-back state. The writer's own failure branch already restores the
    failing record; this covers every earlier hit of the same round.
    """
    from evennia.objects.models import ObjectDB

    for npc_pk, data in snapshots.items():
        entity = ObjectDB.objects.filter(id=npc_pk).first()
        if entity is not None:
            entity.db.relations_data = data


def affinity_stage_line(npc: Any, looker: Any) -> str:
    """The stage flavor line for ``looker``, or ``""`` when no record exists.

    The read never persists; the numeric value never appears.
    """
    if looker is None or not hasattr(npc, "relations"):
        return ""
    handler = npc.relations
    if not handler.has_record(looker):
        return ""
    return handler.stage_for(looker).look_flavor
