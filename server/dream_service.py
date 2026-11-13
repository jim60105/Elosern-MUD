"""Compose guarded dream proposals with the deterministic narrative owner.

Departure never creates a client or calls a model. A background response is
accepted only while its original owner and outstanding submission still match.
"""

from django.db import transaction
from twisted.internet import defer

from web.webclient.presentation.protocol import check_json_safety, json_byte_size, ProtocolValidationError
from world.narrative import dream_proposal
from world.narrative import dream_session as lifecycle
from world.narrative import dream_surface as surface
from world.narrative.authoring import (
    REASON_MESSAGES,
    AuthoringError,
    DIRECTION_KEYS,
    MAX_DIRECTION_BYTES,
    MAX_SUMMARY_CHARACTERS,
    collaborator_creative_brief,
    validate_direction,
)
from world.observability import log_info, log_warn
from world.rules.presentation_events import on_publication_commit

dream_state = surface.dream_state


def _controlled(actor, session):
    if session is None:
        return True
    import evennia
    return (getattr(session, "puppet", None) == actor
            and any(candidate is session for candidate in evennia.SESSION_HANDLER.get_sessions(include_unloggedin=True)))


def _result(outcome, code, message, *, panels=("dream",)):
    return {
        "outcome": outcome,
        "code": code,
        "message": message,
        "affected_panels": panels,
    }


def _refuse(boundary, code, message):
    """One stage refusal: a warn trace carrying the code, and nothing written."""
    log_warn("dream_surface_rejected", context={**boundary, "reason": code})
    return _result("rejected", code, message)


def _direction_refusal(error: AuthoringError) -> str:
    """One bounded player-facing line for a refused direction payload."""
    messages = [
        getattr(reason, "message", "") for reason in getattr(error, "reasons", ())
    ]
    return "；".join(message for message in messages if message) or (
        "夢境方向的內容不完整或超出限制。"
    )


def _refresh(actor, session):
    if session is not None and _controlled(actor, session):
        from web.webclient.presentation.ingress import refresh_after_command
        refresh_after_command(session, actor)


def _sleep_view_panels():
    return ("dream", "sleep_handoff", "status")


def _sleep_result(outcome, code, message, *, continuation=None, panels=None):
    result = {
        "outcome": outcome,
        "code": code,
        "message": message,
        "affected_panels": (
            _sleep_view_panels() if panels is None else panels
        ),
    }
    if continuation is not None:
        result["data"] = {"continuation": str(continuation)}
    return result


def _continue_owner_after_commit(actor, sleep_id, generation):
    """Run the rules continuation after the narrative transaction commits.

    The durable pending intent was written in that same transaction, so a
    crash before this callback leaves a resumable authorization instead of a
    stranded sleep.
    """
    from world.rules.camping import reconcile_camp
    from world.rules.time_skip import continue_owner_sleep

    try:
        result = continue_owner_sleep(
            actor, sleep_id=sleep_id, expected_generation=generation
        )
    except Exception as error:  # observability: ignore R2: the committed narrative closure stays truthful; the durable pending intent resumes the rules continuation
        log_warn(
            "owner_sleep_continuation_deferred",
            context={
                "char": str(getattr(actor, "pk", "?")),
                "sleep_id": sleep_id,
            },
            exc=error,
        )
        return None
    # A camp that entered this dream continues its slower selected sleepers
    # under its own retained authorization once the owner's part settled.
    reconcile_camp(actor)
    return result


def authorize_departure_continuation(actor) -> None:
    """Commit same-receipt intent for an explicit confirm/awaken departure.

    Called inside the narrative transaction. Draft preservation, failed
    generation and rejected confirmation never call it.
    """
    from world.rules.sleep_receipt import read_sleep_view_generation
    from world.rules.time_skip import authorize_owner_sleep_continuation

    value = surface.association(actor)
    if value is None or "sleep_id" not in value:
        return
    owner = surface.owner_character(actor)
    if owner is None:
        return
    generation = read_sleep_view_generation(owner)
    authorized = authorize_owner_sleep_continuation(
        owner,
        sleep_id=value["sleep_id"],
        revision=int(value.get("sleep_revision", 0)),
        generation=generation,
    )
    if authorized is not None:
        # The committed continuation is one settlement of the retained sleep,
        # so it must publish under the causal group of the action that
        # authorized it even though it runs after this transaction commits
        # (webclient-settlement-alignment). A plain ``transaction.on_commit``
        # would run outside that group and the checkpoint would arrive as a
        # second publication.
        on_publication_commit(
            lambda: _continue_owner_after_commit(
                owner, authorized["sleep_id"], authorized["generation"]
            )
        )


def pending_sleep_question(actor) -> str | None:
    """Return the pending owner-sleep dream question, or ``None``."""
    from world.rules.sleep_control import SLEEP_DREAM_QUESTION
    from world.rules.time_skip import owner_sleep_view_state

    state = owner_sleep_view_state(actor)
    if state is None or not state["pending"]:
        return None
    return SLEEP_DREAM_QUESTION


def answer_sleep_dream(
    actor,
    *,
    decision,
    sleep_id,
    revision,
    generation,
    session=None,
    defer_continuation=False,
):
    """Answer the authenticated owner's current pre-recovery dream question.

    Text ``dream enter``/``dream decline`` and the browser's separate answer
    action share this one guarded operation. Enter revalidates owner, control
    and the accepted receipt; decline records the durable decision and starts
    the retained owner continuation only when every operable present body is
    asleep. Neither branch invents elapsed time.

    ``defer_continuation`` is the sleep-entry seam (``world.rules.camping``):
    the caller owns the surrounding entry transaction and the continuation.
    A deferred decline records the explicit decision with no continuation
    authorization and starts nothing; a deferred enter is the ordinary guarded
    entry, whose stage the entry's own completion publishes after commit.
    """
    from world.rules.time_skip import (
        decline_owner_sleep_dream,
        owner_sleep_view_state,
    )

    boundary = {
        "char": getattr(actor, "pk", "?"),
        "sleep_id": sleep_id,
        "decision": decision,
    }
    if decision == "enter":
        view = owner_sleep_view_state(actor)
        if (
            view is None
            or view["sleep_id"] != sleep_id
            or view["revision"] != int(revision)
            or view["generation"] != int(generation)
            or (
                not view["pending"]
                and view["decision"] is not None
                and view["decision"]["decision"] == "declined"
            )
        ):
            return _sleep_result(
                "rejected", "stale_sleep", "這次睡眠已經更新，請重新查看。"
            )
        try:
            state = surface.enter_for_owner(
                actor,
                sleep_id=sleep_id,
                revision=revision,
                generation=generation,
                session=session,
            )
        except surface.DreamEntryError as error:
            log_warn(
                "sleep_dream_answer_rejected",
                context={**boundary, "reason": error.code},
            )
            return _sleep_result("rejected", error.code, error.message)
        except Exception as error:
            log_warn(
                "sleep_dream_answer_rejected",
                context={**boundary, "reason": "invalid_state"},
                exc=error,
            )
            return _sleep_result(
                "rejected", "dream_refused", "目前無法進入夢境，請重新查看睡眠狀態。"
            )
        if state is None:
            return _sleep_result(
                "rejected", "dream_refused", "目前無法進入夢境，請重新查看睡眠狀態。"
            )
        return _sleep_result("success", "dream_entered", "你進入了夢境。")

    if decision != "decline":
        return _sleep_result("rejected", "invalid_decision", "無法執行這個夢境操作。")
    if defer_continuation:
        from world.rules.sleep_receipt import CONTINUATION_NONE, DECISION_DECLINED
        from world.rules.time_skip import record_owner_sleep_decision

        try:
            record_owner_sleep_decision(
                actor,
                sleep_id=sleep_id,
                revision=revision,
                generation=generation,
                decision=DECISION_DECLINED,
                continuation=CONTINUATION_NONE,
            )
        except Exception as error:
            log_warn(
                "sleep_dream_answer_rejected",
                context={**boundary, "reason": "stale_or_invalid"},
                exc=error,
            )
            return _sleep_result(
                "rejected", "stale_sleep", "這次睡眠已經更新，請重新查看。"
            )
        return _sleep_result(
            "success",
            "dream_declined",
            "已保留這次睡眠。",
            continuation="none",
        )
    try:
        value, auto = decline_owner_sleep_dream(
            actor,
            sleep_id=sleep_id,
            revision=revision,
            generation=generation,
        )
    except Exception as error:
        log_warn(
            "sleep_dream_answer_rejected",
            context={**boundary, "reason": "stale_or_invalid"},
            exc=error,
        )
        return _sleep_result(
            "rejected", "stale_sleep", "這次睡眠已經更新，請重新查看。"
        )
    if auto:
        result = _continue_owner_after_commit(
            actor, value["sleep_id"], value["generation"]
        )
        continuation = (
            result.continuation if result is not None else "none"
        )
        message = (
            result.summary
            if result is not None and result.summary
            else "已保留這次睡眠。"
        )
    else:
        continuation = "none"
        message = "已保留這次睡眠；可輸入 sleep continue 繼續。"
    return _sleep_result(
        "success",
        "dream_declined",
        message,
        continuation=continuation,
        panels=() if auto else None,
    )


def resume_owner_sleep_continuation(actor):
    """Resume one durable pending owner continuation after reconnect."""
    from world.rules.camping import reconcile_camp
    from world.rules.time_skip import resume_pending_owner_continuation

    result = resume_pending_owner_continuation(actor)
    # Reconcile a pending camp even when the ordinary owner resume returned
    # early (no receipt, a completed owner sleep or no pending intent).
    reconcile_camp(actor)
    return result


@defer.inlineCallbacks
def act(actor, action, *, session_id, revision, message="", direction="", thread_id=None, session=None, client=None):
    """Authorize a current surface request, then invoke the shared lifecycle."""
    owner = surface.owner_id(actor)
    boundary = {"char": actor.pk, "session_id": session_id, "action": action}
    if owner is None:
        log_warn("dream_surface_rejected", context={**boundary, "reason": "not_owner"})
        return _result("rejected", "dream_not_owner", "只有甦醒的主人可以進入自己的夢境。")
    try:
        with transaction.atomic():
            current = surface.associated_session(actor)
            if (not _controlled(actor, session) or current is None
                    or current.session_id != session_id or current.revision != revision):
                log_warn("dream_surface_rejected", context={**boundary, "reason": "stale_or_owner"})
                return _result("rejected", "stale_dream", "夢境狀態已更新，請重新查看。")
            if action not in {"choose_thread", "say", "finalize", "draft", "confirm", "awaken"}:
                return _result("rejected", "unknown_dream_action", "無法執行這個夢境操作。")
            if action != "awaken" and current.state != lifecycle.STATE_OPEN:
                return _result("rejected", "dream_closed", "夢境已結束。")
            # One stage, one rule: manual editing is allowed exactly when free
            # text is closed. Every refusal below writes nothing.
            wish = surface.wish_state(actor)
            supplied = (
                direction
                if isinstance(direction, dict)
                else (direction or "").strip()
            )
            finalized = current.stage != lifecycle.STAGE_CONVERSING
            if finalized and action in {"say", "finalize"}:
                return _refuse(boundary, "dream_finalized", "你已停止訴說，願望改由你親自修改。")
            if finalized and action == "choose_thread":
                return _refuse(boundary, "thread_choice_closed", "這一夜的訴說已經結束，願望的歸屬不能再改。")
            if action == "finalize" and current.pending_submission_id:
                return _refuse(boundary, "dream_pending_response", "女神還在回應，請稍候再停止訴說。")
            if action == "confirm" and not finalized:
                return _refuse(boundary, "not_finalized", "請先停止訴說，再許下願望。")
            if action == "draft" and not finalized and supplied:
                return _refuse(boundary, "direction_locked", "訴說期間願望由女神修改；停止訴說後才能親自修改。")
            tick = int(surface.association(actor)["sleep"]["tick_to"])
            if action == "choose_thread":
                # The choice precedes the first message and then locks: it is
                # refused without a write both after an accepted message
                # (including one whose generation failed) and for a thread this
                # owner is not currently offered.
                if wish["thread_locked"]:
                    log_warn("dream_surface_rejected", context={**boundary, "reason": "thread_locked"})
                    return _result("rejected", "thread_locked", "說出第一句話後，願望的歸屬便不能再改。")
                if thread_id is not None and thread_id not in [
                        entry["id"] for entry in surface.offered_threads(actor)]:
                    log_warn("dream_surface_rejected", context={**boundary, "reason": "unknown_thread"})
                    return _result("rejected", "unknown_thread", REASON_MESSAGES["unknown_thread"])
                surface.choose_thread(actor, thread_id)
                surface.bump_revision_if_unchanged(actor, revision)
                log_info("dream_surface_action", context={**boundary, "tick": tick})
                return _result("success", "dream_choose_thread", "已選定願望的歸屬。")
            if action == "finalize":
                # Closing free text is the owner's own act; the working
                # proposal becomes the session draft it takes over from.
                lifecycle.finalize_session(session_id, owner, tick=tick)
                lifecycle.preserve_draft(session_id, owner, surface.working_direction(actor), tick=tick)
                text = "你停止了訴說。接下來由你親自修改願望。"
                actor.msg(text)
                log_info("dream_surface_action", context={**boundary, "tick": tick})
                return _result("success", "dream_finalize", text)
            if action == "say":
                turn = lifecycle.begin_turn(session_id, owner, message, tick=tick)
                # The message is the turn's input, never the proposal: the
                # accepted turn locks the thread choice and the collaborator
                # receives the proposal as it stands before this exchange.
                surface.lock_thread(actor)
                proposal = wish["proposal"]
                thread_label = next(
                    (entry["label"] for entry in surface.offered_threads(actor)
                     if entry["id"] == wish["thread_id"]),
                    "",
                )
                completed = current.completed_exchanges
            else:
                passthrough = {}
                form_thread = wish["thread_id"]
                proposal = wish["proposal"]
                # Only the actions that take content can carry a form: a
                # departure leaves both the proposal and the draft alone.
                form = finalized and supplied and action in {"draft", "confirm"}
                if form and isinstance(direction, dict):
                    check_json_safety(direction)
                    if (set(direction) - DIRECTION_KEYS or not isinstance(direction.get("summary", ""), str)
                            or len(direction.get("summary", "")) > MAX_SUMMARY_CHARACTERS):
                        return _result("rejected", "invalid_direction_shape", "故事方向需使用已知欄位，摘要上限為 2000 字。")
                    # The transport bound is the store's own bound: a direction
                    # that carries the maximum summary and the maximum bounded
                    # requirements is legal (authoring accepts it), so the
                    # ingress must not refuse it with a tighter cap.
                    if json_byte_size(direction) > MAX_DIRECTION_BYTES:
                        return _result("rejected", "direction_too_large", f"故事方向 JSON 上限為 {MAX_DIRECTION_BYTES} 位元組。")
                    # The form keeps the locked choice. The key's presence is
                    # what the rule reads: an omitted key keeps the choice (a
                    # text client's form never names it), a present string must
                    # repeat it, and a present null may only release a choice
                    # whose thread has ended.
                    if "thread_id" in direction:
                        candidate = direction["thread_id"]
                        if isinstance(candidate, str):
                            if candidate != wish["thread_id"]:
                                return _refuse(boundary, "thread_locked", "說出第一句話後，願望的歸屬便不能再改。")
                        elif candidate is None:
                            offered = {entry["id"] for entry in surface.offered_threads(actor)}
                            if wish["thread_id"] in offered:
                                return _refuse(boundary, "thread_locked", "說出第一句話後，願望的歸屬便不能再改。")
                        else:
                            return _refuse(boundary, "thread_locked", "說出第一句話後，願望的歸屬便不能再改。")
                        form_thread = candidate
                    try:
                        proposal = dream_proposal.normalize_proposal(direction)
                    except dream_proposal.ProposalEditError:
                        log_warn(
                            "dream_surface_rejected",
                            context={**boundary, "reason": "invalid_direction"},
                        )
                        return _result(
                            "rejected", "invalid_direction", "願望的內容不完整或超出限制。"
                        )
                    passthrough = {
                        key: direction[key] for key in ("effects", "revisions")
                        if key in direction
                    }
                elif form:
                    if len(supplied) > MAX_SUMMARY_CHARACTERS:
                        return _result("rejected", "direction_too_large", "故事方向摘要上限為 2000 字。")
                    # A typed form rewrites the summary the player can read and
                    # keeps the lists and requirement rows the stage shows.
                    proposal = {**wish["proposal"], "summary": supplied}
                # The refusal comes before the surface write: a confirmation
                # without a formed wish must leave the dream exactly as it was.
                if action == "confirm" and not str(proposal["summary"]).strip():
                    return _refuse(boundary, "empty_direction", "請先讓願望成形，再許下願望。")
                if form:
                    surface.store_proposal(actor, proposal, thread_id=form_thread)
                payload = {**surface.working_direction(actor), **passthrough}
                if action == "draft":
                    try:
                        lifecycle.preserve_draft(session_id, owner, payload, tick=tick)
                    except AuthoringError as error:
                        # A malformed shown requirement set is refused without a
                        # durable write: the store owns the row shape, and
                        # nothing malformed may reach the published panel.
                        log_warn(
                            "dream_surface_rejected",
                            context={**boundary, "reason": "invalid_direction"},
                        )
                        return _result(
                            "rejected", "invalid_direction", _direction_refusal(error)
                        )
                    surface.bump_revision_if_unchanged(actor, revision)
                elif action == "confirm":
                    # The form the player submits here is the version shown:
                    # saving it above stamped its requirement identity, so the
                    # check runs on exactly what that save produced and what
                    # gets confirmed is what the player wrote. Deterministic,
                    # no model call.
                    draft = lifecycle.preserve_draft(session_id, owner, payload, tick=tick)
                    validation = validate_direction(draft.direction, owner_id=owner)
                    if not validation.valid:
                        surface.bump_revision_if_unchanged(actor, revision)
                        log_warn("dream_surface_rejected", context={**boundary, "reason": "invalid_direction", "reason_codes": validation.reason_codes})
                        return _result("rejected", "invalid_direction", "；".join(reason.message for reason in validation.reasons))
                    # A truthful receipt through ordinary output: the durable
                    # work record, not the notice, is the evidence, and a
                    # confirmation never claims an arrangement.
                    from world.narrative import dispatch_status

                    lifecycle.confirm_session(session_id, owner, tick=tick)
                    authorize_departure_continuation(actor)
                    # Delivered only once the confirmation has committed, so a
                    # rolled-back confirmation never produced a receipt. The
                    # durable work record, not this notice, is the evidence.
                    transaction.on_commit(
                        lambda: dispatch_status.deliver_status(actor)
                    )
                else:
                    # Awakening keeps the version that is right for the stage:
                    # a conversation still in progress saves what the
                    # collaborator last produced, while a finalized session
                    # leaves the draft its finalize (or sixth exchange) saved.
                    if (current.state == lifecycle.STATE_OPEN and not finalized
                            and not dream_proposal.is_empty(wish["proposal"])):
                        lifecycle.preserve_draft(session_id, owner, surface.working_direction(actor), tick=tick)
                    lifecycle.awaken_session(session_id, owner, tick=tick)
                    authorize_departure_continuation(actor)
                    # The departure is only durable once this transaction
                    # commits, so the surface it changed is published after
                    # that: the retained-sleep continuation publishes only when
                    # this receipt authorizes one for the moment of departure,
                    # and a client that is told nothing keeps showing the dream
                    # it has already left.
                    on_publication_commit(lambda: _refresh(actor, session))
                state = dream_state(actor)
                text = state["ending"] or "願望已替你收著。"
                actor.msg(text)
                log_info("dream_surface_action", context={**boundary, "completed": state["completed"], "tick": tick})
                # The departure changes the dream surface itself, so its result
                # always names that panel. The retained-sleep settlement runs
                # as a continuation that only publishes when it is authorized
                # for this receipt; when it is not, naming the panel here is
                # the only thing that tells the client the dream ended.
                return _result("success", "dream_" + action, text)
    except lifecycle.DreamInputRejected as error:
        log_warn("dream_surface_rejected", context={**boundary, "reason": error.code}, exc=error)
        text = "交流文字不可空白。" if error.code == lifecycle.REASON_EMPTY_INPUT else "交流文字上限為 4000 字。"
        return _result("rejected", error.code, text)
    except (lifecycle.DreamSessionError, AuthoringError, ProtocolValidationError) as error:
        log_warn("dream_surface_rejected", context={**boundary, "reason": "invalid_state_or_direction"}, exc=error)
        # The refused action's Attribute and session writes rolled back with the
        # transaction; drop the in-process cache so the next read (and the
        # panel) serves the authoritative row instead of the aborted value.
        surface.reset_cache(actor)
        return _result("rejected", "dream_refused", "目前無法接受這個操作，請確認故事方向與夢境狀態。")

    _refresh(actor, session)
    tap = None
    try:
        from world.ai.dream import generate_dream_exchange
        from world.ai.guardrail import CallIdTap
        if client is None:
            from world.ai.client import OpenAICompatClient
            from world.ai.profiles import get_profile
            client = OpenAICompatClient(get_profile("dream"))
        # A fresh tap per turn names the actual guarded call in the failure
        # event; it stays None when the failure precedes any guarded call.
        tap = CallIdTap(client)
        response = yield generate_dream_exchange(
            tap, completed=completed, player_message=message,
            brief=collaborator_creative_brief(owner),
            proposal=proposal, thread_label=thread_label,
        )
        with transaction.atomic():
            latest = surface.associated_session(actor)
            # A proposal that moved while this exchange was generated is a
            # different wish than the one the collaborator edited, so the
            # response is stale and applies no edits.
            wish = surface.wish_state(actor)
            if (not _controlled(actor, session) or latest is None
                    or latest.session_id != session_id or latest.state != lifecycle.STATE_OPEN
                    or latest.stage != lifecycle.STAGE_CONVERSING
                    or latest.pending_submission_id != turn.submission_id
                    or wish is None or wish["proposal"] != proposal):
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
            if completed + 1 >= lifecycle.MAX_EXCHANGES:
                # The sixth exchange closes free text: the proposal that
                # exchange produced becomes the session draft in the same
                # transaction that counted it.
                lifecycle.preserve_draft(
                    session_id, owner, surface.working_direction(actor), tick=tick
                )
            log_info("dream_surface_action", context={**boundary, "completed": completed + 1, "tick": tick})
        return _result("success", "dream_delivered", "夢境回應已送達。")
    except Exception as error:
        log_warn("dream_surface_generation_failed", context={
            **boundary, "input": message,
            "call_id": tap.latest if tap is not None else None,
        }, exc=error)
        lifecycle.abandon_turn(session_id, owner, turn.submission_id, reason="generation_failed", tick=tick)
        latest = surface.associated_session(actor)
        if latest and latest.session_id == session_id and latest.state == lifecycle.STATE_OPEN:
            surface.store_failure(actor)
        return _result("rejected", "dream_unavailable", "夢境回應暫時無法生成。你仍可儲存草稿或醒來。")
    finally:
        _refresh(actor, session)
