"""Predicate evaluation, the event-effect planner, and the guild grants.

The event-effect planner (``title_event_effect_planner``) evaluates the
registry's pending predicates against a committed action's ``EventLog`` and
persistent reads, staging fixed-title grants into the triggering action's own
transaction; guild rank grants ride their rank-change transactions instead
(``register_adventurer`` / ``settle_exam_outcome``). This module never writes
outside a caller's transaction.
"""

from collections.abc import Mapping
from typing import Any

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import FIXED_TITLE_REGISTRY, TitlePredicateFamily
from world.rules.clock import get_world_clock
from world.rules.progression import skill_proficiency_level
from world.rules.titles.state import (
    _FIXED_KIND,
    _LINEAGE_CROWN_CAP,
    TitleDataError,
    bank_epithet,
    bank_fixed,
    fixed_display_name,
    read_title_state,
)
# ---------------------------------------------------------------------------
# Predicate evaluation and the event-effect planner.
# ---------------------------------------------------------------------------


def _owned_skill_keys(entity: Any) -> frozenset[str]:
    """No-create ownership read mirroring the shipped handler fold.

    Foreign-state reads fail closed with ``TitleDataError`` on malformed
    storage; they never leak an ``AttributeError``/``TypeError`` into the
    action pipeline.
    """
    try:
        return frozenset(entity.skills.owned_keys())
    except TitleDataError:
        raise
    except Exception:
        raw = entity.db.skills or {}
        if not isinstance(raw, Mapping):
            raise TitleDataError("skills state is not a mapping") from None
        try:
            owned = list(raw.get("active") or ()) + list(raw.get("passive") or ())
        except TypeError:
            raise TitleDataError("skills state is malformed") from None
        from world.skills.handler import INNATE_SKILL_ORDER

        return frozenset([*owned, *INNATE_SKILL_ORDER])


def _experience_type_members(entity: Any) -> frozenset[str]:
    """No-create read of the stored sexual experience types (append-only set)."""
    value = entity.attributes.get(
        "experience_types", default=frozenset(), category="sexual_state"
    )
    if value is None:
        return frozenset()
    try:
        return frozenset(value)
    except TypeError:
        raise TitleDataError("experience_types is not a set-like value")


def _sexual_counter_value(entity: Any, counter: str) -> int:
    """Read one lifetime sexual counter without materializing the handler.

    Mirrors ``status_query``'s no-create discipline: an unmaterialized state
    means every counter is zero (what the shipped ``SexualState`` assumes), a
    materialized record stores each counter as a trait record whose ``current``
    wins over ``base``, and a present-but-malformed entry fails closed.
    """
    value = entity.attributes.get("sexual_traits", default=None, category="traits")
    if value is None:
        return 0
    if not isinstance(value, Mapping):
        raise TitleDataError("sexual_traits is not a mapping")
    entry = value.get(counter)
    if entry is None:
        return 0
    if not isinstance(entry, Mapping):
        raise TitleDataError(f"sexual counter {counter!r} is malformed")
    raw = entry.get("current", entry.get("base"))
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise TitleDataError(f"sexual counter {counter!r} is malformed")
    return raw


def _quest_completed(entity: Any, quest_key: str) -> bool:
    from world.quests.runtime import QuestDataError, QuestState, read_records

    try:
        records = read_records(entity)
    except (QuestDataError, ValueError):
        return False
    return any(
        record.definition_key == quest_key
        and record.state is QuestState.COMPLETED
        for record in records
    )


def _event_defeats_tier(event_log: Any, monster_tier: str) -> bool:
    return any(
        entry.kind == "target_defeated"
        and entry.data.get("monster_tier") == monster_tier
        for entry in event_log.entries
    )


def _church_skills_redeemed_count(entity: Any) -> int:
    """Read the count of redeemed church skills without materializing state."""
    from world.rules.church import ChurchLedgerError, redeemed_keys

    try:
        return len(redeemed_keys(entity))
    except (ChurchLedgerError, AttributeError, TypeError, ValueError):
        raise TitleDataError("church ledger state is malformed") from None


def predicate_satisfied(
    entity: Any,
    event_log: Any,
    predicate: Any,
) -> bool:
    """Evaluate one registry predicate against the actor and the action log.

    Deterministic; reads persistent state through no-create helpers, never
    writes. ``guild_rank_reached`` is evaluated from the current rank (the
    transactional grants make it a dedupe no-op in practice),
    ``first_kill_tier`` from the current action's ``target_defeated`` entries
    (key idempotency makes the first qualifying kill the granting one), and
    the remaining families from current persistent state.
    """
    family = predicate.family
    if family is TitlePredicateFamily.GUILD_RANK_REACHED:
        return getattr(entity, "guild_rank", None) == predicate.guild_rank
    if family is TitlePredicateFamily.FIRST_KILL_TIER:
        return _event_defeats_tier(event_log, predicate.monster_tier)
    if family is TitlePredicateFamily.MASTERY_OWNED:
        return f"{predicate.element}_mastery" in _owned_skill_keys(entity)
    if family is TitlePredicateFamily.QUEST_COMPLETED:
        return _quest_completed(entity, predicate.quest_key)
    if family is TitlePredicateFamily.SEXUAL_EXPERIENCE:
        return predicate.experience_type in _experience_type_members(entity)
    if family is TitlePredicateFamily.COUNTER_THRESHOLD:
        return _sexual_counter_value(entity, predicate.counter) >= predicate.threshold
    if family is TitlePredicateFamily.CHURCH_SKILLS_REDEEMED:
        return _church_skills_redeemed_count(entity) >= predicate.threshold
    if family is TitlePredicateFamily.LINEAGE_COMPLETE:
        if predicate.root_skill_key not in _owned_skill_keys(entity):
            return False
        try:
            level = skill_proficiency_level(entity, predicate.root_skill_key)
        except (AttributeError, TypeError, ValueError):
            raise TitleDataError("skill proficiency state is malformed") from None
        return level >= _LINEAGE_CROWN_CAP
    return False


def title_event_effect_planner(request: Any, event_log: Any) -> list[Any]:
    """Stage pending fixed-title grants derived from one successful action.

    Evaluates every registry row whose key is not yet banked and whose
    predicate is satisfied, staging one ``PendingEffect`` per grant carrying a
    ``notify`` line so ``ActionResolver.resolve`` surfaces the OOB grant toast
    only after the commit. Malformed title state on the actor fails closed by
    staging nothing, and a predicate that trips over another subsystem's
    corrupted storage skips only its own row — a title lookup must never
    reject an otherwise valid player action. The strict ``read_title_state``
    still guards every mutator and command.
    """
    from world.rules.action import PendingEffect

    actor = request.actor
    from typeclasses.characters import PlayerCharacter

    if not isinstance(actor, PlayerCharacter):
        return []
    try:
        collection, _ = read_title_state(actor)
    except TitleDataError:
        return []
    owned = {entry["key"] for entry in collection if entry["kind"] == _FIXED_KIND}
    pending: list[Any] = []
    for definition in FIXED_TITLE_REGISTRY.values():
        if definition.key in owned:
            continue
        try:
            satisfied = predicate_satisfied(actor, event_log, definition.predicate)
        except (TitleDataError, AttributeError, TypeError, ValueError):
            # A predicate reading some other subsystem's corrupted state must
            # never reject the player's action: that row simply grants nothing.
            # The strict ``read_title_state`` still guards every mutator and
            # the title command.
            continue
        if not satisfied:
            continue
        tick = get_world_clock().tick
        key = definition.key
        display = definition.display_name_zh
        notify = f"獲得稱號：{display}"

        def _apply(actor=actor, key=key, tick=tick) -> None:
            bank_fixed(actor, key, tick)

        pending.append(
            PendingEffect(
                actor,
                f"title_granted|{key}",
                frozenset({"titles"}),
                _apply,
                notify=notify,
            )
        )
    return pending


def register_title_planner() -> None:
    """Register the title event-effect planner idempotently (startup seam)."""
    from world.rules.action import register_event_effect_planner

    register_event_effect_planner("title", title_event_effect_planner)


# ---------------------------------------------------------------------------
# Guild title grants (D3/D8 §6.5).
#
# Registration grants the F-rank fixed title only; the starter epithet moved
# to the claim path (``grant_first_quest_epithet``, quest-reward-settlement).
# ---------------------------------------------------------------------------


def grant_rank_title(actor: Any, rank: str) -> tuple[str, ...]:
    """Bank the rank's paired fixed title; returns grant notification lines.

    Called inside the rank-change transaction (F registration and PASS exam
    promotion). New grants return their OOB notification line; repeats return
    nothing (dedupe).
    """
    definition = GUILD_RANK_REGISTRY.get(rank)
    if definition is None:
        return ()
    title_key = definition.title_key
    display = fixed_display_name(title_key)
    tick = get_world_clock().tick
    if bank_fixed(actor, title_key, tick):
        return (f"獲得稱號：{display}",)
    return ()


def grant_first_quest_epithet(actor: Any) -> tuple[str, ...]:
    """Bank the starter epithet at the actor's first guild reward claim.

    Called inside ``turn_in_quest``'s claim transaction
    (quest-reward-settlement). A real bank returns its OOB notification line
    and auto-equips an empty epithet slot through the regular ``bank_epithet``
    writer; a duplicate display is a silent no-op returning nothing, so any
    replayed or repeated invocation is inert.
    """
    from world.lore.titles import STARTER_EPITHET

    tick = get_world_clock().tick
    if bank_epithet(
        actor, STARTER_EPITHET.display, STARTER_EPITHET.origin_basis, tick
    ):
        return (f"獲得異名：{STARTER_EPITHET.display}",)
    return ()

