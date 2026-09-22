"""Buff-application effect handlers and their staging helpers.

Attribution, recovery-policy snapshots, and equipment-immunity neutralization
are decided at staging time so the replayable event tag is fixed before the
commit. Registrations live next to their handlers.
"""

from typing import Any

from world.rules.buffs import (
    BUFF_DEFINITIONS,
    _handle_cleanse,
    _is_damaging_gauge_rate,
    apply_buff,
    get_recovery_policy,
)
from world.rules.equipment_effects import equipment_immune_buff_keys

from world.rules.action.contracts import (
    _entity_key,
    parse_effect_key,
    register_effect_handler,
    PendingEffect,
    RejectedAction,
    RejectReason,
)


def resolve_source_tier(context: dict[str, Any] | None) -> str:
    """Resolve the caster's spell tier for attribution, defaulting to 學徒.

    The resolved effect's ``source_skill`` is optional; the deferred import
    keeps the cost-tier dependency out of the module's top-level import graph.
    """
    source_tier = "學徒"
    resolved = context.get("resolved_effect") if context is not None else None
    source_skill = getattr(resolved, "source_skill", None)
    if source_skill is not None:
        try:
            from world.skills.cost_tiers import spell_tier_for

            resolved_tier = spell_tier_for(source_skill)
            if resolved_tier:
                source_tier = resolved_tier
        except Exception:  # observability: ignore R2: nonspell or out-of-tier skill safely falls back to apprentice rung
            source_tier = "學徒"
    return source_tier


def source_attribution_kwargs(
    definition: Any,
    key: str,
    actor: Any,
    source_skill: Any,
) -> dict[str, Any]:
    """Return authoritative caster attribution for a damaging-gauge-rate buff.

    Attribution is authoritative-actor-derived and cannot be spoofed: the
    caller pops any caller-supplied ``source_pk``/``source_skill`` and
    replaces them from the caster's dbref, and an actor without a resolvable
    positive-int dbref rejects the action before commit (fix-dot-kill-credit
    D1). A non-gauge rate returns an empty mapping and leaves caller kwargs
    untouched.
    """
    rate = definition.modifiers.get("rate") if definition is not None else None
    if not _is_damaging_gauge_rate(rate):
        return {}
    pk = getattr(actor, "pk", None)
    if isinstance(pk, bool) or not isinstance(pk, int) or pk <= 0:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"buff {key!r} requires a caster with a positive-int dbref",
        )
    attribution = {"source_pk": int(pk)}
    if source_skill is not None:
        attribution["source_skill"] = getattr(source_skill, "key", str(source_skill))
    return attribution


def recovery_snapshot_kwargs(
    definition: Any,
    key: str,
    actor: Any,
    context: dict[str, Any],
    *,
    id_fallback: bool,
) -> dict[str, Any] | None:
    """Snapshot recovery-policy modifiers into kwargs, or ``None`` without a policy.

    Captures the caster's heal gain, arousal-scaled grace multiplier, and
    authoritative caster dbref for the buff's recovery policy. ``id_fallback``
    gates the non-dbref ``actor.id`` fallback: the target-scoped buff handler
    uses it, the self-buff twin deliberately does not (the two recovery blocks
    differ in exactly that line). ``key`` is accepted for signature symmetry
    with the sibling staging helpers.
    """
    if definition is None or get_recovery_policy(definition) is None:
        return None
    from world.rules.combat_modifiers import evaluate_combat_modifiers

    caster_mods = evaluate_combat_modifiers(actor) if actor is not None else {}
    snapshot: dict[str, Any] = {}
    heal_gain = caster_mods.get("heal_gain")
    if heal_gain is not None:
        snapshot["snapshot_heal_gain"] = heal_gain
    # The grace tier is read EXACTLY once: saintess_vessel's ceremonial
    # blessing_arousal_scale and priestly_grace's recovery_arousal_scale are
    # both 0.1/ordinal by design and arrive on deliberately distinct keys —
    # same-key numerics ADD at merge, so a shared key would silently double
    # the multiplier for a holder of both. max() folds them into one read.
    arousal_scale = max(
        float(
            caster_mods.get("recovery_arousal_scale", 0.0)
            or caster_mods.get("recovery_scale", 0.0)
            or 0.0
        ),
        float(caster_mods.get("blessing_arousal_scale", 0.0) or 0.0),
    )
    arousal_ordinal = 0
    if actor is not None:
        sexual = getattr(actor, "sexual", None)
        if sexual is not None:
            arousal_level = sexual.arousal
            arousal_ordinal = int(getattr(arousal_level, "value", 0))
        else:
            from world.rules.stored_sexual_reads import stored_sexual_level

            stored_lvl = stored_sexual_level(actor, "arousal")
            if stored_lvl is not None:
                arousal_ordinal = int(getattr(stored_lvl, "value", 0))
    passive_grace = 1.0 + arousal_scale * arousal_ordinal
    context_grace = context.get("grace_multiplier")
    if context_grace is not None:
        final_grace = passive_grace * float(context_grace)
    else:
        final_grace = passive_grace
    snapshot["snapshot_grace_multiplier"] = final_grace
    pk = getattr(actor, "pk", None)
    if isinstance(pk, int) and not isinstance(pk, bool) and pk > 0:
        snapshot["source_pk"] = int(pk)
    elif (
        id_fallback
        and getattr(actor, "id", None)
        and isinstance(actor.id, int)
        and actor.id > 0
    ):
        snapshot["source_pk"] = int(actor.id)
    return snapshot


def stage_buff_pending(
    target: Any,
    key: str,
    kwargs: dict[str, Any],
    definition: Any,
    effect_set: frozenset[str],
    tag: str,
) -> PendingEffect:
    """Stage one buff application, neutralizing an equipment-immunized debuff.

    Worn-equipment immunity is decided at STAGING time so the event tag is
    fixed here, in the ordinary replayable-entry path: a neutralized roll is
    never silently lied about (P3 design D1). Like ``_resist_pending_effect``,
    the staged effect is non-mutating; ``apply_buff`` still carries an
    independent no-write backstop for every direct caller. ``tag`` carries the
    handler's event prefix (``buff_applied`` vs ``self_buff_applied``) and
    ``effect_set`` its declared surfaces; the neutralized branch always uses
    the ``equipment_immune`` tag and an empty surface set.
    """
    if (
        definition is not None
        and definition.polarity == "debuff"
        and key in equipment_immune_buff_keys(target)
    ):
        return PendingEffect(
            target,
            f"equipment_immune|{_entity_key(target)}|{key}",
            frozenset(),
            lambda: None,
        )
    return PendingEffect(
        target,
        f"{tag}|{_entity_key(target)}|{key}",
        effect_set,
        lambda target=target: apply_buff(target, key, **kwargs),
    )


def _handle_buff_apply(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    key = parse_effect_key(effect_id)
    kwargs = dict(context.get("buff_kwargs", {}))
    resolved = context.get("resolved_effect") if context is not None else None
    source_skill = getattr(resolved, "source_skill", None)
    kwargs["source_tier"] = resolve_source_tier(context)
    definition = BUFF_DEFINITIONS.get(key)
    attribution = source_attribution_kwargs(definition, key, actor, source_skill)
    if attribution:
        kwargs.pop("source_pk", None)
        kwargs.pop("source_skill", None)
        kwargs.update(attribution)
    if definition is not None and "divert" in definition.modifiers:
        if source_skill is not None:
            kwargs.setdefault("source_skill", getattr(source_skill, "key", str(source_skill)))
    snapshot = recovery_snapshot_kwargs(definition, key, actor, context, id_fallback=True)
    if snapshot is not None:
        kwargs.update(snapshot)
    battlefield = context.get("battlefield")
    if battlefield is not None:
        kwargs["battlefield"] = battlefield
    return [
        stage_buff_pending(target, key, kwargs, definition, frozenset(), "buff_applied")
        for target in targets
    ]


def _handle_self_buff_apply(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Apply one definition-keyed buff to the caster without a target.

    ``TargetSpec.NONE`` skills resolve to an empty target list, so this handler
    binds the actor directly instead of iterating targets. This keeps a NONE
    skill meaningful (a concentration-style self effect) while still never
    accepting a caller-supplied target. A debuff grant the actor's worn
    equipment immunises stages the same non-mutating neutralization event as
    the target-scoped handler.
    """
    del targets, scale
    key = parse_effect_key(effect_id)
    kwargs: dict[str, Any] = {}
    resolved = context.get("resolved_effect") if context is not None else None
    source_skill = getattr(resolved, "source_skill", None)
    kwargs["source_tier"] = resolve_source_tier(context)
    definition = BUFF_DEFINITIONS.get(key)
    attribution = source_attribution_kwargs(definition, key, actor, source_skill)
    if attribution:
        kwargs.pop("source_pk", None)
        kwargs.pop("source_skill", None)
        kwargs.update(attribution)
    if definition is not None and "divert" in definition.modifiers:
        if source_skill is not None:
            kwargs.setdefault("source_skill", getattr(source_skill, "key", str(source_skill)))
    snapshot = recovery_snapshot_kwargs(
        definition, key, actor, context, id_fallback=False
    )
    if snapshot is not None:
        kwargs.update(snapshot)
    battlefield = context.get("battlefield")
    if battlefield is not None:
        kwargs["battlefield"] = battlefield
    return [
        stage_buff_pending(
            actor, key, kwargs, definition, frozenset({"buffs"}), "self_buff_applied"
        )
    ]


register_effect_handler(
    "buff_apply",
    _handle_buff_apply,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "self_buff_apply",
    _handle_self_buff_apply,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "cleanse",
    _handle_cleanse,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
