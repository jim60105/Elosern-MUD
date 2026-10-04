"""Durable pair submissions, delivered responses, and permissioned W1 prompt views."""

import json
import hashlib
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
    """Capture permitted current state and replay exact, versioned epoch frames."""
    from world.ai.npc_dialogue import build_npc_dialogue_prompt
    from world.ai.profiles import get_profile
    from world.narrative.epochs import ensure_epoch, epoch_frames, append_frame, SUMMARY_PROFILE_LIMITS
    from world.rules.npc_persona import current_persona_version

    owner = str(npc.pk)
    recall = fast_recall(owner_id=owner, requester_id=owner, query=speech)
    budget = build_budget_profile(
        get_profile("npc_dialogue"),
        section_targets={"epoch_summary": SUMMARY_PROFILE_LIMITS["npc_dialogue"]["soft_target"],
                         "character_anchor": 900},
        section_bounds={"epoch_summary": SUMMARY_PROFILE_LIMITS["npc_dialogue"]["hard_limit"],
                        "character_anchor": 1800},
    )
    context = assemble_narrative_context(
        capability="npc_dialogue", prompt_version="npc_dialogue_epochs_v1",
        schema_version="npc_dialogue", owner_id=owner, requester_id=owner,
        budget_profile=budget,
        global_rules="", capability_contract="", character_anchor="",
        recalled_memories=recall.all_selected,
        rendering_version="dialogue_epochs_v1",
    )
    # Recall is one optional rendered part: it survives whole or is omitted whole.
    cognition = context.user_prompt
    sources = context.sources if "【記憶回想】" in cognition else ()
    lines, omitted = pair_view(npc, player)
    npc_persona, player_persona = npc._persona_block(player)
    version = hashlib.sha256(json.dumps({
        "system": build_npc_dialogue_prompt(
            npc._npc_context(), npc._player_context(player), [],
            npc_persona=npc_persona, player_persona=player_persona,
        )[0]["content"],
        "player_persona": player_persona, "rendering": "dialogue_epochs_v1",
        "persona_version": current_persona_version(npc),
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    epoch = ensure_epoch(npc, player, version)
    submission = DialogueTurn.objects.filter(
        npc_id=str(npc.pk), player_id=str(player.pk), kind="player",
    ).order_by("-id").first()
    identity = submission.submission_id if submission and submission.speech == speech else ""
    historical = tuple(frame.content for frame in epoch_frames(epoch)
                       if frame.identity != identity)
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
        epoch_summary=epoch.summary if estimate_tokens(epoch.summary) <= budget.section_bounds["epoch_summary"] else "",
        historical_frames=historical,
        tick=_tick(),
    )
    payload = json.loads(messages[1]["content"])
    current = json.loads(payload["current"]) if "current" in payload else payload
    if current.get("cognition") != cognition:
        sources = ()
    total = sum(estimate_tokens(message["content"]) for message in messages)
    max_input = min(budget.max_input_budget,
                    estimate_tokens(messages[0]["content"]) + budget.section_bounds["turn_frames"])
    # A failed/offline compaction keeps the epoch usable via a deterministic tail.
    while total > max_input and payload.get("frames"):
        payload["frames"].pop(0)
        messages = (messages[0], {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)})
        total = sum(estimate_tokens(message["content"]) for message in messages)
    while total > max_input and current["memory"]:
        current["memory"].pop(0)
        if "current" in payload:
            payload["current"] = json.dumps(current, sort_keys=True, ensure_ascii=False)
        else:
            payload = current
        messages = (messages[0], {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)})
        total = sum(estimate_tokens(message["content"]) for message in messages)
    if total > max_input and current.get("cognition"):
        current.pop("cognition")
        current.pop("cognition_sources", None)
        sources = ()
        if "current" in payload:
            payload["current"] = json.dumps(current, sort_keys=True, ensure_ascii=False)
        else:
            payload = current
        messages = (messages[0], {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)})
        total = sum(estimate_tokens(message["content"]) for message in messages)
    if total > max_input and payload.get("epoch_summary"):
        payload["epoch_summary"] = ""
        messages = (messages[0], {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)})
        total = sum(estimate_tokens(message["content"]) for message in messages)
    if total > max_input:
        from world.narrative.context import ContextBudgetExceededError

        raise ContextBudgetExceededError("Final dialogue prompt exceeds profile input budget.")
    prefix_parts = messages[0]["content"].split("\n\n", 3)
    sections = tuple(RenderedSection(
        name=name, heading="", content=text, rendered_text=text, mandatory=True,
    ) for name, text in zip(
        ("global_rules", "world_digest", "capability_contract", "character_anchor"),
        prefix_parts,
    )) + (
        RenderedSection(name="epoch_summary", heading="", content=payload.get("epoch_summary", ""),
                        rendered_text=payload.get("epoch_summary", ""), mandatory=False),
        RenderedSection(name="turn_frames", heading="", content=messages[1]["content"],
                        rendered_text=messages[1]["content"], mandatory=True),
    )
    for section in sections:
        if section.token_count > budget.section_bounds[section.name]:
            from world.narrative.context import ContextBudgetExceededError

            raise ContextBudgetExceededError("Dialogue section exceeds rendered hard bound.")
    accounting = dict(context.budget_accounting)
    accounting.update(total_rendered_tokens=total, pair_turns_omitted=omitted)
    accounting.update(epoch_id=epoch.pk, prefix_sha256=version)
    captured = replace(
        context, sources=sources, sections=sections, system_prompt=messages[0]["content"],
        user_prompt=messages[1]["content"], budget_accounting=accounting,
    )
    snapshot = persist_context_snapshot(captured)
    if identity:
        append_frame(epoch, identity, json.dumps(current, sort_keys=True, ensure_ascii=False),
                     current["tick"], snapshot.sources)
    log_info("narrative_dialogue_prefix_rendered", context={
        "npc": npc.pk, "char": player.pk, "epoch": epoch.pk,
        "snapshot_id": snapshot.snapshot_id, "prefix_sha256": version,
        "tokens": total,
    })
    return messages, snapshot.snapshot_id
