"""Item-use settlement: apply the plan, emit events, advance the clock.

Part of the ``world.rules/items`` package: the write side of the pipeline —
per-step appliers, the ``item_used`` event log, ``resolve_item_use`` (one
transaction around the whole plan with the rollback journal), and the public
out-of-combat ``use_item`` facade composing the item plan with the canonical
command-source clock advance inside one outer transaction (mirroring
``cast_settlement``).
"""

from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.rules.buffs import BUFF_DEFINITIONS, apply_buff, remove_by_selector
from world.rules.clock import (
    MAX_ADVANCE_SECONDS,
    AdvanceSource,
    ScheduledEvent,
    WorldClock,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
)
from world.rules.equipment import (
    apply_inventory_plan,
    plan_inventory_delta,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules import item_effects
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemStat,
    StatusApplyEffect,
    StatusRemoveEffect,
)
from world.rules.items.contracts import (
    ItemEffectStep,
    ItemUseError,
    ItemUsePlan,
    ItemUseReason,
    ItemUseRequest,
    ItemUseResult,
    ItemUseSettlement,
)
from world.rules.items.journal import ItemTouchedJournal
from world.rules.items.planning import preflight_item_use
from world.rules.items.reads import _gauge_from_storage, _pleasure_current
from world.rules.pleasure import apply_pleasure_gain
from world.rules.status_display import (
    MissingDisplayMetadataError,
    display_for,
)
from world.rules.targeting import RoomActionContext


_GAUGE_NOUN_ZH: dict[ItemStat, str] = {
    ItemStat.HP: "生命值",
    ItemStat.MP: "魔力值",
    ItemStat.SP: "體力值",
    ItemStat.PLEASURE: "快感值",
}
_REMOVAL_NOUN_ZH: dict[str, str] = {
    "negative": "負面狀態",
    "positive": "增益狀態",
    "all": "狀態",
}


def _step_text(display_name: str, step: ItemEffectStep, applied: int) -> str:
    """Render one stable ``item_used`` line for one settled step."""
    effect = step.effect
    if isinstance(effect, GaugeAdjustEffect):
        noun = _GAUGE_NOUN_ZH[effect.stat]
        rendered = str(abs(applied)).replace("{", "{{").replace("}", "}}")
        if applied < 0:
            return f"你使用了「{display_name}」，失去了 {rendered} 點{noun}。"
        verb = "提升" if effect.stat is ItemStat.PLEASURE else "恢復"
        return f"你使用了「{display_name}」，{verb}了 {rendered} 點{noun}。"
    if isinstance(effect, StatusApplyEffect):
        try:
            label = display_for(effect.status).label
        except MissingDisplayMetadataError:  # observability: ignore R2: only a synthetic status lacks display coverage (the shipped coverage test forbids a gap); the raw key keeps the line deterministic instead of failing settlement for presentation
            label = effect.status
        label = label.replace("{", "{{").replace("}", "}}")
        return f"你使用了「{display_name}」，獲得了「{label}」狀態。"
    noun = _REMOVAL_NOUN_ZH.get(effect.selector, "狀態")
    verb = "淨化" if effect.selector == "negative" else "清除"
    return f"你使用了「{display_name}」，{verb}了 {applied} 個{noun}。"


def _item_used_event_log(
    plan: ItemUsePlan, actor_key: str, time_cost_seconds: int, settled: list[tuple[ItemEffectStep, int]]
) -> EventLog:
    """Build one ``item_used`` entry per settled step, in profile order.

    Every entry carries the item key, the consumable flag, and the per-family
    payload: the signed gauge delta actually applied, or the matched status
    keys plus the count actually applied/removed (settlement truth, never the
    preflight estimate). ``status_keys`` are the distinct definition keys
    involved; ``count`` counts buff **instances**, so a multi-instance
    ``unique_per_source`` removal (the same status from several items) reports
    the instance count over deduplicated keys by design. The shipped
    single-effect wording is reproduced byte-for-byte: a restored gauge
    renders the shipped 恢復 sentence.
    """
    definition = ITEM_REGISTRY[plan.item_key]
    display_name = definition.display_name_zh.replace("{", "{{").replace("}", "}}")
    entries: list[EventEntry] = []
    for step, applied in settled:
        effect = step.effect
        data: dict[str, Any] = {
            "item_key": plan.item_key,
            "consumable": plan.consumable,
        }
        if isinstance(effect, GaugeAdjustEffect):
            data["stat"] = effect.stat.value
            data["amount"] = applied
        else:
            data["status_keys"] = list(step.status_keys)
            data["count"] = applied
        entries.append(
            EventEntry(
                kind="item_used",
                actor=actor_key,
                target=str(step.target.key),
                data=data,
                text_template=_step_text(display_name, step, applied),
            )
        )
    return EventLog(
        actor=actor_key,
        skill_key=plan.item_key,
        targets=tuple(dict.fromkeys(str(step.target.key) for step, _ in settled)),
        entries=tuple(entries),
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


def _apply_gauge_step(step: ItemEffectStep) -> int:
    """Write one gauge step and return the signed delta actually applied.

    Re-reads the gauge immediately before the write so the emitted amount is
    what actually moved, not the preflight estimate (design §5.7). The
    pleasure gauge routes through the shared ``apply_pleasure_gain`` writer
    (with its arousal-coupled cascade); every other gauge writes the trait
    handler directly.
    """
    effect = step.effect
    assert isinstance(effect, GaugeAdjustEffect)
    if effect.stat is ItemStat.PLEASURE:
        before = _pleasure_current(step.target)
        apply_pleasure_gain(step.target, step.amount)
        after = _pleasure_current(step.target)
        return after - before
    if effect.stat is ItemStat.MP:
        from world.rules.mp_flow import apply_mp_change

        return apply_mp_change(step.target, step.amount)
    gauge = _gauge_from_storage(step.target, effect.stat.value)
    if gauge is None:
        # Storage went malformed mid-transaction: fail closed so the outer
        # journal restores every surface instead of writing a guessed value.
        raise ItemUseError(f"{effect.stat.value} gauge vanished during item settlement")
    current, maximum = gauge
    desired = max(0, min(maximum, current + step.amount))
    _write_gauge(step.target, effect.stat.value, desired)
    applied = desired - current
    if effect.stat is ItemStat.HP and applied < 0:
        actual_loss = -applied
        if actual_loss > 0:
            from world.rules.state_reactions import dispatch_outcome_reaction

            dispatch_outcome_reaction(
                step.target,
                "hp_loss",
                source_tier="學徒",
                hp_loss_amount=actual_loss,
            )
    return applied


def _apply_status_step(step: ItemEffectStep, item_key: str) -> int:
    """Write one status step and return the count actually applied/removed.

    Applies route through the published ``apply_buff`` applier with the
    stable ``item:<item key>`` source identity so a ``unique_per_source``
    buff keys to this item's use; removals route through the published
    ``remove_by_selector`` applier. The returned count is the settled truth
    for the event payload.
    """
    effect = step.effect
    if isinstance(effect, StatusApplyEffect):
        definition = BUFF_DEFINITIONS[effect.status]
        source_key = f"item:{item_key}"
        instance_key: str | None = None
        if definition.stacking == "unique_per_source":
            instance_key = f"{effect.status}:{source_key}"
        data: dict[str, Any] = {"source_key": source_key}
        apply_buff(step.target, effect.status, instance_key=instance_key, **data)
        return 1
    assert isinstance(effect, StatusRemoveEffect)
    return remove_by_selector(step.target, effect.selector)


def _apply_plan(
    plan: ItemUsePlan, journal: ItemTouchedJournal
) -> list[tuple[ItemEffectStep, int]]:
    """Commit every planned step in order and return each step's applied count.

    Runs inside the caller's transaction. Each step reaches its own target
    through the published applier for its family (gauge trait write / shared
    pleasure writer / ``apply_buff`` / ``remove_by_selector``); the shipped
    single-effect gauge and cleanse items reproduce their exact prior write.
    Inventory removal goes through the inventory planner so ACQUIRE/quest
    journals compose with it; a key-only consumable deletes nothing and no
    mirror is ever fabricated.
    """
    settled: list[tuple[ItemEffectStep, int]] = []
    for step in plan.steps:
        if isinstance(step.effect, GaugeAdjustEffect):
            applied = _apply_gauge_step(step)
        else:
            applied = _apply_status_step(step, plan.item_key)
        settled.append((step, applied))
    if plan.consumable:
        apply_inventory_plan(
            plan_inventory_delta(plan.actor, removals=(plan.item_key,))
        )
    _delete_mirror(plan.actor, plan, journal)
    return settled


def resolve_item_use(
    request: ItemUseRequest, *, in_combat: bool, context: Any | None = None
) -> ItemUseResult:
    """Atomically settle one item use against current canonical state.

    Repeats preflight (a presented descriptor is advisory only), applies the
    complete multi-step effect/consumption plan inside one transaction, and
    restores the durable and in-process surfaces the journal captured —
    including the per-entity sexual surface a pleasure step writes, for
    **every** touched entity — on any failure before re-raising. A rejection
    performs no write and emits no EventLog, carrying the preflight detail
    (the resolver's own reason for a ``target_invalid``) unchanged.
    """
    preflight = preflight_item_use(request, in_combat=in_combat, context=context)
    if not preflight.allowed or preflight.plan is None:
        return ItemUseResult(
            outcome="rejected", reason=preflight.reason, detail=preflight.detail
        )
    plan = preflight.plan
    # Capture every entity the plan steps on before the first write (design
    # D3): a lazy per-target capture could not restore state an earlier
    # target's write cascade touched.
    journal = ItemTouchedJournal.capture(
        request.actor, [step.target for step in plan.steps]
    )
    try:
        with transaction.atomic():
            settled = _apply_plan(plan, journal)
    except Exception:
        journal.restore()
        raise
    event_log = _item_used_event_log(
        plan,
        str(request.actor.key),
        time_cost_seconds=0,
        settled=settled,
    )
    return ItemUseResult(
        outcome="success",
        event_log=event_log,
        time_cost_seconds=0,
        journal=journal,
    )


def use_item(
    actor: Any,
    item_key: str,
    *,
    target: Any | None = None,
    clock: WorldClock | None = None,
) -> ItemUseSettlement:
    """Settle one out-of-combat item use plus its canonical six-second cost.

    Repeats preflight, then wraps the complete item plan and the
    player-driven world's command-source advance in one outer transaction. On
    any failure the clock tick, every callback-owned advance surface, and the
    item journal's trait/inventory/quest/mirror caches are restored together
    — for every touched entity — before the exception propagates. ``target``
    is the caller's single explicit choice consumed by single-scope effects
    (design D1); resolution uses the room context built from the actor's
    location. An active combat session rejects with ``active_combat`` so item
    consumption can never bypass a combat round; a rejection advances no
    time.
    """
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(actor):
        return ItemUseSettlement(
            ItemUseResult(
                outcome="rejected", reason=ItemUseReason.ACTIVE_SESSION
            )
        )
    request = ItemUseRequest(actor=actor, item_key=item_key, target=target)
    preflight = preflight_item_use(
        request, in_combat=False, context=RoomActionContext(actor.location)
    )
    if not preflight.allowed:
        return ItemUseSettlement(
            ItemUseResult(
                outcome="rejected", reason=preflight.reason, detail=preflight.detail
            )
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
            result = resolve_item_use(
                request,
                in_combat=False,
                context=RoomActionContext(actor.location),
            )
            if result.outcome == "success":
                events = tuple(
                    world_clock.advance(
                        item_effects.ITEM_USE_SECONDS, AdvanceSource.COMMAND, (actor,)
                    )
                )
    except Exception:
        # The database rows are gone with the rolled-back transaction; the
        # clock seam restores the tick and every callback-owned surface from
        # the pre-transaction snapshots, and the item journal restores the
        # trait/inventory/quest caches plus the deleted-mirror idmapper and
        # contents caches — per captured entity for the multi-entity
        # surfaces. If the resolver itself failed it already restored its own
        # journal; re-running the restore is an idempotent write.
        _restore_clock_tick(world_clock, tick_snapshot)
        _restore_advance_registry(registry, (actor,))
        if result is not None and result.journal is not None:
            result.journal.restore()
        raise
    return ItemUseSettlement(result=result, events=events)
