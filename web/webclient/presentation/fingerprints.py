"""Situation fingerprint derivation for the AI action-options trigger service.

The fingerprint names the *situation*, not the *moment*: the same room with the
same people, the same executable affordances, and the same displayed public
state always derives the same hash, while walking back and forth through an
unchanged room replays it. Every input a hidden or numeric value could churn
stays out — the anti-oracle rule — so cache-miss patterns leak at most the
public relationship tier, never the affinity number.

This module owns the read-only public-state views (the displayed objective
identity, the public tier labels), the pure ``fingerprint`` combiner, and the
shared exploration situation derivation ``derive_exploration_situation``. The
trigger service (``server.option_proposal_service``) and the presentation
context factory both consume that one derivation, so scheduling and
presentation can never drift on what names the situation; the eligibility
digest and the canonical JSON serializer live in ``affordances.py`` so the
vocabulary, the digest, and the ladder comparison share one serialization.
This module MUST NOT import ``server.option_proposal_service`` or ``world.ai``;
everything here is read-only and none of it mutates state.
"""

import hashlib
from typing import Any, Iterable

from web.webclient.presentation.affordances import canonical_json

__all__ = [
    "derive_exploration_situation",
    "displayed_objective_identity",
    "fingerprint",
    "public_state_digest",
    "public_tier_labels",
]


def displayed_objective_identity(actor: Any) -> tuple[tuple[str, int, str], ...]:
    """The sorted ``(quest_id, stage_index, objective_summary)`` tuples the
    quest view renders for ``actor``'s held objectives.

    Read-only over the quest log: the same records, definition registry, and
    ``describe_objective`` line the ``services`` panel's quest rows use, minus
    the hidden fields (stage progress counters, thresholds, deadlines) that the
    view never turns over per progress. A malformed quest log (which renders
    no quest rows at all) yields the empty tuple, and a row whose definition or
    stage no longer resolves is skipped — partial progress toward the current
    objective therefore never changes the identity.
    """
    from world.quests.describe import QuestDescribeError, describe_objective
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY
    from world.quests.runtime import QuestDataError, read_records
    from world.rules.service_view import MAX_QUEST_ROWS

    try:
        records = read_records(actor)
    except QuestDataError:
        return ()
    identities: list[tuple[str, int, str]] = []
    for record in records[:MAX_QUEST_ROWS]:
        definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        if definition is None:
            continue
        try:
            stage = definition.stages[record.stage_index]
            identities.append(
                (record.quest_id, record.stage_index, describe_objective(stage.objective))
            )
        except (IndexError, KeyError, QuestDescribeError):
            continue
    return tuple(sorted(identities))


def public_tier_labels(actor: Any, npcs: Iterable[Any]) -> tuple[tuple[int, str], ...]:
    """The sorted ``(npc_id, public tier label)`` pairs toward present NPCs.

    The label is the configured stage name the look flavor already shows the
    player (records resolve from their value; recordless players resolve from
    the default stage), so an affinity change within one tier — and the first
    interaction that creates a record at the default tier — never turns over
    the label, while crossing a tier boundary does. Numeric affinity never
    appears.
    """
    pairs: list[tuple[int, str]] = []
    for npc in npcs:
        handler = getattr(npc, "relations", None)
        label = handler.stage_for(actor).name if handler is not None else ""
        pairs.append((int(npc.pk), label))
    return tuple(sorted(pairs))


def public_state_digest(
    objective_identities: Iterable[tuple[str, int, str]],
    tier_labels: Iterable[tuple[int, str]],
) -> str:
    """Digest of the remaining discrete, public state that changes what one
    should *do*: the displayed objective identity and the public tier labels.

    Deliberately excluded (and never accepted here): narrative tail, look
    commands, time of day, and all raw affinity numbers.
    """
    return hashlib.sha256(
        canonical_json(
            {
                "objectives": [list(identity) for identity in sorted(objective_identities)],
                "tiers": [list(pair) for pair in sorted(tier_labels)],
            }
        ).encode("utf-8")
    ).hexdigest()


def fingerprint(
    room_key: str,
    npc_ids: Iterable[int],
    monster_ids: Iterable[int],
    eligible_affordance_digest: str,
    public_state_digest_value: str,
) -> str:
    """One stable SHA-256 over the whole situation.

    ``room_key`` is the room's canonical identity; the two identity lists are
    sorted on entry (callers may pass them in any order); the two digests are
    the shared eligibility digest of the canonical eligible-affordance list
    and the public-state digest. Composing through the shared canonical JSON
    keeps every component unambiguous and order-stable.
    """
    return hashlib.sha256(
        canonical_json(
            [
                str(room_key),
                [int(value) for value in sorted(npc_ids)],
                [int(value) for value in sorted(monster_ids)],
                str(eligible_affordance_digest),
                str(public_state_digest_value),
            ]
        ).encode("utf-8")
    ).hexdigest()


def derive_exploration_situation(
    actor: Any,
) -> "tuple[str, Any, Any, list[Any], list[Any], tuple] | None":
    """Derive ``(fingerprint, vocab, eligible, npcs, monsters, objectives)``
    for the actor's current exploration situation, or ``None`` when no room
    can name the situation.

    This is the single read-only derivation scheduling and presentation both
    use: the trigger service schedules from it and the presentation-context
    factory records its fingerprint, so the two can never drift on what names
    the situation. Every import is function-local (this module stays cold
    importable and never reaches for ``server.option_proposal_service`` or
    ``world.ai``); nothing here mutates state.
    """
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from web.webclient.actions.node_ids import node_id_for_location
    from web.webclient.presentation.affordances import (
        eligible_affordance_digest,
        exploration_affordances,
        in_exploration_mode,
        suggestible_candidates,
    )

    if not in_exploration_mode(actor):
        return None
    location = getattr(actor, "location", None)
    if location is None:
        return None
    room_key = node_id_for_location(location)
    if room_key is None:
        try:
            room_key = "room:%d" % int(location.id)
        except Exception:
            return None

    npcs: list[Any] = []
    monsters: list[Any] = []
    actor_id = getattr(actor, "pk", None)
    for occupant in list(getattr(location, "contents", ()) or ()):
        if getattr(occupant, "pk", None) == actor_id:
            continue
        if isinstance(occupant, Monster):
            monsters.append(occupant)
        elif isinstance(occupant, NPC):
            npcs.append(occupant)
    npcs.sort(key=lambda entity: int(entity.pk))
    monsters.sort(key=lambda entity: int(entity.pk))

    vocab = exploration_affordances(actor)
    eligible = suggestible_candidates(vocab, actor=actor)
    objectives = displayed_objective_identity(actor)
    tiers = public_tier_labels(actor, npcs)
    digest_value = fingerprint(
        room_key,
        (int(entity.pk) for entity in npcs),
        (int(entity.pk) for entity in monsters),
        eligible_affordance_digest(eligible),
        public_state_digest(objectives, tiers),
    )
    return digest_value, vocab, eligible, npcs, monsters, objectives
