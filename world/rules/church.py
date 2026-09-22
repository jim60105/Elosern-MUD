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
enters a wallet path: the wallet modules read ``db.wallet`` only, and this
module never touches it (the merit-isolation test proves both directions).

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
pray/offering accrual and redemption (each a later change) call the
primitives below; the accrual and redemption module names in their docstrings
are the sanctioned write paths, not imports.
"""

from collections.abc import Callable, MutableMapping, MutableSequence
from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ChurchHost
from typeclasses.npcs import NPC
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.observability import log_info
from world.rules.clock import CLOCK_YAML, get_world_clock, read_world_clock

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