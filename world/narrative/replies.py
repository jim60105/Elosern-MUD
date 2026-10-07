"""Explicit optional reply attempts and atomic, idempotent narrative settlement."""

import hashlib
import json

from django.db import transaction
from evennia.objects.models import ObjectDB
from twisted.internet import defer

from world.ai.correspondence import LetterReply, generate_letter_reply
from world.ai.profiles import get_profile
from world.narrative.context import (
    assemble_narrative_context, build_budget_profile, get_context_snapshot,
    persist_context_snapshot,
)
from world.narrative.correspondence import _character, get_letter, send_letter
from world.narrative.correspondence_memory import settle_delivery_cognition
from world.narrative.memory import get_owner_generation
from world.narrative.models import LetterReplyWork, LetterState
from world.narrative.recall import fast_recall
from world.observability import log_info
from world.prompts.loader import render_prompt
from world.rules.affinity import restore_relations_surfaces
from world.rules.correspondence import apply_letter_relationship


def _anchor(npc):
    """Only the recipient's own identity; never inspect a remote player's traits."""
    return json.dumps({"name": npc.key, "description": npc.db.desc or ""},
                      sort_keys=True, ensure_ascii=False)


def _pending(source_id):
    work = LetterReplyWork.objects.select_related("letter").get(letter__source_id=source_id)
    if not LetterState.objects.filter(letter=work.letter, status="delivered").exists():
        raise ValueError("Reply input must be a delivered incoming NPC letter.")
    return work


def prepare_reply(source_id):
    """Capture one intentional attempt, using owner-permitted W1 cognition."""
    with transaction.atomic():
        work = _pending(source_id)
        work = LetterReplyWork.objects.select_for_update().get(pk=work.pk)
        if work.status == "complete":
            return None
        letter = work.letter
        # Order invariant: after the completed-work early return and before the
        # recall/capture below, so a reply either sees the delivered letter's
        # settled cognition or waits instead of generating without it.
        if not settle_delivery_cognition(source_id):
            raise ValueError("Reply input has no settled delivery cognition.")
        npc = _character(letter.recipient_id)
        recall = fast_recall(owner_id=letter.recipient_id, requester_id=letter.recipient_id,
                             query=letter.body)
        budget = build_budget_profile(
            get_profile("correspondence"),
            context_window=32768,
            section_targets={"turn_frames": 22000},
            section_bounds={"turn_frames": 24000},
        )
        incoming_frame = json.dumps({
            "source_id": letter.source_id, "sender_id": letter.sender_id,
            "recipient_id": letter.recipient_id, "body": letter.body,
            "sent_tick": letter.sent_tick, "delivered_tick": letter.due_tick,
        }, sort_keys=True, ensure_ascii=False)
        context = assemble_narrative_context(
            capability="correspondence", prompt_version="correspondence_v1",
            schema_version="correspondence_v1", owner_id=letter.recipient_id,
            requester_id=letter.recipient_id, budget_profile=budget,
            global_rules=render_prompt("npc_dialogue.global_rules"),
            capability_contract=render_prompt("correspondence.system"),
            character_anchor=_anchor(npc), recalled_memories=recall.all_selected,
            turn_frames=[incoming_frame],
            affordances=("information_statement", "invitation_statement", "adjust_relation"),
        )
        # Required incoming text may not be truncated into a different input.
        if incoming_frame not in context.user_prompt:
            raise ValueError("Reply input exceeds the captured context budget.")
        snapshot = persist_context_snapshot(context)
        work.snapshot_id = snapshot.snapshot_id
        work.save(update_fields=["snapshot_id"])
        log_info("correspondence_reply_captured", context={
            "source_id": source_id, "recipient": letter.recipient_id,
            "snapshot_id": snapshot.snapshot_id, "body": letter.body,
        })
        return snapshot


def settle_reply(source_id, snapshot_id, proposal):
    """Commit relationship, reply-to/source snapshot and outgoing send exactly once."""
    if not isinstance(proposal, LetterReply):
        raise ValueError("Reply settlement requires a validated value proposal.")
    if not proposal.body.strip() or len(proposal.body) > 2000:
        raise ValueError("Reply body is outside the channel bound.")
    npc = None
    surfaces = {}
    try:
        with transaction.atomic():
            pending = _pending(source_id)
            work = LetterReplyWork.objects.select_for_update().select_related("letter").get(pk=pending.pk)
            if work.status == "complete":
                return get_letter(work.outgoing_source_id)
            letter = work.letter
            if work.snapshot_id != snapshot_id:
                return None
            snapshot = get_context_snapshot(snapshot_id)
            if snapshot.capability != "correspondence" or snapshot.owner_id != letter.recipient_id:
                raise ValueError("Reply snapshot belongs to a different owner or channel.")
            npc = _character(letter.recipient_id)
            # Advisory row lock; SQLite ignores FOR UPDATE, so replay safety
            # also rests on the single reactor and the deterministic outgoing
            # source_id's unique constraint.
            ObjectDB.objects.select_for_update().get(pk=npc.pk)
            sections = snapshot.rendered_payload["sections"]
            anchor = next(section["content"] for section in sections if section["name"] == "character_anchor")
            if snapshot.owner_generation != get_owner_generation(letter.recipient_id) or anchor != _anchor(npc):
                log_info("correspondence_reply_stale", context={
                    "source_id": source_id, "snapshot_id": snapshot_id, "recipient": npc.pk,
                })
                return None
            correspondent = _character(letter.sender_id)
            surfaces = {npc.pk: npc.db.relations_data}
            # A zero delta is no relationship change, as in the face-to-face
            # seam: never invoke the writer, whose lazy day-tick reset would
            # otherwise materialize an empty affinity record.
            if proposal.relation_delta:
                outcome = apply_letter_relationship(npc, correspondent, proposal.relation_delta)
                if outcome is None or outcome.source_rejected:
                    log_info("correspondence_reply_effect_rejected", context={
                        "source_id": source_id, "recipient": npc.pk, "snapshot_id": snapshot_id,
                    })
                    return None
            outgoing_id = "reply:" + hashlib.sha256(
                f"{source_id}:{letter.recipient_id}".encode()
            ).hexdigest()
            outgoing = send_letter(sender_id=npc.pk, recipient_id=correspondent.pk,
                                   body=proposal.body, source_id=outgoing_id, reply_to=source_id,
                                   source_snapshot_id=snapshot_id)
            work.status = "complete"
            work.outgoing_source_id = outgoing.source_id
            work.save(update_fields=["status", "outgoing_source_id"])
            context = {"source_id": source_id, "outgoing_source_id": outgoing.source_id,
                       "snapshot_id": snapshot_id, "recipient": npc.pk, "tick": outgoing.sent_tick}
            transaction.on_commit(lambda: log_info("correspondence_reply_committed", context=context))
            return outgoing
    except Exception:
        restore_relations_surfaces(surfaces)
        raise


@defer.inlineCallbacks
def attempt_reply(source_id, client):
    """One intentional attempt; delivery and startup never await model service."""
    snapshot = prepare_reply(source_id)
    if snapshot is None:
        return get_letter(_pending(source_id).outgoing_source_id)
    payload = snapshot.rendered_payload
    proposal = yield generate_letter_reply(client, (
        {"role": "system", "content": payload["system_prompt"]},
        {"role": "user", "content": payload["user_prompt"]},
    ))
    if proposal is None:
        log_info("correspondence_reply_pending", context={
            "source_id": source_id, "snapshot_id": snapshot.snapshot_id,
            "recipient": snapshot.owner_id,
        })
        return None
    return settle_reply(source_id, snapshot.snapshot_id, proposal)
