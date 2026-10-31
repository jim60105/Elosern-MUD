"""Exact exploration action payload validators and narrow adapters.

The production exploration actions are ``explore.move``, ``explore.look``,
``explore.talk_open``, ``explore.talk_scripted``, ``explore.talk_freeform``,
``explore.dialogue_complete``, ``explore.dialogue_leave``,
``explore.party_invite``, ``explore.party_leave``, ``explore.engage``,
``explore.wait``, ``explore.practice``, ``explore.possess``, ``explore.possess_release``, and
``explore.deliver``. Each
validator enforces an exact bounded payload shape; each adapter re-resolves
every referenced identity from the actor's **current** location's present
contents and re-verifies the exact eligibility at commit time, calls only
public deterministic APIs, and never assigns ``.db`` attributes, location,
knowledge, traits, dialogue, quests, inventory, party, combat, or time
directly. No payload accepts an actor, host, session, destination room, price,
stock, or clock field, and no action routes through the text command parser.

``explore.dialogue_complete`` is the one in-conversation acknowledgement: its
exact composed payload is ``{npc_id, delivery_id, context_id, topic_id,
scene_revision}`` and the deterministic completion service validates the
server-issued receipt. It is never projected as an affordance or a suggestion.
"""

from typing import Any

from twisted.internet.defer import Deferred

from web.webclient.actions.node_ids import node_id_for_location
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.observability import log_error, log_warn
from world.rules.clock import DaypartError, get_world_clock, seconds_until_daypart
from world.rules.combat_session import CombatSessionError, SessionReason, engage
from world.rules.presentation_events import on_publication_commit, publication_group
from world.rules.travel_plan import PACES
from world.rules.dialogue import (
    DuplicateSelectionError,
    StaleContextError,
    StaleSelectionError,
    TopicNotFoundError,
    DialogueSourceUnavailableError,
    DialogueBudgetExceededError,
    clear_dialogue_session,
    escape_evennia_greeting,
    is_dialogue_host,
    live_dialogue_session,
    open_or_refresh_dialogue,
    resolve_greeting,
    opens_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_context import DialogueContextError
from world.lore.scenes import Speech
from world.rules.map_knowledge import KnowledgeError, decode_node
from world.rules.npc_intents import (
    STALE_CONTEXT_NOTE,
    apply_npc_intent,
    intent_context_ok,
    is_stale_context,
)
from world.rules.npc_schedules import interaction_reason
from world.rules.party import (
    PARTY_MAX_COMPANIONS,
    PartyJoinError,
    is_companion,
    join_party,
    party_size,
)
from world.rules.player_messages import (
    STALE_PERSONA_NOTE,
    dialogue_open_fallback_line,
)
from world.rules.time_skip import (
    DAYPARTS,
    MAX_WEB_SKIP_SECONDS,
    PracticeReject,
    SkipRefused,
    SleepRefused,
    accepted_wait_handoff_offer,
    advance_wait,
    begin_sleep,
    book_member_practice,
    render_skip_summary,
    rejection_message,
    unsafe_rejection,
)
from world.rules.unlock_notices import deliver_unlocks, notices_from_events

# Wire limits (equal to or below the protocol identifier bound).
MAX_EXIT_REF_CHARS = 64
MAX_NODE_ID_CHARS = 128
MAX_KEYWORD_ID_CHARS = 64
MAX_ITEM_KEY_CHARS = 64
MAX_SPEECH_CODE_POINTS = 512

# Stable panels each admitted exploration action may publish. Empty means the
# coordinator publishes a full snapshot (design D3/D5/D7): movement, dialogue,
# and clock skips genuinely change many surfaces together.
AFFECTED_FULL: tuple[str, ...] = ()
# Engage clears any live dialogue session inside the deterministic core, so
# the partial update must re-render ``dialogue`` too (webclient-align-10):
# without it the pre-engage available panel stays committed under combat mode.
# The holdings strip must flip to its combat transfer bar in the same update,
# and the 背包 tab's descriptors to their combat form (gives refused, use
# routed to the member's combat draft; webclient-party-bag-retire).
AFFECTED_ENGAGE = (
    "status",
    "context_actions",
    "dialogue",
    "art",
    "item_holdings",
    "party_inventory",
)


class ExplorationActionError(ValueError):
    """An exploration action payload violates its exact bounded schema."""


def _require_ascii_identifier(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ExplorationActionError(
            f"{field} must be 1..{maximum} ASCII characters"
        )
    if not value.isascii():
        raise ExplorationActionError(f"{field} must be ASCII")
    return value


def _require_node_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_NODE_ID_CHARS:
        raise ExplorationActionError(f"{field} exceeds the maximum node-ID length")
    try:
        decode_node(value)
    except KnowledgeError as error:
        raise ExplorationActionError(f"{field} is not a canonical node ID") from error
    return value


def _require_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExplorationActionError(f"{field} must be a positive integer")
    if value > MAX_SAFE_INTEGER:
        raise ExplorationActionError(f"{field} exceeds the maximum safe integer")
    return value


def _require_non_empty_string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplorationActionError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > maximum:
        raise ExplorationActionError(f"{field} exceeds its bound")
    return value


def validate_move_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.move`` payload, with an optional walk context.

    The admitted union is exactly ``{exit_ref, current_node}`` or that plus
    ``walk: {pace, stop_at_night}``. The movement contract itself never
    changes: the exit/current-node admission and the stale-location guard are
    the same for both forms. The walk context is request-scoped only; nothing
    about it is stored between requests.
    """
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.move payload must be an object")
    keys = set(payload)
    if keys not in (
        {"exit_ref", "current_node"},
        {"exit_ref", "current_node", "walk"},
    ):
        raise ExplorationActionError(
            "explore.move requires exactly exit_ref and current_node, "
            "optionally with walk"
        )
    normalized = {
        "exit_ref": _require_ascii_identifier(
            payload["exit_ref"], "exit_ref", MAX_EXIT_REF_CHARS
        ),
        "current_node": _require_node_id(payload["current_node"], "current_node"),
    }
    if "walk" in keys:
        walk = payload["walk"]
        if not isinstance(walk, dict) or set(walk) != {"pace", "stop_at_night"}:
            raise ExplorationActionError(
                "explore.move walk requires exactly pace and stop_at_night"
            )
        pace = walk["pace"]
        if not isinstance(pace, str) or pace not in PACES:
            raise ExplorationActionError("pace is not an admitted value")
        stop_at_night = walk["stop_at_night"]
        if not isinstance(stop_at_night, bool):
            raise ExplorationActionError("stop_at_night must be a boolean")
        normalized["walk"] = {"pace": pace, "stop_at_night": stop_at_night}
    return normalized


def validate_look_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.look`` payload (room marker or target)."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.look payload must be an object")
    if set(payload) == {"room"}:
        if payload["room"] is not True:
            raise ExplorationActionError("explore.look room must be the exact boolean true")
        return {"room": True}
    if set(payload) == {"target_id"}:
        return {"target_id": _require_positive_int(payload["target_id"], "target_id")}
    raise ExplorationActionError("explore.look requires exactly room or target_id")


def validate_talk_open_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.talk_open`` payload (one host identity)."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.talk_open payload must be an object")
    if set(payload) != {"npc_id"}:
        raise ExplorationActionError("explore.talk_open requires exactly npc_id")
    return {"npc_id": _require_positive_int(payload["npc_id"], "npc_id")}


def validate_talk_scripted_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact composed ``explore.talk_scripted`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.talk_scripted payload must be an object")
    if set(payload) != {"npc_id", "topic_id", "context_id", "selection_id"}:
        raise ExplorationActionError(
            "explore.talk_scripted requires exactly npc_id, topic_id, context_id, selection_id"
        )
    topic_id = payload["topic_id"]
    if not isinstance(topic_id, str) or not topic_id.strip() or len(topic_id) > 2048:
        raise ExplorationActionError("topic_id must be a non-empty string <= 2048 chars")
    context_id = payload["context_id"]
    if context_id is not None and (
        not isinstance(context_id, str) or not context_id.strip() or len(context_id) > 64
    ):
        raise ExplorationActionError("context_id must be a string <= 64 chars or None")
    selection_id = payload["selection_id"]
    if (
        not isinstance(selection_id, str)
        or not selection_id.strip()
        or len(selection_id) > 64
    ):
        raise ExplorationActionError("selection_id must be a non-empty string <= 64 chars")
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "topic_id": topic_id,
        "context_id": context_id,
        "selection_id": selection_id,
    }


def validate_talk_scripted_descriptor(params: Any) -> dict[str, Any]:
    """Validate the projected ``explore.talk_scripted`` descriptor."""
    if not isinstance(params, dict):
        raise ExplorationActionError("explore.talk_scripted params must be an object")
    if set(params) != {"npc_id", "topic_id", "context_id"}:
        raise ExplorationActionError(
            "explore.talk_scripted params requires exactly npc_id, topic_id, context_id"
        )
    topic_id = params["topic_id"]
    if not isinstance(topic_id, str) or not topic_id.strip() or len(topic_id) > 2048:
        raise ExplorationActionError("topic_id must be a non-empty string <= 2048 chars")
    context_id = params["context_id"]
    if context_id is not None and (
        not isinstance(context_id, str) or not context_id.strip() or len(context_id) > 64
    ):
        raise ExplorationActionError("context_id must be a string <= 64 chars or None")
    return {
        "npc_id": _require_positive_int(params["npc_id"], "npc_id"),
        "topic_id": topic_id,
        "context_id": context_id,
    }


def validate_talk_freeform_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.talk_freeform`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.talk_freeform payload must be an object")
    if set(payload) != {"npc_id", "speech"}:
        raise ExplorationActionError(
            "explore.talk_freeform requires exactly npc_id and speech"
        )
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "speech": _require_non_empty_string(
            payload["speech"], "speech", MAX_SPEECH_CODE_POINTS
        ),
    }


def validate_dialogue_leave_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.dialogue_leave`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.dialogue_leave payload must be an object")
    if set(payload) != {"npc_id"}:
        raise ExplorationActionError("explore.dialogue_leave requires exactly npc_id")
    return {"npc_id": _require_positive_int(payload["npc_id"], "npc_id")}


def validate_dialogue_complete_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact composed ``explore.dialogue_complete`` payload.

    The five fields are exactly what the server issued: the host identity, the
    delivery identity, the conversation context, the stable topic ID and the
    exact authored scene revision. Nothing else (no selection identity, no
    availability flag, no owner or actor) is accepted from the client.
    """
    if not isinstance(payload, dict):
        raise ExplorationActionError(
            "explore.dialogue_complete payload must be an object"
        )
    if set(payload) != {
        "npc_id",
        "delivery_id",
        "context_id",
        "topic_id",
        "scene_revision",
    }:
        raise ExplorationActionError(
            "explore.dialogue_complete requires exactly npc_id, delivery_id, "
            "context_id, topic_id and scene_revision"
        )
    delivery_id = payload["delivery_id"]
    if (
        not isinstance(delivery_id, str)
        or not delivery_id.strip()
        or len(delivery_id) > 64
    ):
        raise ExplorationActionError(
            "delivery_id must be a non-empty string <= 64 chars"
        )
    context_id = payload["context_id"]
    if (
        not isinstance(context_id, str)
        or not context_id.strip()
        or len(context_id) > 64
    ):
        raise ExplorationActionError(
            "context_id must be a non-empty string <= 64 chars"
        )
    topic_id = payload["topic_id"]
    if not isinstance(topic_id, str) or not topic_id.strip() or len(topic_id) > 2048:
        raise ExplorationActionError("topic_id must be a non-empty string <= 2048 chars")
    scene_revision = payload["scene_revision"]
    if (
        not isinstance(scene_revision, str)
        or not scene_revision.strip()
        or len(scene_revision) > 64
    ):
        raise ExplorationActionError(
            "scene_revision must be a non-empty string <= 64 chars"
        )
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "delivery_id": delivery_id,
        "context_id": context_id,
        "topic_id": topic_id,
        "scene_revision": scene_revision,
    }


def validate_party_invite_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.party_invite`` payload.

    The invitation message mirrors the free-form speech bound and may be empty
    (the message is optional in the ``invite`` command surface).
    """
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.party_invite payload must be an object")
    if set(payload) != {"npc_id", "message"}:
        raise ExplorationActionError(
            "explore.party_invite requires exactly npc_id and message"
        )
    message = payload["message"]
    if not isinstance(message, str):
        raise ExplorationActionError("explore.party_invite message must be a string")
    if sum(1 for _ in message) > MAX_SPEECH_CODE_POINTS:
        raise ExplorationActionError("explore.party_invite message exceeds its bound")
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "message": message,
    }


def validate_party_leave_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.party_leave`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.party_leave payload must be an object")
    if set(payload) != {"npc_id"}:
        raise ExplorationActionError("explore.party_leave requires exactly npc_id")
    return {"npc_id": _require_positive_int(payload["npc_id"], "npc_id")}


def validate_engage_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.engage`` payload (one monster ID)."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.engage payload must be an object")
    if set(payload) != {"monster_id"}:
        raise ExplorationActionError("explore.engage requires exactly monster_id")
    return {"monster_id": _require_positive_int(payload["monster_id"], "monster_id")}


def validate_wait_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.wait`` payload (one of daypart/seconds/sleep)."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.wait payload must be an object")
    if "sleep" in payload:
        return _validate_sleep_wait_payload(payload)
    if set(payload) == {"daypart"}:
        daypart = payload["daypart"]
        if not isinstance(daypart, str) or daypart not in DAYPARTS:
            raise ExplorationActionError("explore.wait daypart is not a stable value")
        return {"daypart": daypart}
    if set(payload) == {"seconds"}:
        seconds = payload["seconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, int):
            raise ExplorationActionError("explore.wait seconds must be an integer")
        if not 1 <= seconds <= MAX_WEB_SKIP_SECONDS:
            raise ExplorationActionError(
                f"explore.wait seconds must be within 1..{MAX_WEB_SKIP_SECONDS}"
            )
        return {"seconds": seconds}
    raise ExplorationActionError("explore.wait requires exactly one of daypart, seconds, or sleep")


_SLEEP_WAIT_KEYS = frozenset({"sleep", "sleep_scope", "sleep_mode", "seconds"})
_SLEEP_SCOPES = ("self", "party")
_SLEEP_MODES = ("recovery", "duration")


def _validate_sleep_wait_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the declared sleep scope/mode/seconds grammar exactly."""
    if payload.get("sleep") is not True:
        raise ExplorationActionError(
            "explore.wait sleep must be the exact boolean true"
        )
    keys = set(payload)
    if not keys <= _SLEEP_WAIT_KEYS:
        raise ExplorationActionError(
            "explore.wait sleep carries an unknown field"
        )
    scope = payload.get("sleep_scope", "self")
    if scope not in _SLEEP_SCOPES:
        raise ExplorationActionError("explore.wait sleep_scope is not a stable value")
    mode = payload.get("sleep_mode", "recovery")
    if mode not in _SLEEP_MODES:
        raise ExplorationActionError("explore.wait sleep_mode is not a stable value")
    sleep: dict[str, Any] = {"sleep": True}
    if "sleep_scope" in payload:
        sleep["sleep_scope"] = scope
    if "sleep_mode" in payload:
        sleep["sleep_mode"] = mode
    if mode == "duration":
        if "seconds" not in payload:
            raise ExplorationActionError("duration sleep requires seconds")
        seconds = payload["seconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, int):
            raise ExplorationActionError("explore.wait seconds must be an integer")
        if not 1 <= seconds <= MAX_WEB_SKIP_SECONDS:
            raise ExplorationActionError(
                f"explore.wait seconds must be within 1..{MAX_WEB_SKIP_SECONDS}"
            )
        sleep["seconds"] = seconds
    elif "seconds" in payload:
        raise ExplorationActionError("recovery sleep cannot carry seconds")
    return sleep


def validate_sleep_party_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.sleep_party`` payload (an empty object)."""
    if not isinstance(payload, dict) or payload:
        raise ExplorationActionError("explore.sleep_party requires an empty object")
    return {}


def validate_sleep_continue_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact retained-continuation identity."""
    if not isinstance(payload, dict) or set(payload) != {"sleep_id", "revision"}:
        raise ExplorationActionError(
            "explore.sleep_continue requires exactly sleep_id and revision"
        )
    sleep_id = payload["sleep_id"]
    if not isinstance(sleep_id, str) or not 1 <= len(sleep_id) <= MAX_ITEM_KEY_CHARS:
        raise ExplorationActionError("explore.sleep_continue sleep_id is invalid")
    revision = payload["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ExplorationActionError("explore.sleep_continue revision is invalid")
    return {"sleep_id": sleep_id, "revision": revision}


def validate_sleep_dream_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact owner-sleep dream answer identity."""
    if not isinstance(payload, dict) or set(payload) != {
        "sleep_id",
        "revision",
        "generation",
        "decision",
    }:
        raise ExplorationActionError(
            "explore.sleep_dream requires sleep_id, revision, generation and decision"
        )
    sleep_id = payload["sleep_id"]
    if not isinstance(sleep_id, str) or not 1 <= len(sleep_id) <= MAX_ITEM_KEY_CHARS:
        raise ExplorationActionError("explore.sleep_dream sleep_id is invalid")
    if payload["decision"] not in ("enter", "decline"):
        raise ExplorationActionError("explore.sleep_dream decision is invalid")
    values = {"sleep_id": sleep_id, "decision": payload["decision"]}
    for key in ("revision", "generation"):
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExplorationActionError(
                f"explore.sleep_dream {key} is invalid"
            )
        values[key] = value
    return values


def validate_practice_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.practice`` booking payload."""
    if not isinstance(payload, dict) or set(payload) != {"actor_id", "skill"}:
        raise ExplorationActionError("explore.practice requires exactly actor_id and skill")
    skill = payload["skill"]
    if not isinstance(skill, str) or not skill or len(skill) > MAX_ITEM_KEY_CHARS or any(
        character.isspace() for character in skill
    ):
        raise ExplorationActionError("explore.practice skill must be a bounded key")
    return {
        "actor_id": _require_positive_int(payload["actor_id"], "actor_id"),
        "skill": skill,
    }


def validate_possess_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.possess`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.possess payload must be an object")
    if set(payload) != {"npc_id"}:
        raise ExplorationActionError("explore.possess requires exactly npc_id")
    return {"npc_id": _require_positive_int(payload["npc_id"], "npc_id")}


def validate_possess_release_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.possess_release`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.possess_release payload must be an object")
    if set(payload) != {"npc_id"}:
        raise ExplorationActionError("explore.possess_release requires exactly npc_id")
    return {"npc_id": _require_positive_int(payload["npc_id"], "npc_id")}


def validate_deliver_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.deliver`` payload (recipient + item key).

    The payload names only the recipient's integer identity and the bounded
    item key; the quest record, stage, and quantity are re-derived server-side
    by the adapter and the shared delivery rule (design D4).
    """
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.deliver payload must be an object")
    if set(payload) != {"npc_id", "item_key"}:
        raise ExplorationActionError("explore.deliver requires exactly npc_id and item_key")
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "item_key": _require_ascii_identifier(
            payload["item_key"], "item_key", MAX_ITEM_KEY_CHARS
        ),
    }


# ---------------------------------------------------------------------------
# Adapter helpers.
# ---------------------------------------------------------------------------


def _rejected(code: str, message: str) -> dict[str, Any]:
    return {"outcome": "rejected", "code": code, "message": message}


def _success(code: str, message: str, affected: tuple[str, ...]) -> dict[str, Any]:
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected,
    }


def _present_by_id(actor: Any, identity: int) -> Any | None:
    location = getattr(actor, "location", None)
    if location is None:
        return None
    candidates = [obj for obj in location.contents if int(obj.pk) == identity]
    for obj in location.filter_visible(candidates, actor):
        return obj
    return None


def _current_node(actor: Any) -> str | None:
    """Return the canonical node ID of the actor's current location."""
    return node_id_for_location(getattr(actor, "location", None))


def _resolve_exit(actor: Any, exit_ref: str) -> Any | None:
    location = getattr(actor, "location", None)
    if location is None:
        return None
    for exit_obj in location.exits:
        if str(int(exit_obj.id)) == exit_ref:
            return exit_obj
    return None


def _resolve_npc(actor: Any, npc_id: int) -> Any | None:
    from typeclasses.npcs import NPC

    target = _present_by_id(actor, npc_id)
    if target is None or not isinstance(target, NPC):
        return None
    return target


def _resolve_llm_npc(actor: Any, npc_id: int) -> Any | None:
    from typeclasses.npcs import LLMNPC

    target = _present_by_id(actor, npc_id)
    if target is None or not isinstance(target, LLMNPC):
        return None
    return target


def _resolve_monster(actor: Any, monster_id: int) -> Any | None:
    from typeclasses.monsters import Monster

    target = _present_by_id(actor, monster_id)
    if target is None or not isinstance(target, Monster):
        return None
    return target


# ---------------------------------------------------------------------------
# Adapters.
# ---------------------------------------------------------------------------


def _move_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any] | Deferred:
    """Re-resolve the Exit and traverse through its own method (design D3).

    The Exit's own ``at_traverse`` flows through ``MovementCostMixin`` so the
    shared 30-second move charge and the destination-node record fire exactly
    as the typed command produces them, and the ``at_pre_move`` combat veto
    still runs inside the traversal.

    Success is a canonical-coordinate change: a traversal whose canonical
    location node is unchanged rejects ``move_failed`` whatever the room
    object's identity, while a pooled wilderness room reused at another cell
    succeeds because its coordinate node moved.

    A successful wilderness step carries its committed interrupt flags in the
    result ``data`` slot. That result is released only when the move's own
    transaction commits: the adapter returns a ``Deferred`` resolved through
    ``on_publication_commit`` under the group it already captured. Production
    commits inside ``settle_movement``, so the callback runs immediately; a
    caller-owned enclosing transaction that rolls back discards it, and the
    completion therefore never publishes (the external owner keeps its own
    compensation and failure completion). Every refusal and every
    non-wilderness success keeps today's synchronous dictionary shape.
    """
    del session
    from world.rules.movement_settlement import capture_movement_observation

    current_node = _current_node(actor)
    if current_node is None or current_node != payload["current_node"]:
        return _rejected("stale_location", "你的位置已經改變，請重新操作。")
    exit_obj = _resolve_exit(actor, payload["exit_ref"])
    if exit_obj is None or exit_obj.location is not actor.location:
        return _rejected("no_exit", "這裡沒有這個出口。")
    destination = exit_obj.destination
    if destination is None:
        return _rejected("no_exit", "這裡沒有這個出口。")
    try:
        if not bool(exit_obj.access(actor, "traverse")):
            return _rejected("locked", "此出口目前無法通行。")
    except Exception as exc:
        log_warn("exit_access_failed", context={"char": actor.pk, "exit": exit_obj.pk}, exc=exc)
        return _rejected("locked", "此出口目前無法通行。")
    # The traversal, its committed settlement and this result share one causal
    # publication group. The group bound here is the dispatcher's invocation
    # group (a nested scope reuses it); the private slot below makes the
    # attachment explicit, so a completion enqueued before the reactor drain
    # always names the group the movement checkpoint joined and the two
    # coalesce into one publication.
    with publication_group() as captured, capture_movement_observation(
        actor, walk=payload.get("walk")
    ) as observation:
        try:
            exit_obj.at_traverse(actor, destination)
        except Exception as exc:
            log_error("exit_traverse_failed", context={"char": actor.pk, "exit": exit_obj.pk}, exc=exc)
            return _rejected("move_failed", "移動失敗。")
        after_node = _current_node(actor)
        if after_node is None or after_node == current_node:
            from world.rules.combat_session import is_in_active_session

            if is_in_active_session(actor):
                return _rejected("in_combat", "你仍在戰鬥中，無法移動。")
            return _rejected("move_failed", "移動失敗。")
        message = f"你移動到了{actor.location.key}。"
        # The shared exit settlement publishes the committed movement
        # narrative, including first-landmark discovery, once for every
        # traversal lineage.
        result = _success("moved", message, AFFECTED_FULL)
        wilderness_step = after_node.startswith("wild:")
        if wilderness_step:
            data = result.get("data")
            result["data"] = {
                **(data if isinstance(data, dict) else {}),
                "interrupts": list(observation.flags),
            }
        from web.webclient.actions.dispatcher import PUBLICATION_GROUP_FIELD

        result[PUBLICATION_GROUP_FIELD] = captured.id
        if not wilderness_step:
            return result
        # The wilderness success result is commit-qualified: it exists only when
        # the move's transaction really committed, and it joins the captured
        # causal group through the private slot above.
        released = Deferred()

        def _release() -> None:
            released.callback(result)

        on_publication_commit(_release)
        return released


def _look_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Route the look through the ordinary ``at_look`` appearance path (design D4)."""
    del session
    if "room" in payload:
        target = actor.location
        if target is None:
            return _rejected("no_room", "你不在任何房間。")
    else:
        target = _present_by_id(actor, payload["target_id"])
        if target is None:
            return _rejected("no_target", "這裡沒有這個對象。")
    try:
        appearance = actor.at_look(target)
    except Exception as exc:
        log_warn("look_failed", context={"char": actor.pk, "target": target.pk}, exc=exc)
        return _rejected("look_failed", "無法查看。")
    actor.msg(appearance)
    return _success("looked", "你仔細打量了一番。", AFFECTED_FULL)


def _talk_scripted_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-verify the host and topic, then call the deterministic dialogue API."""
    del session
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_TALK,
        is_possessed_actor,
    )

    possessed = is_possessed_actor(actor)

    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    reason = interaction_reason(npc, "talk")
    if reason is not None:
        return _rejected("schedule_blocked", reason)

    topic_id = payload.get("topic_id")
    if possessed:
        from world.rules.dialogue_context import resolve_dialogue_context

        try:
            resolve_dialogue_context(actor, npc)
        except DialogueContextError:  # observability: ignore R2: the stable refusal IS the action result
            return _rejected(
                REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
            )
        if topic_id is None:
            # Non-authored keyword paths (legacy native lines and generated
            # service/commission keywords) stay refused: only complete
            # authored scenes are enabled while possessing.
            return _rejected(
                REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
            )

    if not is_dialogue_host(npc):
        return _rejected("not_dialogue_host", "對方無法交談。")

    if topic_id is not None:
        context_id = payload.get("context_id")
        selection_id = payload.get("selection_id") or "sel-" + str(npc.pk)
        try:
            delivery = select_authored_topic(
                actor,
                npc,
                topic_id,
                selection_id=selection_id,
                expected_context_id=context_id,
            )
        except DialogueContextError as error:  # observability: ignore R2: the stable refusal IS the action result
            if error.reason == "schedule_blocked":
                return _rejected("schedule_blocked", interaction_reason(npc, "talk") or "對方現在正忙著，沒有理會你。")
            return _rejected(
                REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
            )
        except StaleContextError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("stale_context", "對話情境已過期。")
        except StaleSelectionError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("stale_selection", "選取請求已過期。")
        except DuplicateSelectionError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("duplicate_selection", "選取請求重複。")
        except TopicNotFoundError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("unregistered_keyword", "對方不明白這個話題。")
        except DialogueSourceUnavailableError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("not_dialogue_host", "對方無法交談。")
        except DialogueBudgetExceededError:  # observability: ignore R2: rejected response is the contract report
            return _rejected("dialogue_budget_exceeded", "對話內容超過預算上限。")
        except Exception as exc:
            log_error("scripted_dialogue_failed", context={"char": actor.pk, "npc": npc.pk, "topic_id": topic_id}, exc=exc)
            return _rejected("dialogue_failed", "交談失敗。")

        for line in delivery.lines:
            if isinstance(line, Speech):
                if line.speaker == "actor":
                    actor.msg(f"你說：{line.text}")
                else:
                    actor.msg(f"{npc.key}說：{line.text}")
            else:
                actor.msg(line.text)

        last_host_line = ""
        for line in reversed(delivery.lines):
            if getattr(line, "speaker", None) == "host":
                last_host_line = line.text
                break
        summary = f"{npc.key}說：{last_host_line}" if last_host_line else f"{npc.key}與你交談。"
        return _success("talked", summary, AFFECTED_FULL)
    # The composed ``explore.talk_scripted`` payload always names a topic ID
    # (the exact validator rejects a keyword-only payload), so there is no
    # second, body-copying keyword delivery path here.
    return _rejected("unregistered_keyword", "對方不明白這個話題。")


def _talk_open_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Open a conversation with the host's greeting (design D1).

    Mirrors ``_talk_scripted_adapter``'s gates (presence, talk schedule,
    conversable host) and then records the session through the sole writer
    with the authored greeting, or the fixed server-authored fallback line
    when the host has none. A lawfully possessed acting body additionally
    passes the shared possession authorization and needs an authored source:
    freeform-only and otherwise non-authored hosts keep the existing refusal.
    It calls no LLM, advances no clock, and changes no affinity or memory: the
    session write is the only state change.
    """
    del session
    from world.rules.dialogue_context import resolve_dialogue_context
    from world.rules.dialogue_sources import resolve_dialogue_source
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_TALK,
        is_possessed_actor,
    )

    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    reason = interaction_reason(npc, "talk")
    if reason is not None:
        return _rejected("schedule_blocked", reason)
    if not opens_dialogue(npc):
        return _rejected("not_dialogue_host", "對方無法交談。")

    context = None
    if is_possessed_actor(actor):
        try:
            context = resolve_dialogue_context(actor, npc)
        except DialogueContextError:  # observability: ignore R2: the stable refusal IS the action result
            return _rejected(
                REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
            )
        if resolve_dialogue_source(context) is None:
            return _rejected(
                REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
            )

    greeting = resolve_greeting(npc)
    if greeting is None:
        # A greetingless host (an LLMNPC, or a table row with greeting=None)
        # opens on the fixed narration line instead of a quoted greeting.
        line = dialogue_open_fallback_line(npc.key)
        message = line
    else:
        line = greeting.text
        speech = escape_evennia_greeting(greeting.text) if greeting.is_override else greeting.text
        message = f"{npc.key}說：{speech}"
    open_or_refresh_dialogue(actor, npc, line, context=context)
    actor.msg(message)
    return _success("dialogue_opened", message, AFFECTED_FULL)


def _dialogue_leave_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """End the viewer's live session through the sole writer (align-11 D1).

    Re-reads the actor's LIVE session: with none, or one naming another NPC,
    the adapter rejects with the stable code ``dialogue_inactive`` before any
    write. Success clears through ``clear_dialogue_session`` — the ONLY-writer
    helper this seam was added to the spec to name — and the dispatcher's
    post-action full snapshot recompute flips the mode back to ``exploration``
    atomically; the adapter pushes nothing itself.
    """
    del session
    live = live_dialogue_session(actor)
    if live is None or live.npc_id != payload["npc_id"]:
        return _rejected("dialogue_inactive", "你目前沒有在和這個對象交談。")
    clear_dialogue_session(actor)
    message = "你結束了對話。"
    actor.msg(message)
    return _success("dialogue_left", message, AFFECTED_FULL)


_COMPLETION_REFUSAL_MESSAGES = {
    "dialogue_context_closed": "對話已經結束。",
    "dialogue_receipt_unknown": "這段對話沒有交付紀錄。",
    "dialogue_receipt_foreign": "這段對話不屬於你。",
    "dialogue_receipt_stale": "對話情境已過期。",
    "dialogue_receipt_kind": "這段對話沒有可記錄的正式內容。",
    "dialogue_predecessor_unread": "前面的話還沒讀完。",
}


def _dialogue_complete_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Acknowledge one fully played formal delivery (Shared contract v2).

    Re-resolves the named host's presence and the actor's LIVE session before
    the deterministic completion service; the service owns every receipt,
    owner, context, phase, topic and exact-revision check. An accepted
    completion commits reading and schedules the availability refresh; a
    rejected claim writes nothing and schedules nothing. The success message is
    a bounded acknowledgement: the reading projection ships through the
    post-action ``dialogue`` panel, never through this message.
    """
    del session
    from world.rules.dialogue import DialogueCompletionError, complete_dialogue_delivery

    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    live = live_dialogue_session(actor)
    if live is None or live.npc_id != int(npc.pk):
        return _rejected("stale_context", "對話情境已過期。")
    try:
        outcome = complete_dialogue_delivery(
            actor,
            delivery_id=payload["delivery_id"],
            context_id=payload["context_id"],
            topic_id=payload["topic_id"],
            scene_revision=payload["scene_revision"],
            session=live,
        )
    except DialogueCompletionError as error:  # observability: ignore R2: the stable refusal IS the action result
        return _rejected(
            error.code,
            _COMPLETION_REFUSAL_MESSAGES.get(error.code, "這段對話無法記錄。"),
        )
    except Exception as exc:
        log_error(
            "dialogue_completion_failed",
            context={"char": actor.pk, "npc": npc.pk, "topic_id": payload["topic_id"]},
            exc=exc,
        )
        return _rejected("dialogue_completion_failed", "對話紀錄失敗。")
    return _success(
        "dialogue_completed",
        "這段對話已讀完。" if outcome.status == "saved" else "這段對話先前已經讀完了。",
        AFFECTED_FULL,
    )


def _talk_freeform_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> Deferred:
    """Run the guarded dialogue seam through the injected client (design D5/D6).

    Re-resolves a present ``LLMNPC`` synchronously so a tampered, ineligible,
    or schedule-blocked NPC rejects before any client or transport work; the
    Deferred settles after the seam finishes (offline degrade, memory, and
    verified-intent included).
    """
    del session
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_TALK,
        is_possessed_actor,
    )

    if is_possessed_actor(actor):
        return _rejected(REASON_POSSESSED_TALK, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK])

    npc = _resolve_llm_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有可以自由交談的對象。")
    if getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        return _rejected("possessed", "他現在無法回應你。")
    reason = interaction_reason(npc, "talk")
    if reason is not None:
        return _rejected("schedule_blocked", reason)
    from web.webclient.actions.dialogue_composition import build_dialogue_client

    client = build_dialogue_client()

    def _settled_line(line: str) -> None:
        # Observer handed to the seam (webclient-align-07): invoked only after
        # a reply or authored degrade line was actually presented and the
        # completion gate still passed — a mid-flight-stale settlement and a
        # silent degrade never call it. The record lands here, before the
        # dispatcher's newer-revision snapshot publishes.
        open_or_refresh_dialogue(actor, npc, line)

    deferred = npc.at_talked_to(
        payload["speech"], actor, client, settled_line=_settled_line, notify_stale=False
    )

    def _on_success(result: Any) -> dict[str, Any]:
        from typeclasses.npcs import STALE_PERSONA

        if result is STALE_PERSONA:
            return _rejected("stale_persona", STALE_PERSONA_NOTE)
        if is_stale_context(result):
            # The seam showed the speech and the stale note; the panel result
            # carries the same outcome so the client reports the dropped
            # intent (F22 completion gate).
            return _success("talked", STALE_CONTEXT_NOTE, AFFECTED_FULL)
        return _success("talked", "對方回應了你的話。", AFFECTED_FULL)

    def _on_failure(failure: Any) -> dict[str, Any]:
        failure.trap(Exception)
        # The seam's exception is presented as the generic refusal, but it is
        # an operational failure (a locked database, a broken writer): it must
        # leave a named facade event with the chain, like every other
        # dialogue_failed producer in this module.
        log_error(
            "freeform_dialogue_failed",
            context={"char": actor.pk, "npc": npc.pk},
            exc=failure.value,
        )
        return _rejected("dialogue_failed", "交談失敗，請稍後再試。")

    deferred.addCallbacks(_on_success, _on_failure)
    return deferred


def _party_invite_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> Deferred:
    """Propose a party through the guarded dialogue seam (party-core D-2).

    Re-resolves a present ``LLMNPC`` and re-verifies the deterministic gate
    (no existing binding, party not full) synchronously; the Deferred settles
    after the structured exchange. On the degraded terminal the fixed
    threshold decides; otherwise the speech is shown and the verified
    ``party_invite`` intent is applied through the deterministic applier --
    an AI decision is never overridden by the threshold.
    """
    del session
    npc = _resolve_llm_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有可以邀請的對象。")
    from world.rules.party import has_general_membership

    if has_general_membership(npc, actor) or (
        npc.db.party_member is not None and npc.db.party_member != actor.pk
    ):
        from world.rules.party import ALREADY_COMPANION_MESSAGE

        return _rejected("already_companion", ALREADY_COMPANION_MESSAGE)
    if party_size(actor) >= PARTY_MAX_COMPANIONS:
        from world.rules.party import PARTY_FULL_MESSAGE

        return _rejected("party_full", PARTY_FULL_MESSAGE)
    from web.webclient.actions.dialogue_composition import build_dialogue_client

    client = build_dialogue_client()
    deferred = npc.run_npc_exchange(payload["message"], actor, client, path="party_invite")

    def _on_success(result: Any) -> dict[str, Any]:
        if getattr(result, "stale_persona", False):
            return _rejected("stale_persona", STALE_PERSONA_NOTE)
        message = _render_invite_outcome(npc, actor, result)
        return _success("invited", message, AFFECTED_FULL)

    def _on_failure(failure: Any) -> dict[str, Any]:
        failure.trap(Exception)
        return _rejected("invite_failed", "邀請失敗，請稍後再試。")

    deferred.addCallbacks(_on_success, _on_failure)
    return deferred


def _render_invite_outcome(npc: Any, actor: Any, result: Any) -> str:
    """Render one invite exchange into the player's feedback text.

    Mirrors the ``invite`` command's rendering so the two transports never
    drift: the degraded terminal applies the fixed threshold, otherwise the
    speech is shown and the verified intent is applied deterministically.
    """
    from world.rules.party import (
        DEGRADED_ACCEPT_MESSAGE,
        DEGRADED_REJECT_MESSAGE,
        JOINED_MESSAGE,
        JOIN_REJECTION_MESSAGES,
        REFUSED_MESSAGE,
    )

    if getattr(result, "stale_persona", False):
        actor.msg(STALE_PERSONA_NOTE)
        return STALE_PERSONA_NOTE

    if result.degraded:
        from world.rules.affinity_config import get_config

        if not intent_context_ok(npc, actor):
            # The exchange settled after the pair separated or the NPC stopped
            # allowing talk (F22 completion gate): the degraded threshold
            # decides nothing on a stale context.
            actor.msg(STALE_CONTEXT_NOTE)
            return STALE_CONTEXT_NOTE
        affinity = npc.relations.affinity_for(actor)
        if affinity < get_config().invite_threshold:
            actor.msg(f"{npc.key}說：{DEGRADED_REJECT_MESSAGE}")
            from world.narrative.dialogue import settle_response

            settle_response(npc, actor, result.submission_id, DEGRADED_REJECT_MESSAGE,
                            snapshot_id=result.snapshot_id)
            return "她婉拒了你的邀請。"
        try:
            join_party(npc, actor)
        except PartyJoinError as error:
            log_warn("party_join_rejected", context={"char": actor.pk, "npc": npc.pk}, exc=error)
            line = JOIN_REJECTION_MESSAGES.get(error.reason, REFUSED_MESSAGE)
            actor.msg(line)
            return line
        actor.msg(f"{npc.key}說：{DEGRADED_ACCEPT_MESSAGE}")
        from world.narrative.dialogue import settle_response

        settle_response(npc, actor, result.submission_id, DEGRADED_ACCEPT_MESSAGE,
                        snapshot_id=result.snapshot_id)
        actor.msg(JOINED_MESSAGE)
        return JOINED_MESSAGE

    actor.msg(f"{npc.key}說：{result.reply.speech}")
    from world.narrative.dialogue import settle_response

    settle_response(npc, actor, result.submission_id, result.reply.speech,
                    snapshot_id=result.snapshot_id)
    intent = result.reply.intent
    outcome = apply_npc_intent(npc, actor, intent)
    if is_stale_context(outcome):
        # The exchange settled after the pair separated or the NPC stopped
        # allowing talk: keep the speech, skip the intent, and report the
        # stale context (F22 completion gate).
        actor.msg(STALE_CONTEXT_NOTE)
        return STALE_CONTEXT_NOTE
    if not (isinstance(intent, dict) and intent.get("kind") == "party_invite"):
        return result.reply.speech
    if intent.get("accept") is True:
        if outcome.applied:
            actor.msg(JOINED_MESSAGE)
            return JOINED_MESSAGE
        line = JOIN_REJECTION_MESSAGES.get(outcome.reason or "", REFUSED_MESSAGE)
        actor.msg(line)
        return line
    actor.msg(REFUSED_MESSAGE)
    return REFUSED_MESSAGE


def _party_leave_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Dismiss a bound companion through the membership module (party-core)."""
    del session
    from world.rules.party_scope import PartyScopeError, resolve_commander
    from world.rules.party import (
        ESCORT_BOUND_MESSAGE,
        LEAVE_DISMISSED_MESSAGE,
        NOT_COMPANION_MESSAGE,
        REASON_ESCORT_BOUND,
        has_general_membership,
        leave_party,
        reasons_for,
    )

    try:
        commander = resolve_commander(actor)
    except PartyScopeError as error:  # observability: ignore R2: the stable party refusal IS the action result, not a swallowed failure
        return _rejected(error.reason, error.message)
    # The acting puppet may be the dismissal target itself: a player who
    # possesses a general-plus-temporary companion can relinquish that
    # companion's general membership without handing back first. Visibility
    # excludes the looker, so resolve that exact identity directly; every
    # other target still resolves from the puppet's current room.
    from typeclasses.npcs import NPC

    npc_id = int(payload["npc_id"])
    if getattr(actor, "pk", None) == npc_id and isinstance(actor, NPC):
        npc = actor
    else:
        npc = _resolve_npc(actor, npc_id)
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    if not is_companion(npc, commander):
        return _rejected("not_companion", NOT_COMPANION_MESSAGE)
    if not has_general_membership(npc, commander):
        reasons = reasons_for(npc, commander)
        if reasons:
            # A temporary-only member's companionship is a live escort
            # commission: never detach the reason directly; route the player to
            # the affected missions' selected abandonment (escort-rendezvous §3).
            return _rejected(
                REASON_ESCORT_BOUND,
                ESCORT_BOUND_MESSAGE.format(
                    quests="、".join(sorted({quest_id for quest_id, _ in reasons}))
                ),
            )
    leave_party(npc, commander, reason="dismissed")
    commander.msg(LEAVE_DISMISSED_MESSAGE)
    return _success("left", LEAVE_DISMISSED_MESSAGE, AFFECTED_FULL)


def _engage_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-resolve a present monster and delegate to the existing engage contract."""
    del session
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_ENGAGE,
        is_possessed_actor,
    )

    if is_possessed_actor(actor):
        return _rejected(REASON_POSSESSED_ENGAGE, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_ENGAGE])

    monster = _resolve_monster(actor, payload["monster_id"])
    if monster is None:
        return _rejected("no_monster", "這裡沒有這個對象。")
    try:
        engaged = engage(actor, monster)
    except CombatSessionError as error:
        log_warn("engage_rejected", context={"char": actor.pk, "monster": monster.pk}, exc=error)
        reason = error.args[0] if error.args else None
        if reason is SessionReason.ALREADY_IN_COMBAT:
            return _rejected("already_in_combat", "你已在戰鬥中。")
        if reason is SessionReason.TARGET_DEAD:
            return _rejected("target_dead", "目標已經死亡。")
        if reason is SessionReason.NOT_PRESENT:
            return _rejected("no_monster", "這裡沒有這個對象。")
        return _rejected("engage_failed", "無法開始戰鬥。")
    settlement = engaged.get("settlement")
    if settlement is not None:
        # The all-forced-sleep opening already settled through the ordinary
        # terminal writer; present its outcome and republish the full state
        # instead of advertising an active combat session.
        from world.rules.combat_result import settle_to_messages

        _, terminal = settle_to_messages(settlement)
        actor.msg(terminal)
        return _success("engaged", terminal, AFFECTED_FULL)
    from world.skills.narration import engagement_opening_line

    try:
        message = engagement_opening_line(str(monster.key))
    except Exception:  # observability: ignore R2: narration is presentation and degrades rather than abort a legal engage (design D11)
        message = "你向目標發起了攻擊！"
    actor.msg(message)
    return _success("engaged", message, AFFECTED_ENGAGE)


def _practice_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Book one present member's standing practice; advance no time.

    The member is reauthorized through the party boundary for the acting
    purpose, so a forged, absent, or knocked-out id is refused and the
    authenticated puppet is never substituted for it. An active combat
    session refuses with ``booking_in_combat``, then the skill is preflighted
    against that member. The only write is the member's booking; the clock's
    whole-hour practice stage stays the sole progression writer.
    """
    from world.rules.party_scope import PARTY_SCOPE_MESSAGES, PartyScopeError

    del session
    try:
        booking = book_member_practice(
            actor, payload["actor_id"], payload["skill"]
        )
    except PartyScopeError as error:  # observability: ignore R2: the stable party refusal IS the action result, not a swallowed failure
        return _rejected(
            error.reason, PARTY_SCOPE_MESSAGES.get(error.reason, "目前無法排入修煉。")
        )
    if isinstance(booking, PracticeReject):
        return _rejected(booking.reason, booking.message)
    actor.msg(booking.message)
    return _success("booked", booking.message, AFFECTED_FULL)


def _wait_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None,
) -> dict[str, Any]:
    """Recheck safety and run the shared interruptible skip operation."""
    rejection = unsafe_rejection(actor)
    if rejection is not None:
        return _rejected("unsafe_skip", rejection)
    sleep = payload.get("sleep") is True
    if sleep:
        seconds = None
    elif "daypart" in payload:
        daypart = payload["daypart"]
        try:
            clock = get_world_clock()
            seconds = seconds_until_daypart(clock.calendar, daypart)
        except DaypartError as exc:
            log_warn("daypart_rejected", context={"char": actor.pk, "daypart": daypart}, exc=exc)
            return _rejected("unknown_daypart", "未知的時段。")
    elif "seconds" in payload:
        seconds = payload["seconds"]
    else:
        return _rejected("malformed_payload", "缺少等待時長。")
    try:
        if sleep:
            explicit = "seconds" in payload or "sleep_mode" in payload
            if payload.get("sleep_scope", "self") == "party":
                from world.rules.sleep_control import begin_all_party_sleep

                outcome = begin_all_party_sleep(
                    actor,
                    mode=payload.get("sleep_mode", "recovery"),
                    seconds=payload.get("seconds"),
                    session=session,
                )
            else:
                outcome = begin_sleep(
                    actor,
                    mode=payload.get("sleep_mode", "recovery"),
                    seconds=payload.get("seconds"),
                    scope="self",
                    allow_continue=not explicit,
                )
        else:
            result = advance_wait(actor, seconds)
    except SkipRefused as exc:  # observability: ignore R2: the stable skip refusal IS the action result, not a swallowed failure
        return _rejected("unsafe_skip", rejection_message(exc.reason) or "無法跳過時間。")
    except SleepRefused as exc:  # observability: ignore R2: the stable sleep refusal IS the action result, not a swallowed failure
        return _rejected(exc.code, exc.message)
    except Exception as exc:
        log_error(
            "skip_failed",
            context={"char": actor.pk, "seconds": seconds, "sleep": sleep},
            exc=exc,
        )
        return _rejected("skip_failed", "無法跳過時間。")
    if sleep:
        if outcome.message is not None:
            actor.msg(outcome.message)
            return _success("slept", outcome.message, AFFECTED_FULL)
        result = outcome.result
        if result is None:
            return _success("slept", "已接受睡眠。", AFFECTED_FULL)
        elapsed = result.elapsed_seconds
    else:
        elapsed = result.elapsed_seconds
    message = render_skip_summary(elapsed, result.events)
    offer = accepted_wait_handoff_offer(actor)
    if offer is not None:
        message = f"{message}\n{offer}"
    actor.msg(message)
    # The summary already carries each committed unlock line; record the
    # session unread marks from the same committed events.
    deliver_unlocks(actor, notices_from_events(result.events), announce=False)
    return _success("skipped", message, AFFECTED_FULL)


def _sleep_party_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Run the compensated all-party sleep choice; no time passes."""
    del payload
    from world.rules.sleep_control import begin_all_party_sleep
    from world.rules.possession import PossessionGateError, PossessionWriteError

    try:
        outcome = begin_all_party_sleep(actor, session=session)
    except PossessionGateError as error:  # observability: ignore R2: the stable gate refusal IS the action result
        return _rejected(
            error.reason, "目前無法選擇全員一起睡眠。"
        )
    except (SleepRefused, PossessionWriteError) as error:  # observability: ignore R2: the stable sleep/write refusal IS the action result
        return _rejected(
            getattr(error, "code", "party_sleep_failed"),
            getattr(error, "message", None) or "目前無法選擇全員一起睡眠。",
        )
    message = getattr(outcome, "message", None) or "在場成員已進入睡眠。"
    actor.msg(message)
    return _success("sleep_party", message, AFFECTED_FULL)


def _sleep_continue_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Continue the exact offered sleep identity, owner or companion."""
    del session
    from world.rules.time_skip import (
        continue_owner_sleep,
        continue_sleep,
        owner_sleep_view_state,
    )

    owner_state = owner_sleep_view_state(actor)
    try:
        if owner_state is not None:
            if (
                owner_state["sleep_id"] != payload["sleep_id"]
                or owner_state["revision"] != int(payload["revision"])
            ):
                return _rejected(
                    "stale_sleep", "這次睡眠已經更新，請重新查看。"
                )
            if owner_state["pending"]:
                from server.dream_service import answer_sleep_dream

                answer = answer_sleep_dream(
                    actor,
                    decision="decline",
                    sleep_id=owner_state["sleep_id"],
                    revision=owner_state["revision"],
                    generation=owner_state["generation"],
                )
                if answer["outcome"] != "success":
                    return answer
                status = (answer.get("data") or {}).get("continuation")
                if status in ("complete", "paused", "pending"):
                    return answer
                current = owner_sleep_view_state(actor)
                if current is None:
                    return answer
            result = continue_owner_sleep(
                actor,
                sleep_id=payload["sleep_id"],
                expected_generation=owner_state["generation"],
            )
        else:
            result = continue_sleep(
                actor,
                expected_sleep_id=payload["sleep_id"],
                expected_revision=int(payload["revision"]),
            )
    except SkipRefused as error:  # observability: ignore R2: the stable safety refusal IS the action result
        return _rejected(
            "unsafe_skip", rejection_message(error.reason) or "目前無法繼續睡眠。"
        )
    except SleepRefused as error:  # observability: ignore R2: the stable sleep refusal IS the action result
        return _rejected(error.code, error.message)
    message = result.summary or "睡眠已繼續。"
    actor.msg(message)
    return _success("sleep_continued", message, AFFECTED_FULL)


def _sleep_dream_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Answer the pending owner-sleep dream question through the one facade."""
    from server.dream_service import answer_sleep_dream

    return answer_sleep_dream(
        actor,
        decision=payload["decision"],
        sleep_id=payload["sleep_id"],
        revision=payload["revision"],
        generation=payload["generation"],
        session=session,
    )


def _perform_possess_transition(session: Any, player: Any, npc: Any) -> None:
    from web.webclient.actions.account_actions import _clear_transition_pending
    try:
        from world.rules.possession import enter_possession
        enter_possession(player, npc)
    except Exception as exc:
        log_error(
            "possess_transition_failed",
            context={
                "player": str(getattr(player, "pk", "?")),
                "npc": str(getattr(npc, "pk", "?")),
            },
            exc=exc,
        )
        if session is not None:
            from web.webclient.presentation.ingress import synchronize_session
            synchronize_session(session, player)
            session.msg("此刻無法附身於他。")
    finally:
        _clear_transition_pending(session)


def _sleep_handoff_context(
    actor: Any, session: Any
) -> tuple[Any, Any, Any] | None:
    """Resolve the committed sleep-driven handoff context, or ``None``.

    The context is derived from committed state only: the authenticated actor
    is the controlled body (the owner itself or a possessed companion), that
    body is committed asleep, and the account/session still controls it. Any
    other state keeps the ordinary possession path.
    """
    from world.rules.party_scope import PartyScopeError, resolve_commander
    from world.rules.possession import _resolve_account, sleep_handoff_candidates

    try:
        commander = resolve_commander(actor)
    except PartyScopeError:  # observability: ignore R2: no commander means no contextual handoff; the ordinary gate reports it
        return None
    account = _resolve_account(commander, actor)
    if account is None:
        return None
    options = sleep_handoff_candidates(account, commander, actor, session=session)
    if options.transition_id is None:
        return None
    return account, commander, options


def _handoff_rejection(options: Any) -> dict[str, Any]:
    from world.rules.possession import (
        POSSESSION_REJECTION_MESSAGES,
        REASON_NO_CANDIDATE,
        REASON_STALE_HANDOFF,
    )

    code = REASON_NO_CANDIDATE if not options.candidates else REASON_STALE_HANDOFF
    # The result data slot is contractually success-only; a stale selection is a
    # plain stable rejection. The committed panels carry the current choices.
    return _rejected(code, POSSESSION_REJECTION_MESSAGES[code])


def _perform_handoff_transition(
    session: Any,
    account: Any,
    commander: Any,
    current_body: Any,
    candidate_id: int,
    transition_id: str,
) -> None:
    """Run the confirmed contextual handoff after the result-only reply."""
    from web.webclient.actions.account_actions import _clear_transition_pending
    from world.rules.possession import (
        POSSESSION_REJECTION_MESSAGES,
        PossessionGateError,
        confirm_sleep_handoff,
    )

    try:
        confirm_sleep_handoff(
            account,
            commander,
            current_body,
            candidate_id,
            transition_id=transition_id,
            session=session,
        )
    except PossessionGateError as error:  # observability: ignore R2: the stable handoff refusal IS the action result sent to the player, not a swallowed failure
        if session is not None:
            from web.webclient.presentation.ingress import synchronize_session

            synchronize_session(session, getattr(session, "puppet", None) or commander)
            session.msg(
                POSSESSION_REJECTION_MESSAGES.get(error.reason, "交接選項已經失效，請重新選擇。")
            )
    except Exception as exc:
        log_error(
            "sleep_handoff_transition_failed",
            context={
                "char": str(getattr(commander, "pk", "?")),
                "from": str(getattr(current_body, "pk", "?")),
                "to": str(candidate_id),
            },
            exc=exc,
        )
        if session is not None:
            from web.webclient.presentation.ingress import synchronize_session

            synchronize_session(session, getattr(session, "puppet", None) or commander)
            session.msg("交接操作失敗，請稍後再試。")
    finally:
        _clear_transition_pending(session)


def _handoff_result(
    session: Any,
    account: Any,
    commander: Any,
    current_body: Any,
    candidate: Any,
    transition_id: str,
) -> dict[str, Any]:
    """Schedule the confirmed transfer, or run it directly without a session."""
    from web.webclient.actions.account_actions import (
        _set_transition_pending,
        get_clock,
    )
    from world.rules.possession import SLEEP_HANDOFF_RETURN, confirm_sleep_handoff

    # Admission only: the transfer is verified on the next reactor turn. The
    # completed outcome arrives as the committed new-epoch presentation, and a
    # failure sends the stable refusal from the deferred verifier.
    message = "正在交接控制權……"
    if session is not None:
        get_clock().callLater(
            0,
            _perform_handoff_transition,
            session,
            account,
            commander,
            current_body,
            candidate.dbid,
            transition_id,
        )
        _set_transition_pending(session)
        return {
            "outcome": "success",
            "code": "handoff_pending",
            "message": message,
            "no_presentation": True,
        }
    confirm_sleep_handoff(
        account,
        commander,
        current_body,
        candidate.dbid,
        transition_id=transition_id,
        session=None,
    )
    if candidate.kind == SLEEP_HANDOFF_RETURN:
        completed = "你的意識回到了自己的身體。"
    else:
        completed = f"你接手了{candidate.name}的身體。"
    return _success("handoff", completed, AFFECTED_FULL)


def _possess_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Enter possession of a bound companion.

    Synchronously verifies companion binding and entry gates. If admitted on a
    live session, returns a result-only success response (no_presentation=True)
    and schedules the puppet transition on the next reactor turn to prevent
    epoch races with the dispatcher.
    """
    from web.webclient.actions.account_actions import (
        _set_transition_pending,
        _transition_pending,
        get_clock,
    )
    from world.rules.possession import (
        POSSESSION_REJECTION_MESSAGES,
        REASON_NOT_CO_LOCATED,
        enter_possession,
        possession_verdict,
    )

    if _transition_pending(session):
        return _rejected("transition_pending", "角色切換正在進行中，請稍候。")

    context = _sleep_handoff_context(actor, session)
    if context is not None:
        account, commander, options = context
        candidate = next(
            (
                item
                for item in options.candidates
                if item.dbid == int(payload["npc_id"])
            ),
            None,
        )
        if candidate is None:
            return _handoff_rejection(options)
        return _handoff_result(
            session,
            account,
            commander,
            actor,
            candidate,
            options.transition_id,
        )

    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected(REASON_NOT_CO_LOCATED, POSSESSION_REJECTION_MESSAGES[REASON_NOT_CO_LOCATED])

    verdict = possession_verdict(actor, npc)
    if verdict is not None:
        return _rejected(verdict, POSSESSION_REJECTION_MESSAGES.get(verdict, "無法附身。"))

    message = f"你附身到了{npc.key}身上。"
    if session is not None:
        clock = get_clock()
        clock.callLater(0, _perform_possess_transition, session, actor, npc)
        _set_transition_pending(session)
        return {
            "outcome": "success",
            "code": "possessed",
            "message": message,
            "no_presentation": True,
        }

    # Headless / tests with no session context
    enter_possession(actor, npc)
    return _success("possessed", message, AFFECTED_FULL)


def _perform_release_transition(session: Any, player: Any, npc: Any) -> None:
    from web.webclient.actions.account_actions import _clear_transition_pending
    try:
        from world.rules.possession import release_possession
        release_possession(player, npc=npc, reason="handback")
    except Exception as exc:
        log_error(
            "release_transition_failed",
            context={
                "player": str(getattr(player, "pk", "?")),
                "npc": str(getattr(npc, "pk", "?")),
            },
            exc=exc,
        )
        if session is not None:
            from web.webclient.presentation.ingress import synchronize_session
            synchronize_session(session, getattr(session, "puppet", None) or player)
            session.msg("你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。")
    finally:
        _clear_transition_pending(session)


def _possess_release_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Release possession and return puppet to the owning player character."""
    from web.webclient.actions.account_actions import (
        _set_transition_pending,
        _transition_pending,
        get_clock,
    )
    from world.rules.possession import (
        UNPOSSESS_RELEASED_MESSAGE,
        _resolve_live_object,
        current_possession,
        is_possessed_actor,
        release_possession,
    )

    if _transition_pending(session):
        return _rejected("transition_pending", "角色切換正在進行中，請稍候。")

    # A sleeping controlled companion returns control through the same
    # contextual confirmation when its awake owner is a lawful return choice.
    context = _sleep_handoff_context(actor, session)
    if context is not None:
        account, commander, options = context
        if actor is not commander:
            candidate = next(
                (
                    item
                    for item in options.candidates
                    if item.dbid == int(commander.pk)
                ),
                None,
            )
            if candidate is not None:
                return _handoff_result(
                    session,
                    account,
                    commander,
                    actor,
                    candidate,
                    options.transition_id,
                )

    if is_possessed_actor(actor):
        player_id = int(actor.db.possessed_by)
        player = _resolve_live_object(player_id)
        npc = actor
    else:
        player = actor
        npc = _resolve_live_object(payload["npc_id"])

    if player is None or npc is None:
        return _rejected("mismatched_possession", "未處於附身狀態或找不到對應的本體。")

    pos = current_possession(player)
    if pos is None or pos.get("npc_dbid") != getattr(npc, "pk", None) or getattr(npc.db, "possessed_by", None) != getattr(player, "pk", None):
        return _rejected("mismatched_possession", "附身狀態不相符，無法歸位。")

    if session is not None:
        clock = get_clock()
        clock.callLater(0, _perform_release_transition, session, player, npc)
        _set_transition_pending(session)
        return {
            "outcome": "success",
            "code": "released",
            "message": UNPOSSESS_RELEASED_MESSAGE,
            "no_presentation": True,
        }

    # Headless / tests with no session context
    release_possession(player, npc=npc, reason="handback")
    return _success("released", UNPOSSESS_RELEASED_MESSAGE, AFFECTED_FULL)


def _deliver_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Hand the quest item to its bound recipient through the shared rule.

    Re-resolves the recipient as a present entity by identity (bound
    recipients are runtime identities, never client-named quest state) and
    delegates to ``world.rules.quest_delivery.deliver_quest_item``, so the
    action and the ``交付`` command refuse and succeed identically.
    """
    del session
    from world.rules.quest_delivery import deliver_quest_item

    recipient = _present_by_id(actor, payload["npc_id"])
    if recipient is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    outcome = deliver_quest_item(actor, recipient, payload["item_key"])
    if not outcome.applied:
        return _rejected(outcome.code, outcome.message)
    actor.msg(outcome.message)
    return _success("delivered", outcome.message, AFFECTED_FULL)


__all__ = [
    "AFFECTED_ENGAGE",
    "DAYPARTS",
    "ExplorationActionError",
    "MAX_EXIT_REF_CHARS",
    "MAX_ITEM_KEY_CHARS",
    "MAX_KEYWORD_ID_CHARS",
    "MAX_NODE_ID_CHARS",
    "MAX_SPEECH_CODE_POINTS",
    "_sleep_continue_adapter",
    "_sleep_dream_adapter",
    "_sleep_party_adapter",
    "_dialogue_complete_adapter",
    "_talk_open_adapter",
    "validate_engage_payload",
    "validate_deliver_payload",
    "validate_dialogue_complete_payload",
    "validate_look_payload",
    "validate_move_payload",
    "validate_party_invite_payload",
    "validate_party_leave_payload",
    "validate_possess_payload",
    "validate_possess_release_payload",
    "validate_sleep_continue_payload",
    "validate_sleep_dream_payload",
    "validate_sleep_party_payload",
    "validate_talk_freeform_payload",
    "validate_talk_open_payload",
    "validate_talk_scripted_payload",
    "validate_talk_scripted_descriptor",
    "validate_wait_payload",
]
