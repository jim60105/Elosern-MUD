"""Conferral, disguise, grant-revocation, and divine-mystery effect handlers.

Each handler stages ``PendingEffect`` values only; the single commit point in
:mod:`world.rules.action.transaction` applies them. Registrations live next to
their handlers so importing this module populates the handler registry.
"""

from typing import Any

from world.rules.skill_effects import (
    apply_divine_disguise,
    clear_disguise_effect,
    derive_conferrable_skills,
    disguise_provenance_of,
    DISGUISE_PROVENANCE_DIVINE,
    record_conferred_grant,
    reveal_can_pierce,
    reveal_disguise_effect,
    revoke_conferred_grants,
)
from world.skills.effects import parse_effect
from world.skills.registry import SkillDef

from world.rules.buffs import grant_conferred_growth_rate
from world.rules.action.contracts import (
    _entity_key,
    _effect_prefix,
    register_effect_handler,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.routing import _occurrence_scale


# Shared rejection detail so preflight, the preview, and the handler report
# the identical reason and wording for a conferral that derives nothing.
_CONFERRAL_EMPTY_SET_DETAIL = (
    "conferral derives no conferrable skill owned by the caster"
)


def _conferral_empty_set_failure(
    actor: Any,
    skill: SkillDef,
) -> tuple[RejectReason, str] | None:
    """Return the skill-wide conferral rejection ``(reason, detail)`` or ``None``.

    A conferral skill whose caster directly owns nothing conferrable can
    never resolve a grant, so preflight and the shared preview reject it
    with the same ``EFFECT_RESOLUTION_FAILED`` the handler raises — the
    preview never advertises a cast the resolver would reject.
    """
    if not any(
        _effect_prefix(effect_id) == "confer_skill_partial"
        for effect_id in skill.effects
    ):
        return None
    if derive_conferrable_skills(actor):
        return None
    return RejectReason.EFFECT_RESOLUTION_FAILED, _CONFERRAL_EMPTY_SET_DETAIL


def _handle_confer_skill_partial(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one grant per (target, conferrable skill) pair.

    The audienced form of the conferral verb (an AREA node declaring an
    ALLIES audience) routes every member of the resolved audience through
    this handler, so each target must be written individually — mirroring
    the per-target dispatch of ``revoke_grants`` and ``reveal_disguise``.
    A single-target cast degenerates to one recipient, exactly as before.
    """
    del scale
    conferrable = derive_conferrable_skills(actor)
    if not conferrable:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            _CONFERRAL_EMPTY_SET_DETAIL,
        )
    coefficient = _occurrence_scale(context)
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"skill_granted|{_entity_key(target)}|{skill_key}|{coefficient}",
            frozenset(),
            lambda target=target, source_key=source_key, skill_key=skill_key,
            coefficient=coefficient: record_conferred_grant(
                target, source_key, skill_key, coefficient
            ),
        )
        for target in targets
        for skill_key in conferrable
    ]


def _handle_set_disguise(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one veil write or lift from the derived recipe.

    The veil's displayed values are derived from the race registry, never
    supplied through ``event_context``. A cast at another entity always
    applies the derived veil. A cast at the actor toggles only against a
    veil this verb itself placed: a DIVINE veil is lifted, while a mundane
    veil (an authored declaration) or an unveiled state is refreshed, so a
    caster is never trapped behind their own face and never strips the
    authored disguise their character card starts the game wearing.

    Every member of the resolved audience is written individually, so an
    ALLIES-audience veil (the capstone's party-wide veil) reaches each
    recipient instead of only the first routed target.
    """
    del scale, context
    pending: list[PendingEffect] = []
    for target in targets:
        if (
            target is actor
            and disguise_provenance_of(target) == DISGUISE_PROVENANCE_DIVINE
        ):
            pending.append(
                PendingEffect(
                    target,
                    f"disguise_lifted|{_entity_key(target)}",
                    frozenset(),
                    lambda target=target: clear_disguise_effect(target),
                )
            )
        else:
            pending.append(
                PendingEffect(
                    target,
                    f"disguise_set|{_entity_key(target)}",
                    frozenset(),
                    lambda target=target: apply_divine_disguise(target),
                )
            )
    return pending


def _handle_reveal_disguise(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one provenance-scoped reveal attempt per target.

    The attempt always completes and is reported, never rejected: a veil the
    declared strength cannot pierce, or no veil at all, resolves as a clean
    no-op (design D4), so the action pays its cost and the caster learns
    nothing beyond the attempt itself. The outcome token is decided against
    the pre-action state; the staged write re-checks the same strength table
    at commit, keeping that table in the deterministic-core primitive.
    """
    del actor, scale, context
    strength = parse_effect(effect_id).strength
    pending: list[PendingEffect] = []
    for target in targets:
        outcome = "lifted" if reveal_can_pierce(target, strength) else "noop"
        pending.append(
            PendingEffect(
                target,
                f"reveal_{outcome}|{_entity_key(target)}",
                frozenset({"traits"}),
                lambda target=target, strength=strength: reveal_disguise_effect(
                    target, strength
                ),
            )
        )
    return pending


def _handle_confer_growth_rate(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one conferred growth-rate buff per resolved target.

    The ALLIES-audience growth conferrals (the 傳承 chain's party nodes)
    route every member of the audience through this handler, so each
    recipient is written individually; a single-target cast keeps the
    historical one-recipient behavior.
    """
    del scale
    coefficient = _occurrence_scale(context)
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"buff_applied|{_entity_key(target)}|conferred_growth_rate",
            frozenset(),
            lambda target=target, source_key=source_key,
            coefficient=coefficient: grant_conferred_growth_rate(
                target, source_key, coefficient
            ),
        )
        for target in targets
    ]


def _handle_revoke_grants(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one total conferral revocation per target.

    The single staged effect clears BOTH halves of the conferral vocabulary
    (skill grants and conferred growth-rate buffs) under the two declared
    ``skill_grants``/``buffs`` surfaces, so a failed commit restores both
    stores from the same snapshot/restore face (design D1). Revocation is
    unconditional and total: no payload, no source filter, no skill filter
    (design D2/D3).
    """
    del scale
    return [
        PendingEffect(
            target,
            f"grants_revoked|{_entity_key(target)}",
            frozenset(),
            lambda target=target: revoke_conferred_grants(target),
        )
        for target in targets
    ]


def _handle_divine_mystery(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Resolve one divine-mystery effect; unmechanized entries stay inert.

    ``DivineMysteryEffect(mechanized=False)`` is a deliberately declared
    flavor category: the cast is accepted but stages no state change. A
    mechanized entry has no cast path yet and must reject rather than
    silently doing nothing.
    """
    del actor, targets, context, scale
    if parse_effect(effect_id).mechanized:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "mechanized divine mysteries have no cast path yet",
        )
    return []


register_effect_handler(
    "confer_skill_partial",
    _handle_confer_skill_partial,
    frozenset({"skill_grants"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "set_disguise",
    _handle_set_disguise,
    frozenset({"traits"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "reveal_disguise",
    _handle_reveal_disguise,
    frozenset({"traits"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "confer_growth_rate",
    _handle_confer_growth_rate,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "revoke_grants",
    _handle_revoke_grants,
    frozenset({"skill_grants", "buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_mystery",
    _handle_divine_mystery,
    frozenset(),
    requires_event_context=frozenset(),
)
