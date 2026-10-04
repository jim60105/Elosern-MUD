"""Durable pair submissions, delivered responses, and permissioned W1 prompt views."""

import json
from dataclasses import replace
from uuid import uuid4

from django.db import transaction

from world.narrative.context import (
    RenderedSection, assemble_narrative_context, build_budget_profile,
    estimate_tokens, persist_context_snapshot,
)
from world.narrative.models import DialogueTurn
from world.narrative.recall import fast_recall
from world.observability import log_info


def _tick():
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return clock.tick if clock is not None else 0


def submit_turn(npc, player, speech, *, submission_id=None):
    """Allocate identity once at ingress; retries carry the returned identity."""
    identity = submission_id or uuid4().hex
    turn, created = DialogueTurn.objects.get_or_create(
        submission_id=identity, kind="player",
        defaults={"npc_id": str(npc.pk), "player_id": str(player.pk),
                  "speaker": player.key, "speech": speech, "tick": _tick()},
    )
    if (turn.npc_id, turn.player_id, turn.speech) != (str(npc.pk), str(player.pk), speech):
        raise ValueError("Submission identity already belongs to different speech or pair.")
    if created:
        log_info("narrative_dialogue_submitted", context={
            "submission_id": identity, "npc": npc.pk, "char": player.pk, "tick": turn.tick,
        })
    return identity


def settle_response(npc, player, submission_id, speech, *, snapshot_id=""):
    """Record only a successfully presented response, once per ingress identity."""
    with transaction.atomic():
        submission = DialogueTurn.objects.get(
            submission_id=submission_id, kind="player", npc_id=str(npc.pk),
            player_id=str(player.pk),
        )
        turn, created = DialogueTurn.objects.get_or_create(
            submission_id=submission.submission_id, kind="npc",
            defaults={"npc_id": submission.npc_id, "player_id": submission.player_id,
                      "speaker": npc.key, "speech": speech, "tick": _tick(),
                      "provenance": {"snapshot_id": snapshot_id,
                                     "delivery_id": f"{submission_id}:npc"}},
        )
        if turn.speech != speech:
            raise ValueError("Delivery identity already belongs to different speech.")
        if created:
            log_info("narrative_dialogue_delivered", context={
                "submission_id": submission_id, "npc": npc.pk, "char": player.pk,
                "snapshot_id": snapshot_id, "tick": turn.tick,
            })
        return turn


def pair_view(npc, player, *, limit=None):
    """Query only the bounded tail; never delete or materialize the full archive."""
    window = max(1, min(int(limit or npc.max_chat_memory_size), 12))
    turns = DialogueTurn.objects.filter(npc_id=str(npc.pk), player_id=str(player.pk))
    count = turns.count()
    tail = list(turns.order_by("-id")[:window])
    lines = [f"{turn.speaker}: {turn.speech}" for turn in reversed(tail)]
    return lines, max(0, count - window)


def build_dialogue_context(npc, player, speech, *, identity_detail=False):
    """Use permitted recall and the context builder, retaining W1 prompt placement."""
    from world.ai.npc_dialogue import build_npc_dialogue_prompt
    from world.ai.profiles import get_profile

    owner = str(npc.pk)
    recall = fast_recall(owner_id=owner, requester_id=owner, query=speech)
    context = assemble_narrative_context(
        capability="npc_dialogue", prompt_version="npc_dialogue_w1",
        schema_version="npc_dialogue", owner_id=owner, requester_id=owner,
        budget_profile=build_budget_profile(get_profile("npc_dialogue")),
        global_rules="", capability_contract="", character_anchor="",
        recalled_memories=recall.all_selected,
    )
    # Recall is one optional rendered part: it survives whole or is omitted whole.
    cognition = context.user_prompt
    sources = context.sources if "【記憶回想】" in cognition else ()
    lines, omitted = pair_view(npc, player)
    npc_persona, player_persona = npc._persona_block(player)
    messages = build_npc_dialogue_prompt(
        npc._npc_context(), npc._player_context(player, identity_detail=identity_detail),
        lines, affinity_context=npc._affinity_context(player),
        npc_persona=npc_persona, player_persona=player_persona, cognition=cognition,
        omitted_memory_lines=omitted,
        cognition_sources=tuple({
            "source_id": source.source_id, "record_id": source.record_id,
            "revision_number": source.revision_number,
            "knowledge_scope": source.knowledge_scope,
        } for source in sources),
    )
    if json.loads(messages[1]["content"]).get("cognition") != cognition:
        sources = ()
    total = sum(estimate_tokens(message["content"]) for message in messages)
    if total > context.budget_accounting["max_input_budget"]:
        from world.narrative.context import ContextBudgetExceededError

        raise ContextBudgetExceededError("Final dialogue prompt exceeds profile input budget.")
    sections = tuple(RenderedSection(
        name=message["role"], heading="", content=message["content"],
        rendered_text=message["content"], mandatory=True,
    ) for message in messages)
    accounting = dict(context.budget_accounting)
    accounting.update(total_rendered_tokens=total, pair_turns_omitted=omitted)
    captured = replace(
        context, sources=sources, sections=sections, system_prompt=messages[0]["content"],
        user_prompt=messages[1]["content"], budget_accounting=accounting,
    )
    snapshot = persist_context_snapshot(captured)
    return messages, snapshot.snapshot_id
