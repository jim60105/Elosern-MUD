"""Side-effect-free item-use planning: per-step eligibility and preflight.

Part of the ``world.rules.items`` package: the bound-reached reason table, the
gauge/status step planners, and ``preflight_item_use`` — the single
eligibility oracle shared by presentation and settlement that writes nothing.
"""

from collections.abc import Callable
from typing import Any

from world.lore.items import ITEM_REGISTRY
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules import item_effects
from world.rules import item_effects
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
    StatusApplyEffect,
    StatusRemoveEffect,
)
from world.rules.items.contracts import (
    ItemEffectStep,
    ItemUsePlan,
    ItemUsePreflight,
    ItemUseReason,
    ItemUseRequest,
)
from world.rules.items.reads import (
    _active_matching_keys,
    _gauge_from_storage,
    _inventory_list,
    _pleasure_current,
    _rejected,
    _resolve_effect_targets,
    _select_mirror,
)
from world.rules.targeting import RoomActionContext


_FULL_REASON_BY_STAT: dict[ItemStat, ItemUseReason] = {
    ItemStat.HP: ItemUseReason.HP_FULL,
    ItemStat.MP: ItemUseReason.MP_FULL,
    ItemStat.SP: ItemUseReason.SP_FULL,
    ItemStat.PLEASURE: ItemUseReason.PLEASURE_FULL,
}


def _plan_gauge_step(
    effect: GaugeAdjustEffect, target: Any
) -> ItemEffectStep | ItemUseReason:
    """Compute the applicable signed delta for one gauge effect.

    Positive amounts restore up to the gauge maximum, negative amounts drain
    down to zero (design §5.3). An ineligible adjustment names its stat's
    bound-reached reason: a full gauge at the top reports ``*_FULL``; a
    drain blocked at zero reports the same stat code because the settlement
    vocabulary carries no separate floor code (tasks 4.4).
    """
    if effect.stat is ItemStat.PLEASURE:
        try:
            current = _pleasure_current(target)
        except TypeError:  # observability: ignore R2: malformed intimate storage fails closed as a validation rejection
            return ItemUseReason.MALFORMED_TRAITS
        maximum = 100
    else:
        gauge = _gauge_from_storage(target, effect.stat.value)
        if gauge is None:
            return ItemUseReason.MALFORMED_TRAITS
        current, maximum = gauge
    if effect.amount > 0:
        if current >= maximum:
            return _FULL_REASON_BY_STAT[effect.stat]
        return ItemEffectStep(effect=effect, target=target, amount=min(effect.amount, maximum - current))
    if current <= 0:
        return _FULL_REASON_BY_STAT[effect.stat]
    return ItemEffectStep(effect=effect, target=target, amount=max(effect.amount, -current))


def _status_matches(effect: StatusRemoveEffect) -> Callable[[str], bool]:
    """The definition-key predicate one removal selector names."""
    if effect.selector == "all":
        return lambda key: True
    if effect.selector == "negative":
        return lambda key: BUFF_DEFINITIONS[key].polarity == "debuff"
    if effect.selector == "positive":
        return lambda key: BUFF_DEFINITIONS[key].polarity == "buff"
    return lambda key: key == effect.selector


def _plan_status_step(
    effect: StatusApplyEffect | StatusRemoveEffect, target: Any
) -> ItemEffectStep | ItemUseReason:
    """Decide eligibility for one status effect without materializing handlers.

    An apply is blocked only by the same equipment-immunity gate
    ``apply_buff`` enforces for debuffs (grant-time polarity immunity). A
    removal is eligible when at least one active instance matches; the empty
    result of the ``negative`` selector keeps the shipped ``no_debuffs``
    code, every other empty removal names ``nothing_to_remove``.
    """
    if isinstance(effect, StatusApplyEffect):
        from world.rules.equipment_effects import equipment_immune_buff_keys

        definition = BUFF_DEFINITIONS.get(effect.status)
        if definition is None:
            # A profile injected past the loader naming an undefined status
            # fails closed like the scope seam, never as an unhandled
            # KeyError at the command/web boundary.
            return ItemUseReason.UNKNOWN_EFFECT
        if (
            definition.polarity == "debuff"
            and effect.status in equipment_immune_buff_keys(target)
        ):
            return ItemUseReason.STATUS_BLOCKED
        return ItemEffectStep(
            effect=effect, target=target, status_keys=(effect.status,)
        )
    try:
        matched = _active_matching_keys(target, _status_matches(effect))
    except TypeError:  # observability: ignore R2: a malformed buff cache is a validation rejection returned as malformed_traits
        return ItemUseReason.MALFORMED_TRAITS
    if not matched:
        return (
            ItemUseReason.NO_DEBUFFS
            if effect.selector == "negative"
            else ItemUseReason.NOTHING_TO_REMOVE
        )
    return ItemEffectStep(effect=effect, target=target, status_keys=matched)


def preflight_item_use(
    request: ItemUseRequest,
    *,
    in_combat: bool,
    context: Any | None = None,
) -> ItemUsePreflight:
    """Evaluate item-use eligibility against current state, writing nothing.

    Resolves the canonical registry definition and the profile's live
    effect-map entry, verifies at least one held key in the canonical
    inventory, validates the current mode against the definition, then
    computes one step per EFFECTIVE EFFECT-AND-TARGET pair in profile order
    (design §5.1/§5.2). Each effect resolves its targets through the shared
    ``resolve_targets`` with the requirement its scope maps to — the
    identical presence/alive/range/faction pipeline a skill's targets pass —
    and group scopes expand through the caller-supplied action context
    (battlefield roster shorthand in a session, room occupants out of one;
    design D2/D6). ``in_combat`` stays an independent parameter: it gates the
    item's ``combat_allowed`` permission, which is a question about the item,
    while the context is a question about the world. When ``context`` is
    omitted, resolution builds the room context from the actor's location —
    the exploration-side convenience; a resolving request in combat without a
    context is a caller error and raises ``TypeError`` rather than silently
    validating against the wrong world. A single-scope effect with no
    supplied target rejects ``no_target``; a rejected resolver rejects
    ``target_invalid`` carrying the resolver's own reason as ``detail``
    (design D5). An item whose every effect is ineligible against every of
    its targets rejects with the uniform bound reason when every step names
    the same one, otherwise with ``no_effect`` — one effective pair anywhere
    carries the whole use (design §5.4). It never mutates inventory, traits,
    quest state, equipment, combat state, clock, sexual state, or
    presentation.
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
    # Call-time resolution through the module attribute (never a name copy)
    # so reloads and the synthetic kit's scoped profile map reach settlement.
    profile = item_effects.ITEM_EFFECT_PROFILES.get(request.item_key)
    if not isinstance(profile, ItemEffectProfile):
        return _rejected(ItemUseReason.UNKNOWN_EFFECT)
    hp_gauge = _gauge_from_storage(request.actor, "hp")
    if hp_gauge is None:
        return _rejected(ItemUseReason.MALFORMED_TRAITS)
    if hp_gauge[0] <= 0:
        return _rejected(ItemUseReason.NOT_ALIVE)
    steps: list[ItemEffectStep] = []
    reasons: list[ItemUseReason] = []
    needs_resolution = any(
        effect.scope is not ItemTargetScope.SELF for effect in profile.effects
    )
    if context is None:
        # Legacy no-context callers keep working: out of combat the room
        # context is the only world view a preflight needs. In combat the
        # session's BattlefieldActionContext is mandatory the moment an
        # effect reaches beyond the actor (design D2).
        if in_combat and needs_resolution:
            raise TypeError(
                "preflight_item_use requires the caller's action context "
                "to resolve non-self scopes in combat (design D2); pass "
                "the BattlefieldActionContext the session already holds"
            )
        context = RoomActionContext(request.actor.location)
    for effect in profile.effects:
        resolved = _resolve_effect_targets(request, effect, context)
        if isinstance(resolved, ItemUsePreflight):
            return resolved
        for target in resolved:
            if isinstance(effect, GaugeAdjustEffect):
                step = _plan_gauge_step(effect, target)
            else:
                step = _plan_status_step(effect, target)
            if isinstance(step, ItemEffectStep):
                steps.append(step)
            else:
                reasons.append(step)
    if not steps:
        if len(reasons) == 1 or len(set(reasons)) == 1:
            return _rejected(reasons[0])
        return _rejected(ItemUseReason.NO_EFFECT)
    mirror = (
        _select_mirror(request.actor, request.item_key)
        if mechanics.consumable
        else None
    )
    plan = ItemUsePlan(
        actor=request.actor,
        item_key=request.item_key,
        consumable=mechanics.consumable,
        steps=tuple(steps),
        mirror_pk=mirror.id if mirror is not None else None,
    )
    return ItemUsePreflight(allowed=True, reason=None, plan=plan)
