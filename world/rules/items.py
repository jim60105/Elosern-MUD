"""Deterministic item-use resolution (add-inventory-item-actions D1/D2/D9).

Item mechanics identity lives in the immutable lore registry; effect
magnitudes and the canonical out-of-combat item-use time cost live in the
validated ``rulebook/item_effects.yaml`` rulebook. This module is the sole
writer of item-use state: a side-effect-free ``preflight_item_use()`` shared
by presentation and settlement, one atomic plan application, and the public
out-of-combat facade that composes the item plan with the canonical
command-source clock advance inside one outer transaction and rollback
journal (mirroring ``cast_settlement``).

The rules engine never trusts a presented descriptor: every mutating entry
repeats preflight against current canonical state and commits trait,
inventory, quest-progress, and contained-mirror writes atomically. On any
rejection or settlement failure all durable rows and every in-process cache
the plan touched (traits, attributes, idmapper, contents) are restored.

A successful use emits exactly one ``item_used`` EventLog entry whose data
contains exactly ``item_key``, ``effect_key``, ``consumable``, and ``amount``
(the actual bounded restoration, never the configured maximum).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml

from django.db import transaction
from evennia.utils.logger import log_warn

from world.lore.items import ITEM_REGISTRY, ItemEffectKey
from world.quests.transitions import restore_quest_log, snapshot_quest_log
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    active_buff_keys_from_storage,
    cleanse_debuffs,
)
from world.rules.clock import (
    MAX_ADVANCE_SECONDS,
    AdvanceSource,
    ScheduledEvent,
    WorldClock,
    _flush_deleted_instance,
    _refresh_advance_entity_caches,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
)
from world.rules.equipment import (
    apply_inventory_plan,
    plan_inventory_delta,
    registry_key_for_object,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)

_RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "item_effects.yaml"

# One item effect may restore at most this many hit points; the loader
# rejects larger magnitudes so a malformed rulebook can never smuggle an
# unbounded heal into settlement.
MAX_EFFECT_AMOUNT = 9999

_ITEM_EFFECT_YAML = yaml.safe_load(_RULEBOOK_PATH.read_text(encoding="utf-8"))


class ItemEffectsRulebookError(ValueError):
    """The item-effect rulebook is malformed, unknown, or out of bounds."""


class ItemUseError(ValueError):
    """An item-use settlement failed mid-application and was rolled back."""


class ItemUseReason(StrEnum):
    """Stable named rejection reasons for item-use preflight and settlement."""

    UNKNOWN_ITEM = "unknown_item"
    NOT_USABLE = "not_usable"
    ITEM_NOT_HELD = "item_not_held"
    HP_FULL = "hp_full"
    MP_FULL = "mp_full"
    NOT_ALIVE = "not_alive"
    NO_DEBUFFS = "no_debuffs"
    COMBAT_NOT_ALLOWED = "combat_not_allowed"
    UNKNOWN_EFFECT = "unknown_effect"
    ACTIVE_SESSION = "active_combat"
    MALFORMED_TRAITS = "malformed_traits"
    MALFORMED_INVENTORY = "malformed_inventory"


@dataclass(frozen=True)
class ItemEffectRule:
    """One validated deterministic effect with a key and an optional amount.

    ``amount`` is ``None`` for cleanse-family effects (their rulebook entries
    carry no amount field by design); every gauge-restoring effect keeps a
    positive bounded amount.
    """

    effect_key: ItemEffectKey
    amount: int | None


def _require_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ItemEffectsRulebookError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ItemEffectsRulebookError(
            f"{field} must be between {minimum} and {maximum}"
        )
    return value


def load_item_effect_rules(path: Path | None = None) -> dict[str, Any]:
    """Validate the item-effect rulebook against the closed lore vocabulary.

    Returns ``(item_use_seconds, rules)``: every ``ItemEffectKey`` member is
    covered exactly once — gauge-restoring keys with one positively bounded
    amount, cleanse-family keys with an empty entry — and the rulebook
    declares no key the registry vocabulary does not know.
    """
    raw = yaml.safe_load(
        (path or _RULEBOOK_PATH).read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping) or set(raw) != {"item_use_seconds", "effects"}:
        raise ItemEffectsRulebookError(
            "rulebook must declare exactly item_use_seconds and effects"
        )
    seconds = _require_int(
        raw["item_use_seconds"],
        "item_use_seconds",
        minimum=1,
        maximum=MAX_ADVANCE_SECONDS,
    )
    effects = raw["effects"]
    if not isinstance(effects, Mapping):
        raise ItemEffectsRulebookError("effects must be a mapping")
    unknown = set(effects) - {key.value for key in ItemEffectKey}
    if unknown:
        raise ItemEffectsRulebookError(
            f"effects declare unknown keys {sorted(unknown)}"
        )
    missing = {key.value for key in ItemEffectKey} - set(effects)
    if missing:
        raise ItemEffectsRulebookError(
            f"effects missing registered keys {sorted(missing)}"
        )
    rules: dict[str, ItemEffectRule] = {}
    for effect_key_value, entry in effects.items():
        field = f"effects.{effect_key_value}"
        if ItemEffectKey(effect_key_value) is ItemEffectKey.BLESSED_CLEANSE:
            # Cleanse entries carry NO amount: the loader forbids the field
            # so a malformed rulebook can never smuggle an unbounded number
            # into settlement (P3 design D3).
            if not isinstance(entry, Mapping) or len(entry) != 0:
                raise ItemEffectsRulebookError(
                    f"{field} must be an empty mapping (cleanse entries "
                    "carry no amount)"
                )
            amount = None
        else:
            if not isinstance(entry, Mapping) or set(entry) != {"amount"}:
                raise ItemEffectsRulebookError(f"{field} must carry exactly amount")
            amount = _require_int(
                entry["amount"], f"{field}.amount", minimum=1, maximum=MAX_EFFECT_AMOUNT
            )
        rules[effect_key_value] = ItemEffectRule(
            effect_key=ItemEffectKey(effect_key_value), amount=amount
        )
    return {"item_use_seconds": seconds, "rules": rules}


_loaded = load_item_effect_rules()

# The canonical out-of-combat item-use time cost, settled through the same
# command-source advance path as casts.
ITEM_USE_SECONDS: int = _loaded["item_use_seconds"]

# Immutable effect rulebook keyed by the closed lore effect vocabulary.
ITEM_EFFECT_RULES: dict[ItemEffectKey, ItemEffectRule] = _loaded["rules"]
# Which gauge each effect restores (cleanse-family effects own no gauge and
# never appear here). Preflight full-gating, the settlement write, and the
# stable log noun all resolve through this map.
_EFFECT_GAUGES: dict[ItemEffectKey, str] = {
    ItemEffectKey.SELF_HEAL: "hp",
    ItemEffectKey.GREATER_HEAL: "hp",
    ItemEffectKey.MANA_RESTORE: "mp",
}
_FULL_REASON_BY_GAUGE: dict[str, ItemUseReason] = {
    "hp": ItemUseReason.HP_FULL,
    "mp": ItemUseReason.MP_FULL,
}
_GAUGE_NOUN_ZH: dict[str, str] = {"hp": "生命值", "mp": "魔力值"}


def reload_item_effect_rules(path: Path | None = None) -> None:
    """Re-validate and re-mirror the rulebook (idempotent startup sync)."""
    global ITEM_USE_SECONDS, ITEM_EFFECT_RULES
    loaded = load_item_effect_rules(path)
    ITEM_USE_SECONDS = loaded["item_use_seconds"]
    ITEM_EFFECT_RULES = loaded["rules"]


@dataclass(frozen=True)
class ItemUseRequest:
    """The closed deterministic request to use one held item."""

    actor: Any
    item_key: str


@dataclass(frozen=True)
class ItemUsePlan:
    """The complete, immutable settlement computed by a side-effect-free preflight.

    ``amount`` is the actual bounded restoration for the current state on the
    effect's gauge and ``mirror_pk`` is the single existing contained-object
    mirror selected for consumption (``None`` for a key-only holding), never a
    fabricated object. Cleanse-family effects carry ``gauge=None`` with
    ``cleansed_count`` set to the preflight-verified active debuff count.
    """

    actor: Any
    item_key: str
    effect_key: ItemEffectKey
    gauge: str | None
    consumable: bool
    amount: int
    gauge_current: int
    gauge_restored: int
    mirror_pk: int | None
    cleansed_count: int = 0


@dataclass(frozen=True)
class ItemUsePreflight:
    """The outcome of one side-effect-free eligibility check."""

    allowed: bool
    reason: ItemUseReason | None = None
    plan: ItemUsePlan | None = None


@dataclass
class ItemTouchedJournal:
    """Pre-write snapshots of every surface an item-use settlement may touch.

    The resolver captures this before any write and hands it to the caller on
    success, so an outer combat transaction whose later phase fails can
    restore the trait, inventory, quest-progress, buff, and mirror/contents/
    idmapper caches the resolver committed. Restoration is best-effort per
    surface with a logged diagnostic and is safe to run twice (idempotent
    value writes). The buff surface restores through the attribute handler,
    which Evennia's ``BuffHandler`` re-reads on every access, so live handler
    reads recover together with persistence.
    """

    actor: Any
    traits: tuple[bool, Any] | None = None
    inventory: tuple[bool, Any] | None = None
    quest_log: tuple[bool, Any] | None = None
    buffs: tuple[bool, Any] | None = None
    mirror: Any | None = None
    mirror_pk: int | None = None

    @classmethod
    def capture(cls, actor: Any) -> "ItemTouchedJournal":
        """Snapshot traits, inventory, quest progress, and buffs pre-write."""
        return cls(
            actor=actor,
            traits=snapshot_traits(actor),
            inventory=attribute_snapshot(actor, "inventory"),
            quest_log=snapshot_quest_log(actor),
            buffs=attribute_snapshot(actor, "buffs"),
        )

    def note_mirror(self, mirror: Any) -> None:
        """Record the live mirror instance before its deletion."""
        self.mirror = mirror
        self.mirror_pk = mirror.id

    def restore(self) -> None:
        """Restore every snapshotted surface after a rolled-back settlement."""
        actor = self.actor
        if self.traits is not None:
            restore_traits(actor, self.traits)
        if self.inventory is not None:
            restore_attribute_best_effort(actor, "inventory", self.inventory)
        if self.quest_log is not None:
            restore_quest_log(actor, self.quest_log)
        if self.buffs is not None:
            restore_attribute_best_effort(actor, "buffs", self.buffs)
        if self.mirror is not None:
            try:
                _flush_deleted_instance(self.mirror)
            except Exception as error:
                log_warn(
                    f"item journal could not flush mirror {self.mirror_pk}: {error}"
                )
        try:
            contents_cache = getattr(actor, "contents_cache", None)
            if contents_cache is not None:
                contents_cache.init()
        except Exception as error:
            log_warn(f"item journal could not reset contents cache: {error}")
        try:
            _refresh_advance_entity_caches(actor)
        except Exception as error:
            log_warn(f"item journal could not refresh entity caches: {error}")


@dataclass(frozen=True)
class ItemUseResult:
    """The result of one item-use resolution, shaped for round settlement."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None = None
    time_cost_seconds: int = 0
    reason: ItemUseReason | None = None
    detail: str | None = None
    journal: ItemTouchedJournal | None = None


@dataclass(frozen=True)
class ItemUseSettlement:
    """The committed out-of-combat item use and its clock events."""

    result: ItemUseResult
    events: tuple[ScheduledEvent, ...] = ()


def _gauge_from_storage(entity: Any, key: str) -> tuple[int, int] | None:
    """Read one gauge's ``(current, maximum)`` without materializing a handler.

    Mirrors the strict no-create parser in ``world.rules.status_query``; a
    missing or malformed record returns ``None`` so callers fail closed.
    """
    traits = entity.attributes.get("traits", default=None, category="traits")
    if not isinstance(traits, Mapping):
        return None
    raw = traits.get(key)
    if not isinstance(raw, Mapping):
        return None
    base = raw.get("base")
    mod = raw.get("mod", 0)
    mult = raw.get("mult", 1)
    if isinstance(base, bool) or not isinstance(base, int):
        return None
    if isinstance(mod, bool) or not isinstance(mod, (int, float)):
        return None
    if isinstance(mult, bool) or not isinstance(mult, (int, float)):
        return None
    maximum = int(round((base + mod) * mult))
    if maximum <= 0:
        return None
    current = raw.get("current")
    if current is None:
        current = maximum
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    if current < 0 or current > maximum:
        return None
    return current, maximum


def _inventory_list(entity: Any) -> list[str] | None:
    """Return a copy of the canonical key list, or ``None`` when malformed.

    Accepts Evennia's ``_SaverList`` storage (a Sequence, not a ``list``
    subclass); a bare string, mapping, or non-string entry fails closed.
    """
    raw = entity.db.inventory
    if raw is None:
        return []
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        return None
    if not all(isinstance(item, str) for item in raw):
        return None
    return list(raw)


def _select_mirror(entity: Any, item_key: str) -> Any | None:
    """Select at most one existing contained mirror in deterministic order.

    Matching contained objects are ordered by primary key (unsaved objects,
    which cannot legitimately occur, sort last) so every preflight of the same
    state names the same mirror.
    """
    contents = getattr(entity, "contents", None)
    if contents is None:
        return None
    matches = [obj for obj in contents if registry_key_for_object(obj) == item_key]
    if not matches:
        return None
    matches.sort(key=lambda obj: (obj.id is None, obj.id or 0))
    return matches[0]


def _rejected(reason: ItemUseReason) -> ItemUsePreflight:
    return ItemUsePreflight(allowed=False, reason=reason, plan=None)

def _active_debuff_keys(entity: Any) -> tuple[str, ...]:
    """Handler-free read of the active debuff-polarity definition keys.

    Uses the storage accessor exactly like every presentation surface, so a
    conditional read never materializes the buff handler. Raises ``TypeError``
    on malformed buff storage for the caller to fail closed.
    """
    return tuple(
        sorted(
            key
            for key in active_buff_keys_from_storage(entity)
            if BUFF_DEFINITIONS.get(key) is not None
            and BUFF_DEFINITIONS[key].polarity == "debuff"
        )
    )


def preflight_item_use(
    request: ItemUseRequest, *, in_combat: bool
) -> ItemUsePreflight:
    """Evaluate item-use eligibility against current state, writing nothing.

    Resolves the canonical registry definition, verifies at least one held
    key in the canonical inventory, validates the effect binding and the
    current mode against the definition, evaluates the effect condition
    (self-heal requires HP above zero and below maximum), and names at most
    one existing contained-object mirror. It never mutates inventory, traits,
    quest state, equipment, combat state, clock, or presentation.
    """
    definition = ITEM_REGISTRY.get(request.item_key)
    if definition is None:
        return _rejected(ItemUseReason.UNKNOWN_ITEM)
    mechanics = definition.use_mechanics
    if mechanics is None:
        return _rejected(ItemUseReason.NOT_USABLE)
    if in_combat and not mechanics.combat_allowed:
        return _rejected(ItemUseReason.COMBAT_NOT_ALLOWED)
    inventory = _inventory_list(request.actor)
    if inventory is None:
        return _rejected(ItemUseReason.MALFORMED_INVENTORY)
    if request.item_key not in inventory:
        return _rejected(ItemUseReason.ITEM_NOT_HELD)
    rule = ITEM_EFFECT_RULES.get(mechanics.effect_key)
    if rule is None:
        return _rejected(ItemUseReason.UNKNOWN_EFFECT)
    gauge = _EFFECT_GAUGES.get(mechanics.effect_key)
    if gauge is None and mechanics.effect_key is not ItemEffectKey.BLESSED_CLEANSE:
        return _rejected(ItemUseReason.UNKNOWN_EFFECT)
    hp_gauge = _gauge_from_storage(request.actor, "hp")
    if hp_gauge is None:
        return _rejected(ItemUseReason.MALFORMED_TRAITS)
    if hp_gauge[0] <= 0:
        return _rejected(ItemUseReason.NOT_ALIVE)
    if mechanics.effect_key is ItemEffectKey.BLESSED_CLEANSE:
        # Cleanse preflight (P3 D3): at least one active debuff-polarity buff
        # must exist, read without materializing the handler. A clean actor
        # rejects with ``no_debuffs`` (mirroring ``hp_full``): nothing is
        # consumed, no event is logged, and no world clock advances.
        try:
            debuffs = _active_debuff_keys(request.actor)
        except TypeError:
            return _rejected(ItemUseReason.MALFORMED_TRAITS)
        if not debuffs:
            return _rejected(ItemUseReason.NO_DEBUFFS)
        mirror = (
            _select_mirror(request.actor, request.item_key)
            if mechanics.consumable
            else None
        )
        plan = ItemUsePlan(
            actor=request.actor,
            item_key=request.item_key,
            effect_key=mechanics.effect_key,
            gauge=None,
            consumable=mechanics.consumable,
            amount=0,
            gauge_current=hp_gauge[0],
            gauge_restored=hp_gauge[0],
            mirror_pk=mirror.id if mirror is not None else None,
            cleansed_count=len(debuffs),
        )
        return ItemUsePreflight(allowed=True, reason=None, plan=plan)
    target = hp_gauge if gauge == "hp" else _gauge_from_storage(request.actor, gauge)
    if target is None:
        return _rejected(ItemUseReason.MALFORMED_TRAITS)
    current, maximum = target
    if current >= maximum:
        return _rejected(_FULL_REASON_BY_GAUGE[gauge])
    amount = min(rule.amount, maximum - current)
    mirror = _select_mirror(request.actor, request.item_key) if mechanics.consumable else None
    plan = ItemUsePlan(
        actor=request.actor,
        item_key=request.item_key,
        effect_key=mechanics.effect_key,
        gauge=gauge,
        consumable=mechanics.consumable,
        amount=amount,
        gauge_current=current,
        gauge_restored=current + amount,
        mirror_pk=mirror.id if mirror is not None else None,
    )
    return ItemUsePreflight(allowed=True, reason=None, plan=plan)


def _item_used_event_log(
    plan: ItemUsePlan,
    actor_key: str,
    time_cost_seconds: int,
    *,
    cleansed_count: int = 0,
) -> EventLog:
    """Build the single stable ``item_used`` log for one successful use.

    The cleanse branch reports the actually-removed debuff count (settlement
    truth, not the preflight estimate); gauge-restoring effects report the
    bounded amount as today. ``plan.gauge`` is never indexed for a cleanse
    effect.
    """
    definition = ITEM_REGISTRY[plan.item_key]
    display_name = definition.display_name_zh.replace("{", "{{").replace("}", "}}")
    if plan.effect_key is ItemEffectKey.BLESSED_CLEANSE:
        entry = EventEntry(
            kind="item_used",
            actor=actor_key,
            target=actor_key,
            data={
                "item_key": plan.item_key,
                "effect_key": plan.effect_key.value,
                "consumable": plan.consumable,
                "count": cleansed_count,
            },
            text_template=(
                f"你使用了「{display_name}」，淨化了 {cleansed_count} 個負面狀態。"
            ),
        )
    else:
        amount = str(plan.amount).replace("{", "{{").replace("}", "}}")
        noun = _GAUGE_NOUN_ZH[plan.gauge]
        entry = EventEntry(
            kind="item_used",
            actor=actor_key,
            target=actor_key,
            data={
                "item_key": plan.item_key,
                "effect_key": plan.effect_key.value,
                "consumable": plan.consumable,
                "amount": plan.amount,
            },
            text_template=(
                f"你使用了「{display_name}」，恢復了 {amount} 點{noun}。"
            ),
        )
    return EventLog(
        actor=actor_key,
        skill_key=plan.item_key,
        targets=(actor_key,),
        entries=(entry,),
        time_cost_seconds=time_cost_seconds,
    )


def _write_gauge(entity: Any, gauge: str, value: int) -> None:
    """Set one gauge through the trait handler (deterministic clamping)."""
    trait = getattr(entity.traits, gauge)
    if hasattr(trait, "current"):
        trait.current = value
    else:
        trait.value = value


def _delete_mirror(actor: Any, plan: ItemUsePlan, journal: ItemTouchedJournal) -> None:
    """Delete exactly the selected contained mirror and journal the instance."""
    if plan.mirror_pk is None:
        return
    contents = getattr(actor, "contents", None)
    if contents is None:
        raise ItemUseError("actor lost its contents during item settlement")
    mirror = next((obj for obj in contents if obj.id == plan.mirror_pk), None)
    if mirror is None:
        raise ItemUseError(
            f"selected mirror {plan.mirror_pk} vanished during item settlement"
        )
    journal.note_mirror(mirror)
    mirror.delete()


def _apply_plan(
    request: ItemUseRequest, plan: ItemUsePlan, journal: ItemTouchedJournal
) -> int:
    """Commit the plan and return the actually-removed debuff count.

    Runs inside the caller's transaction. The cleanse branch skips the gauge
    write and removes every active debuff-polarity buff through the shipped
    ``cleanse:status`` removal path; gauge effects restore their bounded
    amount as today. Inventory removal goes through the inventory planner so
    ACQUIRE/quest journals compose with it; a key-only consumable deletes
    nothing and no mirror is ever fabricated.
    """
    removed = 0
    if plan.effect_key is ItemEffectKey.BLESSED_CLEANSE:
        removed = cleanse_debuffs(request.actor)
    else:
        _write_gauge(plan.actor, plan.gauge, plan.gauge_restored)
    if plan.consumable:
        apply_inventory_plan(plan_inventory_delta(request.actor, removals=(request.item_key,)))
    _delete_mirror(request.actor, plan, journal)
    return removed


def resolve_item_use(
    request: ItemUseRequest, *, in_combat: bool
) -> ItemUseResult:
    """Atomically settle one item use against current canonical state.

    Repeats preflight (a presented descriptor is advisory only), applies the
    complete effect/consumption plan inside one transaction, and restores the
    durable and in-process surfaces the journal captured on any failure
    before re-raising. A rejection performs no write and emits no EventLog.
    """
    preflight = preflight_item_use(request, in_combat=in_combat)
    if not preflight.allowed or preflight.plan is None:
        return ItemUseResult(outcome="rejected", reason=preflight.reason)
    plan = preflight.plan
    journal = ItemTouchedJournal.capture(request.actor)
    try:
        with transaction.atomic():
            cleansed_count = _apply_plan(request, plan, journal)
    except Exception:
        journal.restore()
        raise
    event_log = _item_used_event_log(
        plan,
        str(request.actor.key),
        time_cost_seconds=0,
        cleansed_count=cleansed_count,
    )
    return ItemUseResult(
        outcome="success",
        event_log=event_log,
        time_cost_seconds=0,
        journal=journal,
    )


def use_item(
    actor: Any, item_key: str, *, clock: WorldClock | None = None
) -> ItemUseSettlement:
    """Settle one out-of-combat item use plus its canonical six-second cost.

    Repeats preflight, then wraps the complete item plan and the
    player-driven world's command-source advance in one outer transaction. On
    any failure the clock tick, every callback-owned advance surface, and the
    item journal's trait/inventory/quest/mirror caches are restored together
    before the exception propagates. An active combat session rejects with
    ``active_combat`` so item consumption can never bypass a combat round; a
    rejection advances no time.
    """
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(actor):
        return ItemUseSettlement(
            ItemUseResult(
                outcome="rejected", reason=ItemUseReason.ACTIVE_SESSION
            )
        )
    request = ItemUseRequest(actor=actor, item_key=item_key)
    preflight = preflight_item_use(request, in_combat=False)
    if not preflight.allowed:
        return ItemUseSettlement(
            ItemUseResult(outcome="rejected", reason=preflight.reason)
        )
    world_clock = clock if clock is not None else get_world_clock()
    registry = build_advance_snapshot_registry(
        world_clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (actor,)
    )
    tick_snapshot = _snapshot_clock_tick(world_clock)
    events: tuple[ScheduledEvent, ...] = ()
    result: ItemUseResult | None = None
    try:
        with transaction.atomic():
            result = resolve_item_use(request, in_combat=False)
            if result.outcome == "success":
                events = tuple(
                    world_clock.advance(
                        ITEM_USE_SECONDS, AdvanceSource.COMMAND, (actor,)
                    )
                )
    except Exception:
        # The database rows are gone with the rolled-back transaction; the
        # clock seam restores the tick and every callback-owned surface from
        # the pre-transaction snapshots, and the item journal restores the
        # trait/inventory/quest caches plus the deleted-mirror idmapper and
        # contents caches. If the resolver itself failed it already restored
        # its own journal; re-running the restore is an idempotent write.
        _restore_clock_tick(world_clock, tick_snapshot)
        _restore_advance_registry(registry, (actor,))
        if result is not None and result.journal is not None:
            result.journal.restore()
        raise
    return ItemUseSettlement(result=result, events=events)
