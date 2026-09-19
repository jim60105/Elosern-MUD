"""Bounded-context serializer (pipeline design doc §2).

Assembles the frozen ``ActionOptionsContext`` from caller-supplied plain data
under the fixed truncation policy, alongside the layer's named error classes.
The same import discipline holds as the schema vocabulary observes: no Evennia
import, no state writer, no live transport, and no module-level logger binding
at module time.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from web.webclient.presentation.affordances import AffordanceView

# ==== Bounded-context serializer (pipeline design doc §2) ====

# Hard context budgets; the single source the trigger service's deterministic
# view mirrors. ``affordances``, ``room_name``, and ``room_summary`` are never
# truncated (a summary of what you *can't* do is useless); every other field is
# truncated by ``build_options_context`` in the fixed order: narrative tail
# first (oldest characters), then persona-digest characters, then the oldest
# NPC (and monster) entries.
MAX_ROOM_NAME_LENGTH = 40
MAX_ROOM_SUMMARY_LENGTH = 300
MAX_NARRATIVE_TAIL_LENGTH = 600
MAX_NPC_ENTRIES = 8
MAX_NPC_DIGEST_LENGTH = 160
MAX_MONSTER_ENTRIES = 4
MAX_MONSTER_ENTRY_LENGTH = 80
MAX_OBJECTIVE_LENGTH = 120
MAX_AFFORDANCES = 16


class ActionOptionsInputError(ValueError):
    """A context input outside its hard budget or of the wrong shape.

    Raised by ``build_options_context`` and ``ActionOptionsContext``
    construction; the generation entry point catches it, logs a bounded
    diagnostic, and resolves ``None`` — out-of-bounds data is never emitted.
    """


class ActionOptionsBindingError(ValueError):
    """A freeform ``{npc_index}`` binding failure (unknown index or duplicate)."""


class ActionOptionsClientRequiredError(TypeError):
    """Raised when a generation call is made with an explicit ``None`` client."""


class ActionOptionsNotRegisteredError(RuntimeError):
    """Raised when the action_options layer's hooks are not installed."""


@dataclass(frozen=True)


class ActionOptionsNPCEntry:
    """One present NPC in the bounded context (stable positional identity).

    ``npc_id`` is the deterministic entity id the freeform binding resolves to;
    ``persona_digest`` is the public persona digest (never true traits);
    ``public_tier`` is the relationship tier label (e.g. 好感層級), never the
    numeric affinity — the same boundary npc_dialogue observes. Construction
    validates every field type so a later digest-length check can never hit a
    non-string.
    """

    npc_id: int
    display_name: str
    dialogue_key: str | None = None
    persona_digest: str = ""
    public_tier: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.npc_id, bool) or not isinstance(self.npc_id, int):
            raise ActionOptionsInputError("npc_id must be an integer")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ActionOptionsInputError("display_name must be a non-empty string")
        if not isinstance(self.persona_digest, str):
            raise ActionOptionsInputError("persona_digest must be a string")
        for field in ("dialogue_key", "public_tier"):
            value = getattr(self, field)
            if value is not None and not isinstance(value, str):
                raise ActionOptionsInputError(f"{field} must be a string or None")


@dataclass(frozen=True)


class ActionOptionsMonsterEntry:
    """One present monster in the bounded context."""

    monster_id: int
    display_name: str
    threat_tier: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.monster_id, bool) or not isinstance(self.monster_id, int):
            raise ActionOptionsInputError("monster_id must be an integer")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ActionOptionsInputError("display_name must be a non-empty string")
        if self.threat_tier is not None and not isinstance(self.threat_tier, str):
            raise ActionOptionsInputError("threat_tier must be a string or None")


@dataclass(frozen=True)


class ActionOptionsContext:
    """The frozen bounded context for one action-options generation.

    Construction is strict: every field is type-checked and every cap is
    enforced, raising ``ActionOptionsInputError`` for out-of-bounds values.
    ``build_options_context`` is the sanctioned constructor that applies the
    fixed truncation policy first. ``affordances`` holds the canonical tuple
    the ladder validates against (never truncated); ``leak_blocklist`` is
    consumed by validation only and never rendered into a prompt.
    """

    room_name: str
    room_summary: str
    npc_entries: tuple[ActionOptionsNPCEntry, ...]
    monster_entries: tuple[ActionOptionsMonsterEntry, ...]
    objective: str | None
    narrative_tail: str
    affordances: tuple[AffordanceView, ...]
    leak_blocklist: frozenset[str]

    def __post_init__(self) -> None:
        self._check_budget("room_name", self.room_name, MAX_ROOM_NAME_LENGTH)
        self._check_budget("room_summary", self.room_summary, MAX_ROOM_SUMMARY_LENGTH)
        self._check_budget("narrative_tail", self.narrative_tail, MAX_NARRATIVE_TAIL_LENGTH)
        if self.objective is not None and not isinstance(self.objective, str):
            raise ActionOptionsInputError("objective must be a string or None")
        if self.objective is not None and len(self.objective) > MAX_OBJECTIVE_LENGTH:
            raise ActionOptionsInputError(
                f"objective exceeds the maximum of {MAX_OBJECTIVE_LENGTH} chars"
            )
        if not isinstance(self.npc_entries, tuple) or not all(
            isinstance(entry, ActionOptionsNPCEntry) for entry in self.npc_entries
        ):
            raise ActionOptionsInputError("npc_entries must be a tuple of NPCEntry")
        if len(self.npc_entries) > MAX_NPC_ENTRIES:
            raise ActionOptionsInputError(
                f"npc_entries exceed the maximum of {MAX_NPC_ENTRIES} entries"
            )
        for entry in self.npc_entries:
            if len(entry.persona_digest) > MAX_NPC_DIGEST_LENGTH:
                raise ActionOptionsInputError(
                    f"persona digest exceeds the maximum of {MAX_NPC_DIGEST_LENGTH} chars"
                )
        if not isinstance(self.monster_entries, tuple) or not all(
            isinstance(entry, ActionOptionsMonsterEntry) for entry in self.monster_entries
        ):
            raise ActionOptionsInputError("monster_entries must be a tuple of MonsterEntry")
        if len(self.monster_entries) > MAX_MONSTER_ENTRIES:
            raise ActionOptionsInputError(
                f"monster_entries exceed the maximum of {MAX_MONSTER_ENTRIES} entries"
            )
        for entry in self.monster_entries:
            if len(entry.display_name) > MAX_MONSTER_ENTRY_LENGTH:
                raise ActionOptionsInputError(
                    f"monster display name exceeds the maximum of "
                    f"{MAX_MONSTER_ENTRY_LENGTH} chars"
                )
        if not isinstance(self.affordances, tuple) or not all(
            isinstance(getattr(entry, "navigation", None), bool)
            and isinstance(getattr(entry, "action_id", None), (str, type(None)))
            and hasattr(entry, "label")
            for entry in self.affordances
        ):
            raise ActionOptionsInputError(
                "affordances must be a tuple of AffordanceView entries"
            )
        if len(self.affordances) > MAX_AFFORDANCES:
            raise ActionOptionsInputError(
                f"affordances exceed the maximum of {MAX_AFFORDANCES} entries"
            )
        if not isinstance(self.leak_blocklist, frozenset) or any(
            not isinstance(token, str) or not token for token in self.leak_blocklist
        ):
            raise ActionOptionsInputError(
                "leak_blocklist must be a frozenset of non-empty strings"
            )

    def _check_budget(self, field: str, value: Any, cap: int) -> None:
        if not isinstance(value, str):
            raise ActionOptionsInputError(f"{field} must be a string")
        if len(value) > cap:
            raise ActionOptionsInputError(f"{field} exceeds the maximum of {cap} chars")


def _build_npc_entry(raw: Mapping[str, Any]) -> ActionOptionsNPCEntry:
    """Validate one plain-data NPC mapping and bound its persona digest."""
    if not isinstance(raw, Mapping):
        raise ActionOptionsInputError("each npc entry must be a mapping")
    npc_id = raw.get("npc_id")
    display_name = raw.get("display_name")
    if isinstance(npc_id, bool) or not isinstance(npc_id, int):
        raise ActionOptionsInputError("npc_id must be an integer")
    if not isinstance(display_name, str) or not display_name:
        raise ActionOptionsInputError("display_name must be a non-empty string")
    for field in ("dialogue_key", "public_tier"):
        value = raw.get(field)
        if value is not None and not isinstance(value, str):
            raise ActionOptionsInputError(f"{field} must be a string or absent")
    digest = raw.get("persona_digest", "")
    if not isinstance(digest, str):
        raise ActionOptionsInputError("persona_digest must be a string")
    return ActionOptionsNPCEntry(
        npc_id=npc_id,
        display_name=display_name,
        dialogue_key=raw.get("dialogue_key"),
        persona_digest=digest[:MAX_NPC_DIGEST_LENGTH],
        public_tier=raw.get("public_tier"),
    )


def _build_monster_entry(raw: Mapping[str, Any]) -> ActionOptionsMonsterEntry:
    """Validate one plain-data monster mapping and bound its display name."""
    if not isinstance(raw, Mapping):
        raise ActionOptionsInputError("each monster entry must be a mapping")
    monster_id = raw.get("monster_id")
    display_name = raw.get("display_name")
    if isinstance(monster_id, bool) or not isinstance(monster_id, int):
        raise ActionOptionsInputError("monster_id must be an integer")
    if not isinstance(display_name, str) or not display_name:
        raise ActionOptionsInputError("display_name must be a non-empty string")
    threat_tier = raw.get("threat_tier")
    if threat_tier is not None and not isinstance(threat_tier, str):
        raise ActionOptionsInputError("threat_tier must be a string or absent")
    return ActionOptionsMonsterEntry(
        monster_id=monster_id,
        display_name=display_name[:MAX_MONSTER_ENTRY_LENGTH],
        threat_tier=threat_tier,
    )


def build_options_context(
    *,
    room_name: str,
    room_summary: str,
    narrative_tail: str,
    npc_entries: Sequence[Mapping[str, Any]],
    monster_entries: Sequence[Mapping[str, Any]] = (),
    objective: str | None = None,
    affordances: Sequence[AffordanceView],
    secret_tokens: Iterable[str] = (),
) -> ActionOptionsContext:
    """Assemble the frozen bounded context from caller-supplied plain data.

    The fixed truncation policy applies to the truncatable fields only:
    narrative tail keeps the most recent ``MAX_NARRATIVE_TAIL_LENGTH``
    characters (oldest dropped first), persona digests keep their first
    ``MAX_NPC_DIGEST_LENGTH`` characters, and NPC/monster entries beyond the
    caps drop the oldest. ``affordances``, ``room_name``, and ``room_summary``
    are never truncated: an over-cap value raises ``ActionOptionsInputError``.
    ``secret_tokens`` (numeric literals + hidden trait keys of the
    deterministic view) compose the context's ``LEAK_BLOCKLIST``, consumed by
    validation only. Identical input produces a byte-identical frozen context
    with no live entity references; NPC order is the caller's stable order.
    """
    if not isinstance(narrative_tail, str):
        raise ActionOptionsInputError("narrative_tail must be a string")
    if objective is not None and not isinstance(objective, str):
        raise ActionOptionsInputError("objective must be a string or None")
    if isinstance(secret_tokens, str):
        raise ActionOptionsInputError(
            "secret_tokens must be an iterable of strings, not a string"
        )
    if len(affordances) > MAX_AFFORDANCES:
        raise ActionOptionsInputError(
            f"affordances exceed the maximum of {MAX_AFFORDANCES} entries"
        )
    npc = tuple(npc_entries)[-MAX_NPC_ENTRIES:]
    monsters = tuple(monster_entries)[-MAX_MONSTER_ENTRIES:]
    return ActionOptionsContext(
        room_name=room_name,
        room_summary=room_summary,
        npc_entries=tuple(_build_npc_entry(entry) for entry in npc),
        monster_entries=tuple(_build_monster_entry(entry) for entry in monsters),
        objective=objective[:MAX_OBJECTIVE_LENGTH] if objective is not None else None,
        narrative_tail=narrative_tail[-MAX_NARRATIVE_TAIL_LENGTH:],
        affordances=tuple(affordances),
        leak_blocklist=frozenset(token for token in secret_tokens if token),
    )
