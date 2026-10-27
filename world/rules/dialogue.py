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

Formal topic selection is the sole writing path: ``select_authored_topic``
delivers one complete scene and grants the capped +1 talk affinity for an
informational topic through the sole-writer affinity API in one transaction.
Generated roles read their complete declarations from the quest-owned immutable
package through :func:`generated_phase_binding`; there is no generated
keyword-response or scripted-talk writer.

The module also owns the character-held dialogue session (webclient-align-07)
as its ONLY read/write surface: ``open_or_refresh_dialogue`` /
``clear_dialogue_session`` / ``live_dialogue_session``. Persistent
``db.dialogue_session`` on the character is the single truth of WHO the
character is speaking to and the latest server-authored LINE; no presenter,
AI layer, or client payload may open, refresh, or clear it.
The opener success paths are the ``explore.talk_open`` opener (a conversation
with the host's greeting, or the fixed fallback line), the
``explore.talk_scripted`` and ``explore.talk_freeform`` adapters, and the
``talk`` text command's authored topic deliveries (its keyword-less greeting
stays text-only).
The clear seams are: movement settlement, combat engage, NPC departure
cleanup, and the ``explore.dialogue_leave`` adapter's explicit exit
(webclient-align-11) — the adapter calls ``clear_dialogue_session`` here and
never touches ``db`` itself.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any
import uuid

from world.lore.dialogue.codec import GeneratedDialogueIdentity, StaticDialogueIdentity
from world.lore.scenes import Narration, Scene, Speech, scene_canonical_bytes

from typeclasses.components import ScriptedDialogue

from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.dialogue.services import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
)
from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse
from world.observability import log_error, log_info

#: The guild counter's dialogue key and deterministic report keyword are owned
#: by the dialogue-service association contract (``world.lore.dialogue.
#: services``) and re-exported here for every historical import path.

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


class TopicNotFoundError(DialogueRuntimeError):
    """Topic was not found in the host's current definition."""


class DialogueSourceUnavailableError(DialogueRuntimeError):
    """Host has no conversable dialogue source."""


class DialogueBudgetExceededError(DialogueRuntimeError):
    """Payload exceeds canonical UTF-8 JSON scene, bundle, or panel limits."""


class DialogueCompletionError(DialogueRuntimeError):
    """A formal reading acknowledgement cannot be accepted.

    ``code`` is the stable refusal identity: ``dialogue_context_closed`` (no
    live authenticated conversation), ``dialogue_receipt_unknown`` (the
    delivery was never issued in the current context set),
    ``dialogue_receipt_foreign`` (another owner/actor or host binding),
    ``dialogue_receipt_stale`` (context, topic, phase or exact scene revision
    no longer match), ``dialogue_receipt_kind`` (not a formal delivery) and
    ``dialogue_predecessor_unread`` (a public successor whose predecessor
    reading is not saved yet). None of them writes reading or gameplay state.
    """


DIALOGUE_SCENE_MAX_BYTES = 8192
DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES = 16384
DIALOGUE_PANEL_MAX_BYTES = 24576

# Server-issued completion receipts (Shared contract v2): one formal receipt
# per topic for the most recently issued delivery, keeping the latest and
# previous delivery per topic inside a <=32 row context bound.
MAX_COMPLETION_RECEIPTS = 32
MAX_RECEIPTS_PER_TOPIC = 2
MAX_COMPLETION_PREDECESSORS = 16
MAX_CHAIN_SUCCESSORS = 15

COMPLETION_CLOSED = "dialogue_context_closed"
COMPLETION_RECEIPT_UNKNOWN = "dialogue_receipt_unknown"
COMPLETION_RECEIPT_FOREIGN = "dialogue_receipt_foreign"
COMPLETION_RECEIPT_STALE = "dialogue_receipt_stale"
COMPLETION_RECEIPT_KIND = "dialogue_receipt_kind"
COMPLETION_PREDECESSOR_UNREAD = "dialogue_predecessor_unread"


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
    # Server-only effect feedback for the delivering surface: the +1 talk
    # affinity this selection attempted was blocked by the daily interaction
    # budget. ``delivery_to_wire`` whitelists the wire fields, so it can never
    # reach the panel, the session storage or a client payload; a replay
    # reconstructs the delivery without it and re-sends no hint.
    affinity_budget_capped: bool = False


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
class PureChainNode:
    """One pre-delivered public successor: its delivered scene and gates."""

    delivery: SceneDelivery
    predecessors: tuple[str, ...]


@dataclass(frozen=True)
class CompletionOutcome:
    """The accepted acknowledgement's status and the owner's reading revision."""

    status: str
    reading_revision: int


def _receipt_for(
    delivery: SceneDelivery, predecessors: Any = ()
) -> dict[str, Any]:
    """The exact completion receipt row for one formal delivered scene.

    Owner/body/host/control are inherited from the parent session, so the row
    carries only what completion must match: the delivery identity, the context
    and topic it was issued in, the exact authored scene revision, the phase it
    was issued under, and the public-chain gates it must satisfy.
    """
    bounded: list[str] = []
    for predecessor in predecessors or ():
        if (
            isinstance(predecessor, str)
            and predecessor
            and len(predecessor) <= 2048
            and predecessor not in bounded
        ):
            bounded.append(predecessor)
    return {
        "delivery_id": delivery.delivery_id,
        "context_id": delivery.context_id,
        "topic_id": delivery.topic_id,
        "scene_revision": delivery.scene_revision,
        "phase_revision": delivery.phase_revision,
        "kind": delivery.kind,
        "predecessors": bounded[:MAX_COMPLETION_PREDECESSORS],
    }


def _normalize_completion_receipt(raw: Any) -> dict[str, Any] | None:
    """One stored receipt row in exact bounded form, or ``None`` when invalid."""
    if not isinstance(raw, Mapping):
        return None
    delivery_id = raw.get("delivery_id")
    context_id = raw.get("context_id")
    topic_id = raw.get("topic_id")
    scene_revision = raw.get("scene_revision")
    for value, maximum in (
        (delivery_id, 64),
        (context_id, 64),
        (topic_id, 2048),
        (scene_revision, 64),
    ):
        if not isinstance(value, str) or not value or len(value) > maximum:
            return None
    if raw.get("kind") != "formal":
        # Refusal, opening and service deliveries never hold a receipt.
        return None
    phase_revision = raw.get("phase_revision")
    if phase_revision is not None and (
        isinstance(phase_revision, bool) or not isinstance(phase_revision, (int, str))
    ):
        return None
    raw_preds = raw.get("predecessors", ())
    # Evennia persists lists as ``_SaverList`` (a MutableSequence, not a list
    # subclass), so the stored value is classified by the sequence protocol.
    if isinstance(raw_preds, (str, bytes)) or not isinstance(raw_preds, Sequence):
        return None
    predecessors: list[str] = []
    for predecessor in raw_preds:
        if (
            not isinstance(predecessor, str)
            or not predecessor
            or len(predecessor) > 2048
        ):
            return None
        if predecessor not in predecessors:
            predecessors.append(predecessor)
    if len(predecessors) > MAX_COMPLETION_PREDECESSORS:
        return None
    return {
        "delivery_id": delivery_id,
        "context_id": context_id,
        "topic_id": topic_id,
        "scene_revision": scene_revision,
        "phase_revision": phase_revision,
        "kind": "formal",
        "predecessors": predecessors,
    }


def _merge_completion_receipts(existing: Any, new: Any = ()) -> list[dict[str, Any]]:
    """Append receipts under the bounded per-topic and total contract.

    Malformed rows are dropped, a repeated delivery identity replaces its row,
    a third receipt for one topic retires that topic's oldest receipt, and the
    whole set keeps its insertion order up to the total bound. The stored row
    keeps the previous delivery of the same topic acknowledgeable until it is
    superseded, so a delayed completion from another topic stays valid.
    """
    merged: list[dict[str, Any]] = []
    for raw in list(existing or ()) + list(new or ()):
        receipt = _normalize_completion_receipt(raw)
        if receipt is None:
            continue
        for index, item in enumerate(merged):
            if item["delivery_id"] == receipt["delivery_id"]:
                merged[index] = receipt
                break
        else:
            merged.append(receipt)
        same_topic = [
            index
            for index, item in enumerate(merged)
            if item["topic_id"] == receipt["topic_id"]
        ]
        if len(same_topic) > MAX_RECEIPTS_PER_TOPIC:
            del merged[same_topic[0]]
        if len(merged) > MAX_COMPLETION_RECEIPTS:
            del merged[: len(merged) - MAX_COMPLETION_RECEIPTS]
    return merged


def _public_chain_topics(source: Any, root_id: str) -> tuple[Any, ...]:
    """The eligible public successor closure of ``root_id``, predecessor-first.

    A candidate qualifies only when it is declared ``pure_chain``, declares no
    ``requires`` (a public node is effect-free and unqualified) and EVERY one of
    its predecessors is the root or an already-qualified node. Traversal
    therefore stops at a qualification boundary: a qualified topic is never
    added to the eligible set, so nothing behind it can be bundled, and a node
    that needs an out-of-chain predecessor is omitted together with its
    dependents. Declaration order breaks ties, making the order deterministic.
    """
    eligible = {root_id}
    ordered: list[Any] = []
    changed = True
    while changed and len(ordered) < MAX_CHAIN_SUCCESSORS:
        changed = False
        for topic in source.dialogue.topics:
            if topic.topic_id in eligible:
                continue
            if getattr(topic, "disclosure", "qualified") != "pure_chain":
                continue
            if getattr(topic, "requires", None) is not None:
                continue
            predecessors = tuple(getattr(topic, "predecessors", ()) or ())
            if not predecessors or not all(p in eligible for p in predecessors):
                continue
            ordered.append(topic)
            eligible.add(topic.topic_id)
            changed = True
            if len(ordered) >= MAX_CHAIN_SUCCESSORS:
                break
    return tuple(ordered)


def _chain_scene(topic: Any, revision: str, context: Any) -> Any | None:
    """The candidate scene of ``topic`` whose exact revision is ``revision``."""
    from world.rules.dialogue_conditions import select_scene_variant

    selected = select_scene_variant(topic, context)
    if selected.revision == revision:
        return selected
    candidates = [topic.fallback] + [
        variant.scene for variant in getattr(topic, "variants", ())
    ]
    for candidate in candidates:
        if candidate.revision == revision:
            return candidate
    return None


def chain_deliveries(
    session: "DialogueSession", host: Any, *, actor: Any = None
) -> tuple[PureChainNode, ...]:
    """Re-derive the current delivery's public chain from retained receipts.

    The chain is anchored to the session's CURRENT scene delivery: only nodes
    reachable from that root through retained receipt rows appear, so a
    predecessor delivered by an earlier selection can never make old playback
    current again while its receipt still serves a delayed acknowledgement.
    Each node keeps the exact authored bytes by requiring the receipt's scene
    revision, omits its dependents when that body no longer resolves, and is
    emitted in predecessor order. Pure: no selection, receipt or reading write.
    """
    delivery = session.delivery
    if session.kind != "scene" or delivery is None or delivery.kind != "formal":
        return ()
    root = delivery.topic_id
    if not root:
        return ()
    from world.rules.dialogue_availability import availability_context
    from world.rules.dialogue_sources import resolve_dialogue_source

    context = availability_context(actor, host)
    source = resolve_dialogue_source(context)
    if source is None:
        return ()
    latest: dict[str, dict[str, Any]] = {}
    for raw in session.completion_receipts:
        receipt = _normalize_completion_receipt(raw)
        if receipt is None or not receipt["predecessors"]:
            continue
        if receipt["context_id"] != session.context_id:
            continue
        if receipt["phase_revision"] != session.phase_revision:
            continue
        latest[receipt["topic_id"]] = receipt
    selected = {root}
    nodes: list[PureChainNode] = []
    changed = True
    while changed and len(nodes) < MAX_CHAIN_SUCCESSORS:
        changed = False
        for raw in session.completion_receipts:
            receipt = _normalize_completion_receipt(raw)
            if receipt is None or not receipt["predecessors"]:
                continue
            topic_id = receipt["topic_id"]
            if topic_id in selected:
                continue
            if not all(p in selected for p in receipt["predecessors"]):
                continue
            chosen = latest.get(topic_id)
            if chosen is None:
                continue
            topic = next(
                (
                    candidate
                    for candidate in source.dialogue.topics
                    if candidate.topic_id == topic_id
                ),
                None,
            )
            if topic is None:
                continue
            # Only an eligible public successor is chain-eligible. A qualified
            # topic's retained receipt still serves a delayed acknowledgement,
            # but its protected body must never be replayed as chain content
            # after the reader selected it explicitly.
            if getattr(topic, "disclosure", "qualified") != "pure_chain":
                continue
            if getattr(topic, "requires", None) is not None:
                continue
            scene = _chain_scene(topic, chosen["scene_revision"], context)
            if scene is None:
                # The authored bytes behind this receipt no longer resolve:
                # omit the node and every dependent node rather than ship a
                # different scene than the receipt acknowledges.
                continue
            selected.add(topic_id)
            nodes.append(
                PureChainNode(
                    delivery=SceneDelivery(
                        delivery_id=chosen["delivery_id"],
                        selection_id="",
                        context_id=chosen["context_id"],
                        actor_id=session.actor_id,
                        owner_id=session.owner_id,
                        host_id=int(getattr(host, "pk", 0) or 0),
                        topic_id=topic_id,
                        scene_id=scene.scene_id,
                        scene_revision=scene.revision,
                        phase_revision=chosen["phase_revision"],
                        kind="formal",
                        lines=scene.lines,
                        updated_tick=session.updated_tick,
                    ),
                    predecessors=tuple(chosen["predecessors"]),
                )
            )
            changed = True
            if len(nodes) >= MAX_CHAIN_SUCCESSORS:
                break
    return tuple(nodes)


@dataclass(frozen=True)
class GeneratedPhaseBinding:
    """One generated host's trusted, currently permitted phase.

    Server-only: the package/role pair comes from the host's stable dialogue
    binding, and the phase/revision are re-read from the quest-owned runtime
    store on every call. ``phase`` carries the complete immutable scene
    declarations (topics, effects, freeform facts, greeting and offline reply).
    """

    package_id: str
    role_id: str
    phase_id: str
    revision: int
    phase: Any
    definition: Any


def generated_dialogue_parts(dialogue_key: str | None) -> tuple[str, str] | None:
    """Split a trusted ``scene_role:<package>:<role>`` key, or ``None``."""
    if not isinstance(dialogue_key, str) or not dialogue_key.startswith(
        GENERATED_DIALOGUE_PREFIX
    ):
        return None
    package_id, _, role_id = dialogue_key[len(GENERATED_DIALOGUE_PREFIX):].partition(":")
    if not package_id or not role_id:
        return None
    return package_id, role_id


def generated_phase_binding(npc: Any) -> GeneratedPhaseBinding | None:
    """Resolve one generated host's trusted current phase, or ``None``.

    Every gate is deterministic and read-only: the published immutable package,
    the exact role-to-actor binding, the conversable role definition, and the
    current selected phase with its monotonic revision. A payload that no
    longer validates (including the removed response-only shape) and a binding
    that names another actor both yield ``None``; no partial or converted view
    is produced.
    """
    parts = generated_dialogue_parts(dialogue_key_for(npc))
    if parts is None:
        return None
    package_id, role_id = parts
    from world.quests import scene_store

    row = scene_store.read_package(package_id)
    if row is None or row.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        return None
    binding = scene_store.get_role_binding(package_id, role_id)
    if binding is None or int(binding.npc_id) != int(getattr(npc, "pk", 0)):
        return None
    definition = _validated_package(package_id, row.payload)
    if definition is None:
        return None
    role = definition.role(role_id)
    if role is None or not role.conversable:
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
    return GeneratedPhaseBinding(
        package_id=package_id,
        role_id=role_id,
        phase_id=phase.phase_id,
        revision=revision,
        phase=phase,
        definition=definition,
    )


def _validated_package(package_id: str, payload: Any) -> Any | None:
    """Return one published payload's validated definition (shared cache).

    The definition is cached by package id inside the validator (a published
    payload is immutable and its id IS the content digest); the *selected phase*
    stays runtime state and is read fresh on every call.
    """
    from world.quests.scene_package import validated_package

    return validated_package(package_id, payload)


def dialogue_phase_revision(npc: Any) -> int | None:
    """Return the current phase revision of a generated host, or ``None``."""
    binding = generated_phase_binding(npc)
    return None if binding is None else binding.revision


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

    This is the static authored-table line view retained for the legacy
    authored rows. Generated roles answer through the common scene provider
    (``resolve_dialogue_source``) and never through a keyword line.
    """
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
    """Whether ``keyword`` resolves in the named authored table."""
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return False
    return any(entry.keyword == keyword for entry in definition.responses)


def dialogue_topic_keywords(npc: Any) -> tuple[str, ...]:
    """Return the ordered keyword identities of a host's static authored table.

    This is the compatibility fallback for a host whose static table still has
    no validated scene source. Generated roles answer through the shared
    availability projection; when their source cannot be resolved they have no
    choices at all, so this returns an empty tuple for them.
    """
    key = dialogue_key_for(npc)
    if key is None:
        return ()
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
    binding = generated_phase_binding(npc)
    if binding is not None:
        return binding.phase.greeting
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
    ``ScriptedDialogue`` component whose trusted source resolves. A component
    host whose source does not resolve has no greeting and no choices, so
    opening a session on it would be a dead end; the caller shows its disabled
    ``dialogue_unavailable`` affordance instead. The adapter and the exploration
    panel share this one predicate, so the rendered affordance and the committed
    action agree. Read-only.
    """
    from typeclasses.npcs import LLMNPC

    if isinstance(npc, LLMNPC):
        return True
    key = dialogue_key_for(npc)
    if key is None:
        return False
    if key in DIALOGUE_TABLE:
        return True
    from world.rules.dialogue_sources import dialogue_source_for_host

    return dialogue_source_for_host(npc) is not None


def authorized_dialogue_open(actor: Any, host: Any) -> bool:
    """Whether ``actor`` may open authored conversation with ``host`` right now.

    An ordinary player keeps the existing host-only answer. A possessed acting
    body additionally needs the complete possession authorization *and* an
    authored source on the host: the newly authorized surface is authored
    scene dialogue, so a freeform-only ``LLMNPC`` stays refused while
    possessed. Schedule blocking stays out of this predicate (the vocabulary
    keeps blocked hosts enumerated; only executable cards are filtered).
    Read-only and never raises.
    """
    from typeclasses.characters import PlayerCharacter

    if isinstance(actor, PlayerCharacter):
        return True
    from world.rules.dialogue_context import DialogueContextError, resolve_dialogue_context
    from world.rules.dialogue_sources import resolve_dialogue_source

    try:
        context = resolve_dialogue_context(actor, host)
    except DialogueContextError:  # observability: ignore R2: an unauthorized context is the disabled-row answer, not a failure
        return False
    except Exception:  # observability: ignore R2: an unreadable context authorizes nothing and disables the row
        return False
    return resolve_dialogue_source(context) is not None


def dialogue_offline_response(npc: Any) -> str | None:
    """Return a generated host's current permitted offline response, or ``None``.

    A generated role always answers offline with its current phase's fixed
    offline response (design §6); an authored host has no such field, so the
    caller keeps its existing authored greeting/silence precedence.
    """
    binding = generated_phase_binding(npc)
    return None if binding is None else binding.phase.offline_response


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

    # Read-side normalization applies the same exact row schema and the same
    # per-topic/total bounds as the writer, so a malformed persisted list can
    # never present an out-of-contract receipt set to a reader.
    comp_receipts = _merge_completion_receipts((), raw.get("completion_receipts", ()))

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
    (one session per acting body). The session belongs to the actor, never to
    the owner: a possessed companion carries its own ``db.dialogue_session``
    while ``owner_id`` and the control key record the owning player.
    """
    from world.rules.dialogue_context import control_key_for, resolve_dialogue_context

    existing = live_dialogue_session(character)
    npc_pk = int(getattr(npc, "pk", 0))
    ctx = context if context is not None else resolve_dialogue_context(character, npc)
    owner = ctx.owner
    control_key = control_key_for(character, owner)
    same_control = existing is not None and existing.control_key == control_key

    # A reused context must still name the SAME host, source identity (for a
    # generated role that identity carries the phase) and phase revision. A
    # changed phase or rebound role retires the old context and both receipt
    # sets, so an obsolete delivery can never be replayed under the new one.
    reusable_existing = bool(
        same_control
        and existing is not None
        and existing.npc_id == npc_pk
        and existing.context_id
        and existing.host_key == str(ctx.host_key)
        and existing.source_identity == ctx.source_identity
        and existing.phase_revision == ctx.phase_revision
    )

    if getattr(ctx, "context_id", None):
        context_id = str(ctx.context_id)
        host_key = str(ctx.host_key)
        source_id = ctx.source_identity
        phase_rev = ctx.phase_revision
    elif reusable_existing and existing is not None:
        context_id = existing.context_id
        host_key = existing.host_key
        source_id = existing.source_identity
        phase_rev = existing.phase_revision
    else:
        context_id = uuid.uuid4().hex[:16]
        host_key = ctx.host_key
        source_id = ctx.source_identity
        phase_rev = ctx.phase_revision

    if reusable_existing and existing is not None and existing.context_id == context_id:
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

    comp_receipts = _merge_completion_receipts(comp_receipts, completion_receipts)

    kind = "scene" if delivery is not None else "line"
    stored_line = str(line)[:MAX_DIALOGUE_SESSION_LINE_CODE_POINTS] if line is not None else None
    line_delivery_id = uuid.uuid4().hex[:16] if kind == "line" else None
    actor_id = int(getattr(character, "pk", 0))
    owner_id = int(getattr(owner, "pk", 0) or 0)
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
    # Every successful open or selection re-projects and refreshes availability
    # after commit (the one non-mutation cause this slice adds). Committed
    # mutation sources call the same API from their owning writers.
    from world.rules.dialogue_availability import refresh_dialogue_availability

    refresh_dialogue_availability(owner, cause="open")
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
    """Select an authored topic and publish complete scene delivery atomically.

    The projection is the single availability authority: an absent (hidden)
    row behaves exactly like an unknown topic, a locked row delivers its
    authored refusal with zero effects, and an open row delivers the currently
    authorized scene. Every rejection is reported once through the boundary
    event with identifiers only.
    """
    from world.rules.dialogue_context import DialogueContextError

    try:
        return _select_authored_topic(
            actor,
            host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=expected_context_id,
            session=session,
        )
    except (DialogueRuntimeError, DialogueContextError) as error:
        log_info(
            "dialogue_selection_rejected",
            context={
                "char": str(getattr(actor, "pk", "?")),
                "actor": str(getattr(actor, "pk", "?")),
                "npc": str(getattr(host, "pk", "?")),
                "topic": str(topic_id),
                "context": str(expected_context_id or "?"),
                "reason": str(getattr(error, "code", None) or getattr(error, "reason", "?")),
            },
        )
        raise


def _select_authored_topic(
    actor: Any,
    host: Any,
    topic_id: str,
    *,
    selection_id: str,
    expected_context_id: str | None,
    session: DialogueSession | None = None,
) -> SceneDelivery:
    """The selection body behind the reported :func:`select_authored_topic`."""
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.dialogue_context import DialogueContext, resolve_dialogue_context
    from world.rules.dialogue_sources import resolve_dialogue_source
    from world.rules.npc_schedules import interaction_reason
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

    context = resolve_dialogue_context(actor, host, session=session)

    # The deterministic selection boundary rechecks the host's talk schedule:
    # a direct API call must reject a busy host before any effect or delivery,
    # exactly like the web and text entry surfaces do.
    if interaction_reason(host, "talk") is not None:
        from world.rules.dialogue_context import DialogueContextError

        raise DialogueContextError("schedule_blocked")

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
    # The source-owner phase revision is authoritative for a generated scene;
    # a brand-new context has no stored revision yet, so the live one is
    # recorded with the delivery and its session.
    phase_revision = (
        source.phase_revision
        if source.phase_revision is not None
        else context.phase_revision
    )

    matched_topic = None
    for t in source.dialogue.topics:
        if t.topic_id == topic_id:
            matched_topic = t
            break
    if matched_topic is None:
        raise TopicNotFoundError("unknown_topic", "對方不明白這個話題。")

    # The shared projection is the ONLY availability authority: the same rows
    # the panel and the affordance vocabulary published decide this selection,
    # re-read against current canonical state. A hidden row is indistinguishable
    # from an unknown topic; a locked row plays its authored refusal.
    from world.rules.dialogue_availability import TOPIC_LOCKED, project_topics
    from world.rules.dialogue_conditions import select_scene_variant

    projected = {
        row.topic_id: row
        for row in project_topics(context, context_id=target_context_id)
    }
    row = projected.get(matched_topic.topic_id)
    if row is None:
        raise TopicNotFoundError("unknown_topic", "對方不明白這個話題。")
    if row.availability == TOPIC_LOCKED:
        # A visibly locked topic stays selectable and plays its authored
        # refusal; it grants no effect and never exposes the formal body.
        kind = "refusal"
        scene = matched_topic.refusal
    else:
        kind = "formal"
        scene = select_scene_variant(matched_topic, context)
    # A declared effect is settled only for a formal, qualified selection. Its
    # authorization is rechecked inside the settlement transaction, so the
    # delivered kind can still fall back to the author's safe refusal.
    requested_effect = (
        source.effects.get(matched_topic.topic_id) if kind == "formal" else None
    )

    owner = context.owner
    from web.webclient.presentation.protocol import json_byte_size

    # 1. Scene canonical UTF-8 JSON bytes check
    scene_bytes = (
        scene_canonical_bytes(scene)
        if hasattr(scene, "lines")
        else json_byte_size(scene)
    )
    if scene_bytes > DIALOGUE_SCENE_MAX_BYTES:
        raise DialogueBudgetExceededError(
            "dialogue_scene_oversized",
            f"Scene {getattr(scene, 'scene_id', '')} ({scene_bytes} bytes) exceeds limit of {DIALOGUE_SCENE_MAX_BYTES}",
        )

    # 2. Delivery plus its eligible public successor bundle. A refusal is not a
    # chain delivery and reveals no successor, so only a formal selection is
    # measured with the exact closure it is about to pre-deliver: an
    # undelivered successor's protected size never blocks the permitted
    # refusal, and a qualified descendant is never part of the bundle.
    chain_topics = (
        _public_chain_topics(source, matched_topic.topic_id)
        if kind == "formal"
        else ()
    )
    if kind == "formal":
        bundle_bytes = scene_bytes
        for successor in chain_topics:
            successor_scenes = [successor.fallback] + [
                variant.scene for variant in getattr(successor, "variants", ())
            ]
            bundle_bytes += max(
                (
                    scene_canonical_bytes(candidate)
                    if hasattr(candidate, "lines")
                    else json_byte_size(candidate)
                )
                for candidate in successor_scenes
            )
        if bundle_bytes > DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES:
            raise DialogueBudgetExceededError(
                "dialogue_bundle_oversized",
                f"Selected delivery bundle ({bundle_bytes} bytes) exceeds limit of {DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES}",
            )

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
        phase_revision=phase_revision,
        kind=kind,
        lines=scene.lines,
        updated_tick=_session_updated_tick(),
    )

    # Pre-delivered public successors: exact scenes plus a server-issued
    # receipt each, so an acknowledgement can never name an undelivered node.
    # They carry no selection receipt and grant no effect (no affinity): the
    # root is the interaction, the successors are reading progress only.
    chain_nodes: list[PureChainNode] = []
    completion_receipts: list[dict[str, Any]] = []
    if kind == "formal":
        completion_receipts.append(
            _receipt_for(delivery, getattr(matched_topic, "predecessors", ()))
        )
        for successor in chain_topics:
            successor_scene = select_scene_variant(successor, context)
            node_delivery = SceneDelivery(
                delivery_id=uuid.uuid4().hex[:16],
                selection_id="",
                context_id=target_context_id,
                actor_id=int(getattr(actor, "pk", 0)),
                owner_id=int(getattr(owner, "pk", 0)),
                host_id=int(getattr(host, "pk", 0)),
                topic_id=successor.topic_id,
                scene_id=successor_scene.scene_id,
                scene_revision=successor_scene.revision,
                phase_revision=phase_revision,
                kind="formal",
                lines=successor_scene.lines,
                updated_tick=delivery.updated_tick,
            )
            chain_nodes.append(
                PureChainNode(
                    delivery=node_delivery,
                    predecessors=tuple(getattr(successor, "predecessors", ()) or ()),
                )
            )
            completion_receipts.append(
                _receipt_for(
                    node_delivery, getattr(successor, "predecessors", ())
                )
            )

    # 3. Preview resulting dialogue panel budget check
    from web.webclient.presentation.affordances import _scripted_keyword_descriptors
    from web.webclient.presentation.dialogue import DIALOGUE_MAX_CHOICES

    choices = _scripted_keyword_descriptors(
        host, actor=actor, context_id=target_context_id
    )[:DIALOGUE_MAX_CHOICES]
    preview_panel = {
        "schema_version": 3,
        "available": True,
        "kind": "dialogue",
        "host": {
            "identity": int(getattr(host, "pk", 1)),
            "display_name": getattr(host, "key", "")[:64],
            "portrait_ref": None,
        },
        "actor": {
            "identity": int(getattr(actor, "pk", 1)),
            "display_name": getattr(actor, "key", "")[:64],
            "portrait_ref": None,
        },
        "bond_stage": None,
        "context_id": target_context_id,
        "delivery": delivery_to_wire(delivery),
        "choices": choices,
        "pure_chain": [
            {
                "delivery": delivery_to_wire(node.delivery),
                "predecessors": list(node.predecessors),
            }
            for node in chain_nodes
        ],
        "reading_revision": 0,
        "completed_topic_ids": [],
        "unlock_batch": None,
    }
    if json_byte_size(preview_panel) > DIALOGUE_PANEL_MAX_BYTES:
        raise DialogueBudgetExceededError(
            "dialogue_panel_oversized",
            f"Resulting dialogue panel ({json_byte_size(preview_panel)} bytes) exceeds limit of {DIALOGUE_PANEL_MAX_BYTES}",
        )

    relations_snapshot = attribute_snapshot(host, "relations_data")
    session_snapshot = attribute_snapshot(actor, "dialogue_session")
    quest_snapshot = None
    escort_effect = False
    escort_actors: tuple[Any, ...] = ()
    if requested_effect is not None:
        from world.quests.transitions import snapshot_quest_log

        quest_snapshot = snapshot_quest_log(owner)
        escort_effect = _is_escort_effect(requested_effect.reference)
        if escort_effect:
            escort_actors = _escort_effect_actors(
                requested_effect.reference, context.source_identity
            )

    context_with_id = DialogueContext(
        actor=context.actor,
        owner=context.owner,
        host=context.host,
        host_key=context.host_key,
        source_identity=context.source_identity,
        context_id=target_context_id,
        phase_revision=phase_revision,
    )

    from contextlib import ExitStack

    compensation = ExitStack()
    if escort_effect:
        # The shared receipt owns one compensation stack for the complete
        # selection transaction, so a later session-write failure restores every
        # scope acceptance touched. The accepting package scope is enlisted
        # BEFORE acceptance performs any write (a later enlistment would
        # snapshot already-mutated state), and the new protected actors are
        # captured explicitly because they are not yet in any record.
        from world.quests.escort_events import (
            enlist_escort_scope,
            escort_event_boundary,
        )

        compensation.enter_context(escort_event_boundary((owner,)))
        package_id = getattr(context.source_identity, "package_id", None)
        if isinstance(package_id, str) and package_id:
            enlist_escort_scope(owner, package_id)
        if escort_actors:
            from world.quests.escort_lifecycle import escort_compensation

            compensation.enter_context(escort_compensation(owner, escort_actors))

    try:
        from django.db import transaction

        with compensation, transaction.atomic():
            from typeclasses.components import GuildStaff
            is_guild_staff = (
                getattr(host, "components", None) is not None
                and host.components.has(GuildStaff.name)
            )
            is_turnin = (
                context.source_identity is not None
                and getattr(context.source_identity, "dialogue_key", "") == GUILD_STAFF_DIALOGUE_KEY
                and (matched_topic.keyword == GUILD_STAFF_TURNIN_KEYWORD or matched_topic.topic_id.endswith(".topic_04"))
            )
            if requested_effect is not None:
                from world.rules.story_effects import apply_story_effect

                outcome = apply_story_effect(
                    host,
                    actor,
                    topic_id=matched_topic.topic_id,
                    expected_phase_revision=phase_revision,
                    context=context_with_id,
                )
                if not outcome.applied:
                    # Operational/domain refusal: only the authored safe
                    # refusal ships. No formal receipt, no protected body and
                    # no affinity is produced.
                    refusal_scene = matched_topic.refusal
                    if refusal_scene is None:
                        raise DialogueSourceUnavailableError(
                            "refusal_unavailable", "對方目前無法回應。"
                        )
                    delivery = replace(
                        delivery,
                        kind="refusal",
                        scene_id=refusal_scene.scene_id,
                        scene_revision=refusal_scene.revision,
                        lines=refusal_scene.lines,
                    )
                    completion_receipts = []
            # A pre-delivered pure successor is effect-free, including the
            # talk affinity the public root already granted once.
            if (
                kind == "formal"
                and requested_effect is None
                and getattr(matched_topic, "disclosure", "qualified") != "pure_chain"
                and not (is_guild_staff and is_turnin)
            ):
                outcome = apply_affinity_change(host, owner, AffinitySource.TALK, 1)
                if outcome.budget_capped:
                    delivery = replace(delivery, affinity_budget_capped=True)
            # The session lives on the acting body; the owner identity rides
            # the delivered context and the selection receipt.
            open_or_refresh_dialogue(
                actor,
                host,
                delivery=delivery,
                context=context_with_id,
                selection_receipt={
                    "topic_id": matched_topic.topic_id,
                    "selection_id": selection_id,
                    "delivery_id": delivery_id,
                    "delivery": delivery,
                },
                completion_receipts=tuple(completion_receipts),
            )
    except Exception:
        restore_attribute_best_effort(host, "relations_data", relations_snapshot)
        restore_attribute_best_effort(actor, "dialogue_session", session_snapshot)
        if quest_snapshot is not None:
            from world.quests.transitions import restore_quest_log

            restore_quest_log(owner, quest_snapshot)
        raise

    return delivery


def _is_escort_effect(definition_key: str) -> bool:
    """Whether the declared commission settles through the escort boundary."""
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY, ObjectiveKind

    definition = QUEST_DEFINITION_REGISTRY.get(definition_key)
    return definition is not None and any(
        stage.objective.kind is ObjectiveKind.ESCORT
        for stage in definition.stages
    )


def _escort_effect_actors(
    definition_key: str, source_identity: Any
) -> tuple[Any, ...]:
    """The live protected actors of an escort commission, for rollback capture."""
    from world.quests import scene_store
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY, ObjectiveKind

    definition = QUEST_DEFINITION_REGISTRY.get(definition_key)
    package_id = getattr(source_identity, "package_id", None)
    if definition is None or not isinstance(package_id, str) or not package_id:
        return ()
    refs = tuple(
        dict.fromkeys(
            role
            for stage in definition.stages
            if stage.objective.kind is ObjectiveKind.ESCORT
            for role in stage.objective.protected_role_refs
        )
    )
    if not refs:
        return ()
    from evennia.objects.models import ObjectDB

    actors: list[Any] = []
    for role_id in refs:
        binding = scene_store.get_role_binding(package_id, role_id)
        if binding is None:
            continue
        actor = ObjectDB.objects.filter(id=int(binding.npc_id)).first()
        if actor is not None:
            actors.append(actor)
    return tuple(actors)


def complete_dialogue_delivery(
    actor: Any,
    *,
    delivery_id: str,
    context_id: str,
    topic_id: str,
    scene_revision: str,
    session: "DialogueSession | None" = None,
) -> CompletionOutcome:
    """Record one formal reading completion for a retained delivered scene.

    The refusal-reporting wrapper around :func:`_complete_dialogue_delivery`.
    Every rejection is reported once with identifiers only and writes nothing.
    """
    try:
        return _complete_dialogue_delivery(
            actor,
            delivery_id=delivery_id,
            context_id=context_id,
            topic_id=topic_id,
            scene_revision=scene_revision,
            session=session,
        )
    except DialogueCompletionError as error:
        log_info(
            "dialogue_completion_rejected",
            context={
                "char": str(getattr(actor, "pk", "?")),
                "actor": str(getattr(actor, "pk", "?")),
                "topic": str(topic_id),
                "context": str(context_id),
                "delivery": str(delivery_id),
                "reason": error.code,
            },
        )
        raise


def _complete_dialogue_delivery(
    actor: Any,
    *,
    delivery_id: str,
    context_id: str,
    topic_id: str,
    scene_revision: str,
    session: "DialogueSession | None" = None,
) -> CompletionOutcome:
    """The completion body behind the reported :func:`complete_dialogue_delivery`.

    Acceptance never re-runs eligibility or settles an effect: it only proves
    that the claim names a retained server receipt of the CURRENT authenticated
    conversation (same host binding, owner, actor, control, context, phase,
    topic and exact scene revision) and that its public predecessor reading is
    already saved, then persists the completion through the narrative writer.
    A supplied ``session`` is treated as a cache hint: liveness and the
    authoritative receipt set always come from the actor's live session.
    """
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC

    from world.narrative.dialogue_reading import (
        STATUS_ALREADY_SAVED,
        completed_topic_ids,
        record_completion,
    )
    from world.rules.dialogue_context import DialogueContextError, resolve_dialogue_context

    def _reject(code: str, message: str) -> None:
        raise DialogueCompletionError(code, message)

    for value, field in (
        (delivery_id, "delivery_id"),
        (context_id, "context_id"),
        (topic_id, "topic_id"),
        (scene_revision, "scene_revision"),
    ):
        if not isinstance(value, str) or not value:
            _reject(COMPLETION_RECEIPT_UNKNOWN, f"empty {field}")

    live = live_dialogue_session(actor)
    if live is None:
        _reject(COMPLETION_CLOSED, "沒有進行中的對話。")
    if session is not None and (
        session.context_id != live.context_id
        or session.npc_id != live.npc_id
        or session.control_key != live.control_key
    ):
        # A caller-captured session that is no longer the live one must never
        # restore a retired receipt set.
        _reject(COMPLETION_RECEIPT_STALE, "對話情境已過期。")
    session = live
    if not session.context_id or context_id != session.context_id:
        _reject(COMPLETION_RECEIPT_STALE, "對話情境已過期。")
    receipt = next(
        (
            item
            for item in session.completion_receipts
            if item.get("delivery_id") == delivery_id
        ),
        None,
    )
    if receipt is None:
        _reject(COMPLETION_RECEIPT_UNKNOWN, "這段對話沒有交付紀錄。")
    if receipt.get("kind") != "formal":
        _reject(COMPLETION_RECEIPT_KIND, "這段對話沒有可記錄的正式內容。")
    if (
        receipt.get("context_id") != context_id
        or receipt.get("topic_id") != topic_id
        or receipt.get("scene_revision") != scene_revision
        or receipt.get("phase_revision") != session.phase_revision
    ):
        _reject(COMPLETION_RECEIPT_STALE, "對話情境已過期。")

    host = ObjectDB.objects.filter(id=session.npc_id).first()
    if host is None or not isinstance(host, NPC):
        _reject(COMPLETION_CLOSED, "對話已經結束。")
    try:
        context = resolve_dialogue_context(actor, host, session=session)
    except DialogueContextError as error:
        raise DialogueCompletionError(
            COMPLETION_RECEIPT_STALE, "對話情境已過期。"
        ) from error
    if context.context_id is None or context.context_id != context_id:
        _reject(COMPLETION_RECEIPT_STALE, "對話情境已過期。")
    if (
        context.host_key != session.host_key
        or context.source_identity != session.source_identity
        or context.phase_revision != session.phase_revision
    ):
        _reject(COMPLETION_RECEIPT_STALE, "對話情境已過期。")
    owner = context.owner
    if (
        owner is None
        or int(getattr(owner, "pk", 0) or 0) != int(session.owner_id)
        or int(getattr(actor, "pk", 0) or 0) != int(session.actor_id)
    ):
        _reject(COMPLETION_RECEIPT_FOREIGN, "這段對話不屬於你。")

    completed = set(completed_topic_ids(owner, context.host_key))
    if any(
        predecessor not in completed
        for predecessor in receipt.get("predecessors", ())
    ):
        # A public successor is acknowledgeable only after its predecessor's
        # reading is saved; nothing is written and no body is released.
        _reject(COMPLETION_PREDECESSOR_UNREAD, "前面的話還沒讀完。")

    outcome = record_completion(
        owner, host_key=context.host_key, topic_id=receipt["topic_id"]
    )
    if outcome.status == STATUS_ALREADY_SAVED:
        log_info(
            "dialogue_reading_already_saved",
            context={
                "char": str(getattr(owner, "pk", "?")),
                "host": context.host_key,
                "topic": receipt["topic_id"],
                "revision": outcome.reading_revision,
                "context": context_id,
            },
        )
    else:
        log_info(
            "dialogue_reading_completed",
            context={
                "char": str(getattr(owner, "pk", "?")),
                "actor": str(getattr(actor, "pk", "?")),
                "npc": str(session.npc_id),
                "host": context.host_key,
                "topic": receipt["topic_id"],
                "context": context_id,
                "revision": outcome.reading_revision,
            },
        )
    # Committed completion only: a rejected claim has already returned above,
    # so it can never schedule an availability refresh or any other effect.
    from world.rules.dialogue_availability import refresh_dialogue_availability

    refresh_dialogue_availability(owner, cause="reading_completed")
    return CompletionOutcome(
        status=outcome.status, reading_revision=outcome.reading_revision
    )


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

    The stored control identity is rechecked against the acting body's current
    lawful control: a session written under a previous account, possession or
    ``since_tick`` is stale and never live, and a body without lawful control
    (a forged or released possession mirror) holds no live session at all.
    """
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.dialogue_context import control_key_for, session_control_owner
    from world.rules.npc_intents import intent_context_ok

    session = _parse_dialogue_session(character.db.dialogue_session)
    if session is None:
        return None
    owner = session_control_owner(character)
    if owner is None:
        return None
    if session.control_key != control_key_for(character, owner):
        return None
    obj = ObjectDB.objects.filter(id=session.npc_id).first()
    if obj is None or not isinstance(obj, NPC):
        return None
    if not intent_context_ok(obj, character):
        return None
    return session
