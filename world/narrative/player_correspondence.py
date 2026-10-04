"""Authorized player correspondence; presentation reads never establish knowledge."""

from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object_by_tag

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.settlements.places import PLACE_REGISTRY
from world.narrative.correspondence import MAX_BODY_CHARACTERS, get_letter, send_letter
from world.narrative.models import LetterState, NarrativeEvent, ProjectionProgress
from world.narrative.correspondence import (
    CORRESPONDENCE_PROJECTOR_VERSION,
    correspondence_event_source_id,
)
from world.narrative.correspondence_memory import project_correspondence_event
from world.observability import log_info
from world.rules.clock import read_world_clock


class CorrespondenceError(ValueError):
    """A safe, player-facing correspondence refusal."""


def authorize_player(actor):
    """Only a persistent player identity owns this personal surface."""
    if not isinstance(actor, PlayerCharacter) or not actor.pk or actor.db.possessed_by:
        raise CorrespondenceError("目前無法使用個人信件。")
    return actor


def branch_available(actor):
    """Read the authored capability at its unique permanent interior anchor."""
    room = actor.location
    if not isinstance(room, Room):
        return False
    for place in PLACE_REGISTRY.values():
        if place.letter_service and room.tags.has(place.key):
            anchors = search_object_by_tag(place.key)
            if len(anchors) == 1 and anchors[0].pk == room.pk:
                return True
    return False


def _require_branch(actor):
    authorize_player(actor)
    if not branch_available(actor):
        raise CorrespondenceError("寄信與領信須在銀羽驛站分站辦理。")


def _tick():
    clock = read_world_clock()
    if clock is None:
        raise CorrespondenceError("信件服務目前無法使用。")
    return clock.tick


def resolve_recipient(value):
    """Resolve a unique established identity, never a fuzzy or first-match name."""
    if not isinstance(value, str) or not value.strip() or len(value) > 255:
        raise CorrespondenceError("請指定已建立的收件人姓名或角色編號。")
    value = value.strip()
    if value.startswith("#") and value[1:].isdigit():
        rows = ObjectDB.objects.filter(pk=int(value[1:]))
    else:
        rows = ObjectDB.objects.filter(db_key__iexact=value)
    matches = [obj for obj in rows if isinstance(obj, (PlayerCharacter, NPC))]
    if len(matches) != 1:
        raise CorrespondenceError("收件人不存在或姓名重複，請使用角色編號。")
    return str(matches[0].pk)


def send(actor, recipient, body, source_id=None):
    """Preflight and immutable send share one all-or-nothing transaction."""
    with transaction.atomic():
        _require_branch(actor)
        recipient_id = resolve_recipient(recipient)
        if not isinstance(body, str) or not body.strip() or len(body) > MAX_BODY_CHARACTERS:
            raise CorrespondenceError(f"信件內容須為 1 至 {MAX_BODY_CHARACTERS} 字。")
        try:
            return send_letter(sender_id=str(actor.pk), recipient_id=recipient_id,
                               body=body, source_id=source_id)
        except ValueError as error:
            raise CorrespondenceError("寄信資料不符合規範。") from error


def collect(actor):
    """Acquire every available letter, without creating a knowledge/read source."""
    with transaction.atomic():
        _require_branch(actor)
        tick = _tick()
        states = LetterState.objects.filter(recipient_id=str(actor.pk), status="available",
                                           due_tick__lte=tick).select_related("letter")
        acquired = []
        for state in states.order_by("due_tick", "pk"):
            changed = LetterState.objects.filter(pk=state.pk, status="available").update(
                status="collected", collection_tick=tick,
            )
            if changed:
                acquired.append(state.letter.source_id)
        ids = tuple(acquired)
        context = {"char": actor.pk, "room": actor.location.pk, "tick": tick, "count": len(ids)}
        transaction.on_commit(lambda: log_info("correspondence_collected", context=context))
        return ids


def list_letters(actor, after=0):
    """Bounded metadata page: no body and no writes, including no clock creation."""
    authorize_player(actor)
    if type(after) is not int or after < 0:
        raise CorrespondenceError("信件頁碼不符合規範。")
    states = LetterState.objects.filter(
        recipient_id=str(actor.pk), status__in=("collected", "read"), pk__gt=after,
    ).select_related("letter").order_by("pk")[:21]
    rows = list(states)
    return {"branch": branch_available(actor), "letters": [
        {"source_id": state.letter.source_id, "sender_id": state.letter.sender_id,
         "sent_tick": state.letter.sent_tick, "read_tick": state.read_tick}
        for state in rows[:20]
    ], "next": rows[19].pk if len(rows) > 20 else None}


def read(actor, source_id):
    """First opening atomically records one durable read; rereads write nothing."""
    authorize_player(actor)
    if not isinstance(source_id, str) or not source_id or len(source_id) > 128:
        raise CorrespondenceError("無法讀取這封信件。")
    with transaction.atomic():
        state = LetterState.objects.select_related("letter").filter(
            letter__source_id=source_id, recipient_id=str(actor.pk),
            status__in=("collected", "read"),
        ).first()
        if state is None:
            raise CorrespondenceError("無法讀取這封信件，請先在分站領取。")
        if state.read_tick is None:
            tick = _tick()
            changed = LetterState.objects.filter(pk=state.pk, read_tick__isnull=True,
                                                 status="collected").update(
                status="read", read_tick=tick,
            )
            if changed:
                source = correspondence_event_source_id(source_id, "read")
                event = NarrativeEvent.objects.create(
                    source_id=source, event_type="correspondence_read",
                    content={"letter_source_id": source_id},
                    participants=[str(actor.pk)], tick=tick, visibility="private",
                )
                ProjectionProgress.objects.create(source_id=source, status="pending",
                                                  projector_version=CORRESPONDENCE_PROJECTOR_VERSION)
                # First reading IS this owner's knowledge boundary, and rereads
                # skip this block, so the told memory commits with the read.
                project_correspondence_event(event)
                context = {"char": actor.pk, "source_id": source_id, "tick": tick}
                transaction.on_commit(lambda: log_info("correspondence_read", context=context))
        return get_letter(source_id)
