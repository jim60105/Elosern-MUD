"""Situation derivation and the frozen generation context.

The read-only path from an actor to what one generation needs: the shared
situation fingerprint derivation and the bounded, deterministically ranked
layer context assembled from world data. Every ``world.ai`` and
``web.webclient`` import is function-local so this module stays cold
importable like the service it backs.
"""

from typing import Any

# Prompt affordance rank — objective-relevant (targeted) entries first, then
# movement, then inspection, then the idle baseline; stable within a rank.
_PROMPT_AFFORDANCE_RANKS = {
    "explore.talk_scripted": 0,
    "explore.talk_freeform": 0,
    "explore.engage": 0,
    "explore.move": 1,
    "explore.look": 2,
}


def _derive_situation(
    actor: Any,
) -> "tuple[str, Any, Any, list[Any], list[Any], tuple] | None":
    """Derive ``(fingerprint, vocab, eligible, npcs, monsters, objectives)``.

    Delegates to the shared read-only derivation in
    ``web.webclient.presentation.fingerprints`` — the same helper the
    presentation-context factory consumes — so scheduling and presentation can
    never drift on what names the situation. The helper import is
    function-local (this module stays cold importable). Returns ``None`` when
    the trigger has no room to name the situation.
    """
    from web.webclient.presentation.fingerprints import derive_exploration_situation

    return derive_exploration_situation(actor)


def _prompt_affordances(eligible: Any) -> tuple[Any, ...]:
    """The bounded, deterministically ranked affordance list for one prompt.

    The full eligible list is what the *fingerprint* digests; the prompt list
    is capped at the layer's bound with targeted entries first, movement next,
    inspection, and the idle baseline last, tie-broken by vocabulary order.
    """
    from world.ai.action_options import MAX_AFFORDANCES

    def _rank(entry: Any) -> int:
        return _PROMPT_AFFORDANCE_RANKS.get(entry.action_id, 3)

    return tuple(sorted(eligible, key=_rank))[:MAX_AFFORDANCES]


def _build_generation_context(
    actor: Any,
    npcs: list[Any],
    monsters: list[Any],
    objectives: tuple,
    eligible: Any,
) -> Any:
    """Assemble the frozen, bounded layer context from read-only world data."""
    from world.ai.action_options import (
        MAX_NARRATIVE_TAIL_LENGTH,
        MAX_OBJECTIVE_LENGTH,
        MAX_ROOM_NAME_LENGTH,
        MAX_ROOM_SUMMARY_LENGTH,
        build_options_context,
    )
    from world.rules.dialogue import dialogue_key_for
    from world.rules.persona import PersonaStore
    from web.webclient.presentation.fingerprints import public_tier_labels

    location = actor.location
    room_name = str(
        getattr(location.db, "name", None) or getattr(location, "key", "") or "???"
    )[:MAX_ROOM_NAME_LENGTH]
    room_summary = str(getattr(location.db, "desc", None) or "")[:MAX_ROOM_SUMMARY_LENGTH]
    narrative_tail = str(
        getattr(location.db, "scene_flavor", None) or ""
    )[-MAX_NARRATIVE_TAIL_LENGTH:]
    objective: str | None = objectives[0][2][:MAX_OBJECTIVE_LENGTH] if objectives else None

    tiers = dict(public_tier_labels(actor, npcs))
    npc_entries = []
    for npc in npcs:
        npc_entries.append(
            {
                "npc_id": int(npc.pk),
                "display_name": str(getattr(npc, "key", None) or "???"),
                "dialogue_key": dialogue_key_for(npc),
                "persona_digest": PersonaStore(npc).flatten() or "",
                "public_tier": tiers.get(int(npc.pk)),
            }
        )
    monster_entries = []
    for monster in monsters:
        threat_tier = getattr(monster, "threat_tier", None)
        monster_entries.append(
            {
                "monster_id": int(monster.pk),
                "display_name": str(getattr(monster, "key", None) or "???"),
                "threat_tier": str(threat_tier) if threat_tier is not None else None,
            }
        )
    secret_tokens = []
    for npc in npcs:
        handler = getattr(npc, "relations", None)
        if handler is not None:
            secret_tokens.append(str(handler.affinity_for(actor)))

    return build_options_context(
        room_name=room_name,
        room_summary=room_summary,
        narrative_tail=narrative_tail,
        npc_entries=npc_entries,
        monster_entries=monster_entries,
        objective=objective,
        affordances=_prompt_affordances(eligible),
        secret_tokens=secret_tokens,
    )
