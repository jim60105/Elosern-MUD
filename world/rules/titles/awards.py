"""Occurrence-linked automatic built-in-title award results.

OpenSpec change: unify-automatic-title-award-results
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5.2
"""

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import FIXED_TITLE_REGISTRY, STARTER_EPITHET, TitlePredicateFamily
from world.rules.clock import get_world_clock
from world.rules.titles.state import (
    _EPITHET_KIND,
    _FIXED_KIND,
    TitleDataError,
    bank_epithet,
    bank_fixed,
    fixed_display_name,
    read_title_state,
)

AwardKind = Literal["fixed", "epithet"]


@dataclass(frozen=True)
class AutomaticTitleAward:
    """A deterministic record of one newly granted built-in title."""

    source_id: str
    recipient_id: str
    kind: AwardKind
    title_id: str
    granted_tick: int
    display_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "recipient_id": self.recipient_id,
            "kind": self.kind,
            "title_id": self.title_id,
            "granted_tick": int(self.granted_tick),
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutomaticTitleAward":
        return cls(
            source_id=str(data["source_id"]),
            recipient_id=str(data["recipient_id"]),
            kind=data["kind"],
            title_id=str(data["title_id"]),
            granted_tick=int(data["granted_tick"]),
            display_name=str(data["display_name"]),
        )


def _resolve_recipient_id(entity: Any) -> str:
    """Derive the durable, persistent recipient identity."""
    pk = getattr(entity, "pk", None)
    if pk is not None:
        return str(pk)
    # Evennia / Django object without pk or raw string ID
    if hasattr(entity, "id") and entity.id is not None:
        return str(entity.id)
    key = getattr(entity, "key", None)
    if key is not None and str(key).strip():
        return str(key).strip()
    clean = str(entity).strip()
    if clean and clean != "None":
        return clean
    raise TitleDataError(f"Entity {entity!r} has no durable recipient identity")


def award_automatic_title(
    entity: Any,
    *,
    source_id: str,
    kind: str,
    title_id: str,
    tick: int | None = None,
) -> tuple[AutomaticTitleAward | None, str | None]:
    """Bank one automatic built-in title for ``entity`` linked to ``source_id``.

    Returns ``(award_record, notification_line)``. If the title was already
    owned or the recipient identity is invalid, returns ``(None, None)``.
    Player acceptance of generated epithets never enters this path.
    """
    clean_source = str(source_id).strip()
    if not clean_source:
        raise TitleDataError("source_id must not be empty")

    recipient_id = _resolve_recipient_id(entity)
    current_tick = get_world_clock().tick if tick is None else int(tick)

    if kind == _FIXED_KIND:
        key = str(title_id).strip()
        display = fixed_display_name(key)
        if bank_fixed(entity, key, current_tick):
            award = AutomaticTitleAward(
                source_id=clean_source,
                recipient_id=recipient_id,
                kind=_FIXED_KIND,
                title_id=key,
                granted_tick=current_tick,
                display_name=display,
            )
            return award, f"獲得稱號：{display}"
        return None, None

    if kind == _EPITHET_KIND:
        # Authored built-in starter epithet
        display = str(title_id).strip()
        if display == STARTER_EPITHET.display:
            origin_basis = STARTER_EPITHET.origin_basis
        else:
            # Fallback or synthetic starter epithet matching currently loaded registry
            from world.lore import titles as lore_titles

            current_starter = getattr(lore_titles, "STARTER_EPITHET", STARTER_EPITHET)
            if display == current_starter.display:
                origin_basis = current_starter.origin_basis
            else:
                # Custom synthetic built-in test epithet
                origin_basis = "合成事蹟依據。"

        if bank_epithet(entity, display, origin_basis, current_tick):
            award = AutomaticTitleAward(
                source_id=clean_source,
                recipient_id=recipient_id,
                kind=_EPITHET_KIND,
                title_id=display,
                granted_tick=current_tick,
                display_name=display,
            )
            return award, f"獲得異名：{display}"
        return None, None

    raise TitleDataError(f"Unsupported title award kind {kind!r}")


def award_guild_rank_title(
    actor: Any,
    rank: str,
    *,
    source_id: str,
    tick: int | None = None,
) -> tuple[AutomaticTitleAward | None, str | None]:
    """Bank the rank's paired fixed title; returns ``(award, notification_line)``."""
    definition = GUILD_RANK_REGISTRY.get(rank)
    if definition is None:
        return None, None
    return award_automatic_title(
        actor,
        source_id=source_id,
        kind=_FIXED_KIND,
        title_id=definition.title_key,
        tick=tick,
    )


def award_first_quest_epithet(
    actor: Any,
    *,
    source_id: str,
    tick: int | None = None,
) -> tuple[AutomaticTitleAward | None, str | None]:
    """Bank the starter epithet at first guild reward claim."""
    from world.lore.titles import STARTER_EPITHET

    return award_automatic_title(
        actor,
        source_id=source_id,
        kind=_EPITHET_KIND,
        title_id=STARTER_EPITHET.display,
        tick=tick,
    )


def settle_quest_completion_awards(
    entity: Any,
    *,
    source_id: str,
    completed_quest_keys: Iterable[str],
    tick: int | None = None,
) -> tuple[AutomaticTitleAward, ...]:
    """Bank every quest-completed fixed title one completion newly earns.

    The completing quest owner calls this after it applied the new quest state
    and before it writes the immutable completion fact, so every grant is
    finalized under the completion occurrence's own ``source_id`` and its
    results ride that fact's award envelope. Only registry rows whose predicate
    is the ``quest_completed`` family for one of ``completed_quest_keys`` are
    considered, and the existing pure evaluator stays authoritative for
    whether a row is satisfied. Collection membership short-circuits re-grants,
    so a later occurrence that merely encounters an already owned title
    contributes no result. Malformed foreign state skips only its own row,
    mirroring the action-time planner: a title lookup never aborts gameplay.
    """
    from world.rules.titles.planner import predicate_satisfied

    quest_keys = {str(key) for key in completed_quest_keys}
    if not quest_keys:
        return ()
    current_tick = get_world_clock().tick if tick is None else int(tick)
    awards: list[AutomaticTitleAward] = []
    for definition in FIXED_TITLE_REGISTRY.values():
        predicate = definition.predicate
        if predicate.family is not TitlePredicateFamily.QUEST_COMPLETED:
            continue
        if str(predicate.quest_key) not in quest_keys:
            continue
        try:
            satisfied = predicate_satisfied(entity, None, predicate)
        except (TitleDataError, AttributeError, TypeError, ValueError):
            continue
        if not satisfied:
            continue
        try:
            award, _note = award_automatic_title(
                entity,
                source_id=source_id,
                kind=_FIXED_KIND,
                title_id=definition.key,
                tick=current_tick,
            )
        except TitleDataError:
            # Malformed title storage stays fail-closed for the grant only: a
            # corrupted collection must never reject an otherwise valid
            # completion (the strict readers still guard every title surface).
            continue
        if award is not None:
            awards.append(award)
    return tuple(awards)
