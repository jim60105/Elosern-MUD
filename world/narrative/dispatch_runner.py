"""Drive one claimed dream-dispatch work record through its stages.

The runner is the seam between the durable work record
(:mod:`world.narrative.dispatch`) and the existing director seams:

* the **story** stage prepares the immutable decision context and asks the
  StoryDirector for at most one beat proposal, then checkpoints the validated
  output;
* the **scene** stage rebuilds the captured context from that checkpoint, asks
  the beat-scoped ScenarioDirector for the extended blueprint and checkpoints it;
* the **publish** stage settles the accepted decision through the deterministic
  owner boundaries -- including the scene package publication -- and marks the
  work ``arranged`` inside that same transaction.

Rules this module keeps:

* a model call never runs inside a database transaction: each stage awaits
  outside every transaction and then persists its output in a short one;
* every write is fenced by the claim's execution token, so a superseded or
  post-shutdown callback mutates nothing and reports ``deferred``;
* a saved checkpoint is reused when it still validates, so a restart never
  replays a completed stage and never regenerates a committed publication;
* a confirmed direction whose frozen requirements demand an executable
  arrangement cannot be satisfied by prose: the story stage refuses it with the
  bounded ``insufficient_arrangement`` reason instead of publishing a statement;
* clients are always injected; this module constructs no transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction
from twisted.internet import defer

from world.ai.story_director import BEAT_KIND_QUEST_SEED, BeatProposal
from world.narrative import dispatch
from world.narrative.director import (
    DirectorError,
    DirectorInvocation,
    DirectorSource,
    generate_beat_proposal,
    prepare_decision,
    resolve_source,
    settle_decision,
)
from world.narrative.models import CreativeRequest
from world.narrative.quest_beats import (
    PreparedQuestBeat,
    confirmed_requirements,
    quest_context,
)
from world.observability import log_warn

__all__ = ["RunResult", "StageClients", "run_next"]


@dataclass(frozen=True)
class StageClients:
    """The injected clients for the two generative stages."""

    story: Any
    scenario: Any


@dataclass(frozen=True)
class RunResult:
    """The outcome of one pump pass over the queue."""

    dispatch_id: str
    outcome: str
    stage: str
    reason: str
    package_id: str = ""


_NO_WORK = RunResult("", "no_work", "", "")


def proposal_payload(proposal: BeatProposal) -> dict[str, Any]:
    """The durable, non-prose-bearing checkpoint form of one beat proposal."""
    return {
        "kind": str(proposal.kind),
        "summary": str(proposal.summary),
        "recipient": str(proposal.recipient or ""),
        "relation_delta": int(proposal.relation_delta),
        "writes": list(proposal.writes),
    }


def _request_for(work: Any) -> Optional[CreativeRequest]:
    request = CreativeRequest.objects.filter(
        submission_key=work.submission_key
    ).first()
    if request is None or int(request.version) != int(work.request_version):
        return None
    return request


def _rebuild(work: Any) -> tuple[Optional[DirectorInvocation], Optional[BeatProposal]]:
    """Rebuild the captured decision from one work record's story checkpoint.

    Returns ``(None, None)`` when the checkpoint cannot be read, which the caller
    reports as a stale source rather than regenerating blindly.
    """
    checkpoint = work.story_checkpoint or None
    if not checkpoint:
        return None, None
    try:
        source = DirectorSource(**checkpoint["source"])
        invocation = DirectorInvocation(
            owner_id=str(checkpoint["owner"]),
            source=source,
            thread_revision=int(checkpoint.get("thread_revision") or 0),
            snapshot_id=str(checkpoint["snapshot_id"]),
            context_frame=str(checkpoint["context_frame"]),
            # Messages are only needed to *generate*; a resumed stage never
            # regenerates, so the captured frame alone is authoritative here.
            messages=(),
        )
        proposal = BeatProposal.from_payload(checkpoint["proposal"])
    except (KeyError, TypeError, ValueError):
        # observability: ignore R2: an unreadable checkpoint is reported as a stale source below
        return None, None
    return invocation, proposal


def _failed(work: Any, token: str, reason: str, tick: int) -> RunResult:
    dispatch.mark_failed(work, token, reason, tick=tick)
    return RunResult(work.dispatch_id, "failed", work.stage, reason)


@defer.inlineCallbacks
def run_next(
    *,
    clients: StageClients,
    capability_enabled: Any,
    process: Optional[str] = None,
    tick: int = 0,
):
    """Process the next eligible work record, in stable confirmation order.

    A work record whose next stage needs a capability that is absent or disabled
    becomes ``waiting_service`` without a model call and without blocking any
    later eligible record: this pass simply moves on to the next one. The pass
    claims at most one record, so the pump never runs two generations.
    """
    for work in dispatch.next_considered(process):
        stage = dispatch.pending_stage(work)
        if stage is None:
            continue
        capability = dispatch.CAPABILITY_BY_STAGE.get(stage)
        if capability and not capability_enabled(capability):
            dispatch.mark_waiting(work, tick=tick)
            continue
        claimed = dispatch.claim(work, process=process, tick=tick)
        if claimed is None:
            continue
        row, token = claimed
        result = yield _advance(
            row.dispatch_id,
            token,
            clients=clients,
            capability_enabled=capability_enabled,
            tick=tick,
        )
        defer.returnValue(result)
    defer.returnValue(_NO_WORK)


@defer.inlineCallbacks
def _advance(
    work_id: str,
    token: str,
    *,
    clients: StageClients,
    capability_enabled: Any,
    tick: int,
):
    """Run the work's pending stages until it is terminal, waiting or deferred."""
    while True:
        work = dispatch.find_work(work_id)
        if work is None:
            defer.returnValue(
                RunResult(work_id, "failed", "", dispatch.REASON_EXECUTION_FAILED)
            )
        stage = dispatch.pending_stage(work)
        if stage is None:
            outcome = (
                "arranged"
                if work.state == dispatch.STATE_ARRANGED
                else "failed"
            )
            defer.returnValue(
                RunResult(work_id, outcome, "", work.reason_code, work.package_id)
            )
        # Each stage is checked against its own configured capability before it
        # runs, so a stage that becomes unavailable mid-chain parks the work at
        # that stage with every earlier checkpoint intact, instead of failing it
        # or running the stage anyway.
        capability = dispatch.CAPABILITY_BY_STAGE.get(stage)
        if capability and not capability_enabled(capability):
            dispatch.mark_waiting(work, tick=tick)
            defer.returnValue(
                RunResult(
                    work.dispatch_id,
                    "waiting",
                    stage,
                    dispatch.REASON_NO_CAPABILITY,
                )
            )
        request = _request_for(work)
        if request is None:
            defer.returnValue(
                _failed(work, token, dispatch.REASON_STALE_SOURCE, tick)
            )
        try:
            source = resolve_source(work.owner_id, request=request)
        except DirectorError as error:
            log_warn(
                "dream_dispatch_source_refused",
                context={
                    "dispatch": work.dispatch_id,
                    "owner": work.owner_id,
                    "stage": stage,
                },
                exc=error,
            )
            defer.returnValue(
                _failed(work, token, dispatch.REASON_STALE_SOURCE, tick)
            )

        if stage == dispatch.STAGE_STORY:
            invocation = prepare_decision(work.owner_id, source=source, now_tick=tick)
            try:
                proposal = yield generate_beat_proposal(
                    clients.story, invocation.messages
                )
            except Exception as error:
                # A stage failure that escaped the guardrail is a bounded
                # terminal reason, never an unhandled callback that would leave
                # the work claimed forever.
                log_warn(
                    "dream_dispatch_stage_failed",
                    context={
                        "dispatch": work.dispatch_id,
                        "owner": work.owner_id,
                        "stage": stage,
                    },
                    exc=error,
                )
                defer.returnValue(
                    _failed(work, token, dispatch.REASON_EXECUTION_FAILED, tick)
                )
            if proposal is None:
                defer.returnValue(
                    _failed(work, token, dispatch.REASON_MODEL_UNAVAILABLE, tick)
                )
            scene_required = (
                proposal.kind == BEAT_KIND_QUEST_SEED and not proposal.writes
            )
            if confirmed_requirements(invocation) and not scene_required:
                # The confirmed direction demands a real executable arrangement;
                # a statement, letter or clue is not a substitute (design §5).
                defer.returnValue(
                    _failed(
                        work, token, dispatch.REASON_INSUFFICIENT_ARRANGEMENT, tick
                    )
                )
            checkpoint = {
                "owner": work.owner_id,
                "source": {
                    "kind": source.kind,
                    "ref": source.ref,
                    "revision": int(source.revision),
                    "thread_id": source.thread_id,
                },
                "thread_revision": int(invocation.thread_revision),
                "snapshot_id": invocation.snapshot_id,
                "context_frame": invocation.context_frame,
                "proposal": proposal_payload(proposal),
                "scene_required": bool(scene_required),
            }
            if not dispatch.checkpoint_story(
                work, token, checkpoint=checkpoint, tick=tick
            ):
                defer.returnValue(
                    RunResult(work.dispatch_id, "deferred", stage, "")
                )
            continue

        invocation, proposal = _rebuild(work)
        if invocation is None or proposal is None:
            defer.returnValue(
                _failed(work, token, dispatch.REASON_STALE_SOURCE, tick)
            )

        if stage == dispatch.STAGE_SCENE:
            captured = quest_context(invocation, proposal)
            if captured is None:
                defer.returnValue(
                    _failed(
                        work, token, dispatch.REASON_INSUFFICIENT_ARRANGEMENT, tick
                    )
                )
            context, issuer_id = captured
            from world.ai.scenario_director import generate_beat_scene_blueprint

            try:
                blueprint = yield generate_beat_scene_blueprint(
                    clients.scenario, context=context
                )
            except Exception as error:
                log_warn(
                    "dream_dispatch_stage_failed",
                    context={
                        "dispatch": work.dispatch_id,
                        "owner": work.owner_id,
                        "stage": stage,
                    },
                    exc=error,
                )
                defer.returnValue(
                    _failed(work, token, dispatch.REASON_EXECUTION_FAILED, tick)
                )
            if blueprint is None:
                defer.returnValue(
                    _failed(work, token, dispatch.REASON_MODEL_UNAVAILABLE, tick)
                )
            if not dispatch.checkpoint_scene(
                work,
                token,
                checkpoint={
                    "context": context,
                    "issuer_id": issuer_id,
                    "blueprint": blueprint,
                },
                tick=tick,
            ):
                defer.returnValue(
                    RunResult(work.dispatch_id, "deferred", stage, "")
                )
            continue

        result = _publish(work, token, invocation=invocation, proposal=proposal, tick=tick)
        defer.returnValue(result)


def _publish(
    work: Any,
    token: str,
    *,
    invocation: DirectorInvocation,
    proposal: BeatProposal,
    tick: int,
) -> RunResult:
    """Settle the accepted decision and mark the work arranged in one transaction."""
    prepared = None
    checkpoint = work.scene_checkpoint or None
    if checkpoint:
        prepared = PreparedQuestBeat(
            _json(checkpoint["context"]),
            _json(checkpoint["blueprint"]),
            str(checkpoint.get("issuer_id") or ""),
        )
    try:
        with transaction.atomic():
            outcome = settle_decision(
                invocation=invocation,
                proposals=(proposal,),
                now_tick=tick,
                prepared_quest=prepared,
            )
            if outcome.scheduled:
                beat = outcome.beat
                quest = (beat.payload or {}).get("quest") or {}
                dispatch.mark_arranged(
                    work,
                    token,
                    decision_id=outcome.decision.decision_id,
                    thread_id=beat.thread.thread_id,
                    beat_id=beat.beat_id,
                    package_id=str(quest.get("package_id") or ""),
                    tick=tick,
                )
            else:
                dispatch.mark_failed(
                    work,
                    token,
                    dispatch.REASON_BY_OUTCOME.get(
                        outcome.outcome, dispatch.REASON_EXECUTION_FAILED
                    ),
                    tick=tick,
                )
    except Exception as error:
        # The publication transaction rolled back with no orphan scene, issuer or
        # accepted quest; the failure is recorded under the still-valid token.
        log_warn(
            "dream_dispatch_publication_failed",
            context={"dispatch": work.dispatch_id, "owner": work.owner_id},
            exc=error,
        )
        return _failed(work, token, dispatch.REASON_PUBLICATION_FAILED, tick)
    settled = dispatch.find_work(work.dispatch_id)
    outcome_name = "arranged" if (settled and settled.state == dispatch.STATE_ARRANGED) else "failed"
    return RunResult(
        work.dispatch_id,
        outcome_name,
        dispatch.STAGE_PUBLISH,
        "" if settled is None else settled.reason_code,
        "" if settled is None else settled.package_id,
    )


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
