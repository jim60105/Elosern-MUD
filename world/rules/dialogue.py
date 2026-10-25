"""Scripted dialogue: keyed read surface, read-only resolution, and the talk writer.

The authored tables live in the lore package ``world/lore/dialogue/``
(place-attendant-profession: authored prose is authored identity); this
module is the rules-side read surface over them: the immutable keyed
``DIALOGUE_TABLE``, component resolution, the keyword lookup, and the
no-keyword greeting. The authored dataclasses are re-exported so every
``world.rules.dialogue`` import path keeps working unchanged.
The lookup surface performs no state writes, preserving the read-side
discipline of the runtime; the ``guild_staff`` action keyword is the one
authored exception: keyword ``回報`` resolves the read-only reportable-quest
listing through ``world.rules.guild`` (or falls back to the authored line),
and the keyword-less lookup never writes.

The module also hosts the deterministic scripted-talk writer
(``run_scripted_talk``), the only dialogue path that writes state: a known
keyword grants +1 talk affinity with the host through the sole-writer
affinity API (``world/rules/affinity.py``) in one transaction, restoring the
relations surface on failure. It lives here because ``world/rules/`` is the
deterministic core and this is the dialogue subsystem's own writer.

The module also owns the character-held dialogue session (webclient-align-07)
as its ONLY read/write surface: ``open_or_refresh_dialogue`` /
``clear_dialogue_session`` / ``live_dialogue_session``. Persistent
``db.dialogue_session`` on the character is the single truth of WHO the
character is speaking to and the latest server-authored LINE; no presenter,
AI layer, or client payload may open, refresh, or clear it.
The opener success paths are the ``explore.talk_open`` opener (a conversation
with the host's greeting, or the fixed fallback line), the
``explore.talk_scripted`` and ``explore.talk_freeform`` adapters, and the
``talk`` text command.
The clear seams are: movement settlement, combat engage, NPC departure
cleanup, and the ``explore.dialogue_leave`` adapter's explicit exit
(webclient-align-11) — the adapter calls ``clear_dialogue_session`` here and
never touches ``db`` itself.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
import uuid

from world.lore.dialogue.codec import GeneratedDialogueIdentity, StaticDialogueIdentity
from world.lore.scenes import Narration, Scene, Speech

from typeclasses.components import ScriptedDialogue

from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse
from world.observability import log_error, log_info

GUILD_STAFF_DIALOGUE_KEY = "guild_staff"
GUILD_STAFF_TURNIN_KEYWORD = "回報"

# A generated story role's dialogue identity names its package and role, e.g.
# ``scene_role:pkg_ab12:mother``. The shared resolver reads the role's current
# permitted phase through the quest-owned scene store, so greetings, keyword
# responses, topic affordances and action validation all answer from the same
# place as the authored tables (quest-scene-encounters 4.1).
GENERATED_DIALOGUE_PREFIX = "scene_role:"

NO_UNDERSTANDING_LINE = "對方皺起眉頭：「我不太明白你的意思。」"

# The session line bound mirrors the accepted-prose bounds the dialogue
# responses already respect (the generative narrator's ``MAX_PROSE_LENGTH``
# and the NPC-dialogue layer's ``MAX_SPEECH_LENGTH``, both 2000). The parity
# is a deliberate local constant: the transport boundary forbids the rules
# layer from importing the generative layer, and a session line can never
# exceed the bound its own producer authored it under.
MAX_DIALOGUE_SESSION_LINE_CODE_POINTS = 2000


# The frozen keyed read over the lore-assembled rows (``world/lore/dialogue/``);
# every table row is authored there, split by domain slice. The dataclasses are
# re-exported above, so the historical import surface is bit-for-bit unchanged.
DIALOGUE_TABLE: MappingProxyType = MappingProxyType(DIALOGUE_ROWS)


def resolve_dialogue_component(npc: Any) -> Any | None:
    """Return the dialogue component carried by ``npc``, or ``None``.

    A host carrying the scripted dialogue component is dialogue-capable.
    """
    components = getattr(npc, "components", None)
    if components is None:
        return None
    if components.has(ScriptedDialogue.name):
        return components.get(ScriptedDialogue.get_component_slot())
    return None


class DialogueRuntimeError(Exception):
    """Base error for dialogue runtime selection and session failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class StaleContextError(DialogueRuntimeError):
    """Context ID does not match the active session."""


class StaleSelectionError(DialogueRuntimeError):
    """Selection request is stale or replayed after intervening selection."""


class DuplicateSelectionError(DialogueRuntimeError):
    """Selection ID was already used for a different topic."""


class TopicLockedError(DialogueRuntimeError):
    """Topic is locked or requires conditions that are not yet permitted."""


class TopicNotFoundError(DialogueRuntimeError):
    """Topic was not found in the host's current definition."""


class DialogueSourceUnavailableError(DialogueRuntimeError):
    """Host has no conversable dialogue source."""


@dataclass(frozen=True)
class SceneDelivery:
    """One delivered authored or generated scene snapshot."""

    delivery_id: str
    selection_id: str
    context_id: str
    actor_id: int
    owner_id: int
    host_id: int
    topic_id: str | None
    scene_id: str
    scene_revision: str
    phase_revision: int | str | None
    kind: str  # formal | refusal | opening | service
    lines: tuple[Speech | Narration, ...]
    updated_tick: int | None


def delivery_to_wire(delivery: SceneDelivery | None) -> dict[str, Any] | None:
    """Serialize SceneDelivery to wire form (omitting server-only identities)."""
    if delivery is None:
        return None
    return {
        "delivery_id": delivery.delivery_id,
        "context_id": delivery.context_id,
        "topic_id": delivery.topic_id,
        "scene_id": delivery.scene_id,
        "scene_revision": delivery.scene_revision,
        "phase_revision": delivery.phase_revision,
        "kind": delivery.kind,
        "lines": [
            {"kind": "speech", "speaker": l.speaker, "text": l.text}
            if isinstance(l, Speech)
            else {"kind": "narration", "text": l.text}
            for l in delivery.lines
        ],
    }


@dataclass(frozen=True)
class GeneratedPhaseDialogue:
    """One generated role's current permitted phase, as a read-only view."""

    package_id: str
    role_id: str
    phase_id: str
    revision: int
    greeting: str
    topics: tuple[tuple[str, str], ...]
    offline_response: str


def _generated_dialogue_for_key(dialogue_key: str | None) -> GeneratedPhaseDialogue | None:
    """Resolve a generated dialogue key to its current permitted phase, or ``None``.

    Read-only: a malformed key, an unpublished package, an unknown role or a
    missing selected phase all resolve to ``None`` (the caller then falls back to
    the authored table or the no-understanding line). Guarded reunion/escort
    content is never invented here -- only the committed selected phase's own
    validated fields are returned.
    """
    if not isinstance(dialogue_key, str) or not dialogue_key.startswith(
        GENERATED_DIALOGUE_PREFIX
    ):
        return None
    package_id, _, role_id = dialogue_key[len(GENERATED_DIALOGUE_PREFIX):].partition(":")
    if not package_id or not role_id:
        return None
    from world.quests import scene_store

    row = scene_store.read_package(package_id)
    if row is None:
        return None
    definition = _validated_package(package_id, row.payload)
    if definition is None:
        return None
    role_dialogue = definition.role_dialogue(role_id)
    if role_dialogue is None:
        return None
    runtime = scene_store.get_dialogue_phase(package_id, role_id)
    phase_id = runtime.selected_phase if runtime is not None else role_dialogue.initial_phase
    revision = int(runtime.revision) if runtime is not None else 0
    phase = next(
        (item for item in role_dialogue.phases if item.phase_id == phase_id), None
    )
    if phase is None:
        return None
    return GeneratedPhaseDialogue(
        package_id=package_id,
        role_id=role_id,
        phase_id=phase.phase_id,
        revision=revision,
        greeting=phase.greeting,
        topics=tuple((topic.keyword, topic.response) for topic in phase.topics),
        offline_response=phase.offline_response,
    )


def _validated_package(package_id: str, payload: Any) -> Any | None:
    """Return one published payload's validated definition (shared cache).

    The definition is cached by package id inside the validator (a published
    payload is immutable and its id IS the content digest); the *selected phase*
    stays runtime state and is read fresh on every call.
    """
    from world.quests.scene_package import validated_package

    return validated_package(package_id, payload)


def generated_dialogue_for(npc: Any) -> GeneratedPhaseDialogue | None:
    """Return the current generated phase definition for ``npc``, or ``None``."""
    return _generated_dialogue_for_key(dialogue_key_for(npc))


def dialogue_phase_revision(npc: Any) -> int | None:
    """Return the current phase revision of a generated host, or ``None``."""
    generated = generated_dialogue_for(npc)
    return None if generated is None else generated.revision


def is_dialogue_host(npc: Any) -> bool:
    """Whether ``npc`` carries any dialogue component."""
    return resolve_dialogue_component(npc) is not None


def dialogue_key_for(npc: Any) -> str | None:
    """Return the host's ``dialogue_key`` or ``None`` for a non-host."""
    component = resolve_dialogue_component(npc)
    if component is None:
        return None
    return getattr(component, "dialogue_key", None)


def table_response(dialogue_key: str, keyword: str, npc: Any = None) -> str:
    """Return the resolved response for one keyword, or the no-understanding line.

    The shared resolver answers authored rows and validated generated
    current-phase definitions alike, so the text ``talk`` path, the webclient
    adapter, the topic affordances and action validation all read one seam
    (quest-scene-encounters 4.1).
    """
    generated = _generated_dialogue_for_key(dialogue_key)
    if generated is not None:
        for candidate, response in generated.topics:
            if candidate == keyword:
                return response
        if npc is not None:
            return misunderstood_line_for(npc)
        return NO_UNDERSTANDING_LINE
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return NO_UNDERSTANDING_LINE
    for entry in definition.responses:
        if entry.keyword == keyword:
            return entry.response
    if npc is not None:
        return misunderstood_line_for(npc)
    return NO_UNDERSTANDING_LINE


def dialogue_has_keyword(dialogue_key: str, keyword: str) -> bool:
    """Whether ``keyword`` resolves in the named authored table or generated phase."""
    generated = _generated_dialogue_for_key(dialogue_key)
    if generated is not None:
        return any(candidate == keyword for candidate, _ in generated.topics)
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return False
    return any(entry.keyword == keyword for entry in definition.responses)


def dialogue_topic_keywords(npc: Any) -> tuple[str, ...]:
    """Return the ordered topic keyword identities of a host's current definition.

    Authored tables and generated current phases answer through the same
    resolver, so the version-2 conversation panel, the text ``talk`` command and
    the action-validation path can never disagree about which topics exist. An
    empty or unresolved definition yields an empty tuple (no choices).
    """
    key = dialogue_key_for(npc)
    if key is None:
        return ()
    generated = _generated_dialogue_for_key(key)
    if generated is not None:
        return tuple(candidate for candidate, _ in generated.topics)
    definition = DIALOGUE_TABLE.get(key)
    if definition is None:
        return ()
    return tuple(entry.keyword for entry in definition.responses)


def dialogue_response(npc: Any, actor: Any, keyword: str) -> str | None:
    """Return the authored response for ``keyword`` on ``npc``, or ``None``.

    ``None`` means the NPC is not a dialogue host (the caller shows the
    no-response line). A host with an unknown keyword yields the
    no-understanding line. The ``guild_staff`` host answers the ``回報``
    keyword with the read-only reportable-quest listing for ``actor`` (the
    registered guild member standing with that host), falling back to the
    authored line when the actor is not a member. This function never writes
    state.
    """
    key = dialogue_key_for(npc)
    if key is None:
        return None
    if key == GUILD_STAFF_DIALOGUE_KEY and keyword == GUILD_STAFF_TURNIN_KEYWORD:
        from world.rules.guild import reportable_quest_summary

        summary = reportable_quest_summary(actor, npc)
        if summary is not None:
            return summary
    return table_response(key, keyword, npc=npc)


def greeting_for(npc: Any) -> str | None:
    """Return the host's authored no-keyword greeting, or ``None``.

    A missing ``dialogue_key`` or a definition with ``greeting=None`` yields
    ``None`` so the caller falls back to the no-response line. A generated
    role answers with its current permitted phase's fixed greeting.
    """
    generated = generated_dialogue_for(npc)
    if generated is not None:
        return generated.greeting
    key = dialogue_key_for(npc)
    if key is None:
        return None
    definition = DIALOGUE_TABLE.get(key)
    if definition is None:
        return None
    return definition.greeting


def misunderstood_line_for(npc: Any) -> str:
    """Return the misunderstood voice line for an NPC (design D3).

    If the host carries profile provenance, resolves that profile's misunderstood
    line. If the profile key cannot be resolved, logs an integrity error and
    falls back to the shared line. Never consults the instance field (instance
    fields answer greetings, not keywords).
    """
    from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
    from world.rules.npc_persona import provenance_profile_key

    key = provenance_profile_key(npc)
    if key is None:
        return NO_UNDERSTANDING_LINE
    profile = NPC_PROFILE_REGISTRY.get(key)
    if profile is None:
        # observability: ignore R3: dangling profile reference is a non-exception integrity event
        log_error("npc_voice_profile_missing", context={"npc": str(getattr(npc, "pk", npc)), "profile": key})
        return NO_UNDERSTANDING_LINE
    return profile.voice.misunderstood or NO_UNDERSTANDING_LINE


@dataclass(frozen=True)
class ResolvedGreeting:
    """One resolved greeting line: its raw text and override status (change 23)."""

    text: str
    is_override: bool


def escape_evennia_greeting(text: str) -> str:
    """Escape an editable greeting for Evennia text-output boundaries.

    Neutralizes Evennia ANSI codes (|/, |r, |n, ||) and MXP command/URL link
    tokens (|lc...|lt...|le, |lu...|lt...|le) so they display as literal text
    without linebreaks, styling, or link creation across telnet and webclient.
    """
    if not text:
        return ""
    import re

    s = text.replace("{", "{{")

    def _sub_pipe(m: re.Match[str]) -> str:
        token = m.group(0)
        if token in ("|lc", "|lt", "|le", "|lu"):
            return "|||n" + token[1:]
        return "||"

    return re.sub(r"\|(?:lc|lt|le|lu)|\|", _sub_pipe, s)


def resolve_greeting(npc: Any) -> ResolvedGreeting | None:
    """Resolve the single greeting for no-keyword and degraded presentation paths.

    Precedence:
    1. db.npc_offline_greeting (plain text, non-empty, verbatim) -> is_override=True
    2. The authored default (``authored_greeting_for``): the dialogue table
       greeting, else the profile greeting -> is_override=False
    """
    field = getattr(getattr(npc, "db", None), "npc_offline_greeting", None)
    if isinstance(field, str) and field:
        return ResolvedGreeting(text=field, is_override=True)
    default = authored_greeting_for(npc)
    if default is not None:
        return ResolvedGreeting(text=default, is_override=False)
    return None


def authored_greeting_for(npc: Any) -> str | None:
    """Resolve the authored greeting below the editable instance field.

    The dialogue table greeting via ``greeting_for(npc)``, else the greeting of
    the profile named by the NPC's provenance, else ``None``. Never reads the
    instance field, so it is exactly what ``resolve_greeting`` answers once
    the field is cleared; the author editor previews it as the default.
    Read-only.
    """
    from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
    from world.rules.npc_persona import provenance_profile_key

    table_greeting = greeting_for(npc)
    if table_greeting is not None:
        return table_greeting
    key = provenance_profile_key(npc)
    if key is None:
        return None
    profile = NPC_PROFILE_REGISTRY.get(key)
    if profile is None:
        # observability: ignore R3: dangling profile reference is a non-exception integrity event
        log_error("npc_voice_profile_missing", context={"npc": str(getattr(npc, "pk", npc)), "profile": key})
        return None
    return profile.voice.greeting or None


def opens_dialogue(npc: Any) -> bool:
    """Whether a conversation can open on ``npc`` (the conversable-host gate).

    True for an ``LLMNPC`` (the generative host) or for a host carrying a
    ``ScriptedDialogue`` component whose ``dialogue_key`` resolves either in
    ``DIALOGUE_TABLE`` or to a generated role's current phase definition. A
    component host whose definition does not resolve has no greeting and no
    choices, so opening a session on it would be a dead end; the caller shows
    its disabled ``dialogue_unavailable`` affordance instead. The adapter and
    the exploration panel share this one predicate, so the rendered affordance
    and the committed action agree. Read-only.
    """
    from typeclasses.npcs import LLMNPC

    if isinstance(npc, LLMNPC):
        return True
    key = dialogue_key_for(npc)
    if key is None:
        return False
    return key in DIALOGUE_TABLE or _generated_dialogue_for_key(key) is not None


def dialogue_offline_response(npc: Any) -> str | None:
    """Return a generated host's current permitted offline response, or ``None``.

    A generated role always answers offline with its current phase's fixed
    offline response (design §6); an authored host has no such field, so the
    caller keeps its existing authored greeting/silence precedence.
    """
    generated = generated_dialogue_for(npc)
    return None if generated is None else generated.offline_response


@dataclass(frozen=True)
class ScriptedTalkResult:
    """One applied scripted talk: the response and whether the gain was capped."""

    response: str
    budget_capped: bool


def run_scripted_talk(npc: Any, character: Any, keyword: str) -> ScriptedTalkResult | None:
    """Apply one known-keyword scripted talk atomically and return the result.

    Shared by the text ``talk`` command and the webclient
    ``explore.talk_scripted`` path. A known keyword commits the +1 ``talk``
    affinity gain with the host in one transaction, restoring the relations
    surface on failure; unknown keywords and componentless hosts return their
    line without writing anything. The ``guild_staff`` ``回報`` action keyword
    is the authored exception: it resolves its read-only listing purely and
    never grants affinity (turn-in rewards follow the guild settlement
    contract).
    """
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

    response = dialogue_response(npc, character, keyword)
    if response is None:
        return None
    dialogue_key = dialogue_key_for(npc)
    if (
        dialogue_key == GUILD_STAFF_DIALOGUE_KEY
        and keyword == GUILD_STAFF_TURNIN_KEYWORD
    ):
        from typeclasses.components import GuildStaff

        if getattr(npc, "components", None) is not None and npc.components.has(
            GuildStaff.name
        ):
            return ScriptedTalkResult(response=response, budget_capped=False)
    if dialogue_key is None or not dialogue_has_keyword(dialogue_key, keyword):
        return ScriptedTalkResult(response=response, budget_capped=False)

    if generated_dialogue_for(npc) is not None:
        from world.rules.story_effects import apply_story_effect, effect_for_keyword

        declared = effect_for_keyword(npc, keyword)
        if declared is not None:
            verb, reference = declared
            apply_story_effect(
                npc, character, keyword=keyword, verb=verb, reference=reference
            )
            # An effect-bearing topic is the interaction: the fixed topic line is
            # the answer and no talk affinity is granted. A refused effect still
            # answers with that line (the deterministic APIs already rechecked
            # everything, and the refusal is logged by the effect boundary).
            return ScriptedTalkResult(response=response, budget_capped=False)

    relations_snapshot = attribute_snapshot(npc, "relations_data")
    try:
        from django.db import transaction

        with transaction.atomic():
            outcome = apply_affinity_change(npc, character, AffinitySource.TALK, 1)
    except Exception:
        restore_attribute_best_effort(npc, "relations_data", relations_snapshot)
        raise
    return ScriptedTalkResult(response=response, budget_capped=outcome.budget_capped)


# ---------------------------------------------------------------------------
# Dialogue session (webclient-align-07): the ONLY writers of
# ``db.dialogue_session`` on the character.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueSession:
    """One live dialogue session: the host dbid, the latest line, the tick.

    ``npc_id`` is a database identity re-resolved per read — the session never
    holds a live object reference. ``updated_tick`` is the world-clock tick at
    write time, or ``None`` when no clock singleton exists yet.
    """

    npc_id: int
    line: str | None
    updated_tick: int | None
    kind: str = "line"
    schema_version: int = 1
    host_key: str = ""
    source_identity: Any = None
    context_id: str = ""
    actor_id: int = 0
    owner_id: int = 0
    control_key: str = ""
    phase_revision: int | str | None = None
    line_delivery_id: str | None = None
    delivery: SceneDelivery | None = None
    selection_receipts: tuple[dict[str, Any], ...] = ()
    completion_receipts: tuple[dict[str, Any], ...] = ()


def _parse_delivery(raw: Any) -> SceneDelivery | None:
    """Parse stored delivery dictionary back to SceneDelivery."""
    if not isinstance(raw, Mapping):
        return None
    try:
        lines = []
        for item in raw.get("lines", ()):
            if not isinstance(item, Mapping):
                return None
            kind = item.get("kind")
            if kind == "speech":
                lines.append(Speech(speaker=item.get("speaker"), text=item.get("text")))
            elif kind == "narration":
                lines.append(Narration(text=item.get("text")))
            else:
                return None
        return SceneDelivery(
            delivery_id=str(raw["delivery_id"]),
            selection_id=str(raw["selection_id"]),
            context_id=str(raw["context_id"]),
            actor_id=int(raw["actor_id"]),
            owner_id=int(raw["owner_id"]),
            host_id=int(raw["host_id"]),
            topic_id=str(raw["topic_id"]) if raw.get("topic_id") is not None else None,
            scene_id=str(raw["scene_id"]),
            scene_revision=str(raw["scene_revision"]),
            phase_revision=raw.get("phase_revision"),
            kind=str(raw["kind"]),
            lines=tuple(lines),
            updated_tick=raw.get("updated_tick"),
        )
    except Exception:  # observability: ignore R2: corrupt delivery payload degrades to None
        return None


def _delivery_to_storage(delivery: SceneDelivery) -> dict[str, Any]:
    """Serialize SceneDelivery to a JSON-safe dictionary for storage."""
    wire = delivery_to_wire(delivery)
    if wire is None:
        return {}
    wire.update(
        {
            "actor_id": delivery.actor_id,
            "owner_id": delivery.owner_id,
            "host_id": delivery.host_id,
            "selection_id": delivery.selection_id,
            "updated_tick": delivery.updated_tick,
        }
    )
    return wire


def _parse_dialogue_session(raw: Any) -> DialogueSession | None:
    """Parse a stored session value, or ``None`` for absent/corrupt state.

    Read-only: a malformed value degrades to "no session" and is never repaired
    or rewritten here — the next clear seam or talk retires it. Accepts exactly
    the positive-int / str / ``int | None`` field shapes (``bool`` is rejected
    as an id/tick even though it subclasses ``int``).
    """
    # Evennia's persisted attribute value is a ``_SaverDict`` (a Mapping, not a
    # dict subclass) — the parse keys off the mapping interface.
    if not isinstance(raw, Mapping):
        return None
    npc_id = raw.get("npc_id")
    kind = raw.get("kind", "line")
    delivery_raw = raw.get("delivery")
    line = raw.get("line")
    updated_tick = raw.get("updated_tick")
    delivery = None

    if not isinstance(npc_id, int) or isinstance(npc_id, bool) or npc_id <= 0:
        return None
    if kind == "scene":
        delivery = _parse_delivery(delivery_raw)
        if delivery is None:
            return None
    elif not isinstance(line, str):
        return None
    # A stored line beyond the write bound or carrying unpaired surrogate code
    # points is corruption (webclient-align-10): the write path truncates and
    # never emits surrogates, so such a value can only come from damaged
    # storage. Corrupt state is "not live" here, which makes the dialogue
    # panel degrade through its REGISTERED unavailable form instead of
    # failing available-form validation as an internal presenter error.
    if line is not None:
        if len(line) > MAX_DIALOGUE_SESSION_LINE_CODE_POINTS:
            return None
        if any(0xD800 <= ord(char) <= 0xDFFF for char in line):
            return None
    if updated_tick is not None and (
        not isinstance(updated_tick, int) or isinstance(updated_tick, bool)
    ):
        return None

    sel_receipts = []
    for r in raw.get("selection_receipts", ()):
        if isinstance(r, Mapping):
            deliv = r.get("delivery")
            parsed_d = _parse_delivery(deliv) if isinstance(deliv, Mapping) else None
            sel_receipts.append(
                {
                    "topic_id": r.get("topic_id"),
                    "selection_id": r.get("selection_id"),
                    "delivery_id": r.get("delivery_id"),
                    "delivery": parsed_d,
                }
            )

    comp_receipts = []
    for c in raw.get("completion_receipts", ()):
        if isinstance(c, Mapping):
            comp_receipts.append(dict(c))

    raw_src = raw.get("source_identity")
    source_id = None
    if isinstance(raw_src, Mapping):
        if "package_id" in raw_src:
            source_id = GeneratedDialogueIdentity(
                raw_src["package_id"],
                raw_src["role_id"],
                raw_src["phase_id"],
            )
        elif "dialogue_key" in raw_src:
            source_id = StaticDialogueIdentity(
                raw_src["profile_key"],
                raw_src["dialogue_key"],
            )

    return DialogueSession(
        npc_id=npc_id,
        line=line if kind == "line" else None,
        updated_tick=updated_tick,
        kind=kind,
        schema_version=raw.get("schema_version", 1),
        host_key=str(raw.get("host_key", "")),
        source_identity=source_id,
        context_id=str(raw.get("context_id", "")),
        actor_id=int(raw.get("actor_id", 0)),
        owner_id=int(raw.get("owner_id", 0)),
        control_key=str(raw.get("control_key", "")),
        phase_revision=raw.get("phase_revision"),
        line_delivery_id=raw.get("line_delivery_id"),
        delivery=delivery,
        selection_receipts=tuple(sel_receipts),
        completion_receipts=tuple(comp_receipts),
    )


def _session_updated_tick() -> int | None:
    """Current world-clock tick, or ``None`` when no clock singleton exists.

    Uses the read-only ``read_world_clock`` accessor — opening a dialogue never
    materializes the clock Script.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return None if clock is None else int(clock.tick)


def refresh_dialogue_phase(character: Any, npc: Any) -> str | None:
    """Refresh a live session naming ``npc`` to the host's current fixed line.

    The deterministic phase-change seam (quest-scene-encounters 4.3/4.5): a
    generated role's phase moved on, so the existing session would otherwise
    present an obsolete greeting and obsolete choices. This re-records the
    current permitted greeting through the existing sole session writer and
    returns it; a character with no live session naming ``npc`` is left alone
    (``None``), and history is never rewritten. Read-only for everything except
    the one session attribute the sole writer owns.
    """
    session = live_dialogue_session(character)
    if session is None or session.npc_id != int(npc.pk):
        return None
    greeting = greeting_for(npc)
    if greeting is None:
        return None
    open_or_refresh_dialogue(character, npc, greeting)
    return greeting


def open_or_refresh_dialogue(
    character: Any,
    npc: Any,
    line: str | None = None,
    *,
    delivery: SceneDelivery | None = None,
    context: Any = None,
    selection_receipt: dict[str, Any] | None = None,
    completion_receipts: Any = (),
) -> DialogueSession:
    """Record one delivered server-authored line or scene delivery as character's session.

    The ONLY opener: called from the deterministic-core success paths (the
    ``explore.talk_open`` opener, the scripted adapter/command branches, and
    the freeform settled observer). Refreshing replaces the value in place
    (one session per character).
    """
    from world.rules.dialogue_context import resolve_dialogue_context

    existing = live_dialogue_session(character)
    npc_pk = int(getattr(npc, "pk", 0))

    if context is not None and getattr(context, "context_id", None):
        context_id = str(context.context_id)
        host_key = str(context.host_key)
        source_id = context.source_identity
        phase_rev = context.phase_revision
    elif existing is not None and existing.npc_id == npc_pk and existing.context_id:
        context_id = existing.context_id
        host_key = existing.host_key
        source_id = existing.source_identity
        phase_rev = existing.phase_revision
    else:
        ctx = resolve_dialogue_context(character, npc)
        context_id = uuid.uuid4().hex[:16]
        host_key = ctx.host_key
        source_id = ctx.source_identity
        phase_rev = ctx.phase_revision

    if existing is not None and existing.npc_id == npc_pk and existing.context_id == context_id:
        sel_receipts = list(existing.selection_receipts)
        comp_receipts = list(existing.completion_receipts)
    else:
        sel_receipts = []
        comp_receipts = []

    if selection_receipt is not None:
        t_id = selection_receipt.get("topic_id")
        replaced = False
        for idx, item in enumerate(sel_receipts):
            if item.get("topic_id") == t_id:
                sel_receipts[idx] = selection_receipt
                replaced = True
                break
        if not replaced:
            sel_receipts.append(selection_receipt)
        if len(sel_receipts) > 16:
            sel_receipts.pop(0)

    for c in completion_receipts:
        comp_receipts.append(c)
    if len(comp_receipts) > 32:
        comp_receipts = comp_receipts[-32:]

    kind = "scene" if delivery is not None else "line"
    stored_line = str(line)[:MAX_DIALOGUE_SESSION_LINE_CODE_POINTS] if line is not None else None
    line_delivery_id = uuid.uuid4().hex[:16] if kind == "line" else None
    actor_id = int(getattr(character, "pk", 0))
    owner_id = int(getattr(character, "pk", 0))
    control_key = f"{owner_id}:{actor_id}"
    updated_tick = _session_updated_tick()

    session = DialogueSession(
        npc_id=npc_pk,
        line=stored_line,
        updated_tick=updated_tick,
        kind=kind,
        schema_version=1,
        host_key=host_key,
        source_identity=source_id,
        context_id=context_id,
        actor_id=actor_id,
        owner_id=owner_id,
        control_key=control_key,
        phase_revision=phase_rev,
        line_delivery_id=line_delivery_id,
        delivery=delivery,
        selection_receipts=tuple(sel_receipts),
        completion_receipts=tuple(comp_receipts),
    )

    serialized_source = None
    if isinstance(source_id, StaticDialogueIdentity):
        serialized_source = {
            "profile_key": source_id.profile_key,
            "dialogue_key": source_id.dialogue_key,
        }
    elif isinstance(source_id, GeneratedDialogueIdentity):
        serialized_source = {
            "package_id": source_id.package_id,
            "role_id": source_id.role_id,
            "phase_id": source_id.phase_id,
        }

    character.db.dialogue_session = {
        "schema_version": 1,
        "kind": kind,
        "npc_id": npc_pk,
        "host_key": host_key,
        "source_identity": serialized_source,
        "context_id": context_id,
        "actor_id": actor_id,
        "owner_id": owner_id,
        "control_key": control_key,
        "phase_revision": phase_rev,
        "line": stored_line,
        "line_delivery_id": line_delivery_id,
        "delivery": _delivery_to_storage(delivery) if delivery else None,
        "selection_receipts": [
            {
                "topic_id": r.get("topic_id"),
                "selection_id": r.get("selection_id"),
                "delivery_id": r.get("delivery_id"),
                "delivery": _delivery_to_storage(r["delivery"])
                if isinstance(r.get("delivery"), SceneDelivery)
                else r.get("delivery"),
            }
            for r in sel_receipts
        ],
        "completion_receipts": list(comp_receipts),
        "updated_tick": updated_tick,
    }
    log_info(
        "dialogue_session_open",
        context={"char": str(getattr(character, "pk", "?")), "npc": str(session.npc_id)},
    )
    return session


def select_authored_topic(
    actor: Any,
    host: Any,
    topic_id: str,
    *,
    selection_id: str,
    expected_context_id: str | None,
    session: DialogueSession | None = None,
) -> SceneDelivery:
    """Select an authored topic and publish complete scene delivery atomically."""
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.dialogue_context import DialogueContext, resolve_dialogue_context
    from world.rules.dialogue_sources import resolve_dialogue_source
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

    context = resolve_dialogue_context(actor, host, session=session)

    # Context validation
    if expected_context_id is not None:
        if context.context_id is None or expected_context_id != context.context_id:
            raise StaleContextError("stale_context", "對話情境已過期。")
        target_context_id = context.context_id
    else:
        if context.context_id is not None:
            raise StaleContextError("stale_context", "已有進行中的對話。")
        target_context_id = uuid.uuid4().hex[:16]

    # Request dedup
    current_sess = session if session is not None else live_dialogue_session(actor)
    if (
        current_sess is not None
        and current_sess.npc_id == int(getattr(host, "pk", 0))
        and current_sess.context_id == target_context_id
    ):
        for receipt in current_sess.selection_receipts:
            if receipt.get("selection_id") == selection_id:
                if receipt.get("topic_id") != topic_id:
                    raise DuplicateSelectionError(
                        "selection_id_reused", "此選取識別碼已被用於不同話題。"
                    )
                if (
                    current_sess.delivery is not None
                    and current_sess.delivery.delivery_id == receipt.get("delivery_id")
                ):
                    return current_sess.delivery
                raise StaleSelectionError("stale_selection", "選取請求已過期。")

    source = resolve_dialogue_source(context)
    if source is None:
        raise DialogueSourceUnavailableError("no_source", "對方目前無法交談。")

    matched_topic = None
    for t in source.dialogue.topics:
        if t.topic_id == topic_id:
            matched_topic = t
            break
    if matched_topic is None:
        raise TopicNotFoundError("unknown_topic", "對方不明白這個話題。")

    if matched_topic.requires is not None or matched_topic.predecessors:
        raise TopicLockedError("topic_locked", "此話題目前無法選取。")

    owner = context.owner
    relations_snapshot = attribute_snapshot(host, "relations_data")
    session_snapshot = attribute_snapshot(owner, "dialogue_session")

    scene = matched_topic.fallback
    delivery_id = uuid.uuid4().hex[:16]
    delivery = SceneDelivery(
        delivery_id=delivery_id,
        selection_id=selection_id,
        context_id=target_context_id,
        actor_id=int(getattr(actor, "pk", 0)),
        owner_id=int(getattr(owner, "pk", 0)),
        host_id=int(getattr(host, "pk", 0)),
        topic_id=matched_topic.topic_id,
        scene_id=scene.scene_id,
        scene_revision=scene.revision,
        phase_revision=context.phase_revision,
        kind="formal",
        lines=scene.lines,
        updated_tick=_session_updated_tick(),
    )
    context_with_id = DialogueContext(
        actor=context.actor,
        owner=context.owner,
        host=context.host,
        host_key=context.host_key,
        source_identity=context.source_identity,
        context_id=target_context_id,
        phase_revision=context.phase_revision,
    )

    try:
        from django.db import transaction

        with transaction.atomic():
            apply_affinity_change(host, owner, AffinitySource.TALK, 1)
            open_or_refresh_dialogue(
                owner,
                host,
                delivery=delivery,
                context=context_with_id,
                selection_receipt={
                    "topic_id": matched_topic.topic_id,
                    "selection_id": selection_id,
                    "delivery_id": delivery_id,
                    "delivery": delivery,
                },
            )
    except Exception:
        restore_attribute_best_effort(host, "relations_data", relations_snapshot)
        restore_attribute_best_effort(owner, "dialogue_session", session_snapshot)
        raise

    return delivery


def clear_dialogue_session(character: Any, npc: Any | None = None) -> bool:
    """Retire the character's session, returning whether one was cleared.

    With ``npc`` set, only a session naming that NPC is cleared (the departure
    seams never touch another host's session); ``npc=None`` is the unconditional
    clear used by movement settlement and combat engage. An absent or corrupt
    value is a no-op ``False``. ``npc`` may be a live object or a pre-captured
    positive dbid — deletion hooks run after the object's ``pk`` is gone, and
    an unresolvable host id is a no-op (it never matches a stored session).
    The ``explore.dialogue_leave`` adapter's success path is the explicit
    exit seam (webclient-align-11): it re-checks liveness itself and clears
    unconditionally.
    """
    session = _parse_dialogue_session(character.db.dialogue_session)
    if session is None:
        if npc is None and character.db.dialogue_session is not None:
            # Unconditional clear also retires a corrupt stored value.
            character.db.dialogue_session = None
            log_info(
                "dialogue_session_clear",
                context={
                    "char": str(getattr(character, "pk", "?")),
                    "npc": "corrupt",
                    "reason": "unconditional",
                },
            )
            return True
        return False
    if npc is not None:
        host_id = npc if isinstance(npc, int) else getattr(npc, "pk", None)
        if not isinstance(host_id, int) or int(host_id) != session.npc_id:
            return False
    character.db.dialogue_session = None
    log_info(
        "dialogue_session_clear",
        context={
            "char": str(getattr(character, "pk", "?")),
            "npc": str(session.npc_id),
            "reason": "named" if npc is not None else "unconditional",
        },
    )
    return True


def live_dialogue_session(character: Any) -> DialogueSession | None:
    """The character's session iff its host still resolves as present+interactable.

    A stale dbid (deleted object, departed NPC, or a host whose schedule state
    no longer allows talk) is reported as not live — the stored value is left
    in place for the next clear seam or talk to retire, mirroring the party
    module's stale-dbid filtering. ``intent_context_ok`` is the canonical
    co-location + talk-interactability gate.
    """
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.npc_intents import intent_context_ok

    session = _parse_dialogue_session(character.db.dialogue_session)
    if session is None:
        return None
    obj = ObjectDB.objects.filter(id=session.npc_id).first()
    if obj is None or not isinstance(obj, NPC):
        return None
    if not intent_context_ok(obj, character):
        return None
    return session
