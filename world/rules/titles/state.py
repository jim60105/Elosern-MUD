"""Title storage state: keys/caps, the strict parser, and the equip surface.

Two kinds of titles live on a character: fixed titles (registry-driven,
append-only) and epithets (banked entries, adopted by the nomination system;
``db.title_collection`` holds entries identified by ``(kind, key | display)``;
``db.title_equipped`` holds the two slot identifiers. Every reader and mutator
passes through the single strict ``read_title_state`` parser: missing
attributes read as the defaults, present-but-malformed state raises
``TitleDataError`` (fail closed), and the D8 slot-non-empty invariant is
asserted on every read.

This module is the canonical home of the storage keys, the wire caps, and the
state read/write surface shared by the planner, ballot, and removal
submodules.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from world.lore.titles import FIXED_TITLE_REGISTRY
from world.rules.clock import CLOCK_YAML
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

