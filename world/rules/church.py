"""The Light Church merit ledger — the SOLE writer of ``db.church``.

The ledger is plain character state persisted on the ``db.church``
attribute, created lazily by the first church-rules write (in practice the
first enrollment transaction, once enrollment lands):

- ``merit`` — cumulative grace (恩寵), a non-currency, non-transferable
  counter: only rulebook accrual rows add it (through :func:`add_merit`) and
  only redemption subtracts it (through :func:`subtract_merit`).
- ``enrolled_tick`` — the world-clock tick of enrollment.
- ``redeemed`` — keys redeemed through the ordination catalogue (one-shot).
- ``daily`` — ``{"day": int, "pray": int}`` per-day counters, reset lazily
  on world-clock day change (the ``climax_today`` daily-reset pattern).

Single-writer boundary: every write to ``db.church`` lives in this module —
no command, typeclass, AI, or presentation module assigns any ``db.church``
field (a grep-enforceable audit in the ledger tests pins that). Merit never
enters a wallet path: the wallet modules read ``db.wallet`` only, and only
the offering accept credits copper into it (the sanctioned payout; the
merit-isolation test proves merit itself never moves).

Every mutating primitive mirrors Evennia's attribute-store discipline: the
attribute is read, mutated in a fresh copy, and reassigned inside
``transaction.atomic()`` — the same all-or-nothing rule every other
deterministic-core write follows.

Enrollment (design §5.1) is wired here: :func:`enroll` is the deterministic
three-stage rite behind ``church join`` — it materializes the ledger, stamps
``enrolled_tick``, optionally grants ``saintess_vessel`` to a female
``human_royal`` through the canonical granted-passive write path, and hands
over exactly one clerical vestment through the ``QuestReward`` item-quantity
rail, all inside one transaction with commit-bound observability events.
The accrual behaviours land with ``implement-church-accrual``: :func:`pray_step`
is the venue-bound, time-costed, daily-capped prayer; :func:`offering_menu`
and :func:`offer_step` are the explicit-selection sexual offering judged by
the NPC's arousal ordinal and the injected dice (never affinity), paying the
row's merit plus integer copper in one commit; the ``climax_while_enrolled``
state-reaction row routes merit through :func:`add_merit` — the single
accrual primitive. Redemption (a later change) calls the primitives below.
"""

from collections.abc import Callable, MutableMapping, MutableSequence
from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ChurchHost
from typeclasses.npcs import NPC
from world.lore.church import OFFERING_CATALOG, OfferingRow
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.observability import log_info
from world.rules.clock import CLOCK_YAML, get_world_clock, read_world_clock
from world.rules.dice import roll_d100

#: Seconds per world-clock day — the identical formula
#: ``world/rules/clock.py::_DAY_SECONDS`` derives from ``CLOCK_YAML``.
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


class ChurchLedgerError(ValueError):
    """A church ledger write violates the single-writer invariants."""


class EnrollmentReason(StrEnum):
    """The named stable rejection reasons of the enrollment rite."""

    NOT_A_PLAYER = "not_a_player"
    ALREADY_ENROLLED = "already_enrolled"
    NO_HOST = "no_host"
    REMOTE_HOST = "remote_host"
    SERVICE_UNAVAILABLE = "service_unavailable"
    MALFORMED_LEDGER = "malformed_ledger"


class EnrollmentError(ValueError):
    """A deterministic enrollment rejection with a named reason."""


#: The two clerical vestments of the enrollment handover (design §5.1.5).
#: Module-level names so deterministic code and tests share one spelling.
SISTER_VESTMENTS_KEY = "sister_vestments"
SAINTESS_VESTMENTS_KEY = "saintess_vestments"

#: The clergy qualifier passive granted at enrollment (design §5.1.4).
VESSEL_KEY = "saintess_vessel"


def _clock_day() -> int:
    """Return the current world-clock day index (0 without a clock script)."""
    clock = read_world_clock()
    if clock is None:
        return 0
    return clock.tick // _DAY_SECONDS


def _new_ledger() -> dict[str, Any]:
    """Return a fresh ledger for a character who never touched the church."""
    return {
        "merit": 0,
        "enrolled_tick": 0,
        "redeemed": [],
        "daily": {"day": _clock_day(), "pray": 0},
    }


def _to_plain(value: Any) -> Any:
    """Recursively unwrap Evennia's persistent-mutable wrappers.

    ``db.*`` attribute reads return ``_SaverDict``/``_SaverList`` instances
    (``MutableMapping``/``MutableSequence``, not plain ``dict``/``list``)
    that auto-save on nested mutation. Every read here normalizes the stored
    ledger to plain built-ins so this module — the sole writer — never
    mutates through a saver proxy: the single reassignment inside
    ``transaction.atomic()`` is the only write, which keeps rollback
    byte-exact.
    """
    if isinstance(value, MutableMapping):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, MutableSequence):
        return [_to_plain(item) for item in value]
    return value


def _require_ledger(entity: Any) -> dict[str, Any]:
    """Read the persisted ledger, failing closed on a malformed shape."""
    raw = getattr(entity.db, "church", None)
    if not isinstance(raw, MutableMapping):
        raise ChurchLedgerError("db.church is malformed")
    return _to_plain(raw)


def _write_ledger(entity: Any, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Apply one mutation to the ledger atomically.

    Lazily materializes the ledger when the character has none (the first
    church-rules write) and reassigns the mutated copy onto the attribute
    inside ``transaction.atomic()`` — a mid-mutation failure rolls the whole
    write back.
    """
    with transaction.atomic():
        raw = getattr(entity.db, "church", None)
        if raw is None:
            ledger = _new_ledger()
        else:
            if not isinstance(raw, MutableMapping):
                raise ChurchLedgerError("db.church is malformed")
            ledger = _to_plain(raw)
        mutate(ledger)
        entity.db.church = ledger
        return ledger


def _require_delta(amount: Any) -> int:
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ChurchLedgerError("merit delta must be an integer")
    if amount < 0:
        raise ChurchLedgerError("merit delta must be non-negative")
    return amount


# --------------------------------------------------------------------------- reads


def read_ledger(entity: Any) -> dict[str, Any] | None:
    """Return a copy of the ledger, or ``None`` for a character who never
    touched the church. Reads never create state."""
    raw = getattr(entity.db, "church", None)
    if raw is None:
        return None
    return _require_ledger(entity)


def merit(entity: Any) -> int:
    """Read the cumulative grace counter (0 for the never-enrolled)."""
    ledger = read_ledger(entity)
    return int(ledger["merit"]) if ledger is not None else 0


def enrolled_tick(entity: Any) -> int:
    """Read the enrollment tick (0 for the never-enrolled)."""
    ledger = read_ledger(entity)
    return int(ledger["enrolled_tick"]) if ledger is not None else 0


def redeemed_keys(entity: Any) -> tuple[str, ...]:
    """Read the redeemed catalogue keys (empty for the never-enrolled)."""
    ledger = read_ledger(entity)
    if ledger is None:
        return ()
    redeemed = ledger.get("redeemed")
    if not isinstance(redeemed, list) or not all(
        isinstance(key, str) for key in redeemed
    ):
        raise ChurchLedgerError("db.church redeemed is malformed")
    return tuple(redeemed)


def daily(entity: Any) -> dict[str, int] | None:
    """Read the ``{"day": int, "pray": int}`` daily counters or ``None``."""
    ledger = read_ledger(entity)
    if ledger is None:
        return None
    daily_block = ledger.get("daily")
    if not isinstance(daily_block, dict):
        raise ChurchLedgerError("db.church daily is malformed")
    return dict(daily_block)


# --------------------------------------------------------------------------- writes


def add_merit(entity: Any, amount: int) -> int:
    """Add rulebook-accrued merit. The only legal path by which accrual rows
    (pray, offering, climax-while-enrolled) increase the ledger."""
    delta = _require_delta(amount)

    def _mutate(entry: dict[str, Any]) -> None:
        entry["merit"] = int(entry["merit"]) + delta

    ledger = _write_ledger(entity, _mutate)
    return int(ledger["merit"])


def subtract_merit(entity: Any, amount: int) -> int:
    """Subtract redemption-spent merit. The only legal path by which the
    redemption catalogue decreases the ledger; refusing to go negative keeps
    insufficient-merit a caller-visible error, never a silent clamp."""
    delta = _require_delta(amount)

    def _mutate(entry: dict[str, Any]) -> None:
        remaining = int(entry["merit"]) - delta
        if remaining < 0:
            raise ChurchLedgerError("insufficient merit for redemption")
        entry["merit"] = remaining

    ledger = _write_ledger(entity, _mutate)
    return int(ledger["merit"])


def record_redemption(entity: Any, key: str) -> tuple[str, ...]:
    """Append one one-shot redemption key; a repeat redemption is rejected."""
    if not isinstance(key, str) or not key:
        raise ChurchLedgerError("redemption key must be a non-empty string")

    def _mutate(entry: dict[str, Any]) -> None:
        redeemed = entry["redeemed"]
        if not isinstance(redeemed, list) or not all(
            isinstance(existing, str) for existing in redeemed
        ):
            raise ChurchLedgerError("db.church redeemed is malformed")
        if key in redeemed:
            raise ChurchLedgerError(f"key {key!r} is already redeemed")
        redeemed.append(key)

    ledger = _write_ledger(entity, _mutate)
    return tuple(ledger["redeemed"])


def ensure_daily_reset(entity: Any) -> None:
    """Reset the daily counters when the world-clock day has changed.

    Mirrors the ``climax_today`` reset pattern: the counters record the day
    they belong to and lazily zero themselves on the first read-side write
    after a day boundary. Never materializes a ledger for a character who
    has none.
    """
    led = read_ledger(entity)
    if led is None:
        return
    today = _clock_day()

    def _mutate(entry: dict[str, Any]) -> None:
        daily_block = entry["daily"]
        if not isinstance(daily_block, dict):
            raise ChurchLedgerError("db.church daily is malformed")
        if int(daily_block.get("day", -1)) == today:
            return
        daily_block.clear()
        daily_block.update({"day": today, "pray": 0})

    _write_ledger(entity, _mutate)


def build_initial_arousal_baseline(level: str) -> dict[str, Any]:
    """Return the authored initial-arousal sexual baseline for a clergy host.

    The roster sync's creation/convergence path (guild_economy) applies this
    baseline to a clergy host's spawn data: a raised initial arousal is
    authored content (design §5.3), stored as ``db.sexual`` the same way the
    import loader writes a record's ``sexual_baseline``. The level must be a
    member of the canonical arousal vocabulary.
    """
    if level not in AROUSAL_LEVELS:
        raise ChurchLedgerError(
            f"initial_arousal {level!r} is outside {AROUSAL_LEVELS}"
        )
    return {"arousal": level, "virgin": True, "sensitivity": {}}


# --------------------------------------------------------------------------- enrollment


def _require_enrollable_host(actor: Any, host: Any) -> None:
    """Validate the host the caller resolved, failing closed with a reason."""
    if not isinstance(host, NPC):
        raise EnrollmentError(EnrollmentReason.NO_HOST)
    if not hasattr(host, "components") or not host.components.has(ChurchHost.name):
        raise EnrollmentError(EnrollmentReason.NO_HOST)
    church_host = host.components.get(ChurchHost.get_component_slot())
    from world.rules.service_gate import (
        REASON_MALFORMED_BINDING,
        REASON_OFF_ANCHOR,
        REASON_REMOTE,
        service_available,
    )

    verdict = service_available(actor, host, church_host)
    if verdict.allowed:
        return
    if verdict.reason == REASON_REMOTE:
        raise EnrollmentError(EnrollmentReason.REMOTE_HOST)
    if verdict.reason in (REASON_OFF_ANCHOR, REASON_MALFORMED_BINDING):
        raise EnrollmentError(EnrollmentReason.SERVICE_UNAVAILABLE)
    raise EnrollmentError(EnrollmentReason.SERVICE_UNAVAILABLE)


def enroll(actor: Any, host: Any) -> dict[str, Any]:
    """Run the deterministic enrollment rite for one initiate (design §5.1).

    ``host`` is the local ``ChurchHost`` the command resolved and schedule-
    gated; this API re-validates it (an NPC carrying the component, co-located
    per its service binding) so every entry point gets the same stable
    rejections. A character who already holds a ledger is refused with
    ``ALREADY_ENROLLED`` (「你已屬光明教會」 on the command surface) and
    nothing is written.

    One ``transaction.atomic()`` covers every write: the ledger materializes
    with ``enrolled_tick`` stamped from the world clock; a female
    ``human_royal`` initiate is additionally granted ``saintess_vessel``
    through the canonical granted-passive write path (its Boolean result
    decides the ``saintess_vessel_granted`` event, so an already-owned vessel
    never emits a false grant); and exactly one clerical vestment —
    ``saintess_vestments`` for the vessel branch, ``sister_vestments``
    otherwise — is granted unconditionally through the ``QuestReward``
    item-quantity rail (no holding check: the celebrant's gift is the rite,
    not the inventory). Both observability events ride ``transaction.on_commit``,
    so a rolled-back transaction emits nothing.

    Returns a plain record ``{"vessel_branch", "vessel_granted", "item"}`` for
    the command's authored presentation.
    """
    if not isinstance(actor, PlayerCharacter):
        raise EnrollmentError(EnrollmentReason.NOT_A_PLAYER)
    try:
        existing = read_ledger(actor)
    except ChurchLedgerError as error:
        raise EnrollmentError(EnrollmentReason.MALFORMED_LEDGER) from error
    if existing is not None:
        raise EnrollmentError(EnrollmentReason.ALREADY_ENROLLED)
    _require_enrollable_host(actor, host)

    vessel_branch = (
        getattr(actor, "subrace", None) == "human_royal"
        and getattr(actor, "sex", None) == "female"
    )
    vestment_key = (
        SAINTESS_VESTMENTS_KEY if vessel_branch else SISTER_VESTMENTS_KEY
    )
    host_id = getattr(host, "key", None) or str(getattr(host, "pk", "") or "")
    vessel_granted = False
    from world.rules.surfaces import restore_attributes, snapshot_attributes

    # Evennia's attribute cache is not transaction-aware: a failure after the
    # inventory/skill writes would otherwise leave stale in-memory values
    # behind a committed DB rollback. Snapshot every surface this transaction
    # touches and restore them best-effort on failure — the same discipline
    # ``turn_in_quest`` and ``apply_inventory_plan`` already follow.
    snapshots = snapshot_attributes(actor, ("church", "skills", "inventory"))
    try:
        with transaction.atomic():

            def _mutate(entry: dict[str, Any]) -> None:
                entry["enrolled_tick"] = get_world_clock().tick

            _write_ledger(actor, _mutate)
            if vessel_branch:
                from world.rules.cross_lineage_unlock import grant_owned_skill
                from world.skills.registry import SKILL_REGISTRY

                vessel_granted = grant_owned_skill(
                    actor, VESSEL_KEY, SKILL_REGISTRY
                )
            from world.rules.equipment import (
                apply_inventory_plan,
                plan_inventory_delta,
            )

            apply_inventory_plan(
                plan_inventory_delta(actor, additions=(vestment_key,))
            )
            transaction.on_commit(
                lambda: log_info(
                    "church_enrolled",
                    context={
                        "char": str(actor),
                        "host": host_id,
                        "item": vestment_key,
                    },
                )
            )
            if vessel_granted:
                transaction.on_commit(
                    lambda: log_info(
                        "saintess_vessel_granted",
                        context={
                            "entity": str(actor),
                            "source": "church_enrollment",
                            "host": host_id,
                            "passive": VESSEL_KEY,
                        },
                    )
                )
    except ChurchLedgerError as error:
        raise EnrollmentError(EnrollmentReason.MALFORMED_LEDGER) from error
    except Exception:
        restore_attributes(actor, snapshots)
        raise
    return {
        "vessel_branch": vessel_branch,
        "vessel_granted": vessel_granted,
        "item": vestment_key,
    }


# --------------------------------------------------------------------------- pray


class PrayerReason(StrEnum):
    """The named stable rejection reasons of the prayer rite."""

    NOT_A_PLAYER = "not_a_player"
    NOT_ENROLLED = "not_enrolled"
    OUTSIDE_VENUE = "outside_venue"
    DAILY_CAP = "daily_cap"
    MALFORMED_LEDGER = "malformed_ledger"


class PrayerError(ValueError):
    """A deterministic prayer rejection with a named reason."""


def _in_church_venue(entity: Any) -> bool:
    """Return whether the entity stands in a derived church venue.

    The venue set is the lore package's derived church places (the
    ``shop_key`` pattern); a place joins it iff its authored kwargs carry the
    ``church`` flag. A location's place identity is its tag, so membership is
    a tag intersection — never a second authored list.
    """
    from world.lore.church.places import CHURCH_PLACES

    location = getattr(entity, "location", None)
    if location is None or not hasattr(location, "tags"):
        return False
    try:
        tags = {str(tag) for tag in location.tags.all()}
    except Exception:  # observability: ignore R2: a broken tag read fails the venue check closed (False) — a prayer rejection, not an operational event
        return False
    return bool(tags & set(CHURCH_PLACES))


def pray_step(entity: Any) -> dict[str, Any]:
    """Run one deterministic prayer (design §5.2): time cost + merit.

    Requires an existing ledger (the unenrolled are told to speak with the
    celebrant) and a church-flagged venue; then the daily cap, the world-clock
    advance by the rulebook duration (the prayer IS the time cost, through the
    existing non-combat clock source), the ``pray_completed`` accrual, and the
    commit. No rolls, no RNG — every rejection is inert.

    The outer transaction covers the clock advance and the ledger write
    together; the clock tick and every advance-touched surface are snapshotted
    before the transaction opens and restored on any failure, so a rolled-back
    prayer is byte-identical (the cast-settlement discipline). The
    ``church_pray`` event rides ``transaction.on_commit``.
    """
    if not isinstance(entity, PlayerCharacter):
        raise PrayerError(PrayerReason.NOT_A_PLAYER)
    try:
        ledger = read_ledger(entity)
    except ChurchLedgerError as error:
        raise PrayerError(PrayerReason.MALFORMED_LEDGER) from error
    if ledger is None:
        raise PrayerError(PrayerReason.NOT_ENROLLED)
    if not _in_church_venue(entity):
        raise PrayerError(PrayerReason.OUTSIDE_VENUE)

    from world.rules.church_rulebook import get_church_rules

    rules = get_church_rules().pray
    # The prayer's merit is the accrual row's value (design §5.2 "accrual row
    # adds merit"); the ``pray`` section owns the duration and the daily cap.
    accrual = get_church_rules().accrual["accrual_pray_completed"]
    if "merit" not in accrual:
        raise PrayerError(PrayerReason.MALFORMED_LEDGER)
    clock = get_world_clock()
    today = clock.tick // _DAY_SECONDS
    daily_block = ledger["daily"]
    if (
        int(daily_block.get("day", -1)) == today
        and int(daily_block.get("pray", 0)) >= rules.daily_cap
    ):
        raise PrayerError(PrayerReason.DAILY_CAP)

    from world.rules.clock import (
        AdvanceSource,
        _restore_advance_registry,
        _restore_clock_tick,
        _snapshot_clock_tick,
        build_advance_snapshot_registry,
    )

    registry = build_advance_snapshot_registry(
        clock, rules.duration_seconds, AdvanceSource.COMMAND, (entity,)
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

    church_snapshot = attribute_snapshot(entity, "church")
    try:
        with transaction.atomic():
            clock.advance(rules.duration_seconds, AdvanceSource.COMMAND, (entity,))

            def _mutate(entry: dict[str, Any]) -> None:
                entry["merit"] = int(entry["merit"]) + int(accrual["merit"])
                daily = entry["daily"]
                if not isinstance(daily, dict):
                    raise ChurchLedgerError("db.church daily is malformed")
                if int(daily.get("day", -1)) != today:
                    daily.clear()
                    daily.update({"day": today, "pray": 0})
                daily["pray"] = int(daily.get("pray", 0)) + 1

            written = _write_ledger(entity, _mutate)
            char_key = str(entity)
            tick_after = clock.tick
            transaction.on_commit(
                lambda: log_info(
                    "church_pray",
                    context={"char": char_key, "tick": tick_after},
                )
            )
    except Exception:
        _restore_clock_tick(clock, tick_snapshot)
        _restore_advance_registry(registry, (entity,))
        restore_attribute_best_effort(entity, "church", church_snapshot)
        raise
    return {"outcome": "prayed", "merit": int(written["merit"]), "tick": clock.tick}


# --------------------------------------------------------------------------- offering


class OfferingReason(StrEnum):
    """The named stable rejection reasons of the sexual offering."""

    NOT_A_PLAYER = "not_a_player"
    NOT_ENROLLED = "not_enrolled"
    ROW_NOT_UNLOCKED = "row_not_unlocked"
    NPC_DECLINED = "npc_declined"
    MALFORMED_LEDGER = "malformed_ledger"
    ACT_REJECTED = "act_rejected"


class OfferingError(ValueError):
    """A deterministic offering rejection with a named reason."""


def _require_offerer(entity: Any) -> None:
    """The offering gate: a player with an existing ledger (enrollment only —
    ministry travels with the sister, never venue-bound)."""
    if not isinstance(entity, PlayerCharacter):
        raise OfferingError(OfferingReason.NOT_A_PLAYER)
    try:
        ledger = read_ledger(entity)
    except ChurchLedgerError as error:
        raise OfferingError(OfferingReason.MALFORMED_LEDGER) from error
    if ledger is None:
        raise OfferingError(OfferingReason.NOT_ENROLLED)


def offering_menu(entity: Any) -> tuple[OfferingRow, ...]:
    """Return the selectable offering rows: exactly the ``OFFERING_CATALOG``
    rows whose ``act_key`` the caller currently owns through the existing
    counter-gated unlock projection (no new unlock system — the menu is a
    projection, never a copy)."""
    _require_offerer(entity)
    owned = set(entity.skills.owned_keys())
    return tuple(
        row for row in OFFERING_CATALOG if row.act_key in owned
    )


def _offering_copper(row: OfferingRow) -> int:
    """Resolve one offering row's integer copper payout.

    Precedence: the row's own ``copper`` override (``OfferingRow.copper`` —
    ``None`` defers), then the rulebook's per-row override map, then a
    deterministic function of one injected ``roll_d100`` inside the
    configured band (integer copper, both band edges reachable). The tuning
    numbers ride the catalogue rows and the rulebook slice, never a code-side
    constant.
    """
    from world.rules.church_rulebook import get_church_rules

    if row.copper is not None:
        return int(row.copper)
    config = get_church_rules().offering
    override = config.overrides.get(row.key)
    if override is not None:
        return int(override["copper"])
    lo, hi = config.copper_lo, config.copper_hi
    if hi <= lo:
        return lo
    roll = roll_d100()
    return lo + ((roll - 1) * (hi - lo)) // 99


def _snapshot_offering_state(
    entities: tuple[Any, ...],
) -> dict[int, tuple[Any, dict[str, Any]]]:
    """Snapshot the action-touched surfaces of every participant, merged by
    object identity — the same surface set the cast settlement restores, so a
    rolled-back offering leaves both bodies byte-identical."""
    from world.rules.cast_settlement import _ENTITY_SURFACES
    from world.rules.surfaces import attribute_snapshot
    from world.quests.transitions import snapshot_quest_log

    snapshots: dict[int, tuple[Any, dict[str, Any]]] = {}
    for entity in entities:
        attributes: dict[Any, tuple[bool, Any]] = {
            (key, category): attribute_snapshot(entity, key, category)
            for key, category in _ENTITY_SURFACES
        }
        # The offering transaction itself writes the church ledger and the
        # copper wallet; neither rides the action-surface list, so they are
        # snapshotted explicitly here.
        attributes[("church", None)] = attribute_snapshot(entity, "church")
        attributes[("wallet", None)] = attribute_snapshot(entity, "wallet")
        attributes[("quest_log", None)] = snapshot_quest_log(entity)
        snapshots[id(entity)] = (entity, attributes)
    return snapshots


def _stored_arousal_ordinal(entity: Any) -> int:
    """Read an entity's arousal ordinal without creating any state.

    The offering consent read must stay write-free: ``entity.sexual`` is a
    lazy property whose first access persists the materialized traits, which
    would break the decline's zero-write promise and the accepted offer's
    all-or-nothing rollback. The no-create pattern (combat-modifier condition
    contexts) derives the ordinal from the stored pleasure counter; a
    never-materialized entity falls back to its authored ``db.sexual``
    baseline label, then to the generic floor (ordinal 0).
    """
    from world.rules.combat_modifiers import _stored_sexual_level

    stored = _stored_sexual_level(entity, "arousal")
    if stored is not None:
        return int(stored.value)
    db = getattr(entity, "db", None)
    baseline = getattr(db, "sexual", None) if db is not None else None
    if isinstance(baseline, dict) and isinstance(baseline.get("arousal"), str):
        try:
            from world.rules.sexual_state.pleasure import PLEASURE_CONFIG

            return PLEASURE_CONFIG.ordinal_for(
                PLEASURE_CONFIG.floor_for_level(baseline["arousal"])
            )
        except Exception:  # observability: ignore R2: a malformed authored baseline fails the consent read closed (ordinal 0)
            return 0
    return 0


def _restore_offering_surfaces(
    snapshots: dict[int, tuple[Any, dict[str, Any]]],
) -> None:
    """Restore every snapshotted surface and refresh the entity caches."""
    from world.rules.clock import _refresh_advance_entity_caches, _restore_registry_attribute
    from world.quests.transitions import restore_quest_log

    for entity, attributes in snapshots.values():
        for (key, category), snapshot in attributes.items():
            if key == "quest_log":
                restore_quest_log(entity, snapshot)
            else:
                _restore_registry_attribute(
                    entity,
                    key,
                    category,
                    snapshot,
                    stage="church_offering_rollback",
                )
        _refresh_advance_entity_caches(entity)


def offer_step(entity: Any, npc: Any, row_key: str) -> dict[str, Any]:
    """Propose one offering row to an NPC (design §5.3).

    Gates on enrollment only; the row must be one the caller owns. Acceptance
    reads the NPC's arousal ordinal, maps it through the monotonic
    ``acceptance`` curve, and resolves via one injected ``roll_d100`` —
    affinity plays no role anywhere in the decision. On accept, the act runs
    through the existing action-resolution pipeline (all pleasure/shame/
    exposure/counter rails execute normally on both bodies) and the same
    transaction adds the row's merit and its copper payout, emitting
    ``church_offering_accepted``. On decline, ``church_offering_declined``
    with zero writes — no penalty, no cooldown, instantly re-proposable.
    """
    _require_offerer(entity)
    if not isinstance(row_key, str) or not row_key:
        raise OfferingError(OfferingReason.ROW_NOT_UNLOCKED)
    row = next(
        (candidate for candidate in OFFERING_CATALOG if candidate.key == row_key),
        None,
    )
    if row is None or row.act_key not in set(entity.skills.owned_keys()):
        raise OfferingError(OfferingReason.ROW_NOT_UNLOCKED)

    from world.rules.church_rulebook import get_church_rules

    ordinal = _stored_arousal_ordinal(npc)
    accept_percent = get_church_rules().acceptance[ordinal][1]
    roll = roll_d100()
    if roll > accept_percent:
        char_key = str(entity)
        npc_key = str(npc)
        row_key_value = row.key
        with transaction.atomic():
            transaction.on_commit(
                lambda: log_info(
                    "church_offering_declined",
                    context={
                        "char": char_key,
                        "npc": npc_key,
                        "row": row_key_value,
                    },
                )
            )
        return {
            "outcome": "declined",
            "row": row.key,
            "roll": roll,
            "accept_percent": accept_percent,
        }

    from world.rules.action import ActionRequest, ActionResolver
    from world.rules.targeting import RoomActionContext
    from world.rules.progression import (
        restore_practice_dedupe,
        snapshot_practice_dedupe,
    )
    from world.skills.registry import SKILL_REGISTRY, TargetSpec

    skill = SKILL_REGISTRY.get(row.act_key)
    if skill is None:
        raise OfferingError(OfferingReason.ROW_NOT_UNLOCKED)
    targets: list[Any] = (
        [] if skill.target_spec is TargetSpec.SELF else [npc]
    )
    request = ActionRequest(
        actor=entity,
        skill_key=row.act_key,
        targets=targets,
        context=RoomActionContext(getattr(entity, "location", None)),
    )
    snapshots = _snapshot_offering_state((entity, npc))
    dedupe_before = snapshot_practice_dedupe()
    try:
        with transaction.atomic():
            result = ActionResolver.resolve(request)
            if result.outcome != "success":
                raise OfferingError(
                    OfferingReason.ACT_REJECTED, str(result.reason)
                )
            copper = _offering_copper(row)

            def _mutate(entry: dict[str, Any]) -> None:
                entry["merit"] = int(entry["merit"]) + row.merit

            _write_ledger(entity, _mutate)
            setattr(
                entity.db,
                "wallet",
                int(getattr(entity.db, "wallet", None) or 0) + copper,
            )
            char_key = str(entity)
            npc_key = str(npc)
            row_key_value = row.key
            transaction.on_commit(
                lambda: log_info(
                    "church_offering_accepted",
                    context={
                        "char": char_key,
                        "npc": npc_key,
                        "row": row_key_value,
                    },
                )
            )
    except Exception:
        _restore_offering_surfaces(snapshots)
        restore_practice_dedupe(dedupe_before)
        raise
    return {
        "outcome": "accepted",
        "row": row.key,
        "roll": roll,
        "accept_percent": accept_percent,
        "merit": row.merit,
        "copper": copper,
    }