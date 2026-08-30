"""Exact exploration action payload validators and narrow adapters.

The eight production exploration actions are ``explore.move``, ``explore.look``,
``explore.talk_scripted``, ``explore.talk_freeform``, ``explore.party_invite``,
``explore.party_leave``, ``explore.engage``, and ``explore.wait``. Each
validator enforces an exact bounded payload shape; each adapter re-resolves
every referenced identity from the actor's **current** location's present
contents and re-verifies the exact eligibility at commit time, calls only
public deterministic APIs, and never assigns ``.db`` attributes, location,
knowledge, traits, dialogue, quests, inventory, party, combat, or time
directly. No payload accepts an actor, host, session, destination room, price,
stock, or clock field, and no action routes through the text command parser.
"""

from typing import Any

from twisted.internet.defer import Deferred

from web.webclient.actions.node_ids import node_id_for_location
from world.onboarding.guide_dialogue import DIALOGUE_TABLE
from world.rules.affinity import AFFINITY_DAILY_CAP_HINT
from world.rules.clock import DaypartError, get_world_clock, seconds_until_daypart
from world.rules.combat_session import CombatSessionError, SessionReason, engage
from world.rules.dialogue import dialogue_key_for, is_dialogue_host
from world.rules.map_knowledge import KnowledgeError, decode_node
from world.rules.npc_intents import (
    STALE_CONTEXT_NOTE,
    apply_npc_intent,
    intent_context_ok,
    is_stale_context,
)
from world.rules.npc_schedules import interaction_reason
from world.rules.onboarding import run_scripted_talk
from world.rules.party import (
    PARTY_MAX_COMPANIONS,
    PartyJoinError,
    is_companion,
    join_party,
    party_size,
)
from world.rules.time_skip import (
    DAYPARTS,
    MAX_WEB_SKIP_SECONDS,
    advance_skip,
    render_skip_summary,
    seconds_to_full_regen,
    unsafe_rejection,
)

# Wire limits (equal to or below the protocol identifier bound).
MAX_EXIT_REF_CHARS = 64
MAX_NODE_ID_CHARS = 128
MAX_KEYWORD_ID_CHARS = 64
MAX_SPEECH_CODE_POINTS = 512

# Stable panels each admitted exploration action may publish. Empty means the
# coordinator publishes a full snapshot (design D3/D5/D7): movement, dialogue,
# and clock skips genuinely change many surfaces together.
AFFECTED_FULL: tuple[str, ...] = ()
AFFECTED_ENGAGE = ("status", "context_actions")


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
    return value


def _require_non_empty_string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplorationActionError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > maximum:
        raise ExplorationActionError(f"{field} exceeds its bound")
    return value


def validate_move_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.move`` payload (exit_ref + current_node)."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.move payload must be an object")
    if set(payload) != {"exit_ref", "current_node"}:
        raise ExplorationActionError("explore.move requires exactly exit_ref and current_node")
    return {
        "exit_ref": _require_ascii_identifier(
            payload["exit_ref"], "exit_ref", MAX_EXIT_REF_CHARS
        ),
        "current_node": _require_node_id(payload["current_node"], "current_node"),
    }


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


def validate_talk_scripted_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.talk_scripted`` payload."""
    if not isinstance(payload, dict):
        raise ExplorationActionError("explore.talk_scripted payload must be an object")
    if set(payload) != {"npc_id", "keyword_id"}:
        raise ExplorationActionError(
            "explore.talk_scripted requires exactly npc_id and keyword_id"
        )
    return {
        "npc_id": _require_positive_int(payload["npc_id"], "npc_id"),
        "keyword_id": _require_non_empty_string(
            payload["keyword_id"], "keyword_id", MAX_KEYWORD_ID_CHARS
        ),
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
    if set(payload) == {"sleep"}:
        if payload["sleep"] is not True:
            raise ExplorationActionError("explore.wait sleep must be the exact boolean true")
        return {"sleep": True}
    raise ExplorationActionError("explore.wait requires exactly one of daypart, seconds, or sleep")


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
    for obj in location.contents:
        if int(obj.pk) == identity:
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


def _move_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-resolve the Exit and traverse through its own method (design D3).

    The Exit's own ``at_traverse`` flows through ``MovementCostMixin`` so the
    shared 30-second move charge and the destination-node record fire exactly
    as the typed command produces them, and the ``at_pre_move`` combat veto
    still runs inside the traversal.
    """
    del session
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
    except Exception:
        return _rejected("locked", "此出口目前無法通行。")
    source_location = actor.location
    try:
        exit_obj.at_traverse(actor, destination)
    except Exception:
        return _rejected("move_failed", "移動失敗。")
    if actor.location is source_location:
        # ``at_traverse`` returns None on both branches (the movement cost and
        # knowledge hooks live in ``at_post_traverse``), so success is detected
        # by the actor actually relocating.
        from world.rules.combat_session import is_in_active_session

        if is_in_active_session(actor):
            return _rejected("in_combat", "你仍在戰鬥中，無法移動。")
        return _rejected("move_failed", "移動失敗。")
    message = f"你移動到了{actor.location.key}。"
    actor.msg(message)
    return _success("moved", message, AFFECTED_FULL)


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
    except Exception:
        return _rejected("look_failed", "無法查看。")
    actor.msg(appearance)
    return _success("looked", "你仔細打量了一番。", AFFECTED_FULL)


def _talk_scripted_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-verify the host and keyword, then call the deterministic dialogue API."""
    del session
    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    reason = interaction_reason(npc, "talk")
    if reason is not None:
        return _rejected("schedule_blocked", reason)
    if not is_dialogue_host(npc):
        return _rejected("not_dialogue_host", "對方無法交談。")
    dialogue_key = dialogue_key_for(npc)
    definition = DIALOGUE_TABLE.get(dialogue_key) if dialogue_key is not None else None
    keyword_ids = (
        [response.keyword for response in definition.responses]
        if definition is not None
        else []
    )
    if payload["keyword_id"] not in keyword_ids:
        return _rejected("unregistered_keyword", "對方不明白這個話題。")
    try:
        result = run_scripted_talk(npc, actor, payload["keyword_id"])
    except Exception:
        return _rejected("dialogue_failed", "交談失敗。")
    if result is None:
        return _rejected("no_response", "對方沒有理會你。")
    hint = f"\n{AFFINITY_DAILY_CAP_HINT}" if result.budget_capped else ""
    message = f"{npc.key}說：{result.response}{hint}"
    actor.msg(message)
    return _success("talked", message, AFFECTED_FULL)


def _talk_freeform_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> Deferred:
    """Run the guarded dialogue seam through the injected client (design D5/D6).

    Re-resolves a present ``LLMNPC`` synchronously so a tampered, ineligible,
    or schedule-blocked NPC rejects before any client or transport work; the
    Deferred settles after the seam finishes (offline degrade, memory, and
    verified-intent included).
    """
    del session
    npc = _resolve_llm_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有可以自由交談的對象。")
    reason = interaction_reason(npc, "talk")
    if reason is not None:
        return _rejected("schedule_blocked", reason)
    from web.webclient.actions.dialogue_composition import build_dialogue_client

    client = build_dialogue_client()
    deferred = npc.at_talked_to(payload["speech"], actor, client)

    def _on_success(result: Any) -> dict[str, Any]:
        if is_stale_context(result):
            # The seam showed the speech and the stale note; the panel result
            # carries the same outcome so the client reports the dropped
            # intent (F22 completion gate).
            return _success("talked", STALE_CONTEXT_NOTE, AFFECTED_FULL)
        return _success("talked", "對方回應了你的話。", AFFECTED_FULL)

    def _on_failure(failure: Any) -> dict[str, Any]:
        failure.trap(Exception)
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
    if is_companion(npc, actor):
        from world.rules.party import ALREADY_COMPANION_MESSAGE

        return _rejected("already_companion", ALREADY_COMPANION_MESSAGE)
    if party_size(actor) >= PARTY_MAX_COMPANIONS:
        from world.rules.party import PARTY_FULL_MESSAGE

        return _rejected("party_full", PARTY_FULL_MESSAGE)
    from web.webclient.actions.dialogue_composition import build_dialogue_client

    client = build_dialogue_client()
    deferred = npc.run_npc_exchange(payload["message"], actor, client)

    def _on_success(result: Any) -> dict[str, Any]:
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
            return "她婉拒了你的邀請。"
        try:
            join_party(npc, actor)
        except PartyJoinError as error:
            line = JOIN_REJECTION_MESSAGES.get(error.reason, REFUSED_MESSAGE)
            actor.msg(line)
            return line
        actor.msg(f"{npc.key}說：{DEGRADED_ACCEPT_MESSAGE}")
        actor.msg(JOINED_MESSAGE)
        return JOINED_MESSAGE

    actor.msg(f"{npc.key}說：{result.reply.speech}")
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
    from world.rules.party import (
        LEAVE_DISMISSED_MESSAGE,
        NOT_COMPANION_MESSAGE,
        leave_party,
    )

    npc = _resolve_npc(actor, payload["npc_id"])
    if npc is None:
        return _rejected("no_npc", "這裡沒有這個對象。")
    if not is_companion(npc, actor):
        return _rejected("not_companion", NOT_COMPANION_MESSAGE)
    leave_party(npc, actor, reason="dismissed")
    actor.msg(LEAVE_DISMISSED_MESSAGE)
    return _success("left", LEAVE_DISMISSED_MESSAGE, AFFECTED_FULL)


def _engage_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Re-resolve a present monster and delegate to the existing engage contract."""
    del session
    monster = _resolve_monster(actor, payload["monster_id"])
    if monster is None:
        return _rejected("no_monster", "這裡沒有這個對象。")
    try:
        engage(actor, monster)
    except CombatSessionError as error:
        reason = error.args[0] if error.args else None
        if reason is SessionReason.ALREADY_IN_COMBAT:
            return _rejected("already_in_combat", "你已在戰鬥中。")
        if reason is SessionReason.TARGET_DEAD:
            return _rejected("target_dead", "目標已經死亡。")
        if reason is SessionReason.NOT_PRESENT:
            return _rejected("no_monster", "這裡沒有這個對象。")
        return _rejected("engage_failed", "無法開始戰鬥。")
    message = "你向目標發起了攻擊！"
    actor.msg(message)
    return _success("engaged", message, AFFECTED_ENGAGE)


def _wait_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck safety and advance the clock through the shared skip helper."""
    del session
    rejection = unsafe_rejection(actor)
    if rejection is not None:
        return _rejected("unsafe_skip", rejection)
    if "daypart" in payload:
        daypart = payload["daypart"]
        try:
            clock = get_world_clock()
            seconds = seconds_until_daypart(clock.calendar, daypart)
        except DaypartError:
            return _rejected("unknown_daypart", "未知的時段。")
    elif "seconds" in payload:
        seconds = payload["seconds"]
    else:
        seconds = seconds_to_full_regen(actor)
    try:
        events = advance_skip(actor, seconds)
    except Exception:
        return _rejected("skip_failed", "無法跳過時間。")
    message = render_skip_summary(seconds, events)
    actor.msg(message)
    # Rest-point nomination trigger (title-system D4 §7.1, change G): the
    # service helper gates on a day-boundary event and never raises. The
    # composition-root import is function-local (the dispatcher precedent).
    from server.title_nomination_service import schedule_rest_boundary_nomination

    schedule_rest_boundary_nomination(actor, events)
    return _success("skipped", message, AFFECTED_FULL)


__all__ = [
    "AFFECTED_ENGAGE",
    "DAYPARTS",
    "ExplorationActionError",
    "MAX_EXIT_REF_CHARS",
    "MAX_KEYWORD_ID_CHARS",
    "MAX_NODE_ID_CHARS",
    "MAX_SPEECH_CODE_POINTS",
    "validate_engage_payload",
    "validate_look_payload",
    "validate_move_payload",
    "validate_party_invite_payload",
    "validate_party_leave_payload",
    "validate_talk_freeform_payload",
    "validate_talk_scripted_payload",
    "validate_wait_payload",
]
