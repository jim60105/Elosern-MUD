"""Deterministic authorization and execution of generated story effects.

A generated role's qualified topic may name one registered domain verb with a
validated reference. A label or a scene line never awards progress or items:
the association is declared beside the immutable package, and the verb executes
through the existing deterministic quest APIs only after the *same* checks on
every path -- presence, the current permitted phase revision, the referenced
commission's role scope, qualification, and the exact issuer authority the role
holds. A selection that cannot pass rechecks delivers only the topic's authored
refusal; no protected success body, formal reading receipt or accepted quest is
created.

Read-only refusals return a named reason; an accepted commission is created
through ``world.quests.runtime.accept_quest``, the sole acceptance writer. The
caller that also publishes the dialogue session owns the surrounding
transaction, so an effect and its delivery commit together or not at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.observability import log_info, log_warn

from .dialogue import generated_phase_binding

OFFER_COMMISSION = "offer_commission"
STORY_EFFECT_VERBS: tuple[str, ...] = (OFFER_COMMISSION,)


@dataclass(frozen=True)
class StoryEffectOutcome:
    """The result of one authorized story effect: whether it applied and why."""

    applied: bool
    reason: str


def effect_for_topic(
    npc: Any,
    topic_id: str,
    *,
    expected_phase_revision: int | None = None,
) -> Any | None:
    """Return the declared effect association of one current topic, or ``None``.

    Read-only and trusted: the association comes from the host's exact published
    package role and currently selected phase, never from a client payload or a
    scene line. A missing binding, a different revision or an undeclared topic
    yields ``None``.
    """
    binding = generated_phase_binding(npc)
    if binding is None:
        return None
    if (
        expected_phase_revision is not None
        and binding.revision != expected_phase_revision
    ):
        return None
    return next(
        (effect for effect in binding.phase.topic_effects if effect.topic_id == topic_id),
        None,
    )


def _resolve_context(
    npc: Any,
    character: Any,
    topic_id: str,
    *,
    expected_phase_revision: int | None,
    context: Any = None,
) -> tuple[tuple[Any, Any, str, Any] | None, str]:
    """Resolve the authorized effect context, or return a named refusal reason."""
    if character is None or npc is None:
        return None, "no_participant"
    if character.location is None or npc.location is None:
        return None, "absent"
    if int(character.location.pk) != int(npc.location.pk):
        return None, "absent"
    binding = generated_phase_binding(npc)
    if binding is None:
        return None, "no_current_phase"
    if (
        expected_phase_revision is not None
        and binding.revision != expected_phase_revision
    ):
        return None, "stale_phase"
    phase = binding.phase
    effect = next(
        (row for row in phase.topic_effects if row.topic_id == topic_id), None
    )
    if effect is None:
        return None, "stale_phase"
    topic = next((row for row in phase.topics if row.topic_id == topic_id), None)
    if topic is None:
        return None, "stale_phase"
    if effect.verb not in STORY_EFFECT_VERBS:
        return None, "unknown_verb"
    if context is None:
        from world.rules.dialogue_context import (
            DialogueContextError,
            resolve_dialogue_context,
        )

        try:
            context = resolve_dialogue_context(character, npc)
        except DialogueContextError as error:  # observability: ignore R2: the named authorization reason IS the refusal
            return None, error.reason
    if topic.requires is None:
        return None, "unqualified"
    from world.rules.dialogue_conditions import evaluate_condition

    if not evaluate_condition(topic.requires, context):
        return None, "unqualified"
    commission = next(
        (
            declared
            for declared in binding.definition.commissions
            if declared.role_id == binding.role_id
            and declared.definition_key == effect.reference
        ),
        None,
    )
    if commission is None:
        return None, "out_of_scope"
    from world.rules.quest_issuance import resolve_issuance, resolve_issuer_key

    issuer_key = resolve_issuer_key(npc)
    if issuer_key is None:
        return None, "unauthorized"
    if resolve_issuance(effect.reference, issuer_key) is None:
        return None, "unregistered_commission"
    return (binding.definition, commission, issuer_key, effect), ""


def apply_story_effect(
    npc: Any,
    character: Any,
    *,
    topic_id: str,
    expected_phase_revision: int | None = None,
    context: Any = None,
    tick: int = 0,
) -> StoryEffectOutcome:
    """Authorize and execute one declared story effect, or refuse by name."""
    resolved, reason = _resolve_context(
        npc,
        character,
        topic_id,
        expected_phase_revision=expected_phase_revision,
        context=context,
    )
    if resolved is None:
        _report_refused(npc, character, topic_id, expected_phase_revision, reason, tick)
        return StoryEffectOutcome(False, reason)
    _definition, commission, issuer_key, effect = resolved
    from world.quests.runtime import accept_quest

    owner = getattr(context, "owner", None) if context is not None else None
    if owner is None:
        from world.rules.dialogue_context import session_control_owner

        owner = session_control_owner(character) or character
    try:
        record = accept_quest(
            owner,
            commission.definition_key,
            issuer_key,
            actual_actor=character if character is not owner else None,
            expected_revision=expected_phase_revision,
        )
    except Exception as error:  # noqa: BLE001 - a refused acceptance is a bounded, named outcome
        log_warn(
            "story_effect_refused",
            context={
                "npc": str(getattr(npc, "pk", "?")),
                "char": str(getattr(character, "pk", "?")),
                "topic": str(topic_id),
                "revision": str(expected_phase_revision),
                "reason": "accept_refused",
                "tick": str(tick),
            },
            exc=error,
        )
        return StoryEffectOutcome(False, "accept_refused")
    log_info(
        "story_effect_applied",
        context={
            "npc": str(getattr(npc, "pk", "?")),
            "char": str(getattr(character, "pk", "?")),
            "topic": str(topic_id),
            "verb": effect.verb,
            "reference": effect.reference,
            "quest": getattr(record, "quest_id", ""),
            "tick": str(tick),
        },
    )
    return StoryEffectOutcome(True, "accepted")


def _report_refused(
    npc: Any,
    character: Any,
    topic_id: str,
    expected_phase_revision: int | None,
    reason: str,
    tick: int,
) -> None:
    log_warn(
        "story_effect_refused",
        context={
            "npc": str(getattr(npc, "pk", "?")),
            "char": str(getattr(character, "pk", "?")),
            "topic": str(topic_id),
            "revision": str(expected_phase_revision),
            "reason": reason,
            "tick": str(tick),
        },
    )


__all__ = [
    "OFFER_COMMISSION",
    "STORY_EFFECT_VERBS",
    "StoryEffectOutcome",
    "apply_story_effect",
    "effect_for_topic",
]
