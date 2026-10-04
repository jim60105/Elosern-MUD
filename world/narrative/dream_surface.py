"""Durable, owner-scoped sleep association and dream presentation read model.

Only accepted, already committed sleep enters here. This owner never advances
world time or touches physical traits; reconnect is a pure read.
"""

from dataclasses import asdict

from django.db import transaction
from evennia.utils.dbserialize import deserialize

from world.narrative import dream_session as lifecycle
from world.narrative.authoring import draft_is_confirmed, get_draft
from world.narrative.dream_track import render_ending, track_state
from world.narrative.models import StoryThread
from world.narrative.threads import TERMINAL_THREAD_STATES, thread_accessible
from world.observability import log_info

OPENING = "純白的夢境裡只有一張床。床上的身影帶著女神般的氣質，面容始終無法辨明。你可以在這裡商談故事方向，也可以隨時醒來。"


def owner_id(actor):
    """Use the same persistent character identity on both transports."""
    return str(actor.pk)


def association(actor):
    value = actor.db.dream_surface
    return deserialize(value) if value else None


def associated_session(actor):
    value = association(actor)
    if value is None:
        return None
    return lifecycle.get_session(value["session_id"], owner_id(actor))


def enter_after_sleep(actor, *, tick_from, tick_to, requested_seconds, events=()):
    """Associate actual committed ticks, including accepted zero-duration sleep."""
    with transaction.atomic():
        previous = associated_session(actor)
        if previous and previous.outcome != lifecycle.OUTCOME_CONFIRMED:
            session = lifecycle.resume_saved_session(previous.session_id, owner_id(actor), tick=int(tick_to))
        else:
            session = lifecycle.open_session_for(owner_id(actor))
        if session is None:
            session = lifecycle.open_session(owner_id(actor), tick=int(tick_to))
        old = association(actor)
        retained = old if old and old["session_id"] == session.session_id else {}
        actor.db.dream_surface = {
            "session_id": session.session_id,
            "sleep": {
                "tick_from": int(tick_from), "tick_to": int(tick_to),
                "requested_seconds": int(requested_seconds),
                "seconds": int(tick_to) - int(tick_from),
                "event_kinds": sorted({str(event.kind) for event in events}),
            },
            "scene": retained.get("scene", ""),
            "dialogue": retained.get("dialogue", ""),
            "direction": retained.get("direction", ""),
            "failure": False,
        }
        if retained:
            bump_revision_if_unchanged(actor, int(session.revision))
        log_info("dream_sleep_associated", context={
            "char": actor.pk, "session_id": session.session_id,
            "tick_from": int(tick_from), "tick_to": int(tick_to),
            "requested_seconds": int(requested_seconds),
            "completed": int(session.completed_exchanges),
        })
    return dream_state(actor)


def store_direction(actor, message):
    value = association(actor)
    value["direction"] = message
    value["failure"] = False
    actor.db.dream_surface = value


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
    value["failure"] = False
    actor.db.dream_surface = value


def store_failure(actor):
    value = association(actor)
    value["failure"] = True
    actor.db.dream_surface = value


def dream_state(actor):
    """Server-authored actions, count, track, prose and committed sleep identity."""
    value = association(actor)
    if value is None:
        return None
    session = associated_session(actor)
    view = lifecycle.progress(session)
    opened = session.state == lifecycle.STATE_OPEN
    ending = render_ending(view.completed) if not opened else None
    draft = get_draft(session.draft_id, owner_id(actor)) if session.draft_id else None
    confirmed = bool(draft and draft_is_confirmed(draft))
    draft_direction = draft.direction if draft else None
    threads = []
    if opened:
        for thread in StoryThread.objects.exclude(state__in=TERMINAL_THREAD_STATES).order_by("-pk").iterator():
            if thread_accessible(thread, owner_id(actor)):
                threads.append(thread.thread_id)
                if len(threads) == 32:
                    break
    displayed_direction = (draft_direction or {}).get("summary", value.get("direction", ""))
    return {
        "session_id": session.session_id, "revision": int(session.revision),
        "completed": view.completed, "remaining": view.remaining,
        "can_input": view.free_text_allowed and not bool(session.pending_submission_id),
        "can_confirm": opened, "can_draft": opened, "can_awaken": True,
        "pending": bool(session.pending_submission_id), "open": opened,
        "confirmed": confirmed, "failure": bool(value.get("failure")),
        "thread_choices": threads,
        "draft_preferences": {key: item for key, item in (draft_direction or {}).items()
                              if key != "summary"} if draft_direction else None,
        "opening": OPENING, "scene": value.get("scene", ""),
        "dialogue": value.get("dialogue", ""),
        "direction_parts": [displayed_direction[offset:offset + 2000]
                            for offset in range(0, len(displayed_direction), 2000)],
        "track": asdict(track_state(view.completed)), "sleep": dict(value["sleep"]),
        "ending": (f"{ending.phase}，餘韻漸漸平息，純白的夢境淡去，你醒了。" if ending and ending.climax_reached else "純白的夢境漸漸淡去，你醒了。") if ending else "",
        "ending_phase": ending.phase if ending else "",
    }
