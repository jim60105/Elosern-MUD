"""Durable, owner-scoped sleep association and dream presentation read model.

Only accepted, already committed sleep enters here. This owner never advances
world time or touches physical traits; reconnect is a pure read.
"""

from dataclasses import asdict

from django.db import transaction
from evennia.utils.dbserialize import deserialize

from world.narrative import dream_proposal, dream_session as lifecycle
from world.narrative.authoring import (
    REQUIREMENT_FIELDS,
    AuthoringError,
    draft_is_confirmed,
    get_draft,
)
from world.narrative.dream_track import render_ending, track_state
from world.narrative.models import StoryThread
from world.narrative.threads import TERMINAL_THREAD_STATES, thread_accessible
from world.observability import log_info

OPENING = (
    "雲海之上矗立著一座純白的王座。王座上的女神面容始終無法辨明，卻一邊撫慰著自己、"
    "一邊從容地和你說話。她那誇張浮誇的性器一看便是長年使用的模樣，正不住地噴湧著淫水；"
    "夢境的地面積水已漫過你的腳踝——看著那湧如泉水的液面，你明白那是女神的淫水。"
    "你可以在這裡商談故事方向，也可以隨時醒來。"
)


class DreamEntryError(RuntimeError):
    """One owner-bound dream entry was refused before any write."""

    def __init__(self, code, message):
        super().__init__(code)
        self.code = code
        self.message = message


def owner_character(actor):
    """The authenticated owner body, or ``None`` for a non-owner caller.

    A possessed companion is never the dream owner: only the player character
    itself may open its own accepted sleep's dream. This keeps every session,
    draft and dispatch record owner-scoped even when the player currently
    drives an NPC.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.possession import current_possession

    if not isinstance(actor, PlayerCharacter):
        return None
    if current_possession(actor) is not None:
        return None
    return actor


def owner_id(actor):
    """Use the authenticated owner character identity on both transports."""
    owner = owner_character(actor)
    return None if owner is None else str(owner.pk)


def scene_subject_id(actor):
    """The dream stage's logical subject identity, scoped to owner and session.

    The dream is one logical place per SLEEP SESSION, so a later session is a
    different subject: the shared loading lifecycle keys its resolution epoch
    on this identity, which is what retires a previous session's callbacks
    instead of letting them settle the surface the player is now looking at.
    The identity is bounded by construction (the owner's decimal pk plus the
    session handle the lifecycle already bounds at 64 characters), so it always
    fits the descriptor's own subject bound.
    """
    session = associated_session(actor)
    if session is None:
        return f"dream:{owner_id(actor)}"
    return f"dream:{owner_id(actor)}:{session.session_id}"


def association(actor):
    value = actor.db.dream_surface
    return deserialize(value) if value else None


def _stored_proposal(raw):
    """One canonical working proposal, or the empty proposal for a refused value."""
    try:
        return dream_proposal.normalize_proposal(raw or {})
    except dream_proposal.ProposalEditError:  # observability: ignore R2: a refused stored proposal reads as the empty proposal; the write path that produced it owns the fault
        return dream_proposal.empty_proposal()


def _seeded_from_draft(actor, session):
    """The saved draft's direction as a starting proposal and chosen thread.

    A resumed session that holds no working proposal yet - an association
    written before this change, a cleared attribute or the camping restore -
    still starts from what the player already saved. A direction the applier
    refuses leaves the proposal empty and the thread unchosen.
    """
    if not session.draft_id:
        return dream_proposal.empty_proposal(), None
    try:
        direction = get_draft(session.draft_id, owner_id(actor)).direction or {}
        proposal = dream_proposal.normalize_proposal(direction)
    except (AuthoringError, dream_proposal.ProposalEditError):  # observability: ignore R2: a foreign or refused saved direction seeds an empty proposal; entry itself still succeeds
        return dream_proposal.empty_proposal(), None
    thread_id = direction.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        thread_id = None
    return proposal, thread_id


def _wish_values(value, session):
    """The four working-proposal values a surface reads, with their defaults.

    An association written before this change still reads: the proposal is
    absent, the report and the thread are unchosen, and the lock is a
    consequence of an accepted exchange, so a lost or pre-change association
    never reopens a choice the player already made.
    """
    completed = int(session.completed_exchanges) if session is not None else 0
    return {
        "proposal": _stored_proposal(value.get("proposal")),
        "changes": value.get("changes"),
        "thread_id": value.get("thread_id"),
        "thread_locked": bool(value.get("thread_locked")) or completed > 0,
    }


def wish_state(actor):
    """The working proposal, its last settled report and the thread choice."""
    value = association(actor)
    if value is None:
        return None
    return _wish_values(value, associated_session(actor))


def offered_threads(actor):
    """The non-terminal story threads this owner may attach the wish to."""
    threads = []
    for thread in StoryThread.objects.exclude(state__in=TERMINAL_THREAD_STATES).order_by("-pk").iterator():
        if thread_accessible(thread, owner_id(actor)):
            threads.append({"id": thread.thread_id,
                            "label": thread.factual_summary.strip()[:160] or "未命名的故事線"})
            if len(threads) == 32:
                break
    return threads


def working_direction(actor):
    """The working proposal as one authoring direction, thread included."""
    wish = wish_state(actor) or {
        "proposal": dream_proposal.empty_proposal(),
        "thread_id": None,
    }
    proposal = wish["proposal"]
    direction = {
        "kind": "thread_direction" if wish["thread_id"] else "new_story",
        "thread_id": wish["thread_id"],
        "summary": proposal["summary"],
        "requirements": [dict(row) for row in proposal["requirements"]],
    }
    for field in dream_proposal.LIST_FIELDS:
        if proposal[field]:
            direction[field] = list(proposal[field])
    return direction


def choose_thread(actor, thread_id):
    """Record the proposal's chosen thread; the service owns the validation."""
    value = association(actor)
    value["thread_id"] = thread_id
    actor.db.dream_surface = value


def lock_thread(actor):
    """The first accepted message fixes the choice for this session."""
    value = association(actor)
    value["thread_locked"] = True
    actor.db.dream_surface = value


def associated_session(actor):
    owner = owner_character(actor)
    if owner is None:
        return None
    value = association(actor)
    if value is None:
        return None
    session = lifecycle.get_session(value["session_id"], owner_id(actor))
    if session is None or session.state != lifecycle.STATE_OPEN:
        return session
    from world.rules.sleep_receipt import (
        read_sleep_receipt,
        read_sleep_view_generation,
    )

    if value.get("view_generation") != read_sleep_view_generation(owner):
        return None
    try:
        receipt = read_sleep_receipt(owner)
    except Exception:  # observability: ignore R2: an unreadable receipt closes the active surface; the authoritative entry reports the fault
        return None
    if (
        receipt is None
        or not receipt.sleeping
        or receipt.sleep_id != value.get("sleep_id")
    ):
        return None
    return session


def _raw_associated_session(actor):
    """The recorded session without the current-view freshness check.

    Entry uses this to resume an unconfirmed discussion across a later
    explicit sleep; every read and action keeps the strict
    :func:`associated_session` guard so a superseded control view is never
    presented as current.
    """
    value = association(actor)
    if value is None or owner_id(actor) is None:
        return None
    return lifecycle.get_session(value["session_id"], owner_id(actor))


def enter_for_owner(
    actor,
    *,
    sleep_id,
    revision,
    generation,
    session=None,
):
    """Associate the authenticated owner's accepted sleeping receipt.

    Entry is legal at zero accepted elapsed time and for a forced receipt with
    explicit opt-in; it never claims completed sleep, restores resources or
    advances the clock. The accepted receipt is the identity: the caller must
    name its exact ``sleep_id``/``revision`` and the owner must still be the
    sleeping, unpossessed body. An NPC companion can never become the owner.
    """
    from world.rules.possession import current_possession
    from world.rules.sleep_receipt import (
        KIND_FORCED,
        KIND_VOLUNTARY,
        STATE_SLEEPING,
        read_sleep_receipt,
        read_sleep_view_generation,
        write_sleep_view_decision,
        DECISION_ENTERED,
        CONTINUATION_NONE,
    )

    owner = owner_character(actor)
    if owner is None:
        raise DreamEntryError(
            "dream_not_owner", "只有甦醒的主人可以進入自己的夢境。"
        )
    if getattr(getattr(owner, "db", None), "possessed_by", None) is not None:
        raise DreamEntryError(
            "dream_not_owner", "只有甦醒的主人可以進入自己的夢境。"
        )
    if current_possession(owner) is not None:
        raise DreamEntryError(
            "dream_possessed", "請先歸位，再進入自己的夢境。"
        )
    if session is not None and getattr(session, "puppet", None) is not owner:
        raise DreamEntryError(
            "dream_not_owner", "只有甦醒的主人可以進入自己的夢境。"
        )
    try:
        receipt = read_sleep_receipt(owner)
    except Exception as error:
        raise DreamEntryError(
            "dream_stale_sleep", "找不到這次睡眠的紀錄，無法進入夢境。"
        ) from error
    if (
        receipt is None
        or not receipt.sleeping
        or receipt.state != STATE_SLEEPING
        or receipt.sleep_id != sleep_id
        or receipt.revision != int(revision)
        or receipt.kind not in (KIND_VOLUNTARY, KIND_FORCED)
        or (
            receipt.owner_id is not None
            and int(receipt.owner_id) != int(owner.pk)
        )
    ):
        raise DreamEntryError(
            "dream_stale_sleep", "這次睡眠已經更新，請重新查看。"
        )
    current_generation = read_sleep_view_generation(owner)
    if int(current_generation) != int(generation):
        raise DreamEntryError(
            "dream_stale_sleep", "這次睡眠已經更新，請重新查看。"
        )
    generation = current_generation
    tick_from = int(receipt.entry_tick)
    tick_to = int(receipt.settled_through_tick)
    requested_seconds = int(receipt.accepted_seconds)
    elapsed = max(0, tick_to - tick_from)
    event_kinds = ()
    if receipt.last_result:
        event_kinds = tuple(receipt.last_result.get("event_kinds", ()))
    with transaction.atomic():
        # The recorded association is read once: it names the sleep this
        # surface was last entered for, which is what distinguishes returning
        # to the same dream from arriving on a later sleep.
        old = association(owner)
        previous = _raw_associated_session(owner)
        if previous and previous.outcome != lifecycle.OUTCOME_CONFIRMED:
            session = lifecycle.resume_saved_session(
                previous.session_id,
                owner_id(actor),
                reopen_conversation=(
                    not old or old.get("sleep_id") != receipt.sleep_id
                ),
                tick=int(tick_to),
            )
        else:
            session = lifecycle.open_session_for(owner_id(actor))
        if session is None:
            session = lifecycle.open_session(owner_id(actor), tick=int(tick_to))
        retained = old if old and old["session_id"] == session.session_id else {}
        if "proposal" in retained:
            proposal = _stored_proposal(retained.get("proposal"))
            thread_id = retained.get("thread_id")
        else:
            proposal, thread_id = _seeded_from_draft(owner, session)
        owner.db.dream_surface = {
            "session_id": session.session_id,
            "owner_id": int(owner.pk),
            "sleep_id": receipt.sleep_id,
            "sleep_revision": int(receipt.revision),
            "view_generation": int(generation),
            "sleep": {
                "tick_from": int(tick_from), "tick_to": int(tick_to),
                "requested_seconds": int(requested_seconds),
                "seconds": elapsed,
                "event_kinds": sorted({str(kind) for kind in event_kinds}),
            },
            "scene": retained.get("scene", ""),
            "dialogue": retained.get("dialogue", ""),
            "proposal": proposal,
            "changes": retained.get("changes"),
            "thread_id": thread_id,
            "thread_locked": bool(retained.get("thread_locked"))
            or int(session.completed_exchanges) > 0,
            "failure": False,
        }
        if retained:
            bump_revision_if_unchanged(owner, int(session.revision))
        write_sleep_view_decision(
            owner,
            {
                "generation": int(generation),
                "sleep_id": receipt.sleep_id,
                "decision": DECISION_ENTERED,
                "continuation": CONTINUATION_NONE,
                "last_operation_id": None,
            },
        )
        log_info("dream_sleep_associated", context={
            "char": owner.pk, "session_id": session.session_id,
            "tick_from": int(tick_from), "tick_to": int(tick_to),
            "requested_seconds": int(requested_seconds),
            "completed": int(session.completed_exchanges),
        })
    return dream_state(owner)


def bump_revision_if_unchanged(actor, revision):
    """Draft edits must invalidate surface requests even with the same handle."""
    session = associated_session(actor)
    if int(session.revision) == revision:
        session.revision = revision + 1
        session.save(update_fields=["revision", "updated_at"])


def store_response(actor, response):
    value = association(actor)
    value["scene"] = response.scene
    value["dialogue"] = response.dialogue
    value["proposal"] = dream_proposal.normalize_proposal(response.proposal)
    value["changes"] = response.changes
    value["failure"] = False
    actor.db.dream_surface = value


def store_failure(actor):
    value = association(actor)
    value["failure"] = True
    actor.db.dream_surface = value


def store_proposal(actor, proposal, *, thread_id):
    """Replace the working proposal with the player's own finalized form.

    A player write is not a settled exchange, so the change report of the last
    exchange is cleared: it described a collaborator edit that this form has
    replaced. The stored proposal is canonical, exactly as a settled response
    stores its own, and a true write clears a previous failure.
    """
    value = association(actor)
    value["proposal"] = dream_proposal.normalize_proposal(proposal)
    value["changes"] = None
    value["thread_id"] = thread_id
    value["failure"] = False
    actor.db.dream_surface = value


def reset_cache(actor):
    """Drop the actor's in-process association cache after a rolled-back action.

    A failed confirmation rolls its Attribute writes back in the database, but
    the in-process Attribute cache would otherwise keep serving the aborted
    value to the next read and to the panel. The idmapper cache holds the
    Attribute instances themselves, so the flush is what makes the next read
    authoritative -- the same discipline ``evict_created_actors`` applies to
    actors a rolled-back activation created. Safely callable on any actor: an
    object without the Attribute handler is simply skipped.
    """
    attributes = getattr(actor, "attributes", None)
    if attributes is not None:
        attributes.reset_cache()
    from world.rules.surfaces import flush_idmapper_cache

    flush_idmapper_cache()


def dream_state(actor):
    """Server-authored actions, count, track, stage, prose and sleep identity.

    The stage is published with the flags the surface derives from it, so a
    client never re-derives what the session already decides: free text is
    offered only while conversing, choosing a thread only before the choice
    locks, finalizing only while conversing with no response in flight, and
    editing or confirmation only after the story is finalized.
    """
    # Imported lazily: the art owner's scene resolver is the single artwork
    # seam, and keeping the import inside the read keeps this model's own
    # module-level surface as light as it was before the artwork moved.
    from world.art.presenter import describe_dream_scene

    value = association(actor)
    if value is None:
        return None
    session = associated_session(actor)
    view = lifecycle.progress(session)
    opened = session.state == lifecycle.STATE_OPEN
    conversing = session.stage == lifecycle.STAGE_CONVERSING
    finalized = session.stage == lifecycle.STAGE_FINALIZED
    pending = bool(session.pending_submission_id)
    ending = render_ending(view.completed) if not opened else None
    draft = get_draft(session.draft_id, owner_id(actor)) if session.draft_id else None
    confirmed = bool(draft and draft_is_confirmed(draft))
    draft_direction = draft.direction if draft else None
    wish = _wish_values(value, session)
    proposal = wish["proposal"]
    displayed_direction = (draft_direction or {}).get("summary", proposal["summary"])
    return {
        "session_id": session.session_id, "revision": int(session.revision),
        "completed": view.completed, "remaining": view.remaining,
        "can_input": view.free_text_allowed and not pending,
        "can_confirm": opened and finalized,
        "can_finalize": opened and conversing and not pending,
        "can_choose_thread": opened and conversing and not wish["thread_locked"] and not pending,
        "can_edit": opened and finalized,
        "can_draft": opened, "can_awaken": True,
        "pending": pending, "open": opened,
        # One stage per session, exactly as the lifecycle stores it: the
        # published working proposal, the last settled report and the chosen
        # thread travel with it, so the panel never reconstructs either.
        "stage": session.stage, "proposal": proposal,
        "changes": wish["changes"], "thread_id": wish["thread_id"],
        "confirmed": confirmed, "failure": bool(value.get("failure")),
        "drafted": bool(session.draft_id),
        "thread_choices": offered_threads(actor) if opened else [],
        # The shown requirement rows and their identity are published once, as
        # the top-level keys below; carrying them a second time inside the
        # preference projection would only grow the payload every client must
        # validate before it can render the stage.
        "draft_preferences": {key: item for key, item in (draft_direction or {}).items()
                              if key not in ("summary", *REQUIREMENT_FIELDS)}
        if draft_direction else None,
        "opening": OPENING, "scene": value.get("scene", ""),
        # The stage's artwork is the shared canonical scene descriptor of the
        # dream's own chain, resolved read-only by the art owner: this model
        # never builds a URL, never reads the sleeper's location and never
        # mutates the session, the authoring store or any art record.
        "scene_art": describe_dream_scene(scene_subject_id(actor)),
        "dialogue": value.get("dialogue", ""),
        "direction_parts": [displayed_direction[offset:offset + 2000]
                            for offset in range(0, len(displayed_direction), 2000)],
        # The readable bounded experience requirements for the version being
        # confirmed, plus the reviewable identity of the persisted shown
        # version. A persisted draft's frozen rows win over the collaborator's
        # latest proposal, because that is the version confirmation compares.
        "requirements": (draft_direction or {}).get("requirements")
        or [dict(row) for row in proposal["requirements"]],
        "requirement_version": (draft_direction or {}).get("requirement_version"),
        "track": asdict(track_state(view.completed)), "sleep": dict(value["sleep"]),
        "ending": (f"{ending.phase}，女神的高潮餘韻漸漸平息，雲海的夢境淡去，你醒了。" if ending and ending.climax_reached else "雲海的夢境漸漸淡去，你醒了。") if ending else "",
        "ending_phase": ending.phase if ending else "",
    }
