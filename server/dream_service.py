"""Compose guarded dream proposals with the deterministic narrative owner.

Departure never creates a client or calls a model. A background response is
accepted only while its original owner and outstanding submission still match.
"""

from django.db import transaction
from twisted.internet import defer

from web.webclient.presentation.protocol import check_json_safety, json_byte_size, ProtocolValidationError
from world.narrative import dream_session as lifecycle
from world.narrative import dream_surface as surface
from world.narrative.authoring import AuthoringError, DIRECTION_KEYS, MAX_SUMMARY_CHARACTERS, collaborator_creative_brief, validate_direction
from world.observability import log_info, log_warn

enter_after_sleep = surface.enter_after_sleep
dream_state = surface.dream_state


def _controlled(actor, session):
    if session is None:
        return True
    import evennia
    return (getattr(session, "puppet", None) == actor
            and any(candidate is session for candidate in evennia.SESSION_HANDLER.get_sessions(include_unloggedin=True)))


def _result(outcome, code, message):
    return {"outcome": outcome, "code": code, "message": message, "affected_panels": ("dream",)}


def _refresh(actor, session):
    if session is not None and _controlled(actor, session):
        from web.webclient.presentation.ingress import refresh_after_command
        refresh_after_command(session, actor)


@defer.inlineCallbacks
def act(actor, action, *, session_id, revision, message="", direction="", session=None, client=None):
    """Authorize a current surface request, then invoke the shared lifecycle."""
    owner = surface.owner_id(actor)
    boundary = {"char": actor.pk, "session_id": session_id, "action": action}
    try:
        with transaction.atomic():
            current = surface.associated_session(actor)
            if (not _controlled(actor, session) or current is None
                    or current.session_id != session_id or current.revision != revision):
                log_warn("dream_surface_rejected", context={**boundary, "reason": "stale_or_owner"})
                return _result("rejected", "stale_dream", "夢境狀態已更新，請重新查看。")
            if action not in {"say", "draft", "confirm", "awaken"}:
                return _result("rejected", "unknown_dream_action", "無法執行這個夢境操作。")
            if action != "awaken" and current.state != lifecycle.STATE_OPEN:
                return _result("rejected", "dream_closed", "夢境已結束。")
            tick = int(surface.association(actor)["sleep"]["tick_to"])
            if action == "say":
                turn = lifecycle.begin_turn(session_id, owner, message, tick=tick)
                surface.store_direction(actor, message)
                completed = current.completed_exchanges
            else:
                saved = surface.association(actor)
                if isinstance(direction, dict):
                    check_json_safety(direction)
                    if (set(direction) - DIRECTION_KEYS or not isinstance(direction.get("summary", ""), str)
                            or len(direction.get("summary", "")) > MAX_SUMMARY_CHARACTERS):
                        return _result("rejected", "invalid_direction_shape", "故事方向需使用已知欄位，摘要上限為 2000 字。")
                    if json_byte_size(direction) > 8192:
                        return _result("rejected", "direction_too_large", "故事方向 JSON 上限為 8192 位元組。")
                    payload = direction
                elif direction.strip():
                    if len(direction.strip()) > MAX_SUMMARY_CHARACTERS:
                        return _result("rejected", "direction_too_large", "故事方向摘要上限為 2000 字。")
                    payload = {"kind": "new_story", "summary": direction.strip()}
                else:
                    payload = saved.get("draft_direction") or {"kind": "new_story", "summary": saved.get("direction", "")}
                summary = str(payload.get("summary", ""))
                if action == "draft":
                    lifecycle.preserve_draft(session_id, owner, payload, tick=tick)
                    surface.store_direction(actor, summary, draft_direction=payload)
                    surface.bump_revision_if_unchanged(actor, revision)
                elif action == "confirm":
                    validation = validate_direction(payload, owner_id=owner)
                    if not validation.valid:
                        lifecycle.preserve_draft(session_id, owner, payload, tick=tick)
                        surface.store_direction(actor, summary, draft_direction=payload)
                        surface.bump_revision_if_unchanged(actor, revision)
                        log_warn("dream_surface_rejected", context={**boundary, "reason": "invalid_direction", "reason_codes": validation.reason_codes})
                        return _result("rejected", "invalid_direction", "；".join(reason.message for reason in validation.reasons))
                    lifecycle.confirm_session(session_id, owner, direction=payload, tick=tick)
                else:
                    if not current.draft_id and current.state == lifecycle.STATE_OPEN:
                        lifecycle.preserve_draft(session_id, owner, payload, tick=tick)
                        surface.store_direction(actor, summary, draft_direction=payload)
                    lifecycle.awaken_session(session_id, owner, tick=tick)
                state = dream_state(actor)
                text = state["ending"] or "故事方向已存為私人草稿。"
                actor.msg(text)
                log_info("dream_surface_action", context={**boundary, "completed": state["completed"], "tick": tick})
                return _result("success", "dream_" + action, text)
    except (lifecycle.DreamSessionError, AuthoringError, ProtocolValidationError) as error:
        log_warn("dream_surface_rejected", context={**boundary, "reason": "invalid_state_or_direction"}, exc=error)
        return _result("rejected", "dream_refused", "目前無法接受這個操作，請確認故事方向與夢境狀態。")

    _refresh(actor, session)
    try:
        from world.ai.dream import generate_dream_exchange
        if client is None:
            from world.ai.client import OpenAICompatClient
            from world.ai.profiles import get_profile
            client = OpenAICompatClient(get_profile("dream"))
        response = yield generate_dream_exchange(
            client, completed=completed, player_message=message,
            brief=collaborator_creative_brief(owner),
        )
        with transaction.atomic():
            latest = surface.associated_session(actor)
            if (not _controlled(actor, session) or latest is None
                    or latest.session_id != session_id or latest.state != lifecycle.STATE_OPEN
                    or latest.pending_submission_id != turn.submission_id):
                lifecycle.abandon_turn(session_id, owner, turn.submission_id, reason="stale_surface", tick=tick)
                log_info("dream_surface_response_stale", context=boundary)
                return _result("rejected", "stale_dream", "夢境已更新。")
            if response is None:
                lifecycle.abandon_turn(session_id, owner, turn.submission_id, reason="generation_unavailable", tick=tick)
                surface.store_failure(actor)
                log_info("dream_surface_generation_unavailable", context=boundary)
                text = "夢境回應暫時無法生成。你仍可儲存草稿或醒來。"
                actor.msg(text)
                return _result("rejected", "dream_unavailable", text)
            # Delivery precedes accounting: a failed transport cannot consume a turn.
            actor.msg(response.scene + "\n" + response.dialogue)
            lifecycle.settle_exchange(session_id, owner, turn.submission_id,
                                      "dream:" + turn.submission_id, tick=tick)
            surface.store_response(actor, response)
            log_info("dream_surface_action", context={**boundary, "completed": completed + 1, "tick": tick})
        return _result("success", "dream_delivered", "夢境回應已送達。")
    except Exception as error:
        log_warn("dream_surface_generation_failed", context=boundary, exc=error)
        lifecycle.abandon_turn(session_id, owner, turn.submission_id, reason="generation_failed", tick=tick)
        latest = surface.associated_session(actor)
        if latest and latest.session_id == session_id and latest.state == lifecycle.STATE_OPEN:
            surface.store_failure(actor)
        return _result("rejected", "dream_unavailable", "夢境回應暫時無法生成。你仍可儲存草稿或醒來。")
    finally:
        _refresh(actor, session)
