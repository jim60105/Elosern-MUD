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

Rest-point triggers (title-system D4 §7.1): player logout, committed voluntary/forced
awakening, and qualifying quest-arc completion after settlement commits.
Midnight alone and passed examinations do not trigger nomination.
"""

from typing import Any

from twisted.internet import defer

from world.observability import log_info, log_warn


# The registered WebClient panel that renders the pending ballot.
BALLOT_PANEL = "title_ballot"

# In-flight player nominations within this server process (keyed by durable player identity).
_IN_FLIGHT_PLAYERS: set[str] = set()

# Process-level set of committed wake/trigger occurrence identities already attempted or processed.
_PROCESSED_OCCURRENCES: set[str] = set()


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


def _build_context(entity: Any, *, frozen_tick: int | None = None) -> Any:
    """Freeze the nomination inputs from rules reads. Raises fail-closed on
    malformed title state (the caller swallows: no round, no state change)."""
    from world.ai.title_nomination import NominationContext
    from world.lore.titles import FIXED_TITLE_REGISTRY
    from world.narrative.recent_deeds import select_authorized_recent_deeds
    from world.rules import titles as title_rules

    deeds_result = select_authorized_recent_deeds(entity, frozen_tick=frozen_tick)
    return NominationContext(
        player_name=str(entity.key or ""),
        full_title=title_rules.safe_full_title(entity),
        declined=title_rules.declined_digest(entity),
        owned_epithet_displays=title_rules.owned_epithet_displays(entity),
        fixed_displays=frozenset(
            definition.display_name_zh
            for definition in FIXED_TITLE_REGISTRY.values()
        ),
        recent_deeds_json=deeds_result.rendered_json,
        supplied_source_ids=frozenset(deeds_result.source_ids),
        removed=title_rules.removal_digest(entity),
    )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@defer.inlineCallbacks
def _generate(
    entity: Any,
    context: Any,
    watchers: tuple,
    client: Any,
    player_id: str,
    *,
    trigger: str = "unknown",
    frozen_tick: int = 0,
    source_count: int = 0,
):
    """One guarded proposal; persist through the rules writer; push panels."""
    from world.ai.title_nomination import generate_epithet_candidates
    from world.rules.titles import persist_nomination_ballot

    try:
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
    except Exception as error:
        log_warn(
            "title_nomination_generation_failed",
            exc=error,
            context={
                "player": player_id,
                "trigger": trigger,
                "frozen_tick": frozen_tick,
                "source_count": source_count,
            },
        )
        return False
    finally:
        _IN_FLIGHT_PLAYERS.discard(player_id)


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


def _durable_player_id(entity: Any) -> str | None:
    pk = getattr(entity, "pk", None)
    if pk is not None:
        return str(pk)
    db_id = getattr(entity, "id", None)
    if db_id is not None:
        return str(db_id)
    return None


def _check_source_award_suppression(
    player_id: str,
    *,
    source_id: str | None = None,
    award_results: Any = None,
) -> bool:
    """Check if the source occurrence newly granted built-in titles to this player.

    Local occurrence suppression rule:
    Only awards whose recipient_id matches this player suppress immediate nomination.
    Awards to other participants and already-owned titles do not suppress.
    Original replayed award results remain authoritative.
    """
    awards = award_results
    if awards is None and source_id:
        from world.narrative.events import get_committed_award_results

        awards = get_committed_award_results(source_id)

    if not awards:
        return False

    for award in awards:
        recipient = getattr(award, "recipient_id", None)
        if recipient is None and isinstance(award, dict):
            recipient = str(award.get("recipient_id", ""))
        else:
            recipient = str(recipient or "")
        if recipient == player_id:
            return True
    return False


def schedule_epithet_nomination(
    entity: Any,
    *,
    frozen_tick: int | None = None,
    watchers: Any = (),
    client: Any = None,
    source_id: str | None = None,
    award_results: Any = None,
    occurrence_id: str | None = None,
    trigger: str = "unknown",
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

        player_id = _durable_player_id(entity)
        if not player_id:
            return None

        # Replay occurrence deduplication
        if occurrence_id:
            clean_occ = str(occurrence_id).strip()
            if clean_occ in _PROCESSED_OCCURRENCES:
                return None
            _PROCESSED_OCCURRENCES.add(clean_occ)

        # Live combat check: nomination SHALL NOT admit while player is in live combat
        from world.rules.combat_session import is_in_active_session

        if is_in_active_session(entity):
            return None

        # Generic immediate source award suppression check
        if _check_source_award_suppression(
            player_id, source_id=source_id, award_results=award_results
        ):
            return None

        from world.rules.titles import nomination_suppressed

        if nomination_suppressed(entity):
            return None

        # Identity-keyed in-flight admission check (at most one per player)
        if player_id in _IN_FLIGHT_PLAYERS:
            return None

        # Claim the in-flight slot
        _IN_FLIGHT_PLAYERS.add(player_id)

        try:
            context = _build_context(entity, frozen_tick=frozen_tick)
            if not context.supplied_source_ids:
                _IN_FLIGHT_PLAYERS.discard(player_id)
                return None
            resolved = client if client is not None else _build_nomination_client()
            if resolved is None:
                _IN_FLIGHT_PLAYERS.discard(player_id)
                return None
        except Exception:
            _IN_FLIGHT_PLAYERS.discard(player_id)
            raise

        actual_frozen_tick = (
            int(frozen_tick)
            if frozen_tick is not None
            else getattr(context, "frozen_tick", 0)
        )
        source_count = len(context.supplied_source_ids)

        log_info(
            "title_nomination_admitted",
            context={
                "player": player_id,
                "trigger": trigger,
                "frozen_tick": actual_frozen_tick,
                "source_count": source_count,
            },
        )

        generation = _generate(
            entity,
            context,
            tuple(watchers),
            resolved,
            player_id,
            trigger=trigger,
            frozen_tick=actual_frozen_tick,
            source_count=source_count,
        )
        generation.addErrback(_log_generation_error)
        return generation
    except Exception as error:  # noqa: BLE001 - fire-and-forget contract
        log_warn(
            "title_nomination_scheduling_failed",
            exc=error,
            context={"char": getattr(entity, "pk", 0) or 0},
        )
        return None


# ---------------------------------------------------------------------------
# Settlement observers (wake / quest-arc completion)
# ---------------------------------------------------------------------------


def _watchers(entity: Any) -> tuple:
    from web.webclient.presentation.watchers import watchers_for

    try:
        return watchers_for(entity)
    except Exception:  # noqa: BLE001 - presentation-only input # observability: ignore R2: presentation-only fallback; an empty watcher tuple degrades the push only
        return ()


def _on_quest_completion(entity: Any, record: Any, definition: Any) -> None:
    """Quest-completion observer: schedule only after the settlement commits."""
    del definition
    quest_id = getattr(record, "quest_id", "") or ""
    actor_pk = getattr(entity, "pk", "") or ""
    source_id = f"quest:{quest_id}:completion:{actor_pk}" if quest_id and actor_pk else None
    _schedule_after_commit(entity, source_id=source_id, trigger="quest_completion")


def _schedule_after_commit(
    entity: Any,
    *,
    source_id: str | None = None,
    award_results: Any = None,
    occurrence_id: str | None = None,
    trigger: str = "unknown",
) -> None:
    from django.db import transaction

    transaction.on_commit(
        lambda: _schedule_committed(
            entity,
            source_id=source_id,
            award_results=award_results,
            occurrence_id=occurrence_id,
            trigger=trigger,
        )
    )


def _schedule_committed(
    entity: Any,
    *,
    source_id: str | None = None,
    award_results: Any = None,
    occurrence_id: str | None = None,
    trigger: str = "unknown",
) -> None:
    try:
        schedule_epithet_nomination(
            entity,
            watchers=_watchers(entity),
            source_id=source_id,
            award_results=award_results,
            occurrence_id=occurrence_id,
            trigger=trigger,
        )
    except Exception as error:  # noqa: BLE001 - fire-and-forget contract
        log_warn(
            "title_nomination_post_commit_failed",
            exc=error,
            context={"char": getattr(entity, "pk", 0) or 0},
        )


def notify_wake_transition(
    entity: Any,
    *,
    occurrence_id: str,
    in_combat: bool = False,
) -> None:
    """Notify committed player awakening after transaction commit."""
    if in_combat:
        # Live combat wake is ineligible
        return
    _schedule_after_commit(
        entity,
        occurrence_id=occurrence_id,
        trigger="wake",
    )


_TRIGGERS_REGISTERED = False


def register_nomination_triggers() -> None:
    """Install the quest-completion observer (idempotent).

    Called from ``at_server_start`` through a boot-tolerant wrapper. The
    logout and wake triggers call :func:`schedule_epithet_nomination` /
    :func:`notify_wake_transition` directly after commit;
    this function wires the settlement-embedded quest-completion rest point.
    """
    global _TRIGGERS_REGISTERED
    if _TRIGGERS_REGISTERED:
        return
    from world.quests.runtime import register_quest_completion_observer
    from world.rules.fatigue import register_wake_transition_observer

    register_quest_completion_observer(_on_quest_completion)
    register_wake_transition_observer(notify_wake_transition)
    _TRIGGERS_REGISTERED = True


def reset_nomination_triggers_for_tests() -> None:
    """Undo the observer registration flag (test seam; does not mutate the
    owning subsystems' observer lists)."""
    global _TRIGGERS_REGISTERED
    _TRIGGERS_REGISTERED = False
    _IN_FLIGHT_PLAYERS.clear()
    _PROCESSED_OCCURRENCES.clear()


__all__ = [
    "BALLOT_PANEL",
    "notify_wake_transition",
    "register_nomination_triggers",
    "reset_nomination_triggers_for_tests",
    "schedule_epithet_nomination",
]
