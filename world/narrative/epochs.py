"""Explicit pair epochs, exact historical frames, and validated compaction."""

import hashlib
import json
from uuid import uuid4

from django.db import transaction
from evennia.objects.models import ObjectDB
from twisted.internet import defer

from world.ai.guardrail import GuardrailHooks, guarded_call
from world.ai.errors import LLMTransportError
from world.ai.profiles import get_profile
from world.narrative.context import (
    assemble_narrative_context, build_budget_profile, build_request_descriptor,
    estimate_tokens, persist_context_snapshot,
)
from world.narrative.models import DialogueEpoch, DialogueFrame, DialogueTurn
from world.observability import log_info
from world.prompts import render_prompt

SUMMARY_SOFT_TARGET = 400
SUMMARY_HARD_LIMIT = 800
SUMMARY_PROFILE_LIMITS = {
    "npc_dialogue": {"soft_target": SUMMARY_SOFT_TARGET, "hard_limit": SUMMARY_HARD_LIMIT},
    "dialogue_summary": {"soft_target": SUMMARY_SOFT_TARGET, "hard_limit": SUMMARY_HARD_LIMIT},
}
SUMMARY_SCHEMA = {"type": "object", "required": ["summary"], "additionalProperties": False,
                  "properties": {"summary": {"type": "string", "minLength": 1}}}


def _fallback():
    return None


_SUMMARY_HOOKS = GuardrailHooks("dialogue_summary", _fallback, {})


class _BoundedSummaryInvocation:
    """Check every rendered attempt before delegating to the existing transport."""

    def __init__(self, client, max_input):
        self.client = client
        self.max_input = max_input

    def get_response(self, descriptor):
        total = sum(estimate_tokens(message["content"]) for message in descriptor.messages)
        if total > self.max_input:
            return defer.fail(LLMTransportError("malformed", "Summary retry exceeds captured input budget."))
        return self.client.get_response(descriptor)


def current_epoch(npc, player):
    return DialogueEpoch.objects.filter(npc_id=str(npc.pk), player_id=str(player.pk)).order_by("-sequence").first()


def _lock(npc):
    # The durable NPC row serializes the initial boundary as well as successors.
    ObjectDB.objects.select_for_update().get(pk=npc.pk)


def _create(npc, player, version, reason, *, summary="", source_refs=(), snapshot_id=""):
    previous = current_epoch(npc, player)
    last = DialogueTurn.objects.filter(npc_id=str(npc.pk), player_id=str(player.pk)).order_by("-id").first()
    epoch = DialogueEpoch.objects.create(
        npc_id=str(npc.pk), player_id=str(player.pk),
        sequence=previous.sequence + 1 if previous else 1, version=version, reason=reason,
        start_turn_id=max((ref["turn_id"] for ref in source_refs if "turn_id" in ref), default=0) if summary else (last.pk if last and previous else 0), summary=summary,
        generation_id=uuid4().hex, source_refs=list(source_refs), snapshot_id=snapshot_id,
    )
    log_info("narrative_dialogue_epoch_started", context={
        "npc": npc.pk, "char": player.pk, "epoch": epoch.pk,
        "sequence": epoch.sequence, "reason": reason, "sources_count": len(source_refs),
    })
    return epoch


def ensure_epoch(npc, player, version):
    with transaction.atomic():
        _lock(npc)
        epoch = current_epoch(npc, player)
        if epoch is None or epoch.version != version:
            epoch = _create(npc, player, version, "initial" if epoch is None else "version_changed")
        return epoch


def start_epoch(npc, player, *, version=None):
    """Explicit natural boundary; independent of current-target sessions."""
    with transaction.atomic():
        _lock(npc)
        previous = current_epoch(npc, player)
        return _create(npc, player, version or (previous.version if previous else ""), "natural_boundary")


def append_frame(epoch, identity, content, tick, sources):
    frame, created = DialogueFrame.objects.get_or_create(
        epoch=epoch, identity=identity,
        defaults={"content": content, "tick": tick, "sources": sources},
    )
    if frame.content != content:
        raise ValueError("Frame identity belongs to different captured state.")
    if created:
        log_info("narrative_dialogue_frame_captured", context={
            "epoch": epoch.pk, "frame": frame.pk, "tick": tick,
            "sources_count": len(sources), "tokens": estimate_tokens(content),
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        })
    return frame


def epoch_frames(epoch, limit=12):
    return list(reversed(list(DialogueFrame.objects.filter(epoch=epoch).order_by("-id")[:limit])))


@defer.inlineCallbacks
def compact_epoch(npc, player, client):
    """Derive bounded retrieval text from preserved originals, never frame secrets."""
    epoch = current_epoch(npc, player)
    if epoch is None:
        return None
    turns = list(DialogueTurn.objects.filter(
        npc_id=str(npc.pk), player_id=str(player.pk), id__gt=epoch.start_turn_id,
    ).order_by("id")[:12])
    if not turns:
        return None
    refs = [{"turn_id": turn.pk, "submission_id": turn.submission_id, "kind": turn.kind,
             "tick": turn.tick, "revision": 1,
             "sha256": hashlib.sha256(turn.speech.encode()).hexdigest()} for turn in turns]
    profile = get_profile("dialogue_summary")
    limits = SUMMARY_PROFILE_LIMITS["dialogue_summary"]
    budget = build_budget_profile(
        profile, section_targets={"turn_frames": 2000, "epoch_summary": limits["soft_target"]},
        section_bounds={"epoch_summary": limits["hard_limit"]},
    )
    captured_personas = npc._persona_block(player)
    frames = [json.dumps({"source": ref, "speaker": turn.speaker, "speech": turn.speech},
                         ensure_ascii=False, sort_keys=True) for ref, turn in zip(refs, turns)]
    bounded = []
    for frame in frames:
        if estimate_tokens("\n\n".join(bounded + [frame])) > 1800:
            break
        bounded.append(frame)
    context = assemble_narrative_context(
        capability="dialogue_summary", prompt_version="dialogue_summary_v1",
        schema_version="dialogue_summary_v1", owner_id=str(npc.pk), requester_id=str(npc.pk),
        budget_profile=budget, global_rules=render_prompt("npc_dialogue.global_rules"),
        capability_contract=render_prompt("npc_dialogue.summary"), character_anchor="Dialogue attribution only.",
        turn_frames=bounded,
        epoch_summary=epoch.summary,
    )
    # Only the exact rendered source subset is claimed by the generation.
    included = [ref for ref, frame in zip(refs, frames) if frame in context.user_prompt]
    if not included:
        return None
    if epoch.summary and epoch.summary in context.user_prompt:
        included.append({"epoch_id": epoch.pk, "generation_id": epoch.generation_id})
    snapshot = persist_context_snapshot(context)
    def validate(parsed):
        summary = parsed.get("summary", "") if isinstance(parsed, dict) else ""
        if not isinstance(summary, str):
            return ["Summary must be text."]
        rendered = "### 紀元摘要\n" + summary
        output = json.dumps({"summary": summary}, ensure_ascii=False, sort_keys=True)
        return [] if summary.strip() and estimate_tokens(rendered) <= SUMMARY_HARD_LIMIT and estimate_tokens(output) <= budget.completion_reservation else ["Summary exceeds rendered bound or is empty."]
    descriptor = build_request_descriptor(context, snapshot, output_schema=SUMMARY_SCHEMA,
                                          semantic_validators={"summary_bound": validate})
    _SUMMARY_HOOKS.install()
    text = yield guarded_call(
        "dialogue_summary", _BoundedSummaryInvocation(client, budget.max_input_budget),
        descriptor.chat_descriptor,
    )
    if text is None:
        log_info("narrative_dialogue_compaction_deferred", context={"epoch": epoch.pk, "snapshot_id": snapshot.snapshot_id})
        return None
    with transaction.atomic():
        _lock(npc)
        if current_epoch(npc, player).pk != epoch.pk or npc._persona_block(player) != captured_personas:
            log_info("narrative_dialogue_compaction_stale", context={"epoch": epoch.pk, "snapshot_id": snapshot.snapshot_id})
            return None
        successor = _create(npc, player, epoch.version, "compaction",
                            summary=json.loads(text)["summary"], source_refs=included,
                            snapshot_id=snapshot.snapshot_id)
    return successor
