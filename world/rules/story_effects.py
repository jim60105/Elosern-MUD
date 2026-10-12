"""Deterministic authorization and execution of generated story effects (4.2).

A generated role's scripted topic may name one registered domain verb with a
validated reference. A label or a fixed line never awards progress or items:
the verb is executed through the existing deterministic quest APIs only after
the *same* checks on every path -- presence, the current permitted phase
revision, the referenced commission's scope, and the exact issuer authority the
role holds. A free-form intent validated by the intent applier reaches this same
function, so scripted and free-form effects cannot diverge.

Read-only refusals return a named reason; an accepted commission is created
through ``world.quests.runtime.accept_quest``, the sole acceptance writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.observability import log_info, log_warn

from .dialogue import generated_dialogue_for

OFFER_COMMISSION = "offer_commission"
STORY_EFFECT_VERBS: tuple[str, ...] = (OFFER_COMMISSION,)


@dataclass(frozen=True)
class StoryEffectOutcome:
    """The result of one authorized story effect: whether it applied and why."""

    applied: bool
    reason: str


def _resolve_context(
    npc: Any, character: Any, keyword: str, reference: str
) -> tuple[Any | None, str]:
    """Resolve the authorized effect context, or return a named refusal reason."""
    if character is None or npc is None:
        return None, "no_participant"
    if character.location is None or npc.location is None:
        return None, "absent"
    if int(character.location.pk) != int(npc.location.pk):
        return None, "absent"
    generated = generated_dialogue_for(npc)
    if generated is None:
        return None, "no_current_phase"
    from world.quests import scene_store
    from world.quests.scene_package import validate_scene_package

    row = scene_store.read_package(generated.package_id)
    if row is None:
        return None, "unknown_package"
    definition = validate_scene_package(row.payload)
    commission = next(
        (
            declared
            for declared in definition.commissions
            if declared.definition_key == reference
        ),
        None,
    )
    if commission is None:
        return None, "out_of_scope"
    role_dialogue = definition.role_dialogue(generated.role_id)
    if role_dialogue is None:
        return None, "no_current_phase"
    phase = next(
        (item for item in role_dialogue.phases if item.phase_id == generated.phase_id),
        None,
    )
    if phase is None:
        return None, "no_current_phase"
    topic = next((item for item in phase.topics if item.keyword == keyword), None)
    if topic is None or topic.effect_verb is None or topic.effect_reference != reference:
        return None, "stale_phase"
    from world.rules.quest_issuance import resolve_issuance, resolve_issuer_key

    issuer_key = resolve_issuer_key(npc)
    if issuer_key is None:
        return None, "unauthorized"
    if resolve_issuance(reference, issuer_key) is None:
        return None, "unregistered_commission"
    return (definition, commission, issuer_key), ""


def apply_story_effect(
    npc: Any,
    character: Any,
    *,
    keyword: str,
    verb: str,
    reference: str,
    tick: int = 0,
) -> StoryEffectOutcome:
    """Authorize and execute one declared story effect, or refuse by name."""
    if verb not in STORY_EFFECT_VERBS:
        return StoryEffectOutcome(False, "unknown_verb")
    context, reason = _resolve_context(npc, character, keyword, reference)
    if context is None:
        log_warn(
            "story_effect_refused",
            context={
                "npc": str(getattr(npc, "pk", "?")),
                "char": str(getattr(character, "pk", "?")),
                "keyword": keyword,
                "verb": verb,
                "reference": reference,
                "reason": reason,
                "tick": str(tick),
            },
        )
        return StoryEffectOutcome(False, reason)
    definition, commission, issuer_key = context
    from world.quests.runtime import accept_quest

    try:
        record = accept_quest(character, commission.definition_key, issuer_key)
    except Exception as error:  # noqa: BLE001 - a refused acceptance is a bounded, named outcome
        log_warn(
            "story_effect_refused",
            context={
                "npc": str(getattr(npc, "pk", "?")),
                "char": str(getattr(character, "pk", "?")),
                "keyword": keyword,
                "verb": verb,
                "reference": reference,
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
            "keyword": keyword,
            "verb": verb,
            "reference": reference,
            "quest": getattr(record, "quest_id", ""),
            "tick": str(tick),
        },
    )
    return StoryEffectOutcome(True, "accepted")


def effect_for_keyword(npc: Any, keyword: str) -> tuple[str, str] | None:
    """Return ``(verb, reference)`` for a keyword in the host's current phase."""
    generated = generated_dialogue_for(npc)
    if generated is None:
        return None
    from world.quests import scene_store
    from world.quests.scene_package import validate_scene_package

    row = scene_store.read_package(generated.package_id)
    if row is None:
        return None
    definition = validate_scene_package(row.payload)
    role_dialogue = definition.role_dialogue(generated.role_id)
    if role_dialogue is None:
        return None
    phase = next(
        (item for item in role_dialogue.phases if item.phase_id == generated.phase_id),
        None,
    )
    if phase is None:
        return None
    topic = next((item for item in phase.topics if item.keyword == keyword), None)
    if topic is None or topic.effect_verb is None or topic.effect_reference is None:
        return None
    return topic.effect_verb, topic.effect_reference


__all__ = [
    "OFFER_COMMISSION",
    "STORY_EFFECT_VERBS",
    "StoryEffectOutcome",
    "apply_story_effect",
    "effect_for_keyword",
]