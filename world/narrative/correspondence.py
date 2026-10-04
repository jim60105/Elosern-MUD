"""Identity-addressed, generation-free fixed-hour correspondence settlement."""

from dataclasses import dataclass
from uuid import uuid4

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.narrative.models import LetterReplyWork, LetterSend, LetterState, NarrativeEvent, ProjectionProgress
from world.observability import log_info
from world.rules.clock import CLOCK_YAML, ScheduledEvent, get_world_clock, register_event_source


MAX_BODY_CHARACTERS = 8000
# The generic event-memory projector consumes version 1 at startup. This queue
# is reserved for the correspondence-owned projection consumer.
CORRESPONDENCE_PROJECTOR_VERSION = 2


@dataclass(frozen=True)
class LetterRecord:
    """Detached read value: never retained or mutated by settlement."""

    source_id: str
    sender_id: str
    recipient_id: str
    body: str
    sent_tick: int
    due_tick: int
    status: str
    transition_id: str


def _character(identity):
    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import NPC

    try:
        pk = int(identity)
    except (ValueError, TypeError) as error:
        raise ValueError("Recipient must have an established character identity.") from error
    obj = ObjectDB.objects.filter(pk=pk).first()
    if obj is None or not isinstance(obj, (PlayerCharacter, NPC)):
        raise ValueError("Recipient must have an established character identity.")
    return obj


def send_letter(*, sender_id, recipient_id, body, source_id=None, reply_to="", source_snapshot_id=""):
    """Validate before writes, then atomically fix immutable send and state."""
    from typeclasses.characters import PlayerCharacter

    sender = _character(sender_id)
    recipient = _character(recipient_id)
    if not isinstance(body, str) or not body.strip() or len(body) > MAX_BODY_CHARACTERS:
        raise ValueError("Letter body must contain 1..8000 characters.")
    identity = source_id if source_id is not None else uuid4().hex
    if not isinstance(identity, str) or not identity.strip() or len(identity) > 128:
        raise ValueError("Letter source identity must contain 1..128 characters.")
    if reply_to and not LetterSend.objects.filter(source_id=reply_to).exists():
        raise ValueError("Reply must reference an accepted letter.")
    with transaction.atomic():
        existing = LetterSend.objects.filter(source_id=identity).first()
        if existing is not None:
            if (existing.sender_id, existing.recipient_id, existing.body, existing.reply_to, existing.source_snapshot_id) != (
                str(sender.pk), str(recipient.pk), body, reply_to, source_snapshot_id
            ):
                raise ValueError("Send identity belongs to different correspondence.")
            return get_letter(identity)
        tick = get_world_clock().tick
        letter, created = LetterSend.objects.get_or_create(
            source_id=identity,
            defaults={
                "sender_id": str(sender.pk), "recipient_id": str(recipient.pk),
                "recipient_kind": "player" if isinstance(recipient, PlayerCharacter) else "npc",
                "body": body, "sent_tick": tick,
                "due_tick": tick + CLOCK_YAML["seconds_per_hour"], "reply_to": reply_to,
                "source_snapshot_id": source_snapshot_id,
            },
        )
        if not created:
            if (letter.sender_id, letter.recipient_id, letter.body, letter.reply_to, letter.source_snapshot_id) != (
                str(sender.pk), str(recipient.pk), body, reply_to, source_snapshot_id
            ):
                raise ValueError("Send identity belongs to different correspondence.")
            return get_letter(identity)
        LetterState.objects.create(
            letter=letter, recipient_id=letter.recipient_id, due_tick=letter.due_tick,
        )
        context = {"source_id": identity, "char": sender.pk, "recipient": recipient.pk,
                   "tick": tick, "due_tick": letter.due_tick}
        transaction.on_commit(lambda: log_info("correspondence_sent", context=context))
        return get_letter(identity)


def get_letter(source_id):
    """Read fresh rows, with no ORM/read-model cache crossing transactions."""
    state = LetterState.objects.select_related("letter").get(letter__source_id=source_id)
    letter = state.letter
    return LetterRecord(letter.source_id, letter.sender_id, letter.recipient_id,
                        letter.body, letter.sent_tick, letter.due_tick,
                        state.status, state.transition_id)


def due_letters(start_tick, end_tick):
    return LetterState.objects.filter(
        status="sent", due_tick__gt=start_tick, due_tick__lte=end_tick,
    ).select_related("letter").order_by("due_tick", "pk")


def snapshot_correspondence_surfaces(start_tick, end_tick):
    """Declare table-only writes; detached reads and fresh queries need no cache restore.

    Django's ordinary models have no Evennia idmapper cache. Settlement uses
    queryset updates, never mutates instances, and retains no row/read-model
    references. The enclosing clock transaction owns all table rollback.
    """
    return {}


def settle_correspondence_delivery(start_tick, end_tick):
    """Settle exact crossed deadlines without looking up any recipient handler."""
    events = []
    with transaction.atomic():
        for state in due_letters(start_tick, end_tick):
            letter = state.letter
            status = "delivered" if letter.recipient_kind == "npc" else "available"
            transition = f"correspondence:{letter.source_id}:{status}"
            changed = LetterState.objects.filter(pk=state.pk, status="sent").update(
                status=status, transition_id=transition,
            )
            if not changed:
                continue
            NarrativeEvent.objects.create(
                source_id=transition, event_type="correspondence_delivery",
                content={"letter_source_id": letter.source_id, "status": status},
                participants=[letter.sender_id, letter.recipient_id], tick=letter.due_tick,
                visibility="private",
            )
            # Later correspondence-memory projection owns consumption, not the
            # generic event projector's live-character workflow.
            ProjectionProgress.objects.create(
                source_id=transition, status="pending",
                projector_version=CORRESPONDENCE_PROJECTOR_VERSION,
            )
            if status == "delivered":
                LetterReplyWork.objects.get_or_create(letter=letter)
            context = {"source_id": letter.source_id, "recipient": letter.recipient_id,
                       "tick": letter.due_tick, "status": status}
            transaction.on_commit(
                lambda c=context: log_info("correspondence_settled", context=c)
            )
            events.append(ScheduledEvent("correspondence_delivery", letter.due_tick,
                                         {"source_id": letter.source_id, "status": status}))
    return events


def register_correspondence_delivery():
    """Idempotent deterministic startup registration."""
    register_event_source("correspondence_delivery", settle_correspondence_delivery,
                          snapshot_correspondence_surfaces)
