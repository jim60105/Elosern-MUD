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


# The frozen requirement kinds that demand an executable arrangement: a named
# place, a required new character or a requested private commission. A confirmed
# direction carrying any of them cannot be answered by prose alone.
SCENE_REQUIREMENT_KINDS = frozenset({"place", "new_character", "private_commission"})
#: Marks a planning context whose package declares its own symbolic role issuers.
SCENE_PACKAGE_MARKER = "scene_package"


def confirmed_requirements(invocation):
    """The confirmed direction's frozen executable requirements, in order."""
    from world.narrative.attention import SOURCE_REQUEST
    from world.narrative.models import CreativeRequest

    if invocation.source.kind != SOURCE_REQUEST:
        return ()
    request = CreativeRequest.objects.filter(
        submission_key=invocation.source.ref
    ).first()
    if request is None:
        return ()
    rows = (request.direction or {}).get("requirements") or []
    return tuple(
        dict(row)
        for row in rows
        if isinstance(row, dict) and row.get("kind") in SCENE_REQUIREMENT_KINDS
    )


def declares_executable_requirements(invocation) -> bool:
    """Whether the confirmed direction demands a real executable arrangement."""
    return bool(confirmed_requirements(invocation))


def is_scene_package(payload) -> bool:
    """Whether one prepared payload is a scene package rather than a bare quest.

    The scene route is identified by the package's own structural sections, so a
    quest-only blueprint keeps its existing compile path untouched.
    """
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("roles"), list)
        and isinstance(payload.get("encounters"), list)
    )


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
        elif declares_executable_requirements(invocation):
            # The confirmed direction demands a privately issued escort: the
            # package declares its own symbolic roles and role-issued
            # commissions, so the planning context names no guild branch and
            # requires no rank. Strict actual-entity checks belong to
            # materialization and registration, never to planning.
            issuer_key = ""
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
        "anchor": getattr(location, "anchor_key", None),
        "note": json.dumps({
            "quest_seed": proposal.summary,
            "snapshot_id": invocation.snapshot_id,
            "source": invocation.context_frame,
            "instruction": "Propose future objectives only; never assert acceptance or completion.",
        }, ensure_ascii=False),
    }
    if issuer_key:
        context["issuer_branch"] = issuer_key
    else:
        # A symbolic scene: the frozen requirements travel with the planning
        # context so the proposal can answer them, and the marker tells the
        # ScenarioDirector route that its own role declarations are the authority.
        context[SCENE_PACKAGE_MARKER] = True
        context["requirements"] = [
            dict(row) for row in confirmed_requirements(invocation)
        ]
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
    payload = json.loads(prepared.blueprint_json)
    if is_scene_package(payload):
        # A complete scene package: publication goes through the quest owner's
        # package boundary, not the quest-only compile path.
        _publish_scene_package(invocation, payload, beat, thread, now_tick)
        return
    try:
        compiled = compile_quest_blueprint(payload)
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


def _publish_scene_package(invocation, payload, beat, thread, now_tick):
    """Publish one validated scene package and link it to the settled beat.

    The publication joins the caller's transaction -- settlement wraps this call
    in its savepoint and its registration/cache scope -- so the accepted
    decision, the thread linkage, the scheduled beat, the published package and
    the work's publication references commit together or not at all. Nothing
    here activates a role, accepts a commission, advances a quest or rewards the
    player: publication is an arrangement, not evidence of gameplay completion.

    The symbolic commission stays a validated planning declaration until the
    role is materialized and provisioned at activation, so no runtime issuer key
    is invented here.
    """
    from django.db import transaction

    from world.narrative.director import OUTCOME_NO_CONTENT, _EffectRejected
    from world.narrative.threads import record_thread_development
    from world.quests.compile.contracts import QuestCompileError
    from world.quests.encounters import publish_scene_package
    from world.quests.scene_package import ScenePackageError

    try:
        published = publish_scene_package(
            payload,
            owner=str(invocation.owner_id),
            source_id=beat.execution_ref,
            tick=int(now_tick),
        )
    except (ScenePackageError, QuestCompileError, ValueError) as error:
        # Compiler diagnostics may quote proposal fields. Keep the operational
        # exception type, never its prose-bearing message or chained payload.
        safe_error = type(error)("scene package rejected")
        log_warn(
            "quest_beat_publication_rejected",
            context={
                "beat_id": beat.beat_id,
                "snapshot_id": invocation.snapshot_id,
                "owner": invocation.owner_id,
            },
            exc=safe_error,
        )
        raise _EffectRejected(OUTCOME_NO_CONTENT) from error
    beat.payload = {
        **beat.payload,
        "quest": {
            "package_id": published.package_id,
            "definition_key": published.definition_key,
            # A symbolic role-issued commission: the real issuer key appears only
            # when its role is materialized and provisioned at activation.
            "issuer_key": "",
            "symbolic": True,
            "snapshot_id": invocation.snapshot_id,
            "blueprint": payload,
        },
    }
    record_thread_development(
        thread_id=thread.thread_id, tick=int(now_tick), actor_id=invocation.owner_id
    )
    transaction.on_commit(
        lambda: log_info(
            "quest_beat_published",
            context={
                "beat_id": beat.beat_id,
                "package": published.package_id,
                "quest": published.definition_key,
                "snapshot_id": invocation.snapshot_id,
                "owner": invocation.owner_id,
            },
        )
    )
