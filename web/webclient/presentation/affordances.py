"""Canonical exploration affordance vocabulary (read-only).

This module owns the shared, read-only affordance rules for a puppeted player
in exploration mode: the frozen discriminated :class:`AffordanceView` contract
(action vs navigation), the eight emitted action codes plus the guild/shop
surfaces, validator-normalized params, the freeform binding-only exception, the
idle baseline, the suggestion-eligibility layer, and the deterministic
``default_cards()`` degradation derivation.

The version-1 ``exploration`` panel presenter and the ``context_actions``
exploration presenter both consume this vocabulary; the v1 panel serializer
keeps its own descriptor shape while delegating every eligibility rule here.
All builders are read-only: nothing here mutates traits, knowledge, dialogue,
quests, inventory, combat sessions, party, or world time.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from web.webclient.actions.exploration_actions import (
    validate_engage_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from web.webclient.actions.node_ids import node_id_for_location
from world.onboarding.guide_dialogue import DIALOGUE_TABLE
from world.rules.dialogue import dialogue_key_for, is_dialogue_host
from world.rules.npc_schedules import interaction_reason
from world.rules.party import is_companion, party_size
from world.rules.time_skip import unsafe_rejection

# The eight action codes the vocabulary may emit. ``explore.interact`` is
# deliberately absent: the exploration panel's interact group is a label over
# per-target affordances, never a dispatcher action.
ACTION_CODE_ALLOWLIST = (
    "explore.move",
    "explore.look",
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
    "explore.wait",
)

# The subset of action codes a suggestion may carry: party management is a
# dock affordance, not a suggested action.
SUGGESTIBLE_ACTION_IDS = frozenset(ACTION_CODE_ALLOWLIST) - {
    "explore.party_invite",
    "explore.party_leave",
}

SURFACES = ("guild", "shop")

# The deterministic fallback card cap.
MAX_CARDS = 5

# Exact shared bounds (carried over from the version-1 panel).
MAX_MOVE_EXITS = 12
MAX_LOOK_OBJECTS = 32
MAX_INTERACT_TARGETS = 32
MAX_AFFORDANCES = 8
MAX_SCRIPTED_KEYWORDS = 16
MAX_EXIT_REF_CHARS = 64
MAX_NODE_ID_CHARS = 128
MAX_DISPLAY_NAME_CODE_POINTS = 128
MAX_LABEL_CODE_POINTS = 128
MAX_KEYWORD_ID_CHARS = 64
MAX_KEYWORD_LABEL_CODE_POINTS = 128
MAX_REASON_MESSAGE_CODE_POINTS = 128

# Stable localized disabled reasons.
_LOCKED_REASON = ("locked", "此出口目前無法通行。")
_DIALOGUE_UNAVAILABLE_REASON = (
    "dialogue_unavailable",
    "對方目前沒有可以交談的話題。",
)

# The fixed legal wait daypart of the idle baseline (member of DAYPARTS).
BASELINE_WAIT_DAYPART = "noon"


@dataclass(frozen=True)
class AffordanceView:
    """One canonical affordance view entry: exactly one of two shapes.

    An **action entry** carries ``action_id`` (member of
    ``ACTION_CODE_ALLOWLIST``), ``label``, ``params`` (validator-normalized, or
    the freeform binding shape), ``freeform``, ``navigation`` (false),
    ``enabled``, and nullable ``disabled_reason``; it carries no ``surface``.
    A **navigation entry** carries ``surface`` (``"guild"``/``"shop"``),
    ``label``, ``navigation`` (true), ``enabled``, and nullable
    ``disabled_reason``; it carries no ``action_id``, ``params``, or
    ``freeform`` — a navigation entry is a dock surface-opener with no
    dispatcher action code.
    """

    label: str
    enabled: bool
    disabled_reason: tuple[str, str] | None
    action_id: str | None = None
    params: dict[str, Any] | None = None
    freeform: bool | None = None
    navigation: bool = False
    surface: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.navigation, bool):
            raise ValueError("navigation must be a boolean")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string")
        if len(self.label) > MAX_LABEL_CODE_POINTS:
            raise ValueError("label exceeds its bound")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if self.enabled and self.disabled_reason is not None:
            raise ValueError("an enabled entry must not carry a disabled_reason")
        if not self.enabled and self.disabled_reason is None:
            raise ValueError("a disabled entry requires a disabled_reason")
        if self.navigation:
            if self.surface not in SURFACES:
                raise ValueError("surface is not a stable value")
            if (
                self.action_id is not None
                or self.params is not None
                or self.freeform is not None
            ):
                raise ValueError(
                    "a navigation entry carries no action_id, params, or freeform"
                )
        else:
            if self.action_id not in ACTION_CODE_ALLOWLIST:
                raise ValueError("action_id is not a registered exploration action")
            if not isinstance(self.params, dict):
                raise ValueError("params must be an object")
            if not isinstance(self.freeform, bool):
                raise ValueError("freeform must be a boolean")
            if self.surface is not None:
                raise ValueError("an action entry carries no surface")

    def as_dict(self) -> dict[str, Any]:
        """Serialize the entry into its exact wire object."""
        reason = (
            None
            if self.disabled_reason is None
            else {"code": self.disabled_reason[0], "message": self.disabled_reason[1]}
        )
        if self.navigation:
            return {
                "surface": self.surface,
                "label": self.label,
                "navigation": True,
                "enabled": self.enabled,
                "disabled_reason": reason,
            }
        return {
            "action_id": self.action_id,
            "label": self.label,
            "params": dict(self.params),
            "freeform": self.freeform,
            "navigation": False,
            "enabled": self.enabled,
            "disabled_reason": reason,
        }


# ---------------------------------------------------------------------------
# Shared read-only helpers (carried over from the version-1 panel).
# ---------------------------------------------------------------------------


def in_exploration_mode(actor: Any) -> bool:
    """Whether the actor is a puppeted player outside creation and combat."""
    from world.rules.combat_session import is_in_active_session

    if bool(getattr(actor, "creation_pending", False)):
        return False
    if is_in_active_session(actor):
        return False
    return True


def _bounded_display_name(obj: Any) -> str:
    return str(getattr(obj, "key", "?"))[:MAX_DISPLAY_NAME_CODE_POINTS]


def _bounded_label(text: str) -> str:
    return text[:MAX_LABEL_CODE_POINTS]


def _entity_kind(obj: Any) -> str | None:
    from typeclasses.characters import PlayerCharacter
    from typeclasses.monsters import Monster
    from typeclasses.npcs import LLMNPC, NPC

    for typeclass, kind in (
        (PlayerCharacter, "character"),
        (LLMNPC, "npc"),
        (NPC, "npc"),
        (Monster, "monster"),
    ):
        if isinstance(obj, typeclass):
            return kind
    return None


def _is_exit(obj: Any) -> bool:
    from evennia.objects.objects import DefaultExit

    return isinstance(obj, DefaultExit)


def _exit_ref(exit_obj: Any) -> str:
    """An opaque, stable ASCII identifier for a real exit (its dbref)."""
    return str(int(exit_obj.id))


def _traversable(exit_obj: Any, actor: Any) -> bool:
    try:
        return bool(exit_obj.access(actor, "traverse"))
    except Exception:
        return False


def _resolve_single_host(actor: Any, component_class: type) -> Any | None:
    from world.rules.guild import GuildServiceError, resolve_local_service_host

    try:
        return resolve_local_service_host(actor, component_class)
    except GuildServiceError:
        return None


def _present_npc(actor: Any, npc_id: int) -> Any | None:
    """Resolve a present NPC by identity, or ``None`` when absent."""
    from typeclasses.npcs import NPC

    location = getattr(actor, "location", None)
    if location is None:
        return None
    for obj in location.contents:
        if isinstance(obj, NPC) and int(obj.pk) == npc_id:
            return obj
    return None


# ---------------------------------------------------------------------------
# Candidate builders (same eligibility gates and disabled semantics as v1).
# ---------------------------------------------------------------------------


def _scripted_entries(npc: Any) -> list[AffordanceView]:
    """One ``explore.talk_scripted`` entry per authored keyword of a host."""
    dialogue_key = dialogue_key_for(npc)
    definition = DIALOGUE_TABLE.get(dialogue_key) if dialogue_key is not None else None
    if definition is None:
        return []
    npc_id = int(npc.pk)
    entries: list[AffordanceView] = []
    for response in definition.responses[:MAX_SCRIPTED_KEYWORDS]:
        params = validate_talk_scripted_payload(
            {"npc_id": npc_id, "keyword_id": response.keyword}
        )
        entries.append(
            AffordanceView(
                action_id="explore.talk_scripted",
                label=_bounded_label(response.keyword),
                params=params,
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
            )
        )
    return entries


def _scripted_keyword_descriptors(npc: Any) -> list[dict[str, str]]:
    """Return the bounded scripted keyword descriptors of a dialogue host.

    The keyword pool is a version-1 panel serialization detail: the panel's
    nested ``keywords`` list is bounded by ``MAX_SCRIPTED_KEYWORDS``
    independently of the vocabulary's per-target affordance budget.
    """
    dialogue_key = dialogue_key_for(npc)
    definition = DIALOGUE_TABLE.get(dialogue_key) if dialogue_key is not None else None
    if definition is None:
        return []
    return [
        {"keyword_id": response.keyword, "label": response.keyword}
        for response in definition.responses[:MAX_SCRIPTED_KEYWORDS]
    ]


def _freeform_entry(npc: Any) -> AffordanceView:
    """The always-enabled freeform talk entry for a present ``LLMNPC``.

    The params are binding-only: no registered validator produces the shape
    without ``speech``, so the entry carries exactly ``{"npc_id": int}`` and
    the full validator runs only on the client-composed dispatch payload.
    """
    return AffordanceView(
        action_id="explore.talk_freeform",
        label="自由交談",
        params={"npc_id": int(npc.pk)},
        freeform=True,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _party_invite_entry(npc: Any, actor: Any) -> AffordanceView:
    """The invite entry for a present unbound ``LLMNPC``.

    Mirrors the ``invite`` command's deterministic preflight: the entry is
    disabled with the full-party reason when the actor's party is at the bound
    (the caller decides it is never offered for an already-bound companion).
    """
    from world.rules.party import PARTY_FULL_MESSAGE, PARTY_MAX_COMPANIONS

    params = validate_party_invite_payload({"npc_id": int(npc.pk), "message": ""})
    if party_size(actor) >= PARTY_MAX_COMPANIONS:
        return AffordanceView(
            action_id="explore.party_invite",
            label="邀請",
            params=params,
            freeform=False,
            navigation=False,
            enabled=False,
            disabled_reason=("party_full", PARTY_FULL_MESSAGE),
        )
    return AffordanceView(
        action_id="explore.party_invite",
        label="邀請",
        params=params,
        freeform=False,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _party_leave_entry(npc: Any) -> AffordanceView:
    """The leave entry for a present bound companion."""
    params = validate_party_leave_payload({"npc_id": int(npc.pk)})
    return AffordanceView(
        action_id="explore.party_leave",
        label="解散",
        params=params,
        freeform=False,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _engage_entry(monster: Any) -> AffordanceView:
    """The engage entry for a present monster (dead monsters stay disabled)."""
    traits = getattr(monster, "traits", None)
    living = getattr(traits, "hp", None) is not None and monster.traits.hp.value > 0
    params = validate_engage_payload({"monster_id": int(monster.pk)})
    if not living:
        return AffordanceView(
            action_id="explore.engage",
            label="戰鬥",
            params=params,
            freeform=False,
            navigation=False,
            enabled=False,
            disabled_reason=("target_dead", "目標已經死亡。"),
        )
    return AffordanceView(
        action_id="explore.engage",
        label="戰鬥",
        params=params,
        freeform=False,
        navigation=False,
        enabled=True,
        disabled_reason=None,
    )


def _service_entry(surface: str) -> AffordanceView:
    """The navigate-kind service entry for one surface."""
    return AffordanceView(
        surface=surface,
        label="公會服務" if surface == "guild" else "商店",
        navigation=True,
        enabled=True,
        disabled_reason=None,
    )


def _target_affordance_entries(
    obj: Any,
    actor: Any,
    *,
    guild_host: Any | None,
    shop_host: Any | None,
) -> list[AffordanceView]:
    """The untruncated affordance entries of one present NPC/monster target.

    Mirrors the version-1 panel's per-target assembly order: scripted keyword
    entries (authored order), freeform, party leave/invite, engage, then the
    exact-local-host navigation entries.
    """
    from typeclasses.monsters import Monster
    from typeclasses.npcs import LLMNPC, NPC

    entries: list[AffordanceView] = []
    if isinstance(obj, NPC) and is_dialogue_host(obj):
        entries.extend(_scripted_entries(obj))
    if isinstance(obj, LLMNPC):
        entries.append(_freeform_entry(obj))
    if isinstance(obj, NPC) and is_companion(obj, actor):
        entries.append(_party_leave_entry(obj))
    elif isinstance(obj, LLMNPC):
        entries.append(_party_invite_entry(obj, actor))
    if isinstance(obj, Monster):
        entries.append(_engage_entry(obj))
    if guild_host is not None and obj is guild_host:
        entries.append(_service_entry("guild"))
    if shop_host is not None and obj is shop_host:
        entries.append(_service_entry("shop"))
    return entries


def _move_entries(actor: Any) -> list[AffordanceView]:
    """One ``explore.move`` entry per present, traversable exit.

    Wilderness rooms route every direction through the canonical destination
    resolver exactly like the version-1 panel: an exit whose destination
    cannot be resolved is omitted (the move adapter would reject it). The
    entry's ``current_node`` and every destination node are derived through
    the shared node-ID encoder, so the adapter's ``stale_location`` compare
    passes byte-identically for ordinary rooms, ``GridRoom``, and
    ``TerrainRoom`` destinations alike.
    """
    from typeclasses.rooms import TerrainRoom
    from world.maps.wilderness_destination import (
        normalize_wilderness_direction,
        resolve_wilderness_destination,
    )

    location = getattr(actor, "location", None)
    if location is None:
        return []
    current_node = node_id_for_location(location)
    if current_node is None:
        return []
    wilderness = isinstance(location, TerrainRoom)
    exits = sorted(
        location.exits, key=lambda exit_obj: (exit_obj.key or "", int(exit_obj.id))
    )
    entries: list[AffordanceView] = []
    for exit_obj in exits[:MAX_MOVE_EXITS]:
        if exit_obj.destination is None:
            continue
        if wilderness:
            direction = normalize_wilderness_direction(exit_obj.key)
            destination_node = (
                resolve_wilderness_destination(location, direction)
                if direction is not None
                else None
            )
        else:
            destination_node = node_id_for_location(exit_obj.destination)
        if destination_node is None:
            continue
        enabled = _traversable(exit_obj, actor)
        params = validate_move_payload(
            {"exit_ref": _exit_ref(exit_obj), "current_node": current_node}
        )
        entries.append(
            AffordanceView(
                action_id="explore.move",
                label=_bounded_display_name(exit_obj),
                params=params,
                freeform=False,
                navigation=False,
                enabled=enabled,
                disabled_reason=None if enabled else _LOCKED_REASON,
            )
        )
    return entries


def _look_entries(actor: Any) -> list[AffordanceView]:
    """One ``explore.look`` entry per present non-exit object."""
    location = getattr(actor, "location", None)
    if location is None:
        return []
    present = [
        obj
        for obj in location.contents
        if obj is not actor and _entity_kind(obj) is None and not _is_exit(obj)
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    entries: list[AffordanceView] = []
    for obj in present[:MAX_LOOK_OBJECTS]:
        params = validate_look_payload({"target_id": int(obj.pk)})
        entries.append(
            AffordanceView(
                action_id="explore.look",
                label=_bounded_display_name(obj),
                params=params,
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
            )
        )
    return entries


def _target_entries(actor: Any) -> list[AffordanceView]:
    """The bounded per-target affordance entries of every present NPC/monster."""
    from typeclasses.components import GuildStaff, Merchant
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC

    location = getattr(actor, "location", None)
    if location is None:
        return []
    guild_host = _resolve_single_host(actor, GuildStaff)
    shop_host = _resolve_single_host(actor, Merchant)
    present = [
        obj
        for obj in location.contents
        if obj is not actor and isinstance(obj, (NPC, Monster))
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    entries: list[AffordanceView] = []
    for obj in present[:MAX_INTERACT_TARGETS]:
        entries.extend(
            _target_affordance_entries(
                obj, actor, guild_host=guild_host, shop_host=shop_host
            )[:MAX_AFFORDANCES]
        )
    return entries


def _baseline_entries(actor: Any) -> list[AffordanceView]:
    """The idle baseline: room-look always, wait only in a safe room."""
    location = getattr(actor, "location", None)
    look_params = validate_look_payload({"room": True})
    entries = [
        AffordanceView(
            action_id="explore.look",
            label=_bounded_display_name(location),
            params=look_params,
            freeform=False,
            navigation=False,
            enabled=True,
            disabled_reason=None,
        )
    ]
    if unsafe_rejection(actor) is None:
        wait_params = validate_wait_payload({"daypart": BASELINE_WAIT_DAYPART})
        entries.append(
            AffordanceView(
                action_id="explore.wait",
                label="等待",
                params=wait_params,
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Vocabulary collector and eligibility layers.
# ---------------------------------------------------------------------------


def exploration_affordances(actor: Any) -> tuple[AffordanceView, ...]:
    """Return the ordered canonical affordance vocabulary of one actor.

    The order is stable: move rows, then per-object look entries, then the
    per-target entries (targets sorted by identity, affordances in the
    version-1 assembly order), then the idle baseline. Outside exploration
    mode (creation-pending, active combat, absent location) the vocabulary is
    empty.
    """
    if not in_exploration_mode(actor):
        return ()
    location = getattr(actor, "location", None)
    if location is None:
        return ()
    entries: list[AffordanceView] = []
    entries.extend(_move_entries(actor))
    entries.extend(_look_entries(actor))
    entries.extend(_target_entries(actor))
    entries.extend(_baseline_entries(actor))
    return tuple(entries)


def suggestible_candidates(
    affordances: tuple[AffordanceView, ...] | list[AffordanceView],
    *,
    actor: Any | None = None,
) -> tuple[AffordanceView, ...]:
    """Return exactly the executable suggestion entries of a vocabulary.

    An entry is suggestible iff it is an enabled action entry whose code is in
    ``SUGGESTIBLE_ACTION_IDS`` — never a navigation, party, or disabled entry.
    Talk entries are suggestible only when ``actor`` is provided and the host
    is present and not blocked by the talk schedule gate; a wait entry is
    suggestible only when the room is safe (the vocabulary never emits an
    unsafe wait, and ``actor`` re-verifies it). Without an actor the schedule
    and safety gates cannot be verified, so talk entries are excluded —
    executability is never claimed for an unverifiable card. This layer is the
    single source of "is this card runnable right now" for the deterministic
    fallback and the later AI proposal ladder; the vocabulary itself is
    unchanged by this filtering.
    """
    results: list[AffordanceView] = []
    for entry in affordances:
        if entry.navigation:
            continue
        if not entry.enabled:
            continue
        if entry.action_id not in SUGGESTIBLE_ACTION_IDS:
            continue
        if entry.action_id in ("explore.talk_scripted", "explore.talk_freeform"):
            if actor is None:
                continue
            npc = _present_npc(actor, entry.params["npc_id"])
            if npc is None:
                continue
            if interaction_reason(npc, "talk") is not None:
                continue
        if entry.action_id == "explore.wait":
            if actor is not None and unsafe_rejection(actor) is not None:
                continue
        results.append(entry)
    return tuple(results)


def default_cards(
    affordances: tuple[AffordanceView, ...] | list[AffordanceView],
    *,
    objective_npc_ids: frozenset[int] = frozenset(),
    actor: Any | None = None,
    max_cards: int = MAX_CARDS,
) -> tuple[AffordanceView, ...]:
    """Derive the deterministic degradation suggestion list (rule cards).

    Filters through :func:`suggestible_candidates`, ranks objective-relevant
    entries first (params referencing a present NPC id in ``objective_npc_ids``),
    then talk and engage entries over the remaining baseline, preserves
    vocabulary order within a rank, and caps at ``max_cards``. In v1
    exploration the room-look baseline is always suggestible, so the result is
    never empty there. Production callers pass the ``actor`` so talk
    eligibility re-verifies presence and the schedule gate; without it, talk
    entries are excluded (see :func:`suggestible_candidates`). The function is
    pure: it never mutates state and only reads what the caller passes.
    """
    suggestible = suggestible_candidates(affordances, actor=actor)

    def _is_objective(entry: AffordanceView) -> bool:
        return (
            isinstance(entry.params, dict)
            and isinstance(entry.params.get("npc_id"), int)
            and entry.params["npc_id"] in objective_npc_ids
        )

    def _rank(entry: AffordanceView) -> int:
        if _is_objective(entry):
            return 0
        if entry.action_id in ("explore.talk_scripted", "explore.talk_freeform", "explore.engage"):
            return 1
        return 2

    ordered = sorted(suggestible, key=_rank)
    return tuple(ordered[:max_cards])


# ---------------------------------------------------------------------------
# Canonical serialization and the eligibility digest (shared sources).
# ---------------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    """Serialize one JSON-safe value into its canonical stable-key form.

    Keys are recursively sorted, non-ASCII text is kept literal, and compact
    separators are used, so byte-identical input produces byte-identical output
    regardless of key insertion order. Tuples serialize as arrays (the
    deterministic type coercion over the vocabulary's containers). This is the
    single serialization the schema ladder's canonical comparison, the
    trigger-service eligibility and public-state digests, and the test fixtures
    all share, so builder-side and validator-side representations cannot drift.

    Raises ``ValueError`` for containers with non-string keys, which have no
    deterministic ordering.
    """
    _ensure_canonical(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _ensure_canonical(value: Any) -> None:
    """Recursively verify that ``value`` is deterministically serializable."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON requires string-sortable keys")
            _ensure_canonical(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _ensure_canonical(item)
    elif not isinstance(value, (str, int, float, bool)) and value is not None:
        raise ValueError(
            f"canonical JSON cannot serialize {type(value).__name__}; "
            "sets have no deterministic ordering"
        )


def eligible_affordance_digest(affordances: Any) -> str:
    """Digest of the canonical eligible-affordance list (labels excluded).

    ``affordances`` is a sequence of action-entry :class:`AffordanceView`
    (navigation entries are rejected — a navigation surface has no dispatcher
    action code and no eligibility). The digest is the SHA-256 of the canonical
    JSON of the ``sorted((action_id, params))`` pairs with ``params`` serialized
    key-sorted, so any change that makes an action executable or not —
    schedule-gate flips, locked exits, monster death, vanishing objects —
    changes the digest while identical eligibility (labels, display names, and
    ordering aside) always produces the same value.
    """
    pairs = []
    for entry in affordances:
        if getattr(entry, "navigation", False):
            raise ValueError("the eligibility digest covers action entries only")
        if entry.params is None:
            raise ValueError("a digest action entry carries no params")
        pairs.append((entry.action_id, canonical_json(entry.params)))
    pairs.sort()
    return hashlib.sha256(
        canonical_json([list(pair) for pair in pairs]).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ACTION_CODE_ALLOWLIST",
    "AffordanceView",
    "BASELINE_WAIT_DAYPART",
    "MAX_AFFORDANCES",
    "MAX_CARDS",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_EXIT_REF_CHARS",
    "MAX_INTERACT_TARGETS",
    "MAX_KEYWORD_ID_CHARS",
    "MAX_KEYWORD_LABEL_CODE_POINTS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_LOOK_OBJECTS",
    "MAX_MOVE_EXITS",
    "MAX_NODE_ID_CHARS",
    "MAX_REASON_MESSAGE_CODE_POINTS",
    "MAX_SCRIPTED_KEYWORDS",
    "SUGGESTIBLE_ACTION_IDS",
    "SURFACES",
    "canonical_json",
    "default_cards",
    "eligible_affordance_digest",
    "exploration_affordances",
    "in_exploration_mode",
    "suggestible_candidates",
]
