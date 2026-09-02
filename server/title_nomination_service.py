"""Composition root scheduling AI epithet nominations (change G trigger service).

``schedule_epithet_nomination`` is the single production caller of
``world.ai.title_nomination.generate_epithet_candidates``. It mirrors the
``option_proposal_service`` discipline exactly: every ``world.ai`` import is
deferred into the call path so a cold import binds no guardrail logger, the
scheduling never blocks or raises into a rest-point hook, and an offline or
disabled ``title_nomination`` profile means the stage simply does not fire
(the deterministic game stays fully playable; fixed titles are unaffected).

The service writes no durable state itself. Ballot persistence is performed
solely by the rules-layer writer ``world.rules.titles.
persist_nomination_ballot`` — which re-checks single-ballot + cooldown
suppression after the proposal returns — and the panel push is the same
epoch-guarded ``publish_panel_update`` helper the options generation uses, so
a reconnect or puppet change between proposal and delivery silently drops a
stale push while the next full snapshot re-renders the truth.

Rest-point triggers (title-system D4 §7.1): logout and the resting day
boundary schedule directly; exam pass and quest-arc completion arrive through
observers registered on their owning subsystems (``register_nomination_triggers``,
called from ``at_server_start``), whose bodies defer to
``transaction.on_commit`` so a rolled-back settlement nominates nothing.
"""

from typing import Any

from twisted.internet import defer

from world.observability import log_warn


# The registered WebClient panel that renders the pending ballot.
BALLOT_PANEL = "title_ballot"


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------


def _build_nomination_client() -> Any:
    """Build the injected ``title_nomination`` client, or ``None`` when off.

    Unlike the options layer there is no ephemeral display state to keep warm
    while the profile is disabled: an offline nomination stage must not fire
    at all (the deterministic-offline invariant), so ``None`` means "no call".
    """
    from world.ai.client import OpenAICompatClient
    from world.ai.profiles import get_profile

    profile = get_profile("title_nomination")
    if profile.enabled:
        return OpenAICompatClient(profile)
    return None


# ---------------------------------------------------------------------------
# Context assembly (plain-data only; no entity leaves this module)
# ---------------------------------------------------------------------------


def _build_context(entity: Any, event_logs: Any) -> Any:
    """Freeze the nomination inputs from rules reads. Raises fail-closed on
    malformed title state (the caller swallows: no round, no state change)."""
    from world.ai.title_nomination import NominationContext
    from world.lore.titles import FIXED_TITLE_REGISTRY
    from world.rules import titles as title_rules

    return NominationContext(
        player_name=str(entity.key or ""),
        full_title=title_rules.safe_full_title(entity),
        declined=title_rules.declined_digest(entity),
        owned_epithet_displays=title_rules.owned_epithet_displays(entity),
        fixed_displays=frozenset(
            definition.display_name_zh
            for definition in FIXED_TITLE_REGISTRY.values()
        ),
        event_logs=tuple(event_logs or ()),
        removed=title_rules.removal_digest(entity),
    )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@defer.inlineCallbacks
def _generate(entity: Any, context: Any, watchers: tuple, client: Any):
    """One guarded proposal; persist through the rules writer; push panels."""
    from world.ai.title_nomination import generate_epithet_candidates
    from world.rules.titles import persist_nomination_ballot

    candidates = yield generate_epithet_candidates(context, client)
    if not candidates:
        # None: round void (transport/schema/degraded); (): every candidate
        # was filtered out. Both leave no ballot and start no cooldown.
        return False
    persisted = persist_nomination_ballot(
        entity,
        [{"display": c.display, "basis": c.basis} for c in candidates],
    )
    if persisted:
        _push_ballot_panel(entity, watchers)
    return persisted


def _push_ballot_panel(entity: Any, watchers: tuple) -> None:
    """Epoch-guarded push of the freshly persisted ballot to live watchers."""
    from web.webclient.presentation.coordinator import publish_panel_update
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.registry import build_production_registry

    for session, captured_epoch in watchers:
        try:
            context = build_presentation_context(session, entity)
            panels = {
                BALLOT_PANEL: build_production_registry().render(
                    BALLOT_PANEL, context
                )
            }
            publish_panel_update(
                session,
                entity,
                panels,
                context=context,
                expected_epoch=captured_epoch,
            )
        except Exception as error:  # noqa: BLE001 - guarded push, next sync wins
            log_warn(
                "title_nomination_panel_push_failed",
                exc=error,
                context={
                    "char": getattr(entity, "pk", 0) or 0,
                    "sessid": getattr(session, "sessid", 0) or 0,
                },
            )


def _log_generation_error(failure: Any) -> None:
    """Swallow a generation Deferred that still errbacks after routing."""
    log_warn(
        "title_nomination_generation_failed",
        exc=failure.value,
        context={"reason": failure.getErrorMessage()},
    )
    failure.trap(Exception)


# ---------------------------------------------------------------------------
# Public scheduling
# ---------------------------------------------------------------------------


def schedule_epithet_nomination(
    entity: Any,
    *,
    event_logs: Any = (),
    watchers: Any = (),
    client: Any = None,
) -> "defer.Deferred | None":
    """Fire one rest-point epithet nomination for ``entity`` (fire-and-forget).

    Returns the joinable generation Deferred when a round was scheduled, or
    ``None`` when suppressed, un-gated, offline, or synchronously broken.
    Never raises into the caller: any synchronous failure logs a bounded
    diagnostic and resolves to nothing.
    """
    try:
        from typeclasses.characters import PlayerCharacter

        if not isinstance(entity, PlayerCharacter):
            return None
        from world.rules.titles import nomination_suppressed

        if nomination_suppressed(entity):
            return None
        context = _build_context(entity, event_logs)
        resolved = client if client is not None else _build_nomination_client()
        if resolved is None:
            return None
        generation = _generate(entity, context, tuple(watchers), resolved)
        generation.addErrback(_log_generation_error)
        return generation
    except Exception as error:  # noqa: BLE001 - fire-and-forget contract
        log_warn(
            "title_nomination_scheduling_failed",
            exc=error,
            context={"char": getattr(entity, "pk", 0) or 0},
        )
        return None


def schedule_rest_boundary_nomination(entity: Any, events: Any) -> None:
    """Rest trigger: nominate when a SKIP advance crossed a day boundary.

    ``events`` is the list ``WorldClock.advance`` returned; a day crossing is
    marked by a ``daily_reset`` event. All failures are bounded and swallowed.
    """
    try:
        crossed = any(
            getattr(event, "kind", None) == "daily_reset" for event in events or ()
        )
        if not crossed:
            return
        from web.webclient.presentation.watchers import watchers_for

        schedule_epithet_nomination(entity, watchers=watchers_for(entity))
    except Exception as error:  # noqa: BLE001 - fire-and-forget contract
        log_warn(
            "title_nomination_rest_trigger_failed",
            exc=error,
            context={"char": getattr(entity, "pk", 0) or 0},
        )


# ---------------------------------------------------------------------------
# Settlement observers (exam pass / quest-arc completion)
# ---------------------------------------------------------------------------


def _watchers(entity: Any) -> tuple:
    from web.webclient.presentation.watchers import watchers_for

    try:
        return watchers_for(entity)
    except Exception:  # noqa: BLE001 - presentation-only input # observability: ignore R2: presentation-only fallback; an empty watcher tuple degrades the push only
        return ()


def _on_exam_pass(actor: Any, target_rank: str) -> None:
    """Exam-pass observer: schedule only after the settlement commits."""
    del target_rank
    _schedule_after_commit(actor)


def _on_quest_completion(entity: Any, record: Any, definition: Any) -> None:
    """Quest-completion observer: schedule only after the settlement commits."""
    del record, definition
    _schedule_after_commit(entity)


def _schedule_after_commit(entity: Any) -> None:
    from django.db import transaction

    transaction.on_commit(lambda: _schedule_committed(entity))


def _schedule_committed(entity: Any) -> None:
    try:
        schedule_epithet_nomination(entity, watchers=_watchers(entity))
    except Exception as error:  # noqa: BLE001 - fire-and-forget contract
        log_warn(
            "title_nomination_post_commit_failed",
            exc=error,
            context={"char": getattr(entity, "pk", 0) or 0},
        )


_TRIGGERS_REGISTERED = False


def register_nomination_triggers() -> None:
    """Install the exam-pass and quest-completion observers (idempotent).

    Called from ``at_server_start`` through a boot-tolerant wrapper. The
    logout and resting-boundary triggers call
    :func:`schedule_epithet_nomination` directly from their owning layers;
    this function wires only the two settlement-embedded rest points.
    """
    global _TRIGGERS_REGISTERED
    if _TRIGGERS_REGISTERED:
        return
    from world.quests.runtime import register_quest_completion_observer
    from world.rules.guild_exams import register_exam_pass_observer

    register_exam_pass_observer(_on_exam_pass)
    register_quest_completion_observer(_on_quest_completion)
    _TRIGGERS_REGISTERED = True


def reset_nomination_triggers_for_tests() -> None:
    """Undo the observer registration flag (test seam; does not mutate the
    owning subsystems' observer lists)."""
    global _TRIGGERS_REGISTERED
    _TRIGGERS_REGISTERED = False


__all__ = [
    "BALLOT_PANEL",
    "register_nomination_triggers",
    "reset_nomination_triggers_for_tests",
    "schedule_epithet_nomination",
    "schedule_rest_boundary_nomination",
]
