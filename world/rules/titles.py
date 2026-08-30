"""Deterministic title storage, composition, equip surface, and grants.

Two kinds of titles live on a character: fixed titles (registry-driven,
append-only) and epithets (banked entries, adopted by the nomination system
later; F only banks them for the starter pair). ``db.title_collection`` holds
entries identified by ``(kind, key | display)``; ``db.title_equipped`` holds
the two slot identifiers. Every reader and mutator passes through the single
strict ``read_title_state`` parser: missing attributes read as the defaults,
present-but-malformed state raises ``TitleDataError`` (fail closed), and the
D8 slot-non-empty invariant is asserted on every read.

The event-effect planner (``title_event_effect_planner``) evaluates the
registry's pending predicates against a committed action's ``EventLog`` and
persistent reads, staging fixed-title grants into the triggering action's own
transaction; guild rank grants ride their rank-change transactions instead
(``register_adventurer`` / ``settle_exam_outcome``). This module never writes
outside a caller's transaction.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import (
    FIXED_TITLE_REGISTRY,
    FixedTitleDef,
    TitlePredicateFamily,
)
from world.rules.clock import get_world_clock
from world.rules.progression import skill_proficiency_level

TITLE_COLLECTION_KEY = "title_collection"
TITLE_EQUIPPED_KEY = "title_equipped"
_FIXED_KIND = "fixed"
_EPITHET_KIND = "epithet"
_FULL_WIDTH_SPACE = "　"

# Wire bound on the composed full title, mirrored by the panel validator
# (``web.webclient.presentation.character.MAX_FULL_TITLE_CODE_POINTS``); the
# status/character producers fail closed past it. Epithet displays carry their
# own storage cap so a legitimate banking write can never compose past it.
MAX_FULL_TITLE_CODE_POINTS = 128
MAX_EPITHET_DISPLAY_CODE_POINTS = 64
# Forward seam: Change C (use-driven-skill-lineage) raises this to the
# registry-derived tree-crown cap (`PROFICIENCY_TIP_CAP` in progression.yaml).
# A lineage root with no satisfying edges is a crown, so 10 is the exact
# crown cap today; no lineage rows are authored in F.
_LINEAGE_CROWN_CAP = 10

# Bounded format for consultation helpers (dialogue identity entries).
MAX_TITLE_ENTRIES = 5


class TitleDataError(ValueError):
    """Title state is absent, malformed, or violates the D8 slot invariant."""


class TitleEquipError(ValueError):
    """An equip target is unbanked, unknown, or the wrong kind."""


def _require_identifier(value: Any, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, str) or not value:
        raise TitleDataError(f"{label} must be a non-empty string")
    return value


def _require_tick(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TitleDataError(f"{label} must be a non-negative integer")
    return value


def read_title_state(entity: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Strictly parse ``title_collection`` and ``title_equipped``.

    Missing attributes read exactly as ``[]`` and ``{"fixed": None,
    "epithet": None}``. Present-but-malformed state raises
    ``TitleDataError`` (fail closed), and the D8 slot-non-empty invariant is
    re-asserted on every read: for each kind, a non-empty collection SHALL
    have the matching slot populated with an identifier the collection
    actually holds. Both attributes are plain (category-less) attributes.
    """
    raw_collection = entity.attributes.get(TITLE_COLLECTION_KEY, default=None)
    raw_equipped = entity.attributes.get(TITLE_EQUIPPED_KEY, default=None)

    if raw_collection is None:
        collection: list[dict[str, Any]] = []
    else:
        # Evennia deserializes stored lists as ``_SaverList`` (a ``Sequence``,
        # not a ``list`` subclass) and stored dicts as ``_SaverDict``.
        if not isinstance(raw_collection, Sequence) or isinstance(
            raw_collection, (str, bytes)
        ):
            raise TitleDataError("title_collection must be a list")
        collection = [
            _parse_collection_entry(entry, index)
            for index, entry in enumerate(raw_collection)
        ]
        fixed_keys = [e["key"] for e in collection if e["kind"] == _FIXED_KIND]
        if len(set(fixed_keys)) != len(fixed_keys):
            raise TitleDataError("title_collection holds a duplicate fixed key")
        displays = [e["display"] for e in collection if e["kind"] == _EPITHET_KIND]
        if len(set(displays)) != len(displays):
            raise TitleDataError("title_collection holds a duplicate epithet display")

    if raw_equipped is None:
        equipped: dict[str, Any] = {"fixed": None, "epithet": None}
    else:
        if not isinstance(raw_equipped, Mapping):
            raise TitleDataError("title_equipped must be a mapping")
        unknown = set(raw_equipped) - {"fixed", "epithet"}
        if unknown:
            raise TitleDataError(
                f"title_equipped has unknown fields {sorted(unknown)}"
            )
        missing = {"fixed", "epithet"} - set(raw_equipped)
        if missing:
            raise TitleDataError(
                f"title_equipped is missing fields {sorted(missing)}"
            )
        equipped = {
            "fixed": _optional_identifier(raw_equipped["fixed"], "fixed slot"),
            "epithet": _optional_identifier(raw_equipped["epithet"], "epithet slot"),
        }

    _assert_slot_invariant(collection, equipped)
    return collection, equipped


def _parse_collection_entry(entry: Any, index: int) -> dict[str, Any]:
    label = f"title_collection[{index}]"
    if not isinstance(entry, Mapping):
        raise TitleDataError(f"{label} must be a mapping")
    kind = entry.get("kind")
    granted_tick = _require_tick(entry.get("granted_tick"), f"{label} granted_tick")
    if kind == _FIXED_KIND:
        if set(entry) != {"kind", "key", "granted_tick"}:
            raise TitleDataError(
                f"{label} fixed entry must carry exactly kind/key/granted_tick"
            )
        return {
            "kind": _FIXED_KIND,
            "key": _require_identifier(entry["key"], f"{label} key"),
            "granted_tick": granted_tick,
        }
    if kind == _EPITHET_KIND:
        if set(entry) != {"kind", "display", "origin_quote", "granted_tick"}:
            raise TitleDataError(
                f"{label} epithet entry must carry exactly "
                "kind/display/origin_quote/granted_tick"
            )
        return {
            "kind": _EPITHET_KIND,
            "display": _require_identifier(entry["display"], f"{label} display"),
            "origin_quote": _require_identifier(
                entry["origin_quote"], f"{label} origin_quote"
            ),
            "granted_tick": granted_tick,
        }
    raise TitleDataError(f"{label} has unknown kind {kind!r}")


def _optional_identifier(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_identifier(value, label)


def _assert_slot_invariant(
    collection: list[dict[str, Any]], equipped: dict[str, Any]
) -> None:
    """D8: for each kind, collection non-empty implies a populated slot."""
    fixed_entries = [e for e in collection if e["kind"] == _FIXED_KIND]
    epithet_entries = [e for e in collection if e["kind"] == _EPITHET_KIND]
    if fixed_entries and equipped["fixed"] is None:
        raise TitleDataError(
            "title_collection holds fixed entries but the fixed slot is empty"
        )
    if epithet_entries and equipped["epithet"] is None:
        raise TitleDataError(
            "title_collection holds epithets but the epithet slot is empty"
        )
    if equipped["fixed"] is not None:
        if not any(
            e["kind"] == _FIXED_KIND and e["key"] == equipped["fixed"]
            for e in collection
        ):
            raise TitleDataError(
                f"title_equipped fixed slot names unbanked key "
                f"{equipped['fixed']!r}"
            )
    if equipped["epithet"] is not None:
        if not any(
            e["kind"] == _EPITHET_KIND and e["display"] == equipped["epithet"]
            for e in collection
        ):
            raise TitleDataError(
                f"title_equipped epithet slot names unbanked display "
                f"{equipped['epithet']!r}"
            )


def _write_title_state(
    entity: Any,
    collection: list[dict[str, Any]],
    equipped: dict[str, Any],
) -> None:
    """Persist both attributes inside the caller's open transaction."""
    _assert_slot_invariant(collection, equipped)
    entity.attributes.add(TITLE_COLLECTION_KEY, collection)
    entity.attributes.add(TITLE_EQUIPPED_KEY, equipped)


def bank_fixed(entity: Any, key: str, tick: int) -> bool:
    """Bank one fixed entry keyed by ``key``; returns whether it was added.

    A duplicate key is a silent no-op. When the fixed slot is empty the new
    entry is auto-equipped in the same write (D8). Runs inside the caller's
    transaction; rollback is the caller's snapshot/restore responsibility.
    """
    _require_tick(tick, "granted_tick")
    _require_identifier(key, "fixed title key")
    if key not in FIXED_TITLE_REGISTRY:
        raise TitleDataError(f"unknown fixed title key {key!r}")
    collection, equipped = read_title_state(entity)
    if any(e["kind"] == _FIXED_KIND and e["key"] == key for e in collection):
        return False
    entry = {"kind": _FIXED_KIND, "key": key, "granted_tick": tick}
    new_collection = [*collection, entry]
    new_equipped = {**equipped, "fixed": equipped["fixed"] if equipped["fixed"] else key}
    _write_title_state(entity, new_collection, new_equipped)
    return True


def bank_epithet(
    entity: Any,
    display: str,
    origin_quote: str,
    tick: int,
) -> bool:
    """Bank one epithet entry; duplicate displays are silent no-ops (D8).

    Auto-equips the epithet slot when empty, mirroring ``bank_fixed``. The
    starter epithet and (later, change G) adopted epithets both arrive here.
    """
    _require_tick(tick, "granted_tick")
    _require_identifier(display, "epithet display")
    _require_identifier(origin_quote, "epithet origin quote")
    if not display.strip() or not origin_quote.strip():
        raise TitleDataError("epithet display and quote must not be blank")
    if len(display) > MAX_EPITHET_DISPLAY_CODE_POINTS:
        raise TitleDataError(
            f"epithet display exceeds {MAX_EPITHET_DISPLAY_CODE_POINTS} code points"
        )
    collection, equipped = read_title_state(entity)
    if any(e["kind"] == _EPITHET_KIND and e["display"] == display for e in collection):
        return False
    entry = {
        "kind": _EPITHET_KIND,
        "display": display,
        "origin_quote": origin_quote,
        "granted_tick": tick,
    }
    new_collection = [*collection, entry]
    new_equipped = {
        **equipped,
        "epithet": equipped["epithet"] if equipped["epithet"] else display,
    }
    _write_title_state(entity, new_collection, new_equipped)
    return True


def compose_title(fixed: str | None, epithet: str | None) -> str:
    """Join the non-empty parts fixed-first with a full-width space.

    Both slots empty returns the empty string; every consumer falls back to
    the character's own name then. No consumer stores the composed copy.
    """
    return _FULL_WIDTH_SPACE.join(part for part in (fixed, epithet) if part)


def fixed_display_name(key: str) -> str:
    """Resolve one fixed key to its registry display name (unregistered → key)."""
    definition = FIXED_TITLE_REGISTRY.get(key)
    if definition is None:
        return key
    return definition.display_name_zh


def compose_full_title(entity: Any) -> str:
    """Compose the live full title from the two slot identifiers."""
    _, equipped = read_title_state(entity)
    fixed = (
        fixed_display_name(equipped["fixed"]) if equipped["fixed"] is not None else None
    )
    return compose_title(fixed, equipped["epithet"])


def safe_full_title(entity: Any) -> str:
    """Presentation-facing compose that degrades to "" on malformed state.

    Rules-layer consumers (grants, commands, codex views) must use the strict
    ``compose_full_title``; narrative edges (look prose, prompt context) use
    this so a corrupted record degrades to the name fallback instead of
    breaking the whole surface.
    """
    try:
        return compose_full_title(entity)
    except TitleDataError:
        return ""


def safe_title_context_entries(
    entity: Any, limit: int = MAX_TITLE_ENTRIES
) -> tuple[dict, ...]:
    """Presentation-facing identity read that degrades to ``()`` on bad state.

    The mirror of :func:`safe_full_title` for the other narrative consumer (the
    NPC dialogue prompt): a corrupted title record omits both sections instead
    of breaking the talk, while rules-layer readers keep the strict
    :func:`title_context_entries`.
    """
    try:
        return title_context_entries(entity, limit=limit)
    except TitleDataError:
        return ()


def equip_fixed(entity: Any, identifier: str) -> str:
    """Equip one banked fixed entry by key or display name (swap-only).

    Accepts only identifiers the collection holds; unknown or unbanked
    targets raise ``TitleEquipError`` without listing candidates. The slot is
    never emptied (there is no unequip path and no ``title clear``).
    """
    collection, equipped = read_title_state(entity)
    match = next(
        (
            entry
            for entry in collection
            if entry["kind"] == _FIXED_KIND
            and (
                entry["key"] == identifier
                or fixed_display_name(entry["key"]) == identifier
            )
        ),
        None,
    )
    if match is None:
        raise TitleEquipError(f"unbanked fixed title {identifier!r}")
    if equipped["fixed"] != match["key"]:
        _write_title_state(entity, collection, {**equipped, "fixed": match["key"]})
    return fixed_display_name(match["key"])


def equip_epithet(entity: Any, display: str) -> str:
    """Equip one banked epithet by display (swap-only; never empties)."""
    collection, equipped = read_title_state(entity)
    match = next(
        (
            entry
            for entry in collection
            if entry["kind"] == _EPITHET_KIND and entry["display"] == display
        ),
        None,
    )
    if match is None:
        raise TitleEquipError(f"unbanked epithet {display!r}")
    if equipped["epithet"] != display:
        _write_title_state(entity, collection, {**equipped, "epithet": display})
    return display


def banked_fixed_keys(entity: Any) -> tuple[str, ...]:
    """Every banked fixed key in collection order (mechanical reads)."""
    collection, _ = read_title_state(entity)
    return tuple(e["key"] for e in collection if e["kind"] == _FIXED_KIND)


def banked_epithets(entity: Any) -> tuple[dict[str, Any], ...]:
    """Every banked epithet entry (display, origin_quote, granted_tick)."""
    collection, _ = read_title_state(entity)
    return tuple(e for e in collection if e["kind"] == _EPITHET_KIND)


def title_context_entries(entity: Any, limit: int = MAX_TITLE_ENTRIES) -> tuple[dict, ...]:
    """The most recent ``limit`` banked epithets as ``{display, basis}``.

    Delivered to NPC dialogue as identity context (design D6: "up to five
    banked entries with their basis quotes when the Director asks for
    identity context"). Deterministic: reverse collection order (most recent
    first), bounded, never live references.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("title_context_entries limit must be a non-negative int")
    return tuple(
        {"display": entry["display"], "basis": entry["origin_quote"]}
        for entry in reversed(banked_epithets(entity)[-limit:])
        if limit
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
# Guild pairing grants (D3/D8 §6.5).
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


def grant_starter_pair(actor: Any) -> tuple[str, ...]:
    """Grant the F-rank title plus the starter epithet (D8 §6.5).

    Both grants ride ``register_adventurer``'s transaction; both auto-equip
    their empty slots, so the onboarding-complete full title is
    「F級冒險者　南門新客」. Re-registration no-ops through the two dedupe
    rules.
    """
    from world.lore.titles import STARTER_EPITHET

    lines = list(grant_rank_title(actor, "F"))
    tick = get_world_clock().tick
    if bank_epithet(
        actor, STARTER_EPITHET.display, STARTER_EPITHET.origin_basis, tick
    ):
        lines.append(f"獲得異名：{STARTER_EPITHET.display}")
    return tuple(lines)