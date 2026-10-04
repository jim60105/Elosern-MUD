"""Value preparation and deterministic publication of narrative quest seeds."""

import json
from dataclasses import dataclass

from world.lore.guild import GUILD_RANK_REGISTRY
from world.observability import log_info, log_warn
from world.quests.compile import compile_quest_blueprint, register_generated_quest
from world.quests.compile.contracts import QuestCompileError
from world.rules.guild import GuildDataError, parse_guild_registration
from world.rules.quest_issuance import IssuerKeyError, resolve_issuer_key


@dataclass(frozen=True)
class PreparedQuestBeat:
    context_json: str
    blueprint_json: str
    issuer_id: str


def quest_context(invocation, proposal):
    """Pin issuance to an actual participant or the owner's registered branch."""
    from world.narrative.director import _resolve_character
    from world.narrative.models import StoryThread

    owner = _resolve_character(invocation.owner_id)
    if owner is None:
        return None
    rank = owner.guild_rank
    if rank is None:
        rank = min(GUILD_RANK_REGISTRY, key=lambda key: GUILD_RANK_REGISTRY[key].order)
    issuer_id = ""
    try:
        if proposal.recipient:
            thread = StoryThread.objects.filter(thread_id=invocation.source.thread_id).first()
            participants = {str(item) for item in (thread.participants or [])} if thread else set()
            if str(proposal.recipient) not in participants:
                return None
            issuer = _resolve_character(proposal.recipient)
            issuer_key = resolve_issuer_key(issuer) if issuer is not None else None
            if not issuer_key:
                return None
            issuer_id = str(issuer.pk)
        else:
            registration = parse_guild_registration(owner)
            if registration is None or owner.guild_rank is None:
                return None
            issuer_key = registration["branch_key"]
    except (GuildDataError, IssuerKeyError):
        # observability: ignore R2: corrupt authority is an unavailable target
        return None
    location = owner.location
    context = {
        "allowed_rank": rank,
        "issuer_branch": issuer_key,
        "anchor": getattr(location, "anchor_key", None),
        "note": json.dumps({
            "quest_seed": proposal.summary,
            "snapshot_id": invocation.snapshot_id,
            "source": invocation.context_frame,
            "instruction": "Propose future objectives only; never assert acceptance or completion.",
        }, ensure_ascii=False),
    }
    return context, issuer_id


def publish_quest_beat(prepared, invocation, proposal, beat, thread, now_tick):
    """Revalidate a captured proposal and publish only through the quest owner."""
    from world.narrative.director import _EffectRejected, OUTCOME_STALE, OUTCOME_NO_CONTENT
    from world.narrative.threads import record_thread_development

    if prepared is None:
        raise _EffectRejected(OUTCOME_NO_CONTENT)
    current = quest_context(invocation, proposal)
    captured = json.loads(prepared.context_json)
    if current is None or current != (captured, prepared.issuer_id):
        raise _EffectRejected(OUTCOME_STALE)
    try:
        compiled = compile_quest_blueprint(json.loads(prepared.blueprint_json))
        rank = GUILD_RANK_REGISTRY.get(captured["allowed_rank"])
        quest_rank = GUILD_RANK_REGISTRY.get(compiled.definition.rank)
        expected_issuer = captured["issuer_branch"]
        if not expected_issuer.startswith(("npc:", "guild:")):
            expected_issuer = f"guild:{expected_issuer}"
        anchor = captured["anchor"]
        if (
            rank is None or quest_rank is None or quest_rank.order > rank.order
            or compiled.issuance.issuer_key != expected_issuer
            or (anchor is not None and not any(
                requirement.anchor_near == anchor
                or (requirement.location is not None and requirement.location.anchor_key == anchor)
                for requirement in compiled.stage_requirements
            ))
        ):
            raise QuestCompileError("quest blueprint does not fit captured authority")
        register_generated_quest(compiled)
    except (QuestCompileError, ValueError) as error:
        # Compiler diagnostics may quote proposal fields. Keep the operational
        # exception type, never its prose-bearing message or chained payload.
        safe_error = type(error)("quest proposal rejected")
        log_warn("quest_beat_publication_rejected", context={
            "beat_id": beat.beat_id, "snapshot_id": invocation.snapshot_id,
            "owner": invocation.owner_id,
        }, exc=safe_error)
        raise _EffectRejected(OUTCOME_NO_CONTENT) from error
    beat.payload = {**beat.payload, "quest": {
        "definition_key": compiled.definition.key,
        "issuer_key": compiled.issuance.issuer_key,
        "snapshot_id": invocation.snapshot_id,
        "blueprint": json.loads(prepared.blueprint_json),
    }}
    # The publication is an arrangement, not evidence of gameplay completion.
    record_thread_development(thread_id=thread.thread_id, tick=int(now_tick),
                              actor_id=invocation.owner_id)
    from django.db import transaction
    transaction.on_commit(lambda: log_info("quest_beat_published", context={
        "beat_id": beat.beat_id, "quest": compiled.definition.key,
        "snapshot_id": invocation.snapshot_id, "owner": invocation.owner_id,
    }))
