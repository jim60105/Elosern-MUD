"""Deterministic title storage, composition, equip surface, and grants.

Two kinds of titles live on a character: fixed titles (registry-driven,
append-only) and epithets (banked entries, adopted by the nomination system;
``db.title_collection`` holds entries identified by ``(kind, key | display)``;
``db.title_equipped`` holds the two slot identifiers. Every reader and mutator
passes through the single strict ``read_title_state`` parser: missing
attributes read as the defaults, present-but-malformed state raises
``TitleDataError`` (fail closed), and the D8 slot-non-empty invariant is
asserted on every read.

The only delete path in the title surface is ``remove_epithet`` — the
two-gated, two-step epithet removal (change H, title-system D5 §8). It deletes
exactly one epithet collection entry, never a fixed entry and never an
equipped-identifier list, and leaves the equipment slots byte-identical; the
D8 invariant stays structurally unbreakable. Fixed titles have no removal
path, and no module-level callable in this file other than ``remove_epithet``
deletes a title entry (the structural-absence boundary test guards this).

The event-effect planner (``title_event_effect_planner``) evaluates the
registry's pending predicates against a committed action's ``EventLog`` and
persistent reads, staging fixed-title grants into the triggering action's own
transaction; guild rank grants ride their rank-change transactions instead
(``register_adventurer`` / ``settle_exam_outcome``). This module never writes
outside a caller's transaction.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import (
    FIXED_TITLE_REGISTRY,
    NOMINATION_COOLDOWN_DAYS,
    FixedTitleDef,
    TitlePredicateFamily,
)
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.event_log import EventEntry, EventLog
from world.rules.progression import skill_proficiency_level
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
)

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

# Epithet nomination (change G, title-system D4 §7). The pending ballot is a
# plain list of ``{"display", "basis"}`` mappings (1..3, never expiring); the
# decline log is a bounded newest-first list of ``{"tick", "displays"}``
# records — the single durable source for both the day-boundary cooldown and
# the Director's softly-learned "recently declined" digest (no programmatic
# blacklist: the digest is prompt context only, never a filter rule).
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
PENDING_BALLOT_KEY = "pending_title_ballot"
DECLINED_LOG_KEY = "title_nomination_declines"
MAX_BALLOT_CANDIDATES = 3
MAX_DECLINE_RECORDS = 3
# Epithet removal (change H, title-system D5 §8). The bounded newest-first
# removal log is the durable Director-facing feed mirroring the decline log:
# ``{tick, display}`` records the nomination prompt digests as soft-learning
# context (prompt context only, never a filter rule — the removed name is
# renominatable through the live-collection filter).
REMOVALS_LOG_KEY = "title_epithet_removals"
MAX_REMOVAL_RECORDS = 3
# Wire bound shared by the closed AI schema (overlong basis voids the round)
# and the WebClient ballot panel validator (mirrored constant).
BALLOT_BASIS_MAX_CHARS = 80

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


# ---------------------------------------------------------------------------
# Epithet nomination: ballot reads and the rules-layer writers (D4, change G).
# ---------------------------------------------------------------------------
# The ONLY ballot writers are ``persist_nomination_ballot``,
# ``accept_epithet``, and ``decline_epithet_ballot``. The ``world/ai`` layer
# proposes filtered candidates and never touches an attribute; the server-
# side composition-root service schedules the call and hands survivors here
# (single-writer boundary, design §14).


class TitleBallotReason(StrEnum):
    """Stable ballot-answer rejection codes (design §13 error table)."""

    NO_PENDING_BALLOT = "title_no_pending_ballot"
    BALLOT_INDEX_OUT_OF_RANGE = "title_ballot_index_out_of_range"


class TitleBallotError(ValueError):
    """A ballot answer hit a stable reason; no state changed."""

    def __init__(self, reason: TitleBallotReason, detail: str | None = None) -> None:
        super().__init__(detail or reason.value)
        self.reason = reason


def _parse_ballot_entry(entry: Any, index: int) -> dict[str, Any]:
    label = f"pending_title_ballot[{index}]"
    if not isinstance(entry, Mapping):
        raise TitleDataError(f"{label} must be a mapping")
    if set(entry) != {"display", "basis"}:
        raise TitleDataError(f"{label} must hold exactly display/basis")
    display = _require_identifier(entry["display"], f"{label} display")
    basis = _require_identifier(entry["basis"], f"{label} basis")
    if len(display) > MAX_EPITHET_DISPLAY_CODE_POINTS:
        raise TitleDataError(
            f"{label} display exceeds {MAX_EPITHET_DISPLAY_CODE_POINTS} code points"
        )
    if len(basis) > BALLOT_BASIS_MAX_CHARS:
        raise TitleDataError(f"{label} basis exceeds {BALLOT_BASIS_MAX_CHARS}")
    return {"display": display, "basis": basis}


def read_pending_ballot(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of ``pending_title_ballot``; absent or empty reads ``()``.

    Present-but-malformed state raises ``TitleDataError`` (fail closed), the
    same discipline as ``read_title_state``. A stored ballot never expires:
    there is no time-based transition anywhere on this face.
    """
    raw = entity.attributes.get(PENDING_BALLOT_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("pending_title_ballot must be a list")
    if len(raw) > MAX_BALLOT_CANDIDATES:
        raise TitleDataError(
            f"pending_title_ballot holds more than {MAX_BALLOT_CANDIDATES} entries"
        )
    return tuple(_parse_ballot_entry(entry, index) for index, entry in enumerate(raw))


def safe_pending_ballot(entity: Any) -> tuple[dict[str, Any], ...]:
    """Presentation-facing ballot read that degrades to ``()`` on bad state."""
    try:
        return read_pending_ballot(entity)
    except TitleDataError:
        return ()


def decline_records(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of the bounded decline log (newest-first storage order)."""
    raw = entity.attributes.get(DECLINED_LOG_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("title_nomination_declines must be a list")
    if len(raw) > MAX_DECLINE_RECORDS:
        raise TitleDataError(
            f"title_nomination_declines exceeds the {MAX_DECLINE_RECORDS}-record cap"
        )
    records: list[dict[str, Any]] = []
    for index, record in enumerate(raw):
        label = f"title_nomination_declines[{index}]"
        if not isinstance(record, Mapping) or set(record) != {"tick", "displays"}:
            raise TitleDataError(f"{label} must hold exactly tick/displays")
        tick = _require_tick(record["tick"], f"{label} tick")
        displays = record["displays"]
        if (
            not isinstance(displays, Sequence)
            or isinstance(displays, (str, bytes))
            or not 1 <= len(displays) <= MAX_BALLOT_CANDIDATES
        ):
            raise TitleDataError(
                f"{label} displays must be a 1..{MAX_BALLOT_CANDIDATES} list"
            )
        items = tuple(
            _require_identifier(display, f"{label} display") for display in displays
        )
        records.append({"tick": tick, "displays": items})
    return tuple(records)


def nomination_cooldown_active(entity: Any, now_tick: int | None = None) -> bool:
    """Whether the decline-derived cooldown still suppresses nomination.

    Cooldown is derived from the newest decline record: it is active while
    fewer than ``NOMINATION_COOLDOWN_DAYS`` day boundaries have passed since
    the decline (same day and the next day suppressed; nominations resume on
    the second boundary). Accepting a ballot never records a decline, so an
    accepted ballot never starts a cooldown.
    """
    records = decline_records(entity)
    if not records:
        return False
    tick = get_world_clock().tick if now_tick is None else now_tick
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise TitleDataError("now_tick must be a non-negative integer")
    declined_day = max(record["tick"] for record in records) // _DAY_SECONDS
    return tick // _DAY_SECONDS - declined_day < NOMINATION_COOLDOWN_DAYS


def nomination_suppressed(entity: Any, now_tick: int | None = None) -> bool:
    """Single-ballot + cooldown suppression, fail-closed on malformed state.

    A corrupt nomination face suppresses the writer silently (the ballot was
    never ours to guess) while presentation still degrades to an empty menu
    through ``safe_pending_ballot``.
    """
    try:
        if read_pending_ballot(entity):
            return True
        return nomination_cooldown_active(entity, now_tick)
    except TitleDataError:
        return True


def owned_epithet_displays(entity: Any) -> frozenset[str]:
    """Live collection epithet displays for the collision filter.

    Deleted names are absent here by construction, so they are renominable
    (D5 collision semantics; no blacklist exists anywhere).
    """
    return frozenset(
        entry["display"] for entry in banked_epithets(entity)
    )


def declined_digest(entity: Any, limit: int = MAX_DECLINE_RECORDS) -> tuple[str, ...]:
    """Distinct recent decline-log displays for the prompt's soft-learning
    digest (newest record first). Malformed history degrades to empty; this
    is prompt context only and never a filter rule.
    """
    try:
        records = decline_records(entity)
    except TitleDataError:
        return ()
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("declined_digest limit must be a non-negative int")
    seen: set[str] = set()
    digest: list[str] = []
    for record in records[:limit]:
        for display in record["displays"]:
            if display not in seen:
                seen.add(display)
                digest.append(display)
    return tuple(digest)


def persist_nomination_ballot(entity: Any, candidates: Any) -> bool:
    """The rules-layer-only ballot persist (DG2): re-check suppression after
    the proposal returns, then persist in one all-or-nothing step.

    Validates the wire shape (1..3 ``{display, basis}`` entries within the
    storage caps); anything invalid, a suppressed entity, or a failed write
    returns ``False`` and leaves no partial proposal.
    """
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return False
    if not 1 <= len(candidates) <= MAX_BALLOT_CANDIDATES:
        return False
    normalized: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        try:
            normalized.append(_parse_ballot_entry(candidate, index))
        except TitleDataError:
            return False
    now_tick = get_world_clock().tick
    if nomination_suppressed(entity, now_tick):
        return False
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            entity.attributes.add(PENDING_BALLOT_KEY, normalized)
    except Exception:
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        return False
    return True


def accept_epithet(entity: Any, index: int) -> tuple[str, bool]:
    """Adopt the 1-based ballot candidate (D4 §7.2-6).

    One atomic, snapshot-registered transaction banks the entry
    (display, ``origin_quote = basis``, granted_tick), auto-equips the
    epithet slot only when empty (bank_epithet's D8 discipline), and clears
    the ballot. Returns ``(display, newly_banked)``; ``newly_banked`` is
    ``False`` when an identical display entered the collection between the
    ballot and the answer (the bank dedupes; the ballot is consumed either
    way). Stable ``TitleBallotError`` reasons change nothing.
    """
    ballot = read_pending_ballot(entity)
    if not ballot:
        raise TitleBallotError(TitleBallotReason.NO_PENDING_BALLOT)
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 1 <= index <= len(ballot)
    ):
        raise TitleBallotError(TitleBallotReason.BALLOT_INDEX_OUT_OF_RANGE)
    entry = ballot[index - 1]
    tick = get_world_clock().tick
    collection_snapshot = attribute_snapshot(entity, TITLE_COLLECTION_KEY)
    equipped_snapshot = attribute_snapshot(entity, TITLE_EQUIPPED_KEY)
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            banked = bank_epithet(entity, entry["display"], entry["basis"], tick)
            entity.attributes.remove(PENDING_BALLOT_KEY)
    except Exception:
        restore_attribute_best_effort(
            entity, TITLE_COLLECTION_KEY, collection_snapshot
        )
        restore_attribute_best_effort(
            entity, TITLE_EQUIPPED_KEY, equipped_snapshot
        )
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        raise
    return entry["display"], banked


def decline_epithet_ballot(entity: Any) -> EventLog:
    """Discard the batch, start the cooldown, and record what was declined.

    The declined displays persist to the bounded decline log — the single
    durable feed the nomination prompt digests so the Director's future
    summaries see what the player rejected (soft learning; there is no
    programmatic blacklist) — and are returned as a
    ``title_epithet_declined`` EventLog for the answering surface to render
    and for the EventLog consumers. Raises ``TitleBallotError`` when no
    ballot is pending; malformed decline history raises ``TitleDataError``
    and changes NOTHING (fail-closed — the corrupt cooldown source is never
    silently overwritten by a player answer).
    """
    ballot = read_pending_ballot(entity)
    if not ballot:
        raise TitleBallotError(TitleBallotReason.NO_PENDING_BALLOT)
    displays = tuple(entry["display"] for entry in ballot)
    tick = get_world_clock().tick
    record = {"tick": tick, "displays": list(displays)}
    history = [dict(entry) for entry in decline_records(entity)]
    log_snapshot = attribute_snapshot(entity, DECLINED_LOG_KEY)
    ballot_snapshot = attribute_snapshot(entity, PENDING_BALLOT_KEY)
    try:
        with transaction.atomic():
            entity.attributes.add(
                DECLINED_LOG_KEY, [record, *history][:MAX_DECLINE_RECORDS]
            )
            entity.attributes.remove(PENDING_BALLOT_KEY)
    except Exception:
        restore_attribute_best_effort(entity, DECLINED_LOG_KEY, log_snapshot)
        restore_attribute_best_effort(
            entity, PENDING_BALLOT_KEY, ballot_snapshot
        )
        raise
    entry = EventEntry(
        kind="title_epithet_declined",
        actor=str(entity.key),
        target=None,
        data={"displays": list(displays), "joined": "、".join(displays)},
        text_template="{actor}拒絕了異名提名：{data[joined]}",
    )
    return EventLog(
        actor=str(entity.key),
        skill_key="title",
        targets=(),
        entries=(entry,),
        time_cost_seconds=0,
    )


# ---------------------------------------------------------------------------
# Epithet removal (change H, title-system D5 §8) — the ONLY delete path.
# ---------------------------------------------------------------------------


class TitleRemovalReason(StrEnum):
    """Stable removal-gate rejection codes (design §13 error table)."""

    TARGET_UNKNOWN = "title_removal_target_unknown"
    LAST_EPITHET = "title_last_epithet"
    EQUIPPED_UNREMOVABLE = "title_equipped_unremovable"


class TitleRemovalError(ValueError):
    """A removal attempt hit a stable gate; no state changed."""

    def __init__(self, reason: TitleRemovalReason, detail: str | None = None) -> None:
        super().__init__(detail or reason.value)
        self.reason = reason


def epithet_removal_gate(
    entity: Any, display: Any
) -> TitleRemovalReason | None:
    """Pure two-gate verdict; ``None`` means the removal may proceed.

    Gate precedence (design DH1): unknown/wrong-kind first, then
    ``LAST_EPITHET``, then ``EQUIPPED_UNREMOVABLE`` — a sole epithet is
    necessarily equipped (D8), and the spec scenario demands LAST for that
    row, so LAST is evaluated before EQUIPPED. Malformed title state
    propagates ``TitleDataError`` (fail closed).
    """
    if isinstance(display, bool) or not isinstance(display, str) or not display:
        return TitleRemovalReason.TARGET_UNKNOWN
    collection, equipped = read_title_state(entity)
    epithets = [entry for entry in collection if entry["kind"] == _EPITHET_KIND]
    if not any(entry["display"] == display for entry in epithets):
        return TitleRemovalReason.TARGET_UNKNOWN
    if len(epithets) <= 1:
        return TitleRemovalReason.LAST_EPITHET
    if display == equipped["epithet"]:
        return TitleRemovalReason.EQUIPPED_UNREMOVABLE
    return None


def removal_records(entity: Any) -> tuple[dict[str, Any], ...]:
    """Strict read of the bounded removal log (newest-first storage order)."""
    raw = entity.attributes.get(REMOVALS_LOG_KEY, default=None)
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TitleDataError("title_epithet_removals must be a list")
    if len(raw) > MAX_REMOVAL_RECORDS:
        raise TitleDataError(
            f"title_epithet_removals exceeds the {MAX_REMOVAL_RECORDS}-record cap"
        )
    records: list[dict[str, Any]] = []
    for index, record in enumerate(raw):
        label = f"title_epithet_removals[{index}]"
        if not isinstance(record, Mapping) or set(record) != {"tick", "display"}:
            raise TitleDataError(f"{label} must hold exactly tick/display")
        records.append(
            {
                "tick": _require_tick(record["tick"], f"{label} tick"),
                "display": _require_identifier(
                    record["display"], f"{label} display"
                ),
            }
        )
    return tuple(records)


def removal_digest(
    entity: Any, limit: int = MAX_REMOVAL_RECORDS
) -> tuple[str, ...]:
    """Distinct recent removal-log displays for the nomination prompt's
    soft-learning digest (newest record first). Malformed history degrades to
    empty; this is prompt context only and never a filter rule — a removed
    name stays renominatable through the live-collection collision filter.
    """
    try:
        records = removal_records(entity)
    except TitleDataError:
        return ()
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("removal_digest limit must be a non-negative int")
    seen: set[str] = set()
    digest: list[str] = []
    for record in records[:limit]:
        display = record["display"]
        if display not in seen:
            seen.add(display)
            digest.append(display)
    return tuple(digest)


def remove_epithet(entity: Any, display: Any) -> EventLog:
    """Delete exactly one banked epithet; the ONLY delete path in the surface.

    One gate pass executes (answering surfaces re-validate at execution
    time): a gated target raises ``TitleRemovalError`` and a malformed state
    raises ``TitleDataError``, each with NOTHING changed. On success the
    collection shrinks by exactly the one entry, the durable bounded removal
    log gains a newest-first ``{tick, display}`` record in the same
    transaction, and the equipment slots are written back unchanged — a
    removal can never empty a slot or orphan an identifier, so the D8
    invariant is structurally unbreakable here. Returns a renderable
    ``title_epithet_removed`` EventLog (``decline_epithet_ballot`` shape)
    for the answering surface and the EventLog consumers.
    """
    reason = epithet_removal_gate(entity, display)
    if reason is not None:
        raise TitleRemovalError(reason)
    tick = get_world_clock().tick
    collection, equipped = read_title_state(entity)
    new_collection = [
        entry
        for entry in collection
        if not (entry["kind"] == _EPITHET_KIND and entry["display"] == display)
    ]
    record = {"tick": tick, "display": display}
    history = [dict(entry) for entry in removal_records(entity)]
    collection_snapshot = attribute_snapshot(entity, TITLE_COLLECTION_KEY)
    equipped_snapshot = attribute_snapshot(entity, TITLE_EQUIPPED_KEY)
    removals_snapshot = attribute_snapshot(entity, REMOVALS_LOG_KEY)
    try:
        with transaction.atomic():
            _write_title_state(entity, new_collection, equipped)
            entity.attributes.add(
                REMOVALS_LOG_KEY, [record, *history][:MAX_REMOVAL_RECORDS]
            )
    except Exception:
        restore_attribute_best_effort(
            entity, TITLE_COLLECTION_KEY, collection_snapshot
        )
        restore_attribute_best_effort(
            entity, TITLE_EQUIPPED_KEY, equipped_snapshot
        )
        restore_attribute_best_effort(
            entity, REMOVALS_LOG_KEY, removals_snapshot
        )
        raise
    entry = EventEntry(
        kind="title_epithet_removed",
        actor=str(entity.key),
        target=None,
        data={"display": display, "tick": tick},
        text_template="{actor}放下了異名：{data[display]}",
    )
    return EventLog(
        actor=str(entity.key),
        skill_key="title",
        targets=(),
        entries=(entry,),
        time_cost_seconds=0,
    )