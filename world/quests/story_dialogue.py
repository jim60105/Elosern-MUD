"""Revisioned story-phase transitions through the deterministic owner.

``transition_story_dialogue`` joins the owning committed-observation transaction
and selects exactly one complete dialogue phase for one role, writing the new
phase and its monotonic revision through the store, recording the role's
permitted knowledge through the narrative owner, and refreshing live dialogue
sessions through the existing session helpers after the commit. Persona, prior
turns and previous frames are never rewritten (design §6).

``commit_reunion_participation`` records a committed exclusive result as each
participant role's own knowledge and advances the role's dialogue to its
acknowledgment phase. The boundary refuses guarded acceptance/progress
observations, refuses a stale expected revision, refuses an ambiguous selection,
and never derives an outcome from prose: the observation provenance must name
only registered deterministic facts, and the ``reunion``/``reunion_closure``
values are re-derived from the committed result state (escort-rendezvous §7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.observability import log_info

from . import scene_store
from .encounters import ScenePackageNotFound
from .phases import resolve_observations
from .scene_package import select_dialogue_phase, validate_scene_package


class StoryDialogueError(RuntimeError):
    """A phase transition violates its deterministic contract."""


class StalePhaseRevision(StoryDialogueError):
    """The caller's expected phase revision is no longer current."""


class StoryRoleNotFound(LookupError):
    """The referenced package role has no dialogue definition."""


@dataclass(frozen=True)
class StoryPhaseTransition:
    """The committed result of one phase transition."""

    package_id: str
    role_id: str
    phase_id: str
    revision: int
    changed: bool


def _resolve_role_actor(package_id: str, role_id: str) -> Any | None:
    from evennia.objects.models import ObjectDB

    binding = scene_store.get_role_binding(package_id, role_id)
    if binding is None:
        return None
    return ObjectDB.objects.filter(id=int(binding.npc_id)).first()


def transfer_story_knowledge(
    package_id: str,
    role_id: str,
    claim_id: str,
    *,
    tick: int = 0,
) -> bool:
    """Record one truthfully transferred published claim for a receiving role.

    The claim must exist in the package and belong to a *different* role: this is
    the permitted information-transfer boundary, so one role can learn another
    role's published claim when the story makes that transfer real. Nothing is
    inferred from prose and no private authoring text is copied. Returns whether a
    new knowledge record was written.
    """
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    definition = validate_scene_package(row.payload)
    if definition.role(role_id) is None or definition.role_dialogue(role_id) is None:
        raise StoryRoleNotFound(f"role {role_id!r} has no dialogue definition")
    claim = next(
        (item for item in definition.knowledge if item.claim_id == claim_id), None
    )
    if claim is None:
        raise StoryDialogueError(f"package {package_id!r} has no claim {claim_id!r}")
    if claim.role_id == role_id:
        return False
    actor = _resolve_role_actor(package_id, role_id)
    if actor is None:
        raise StoryDialogueError(
            f"role {role_id!r} is not materialized; knowledge cannot be transferred"
        )
    from world.narrative.memory import record_memory

    _record, _revision, created = record_memory(
        owner_id=str(actor.pk),
        content={
            "claim_id": claim.claim_id,
            "claim": claim.text,
            "package": package_id,
            "role": role_id,
            "transferred_from": claim.role_id,
        },
        tick=tick,
        category="knowledge",
        knowledge_scope="told",
        source_id=f"transfer:{package_id}:{role_id}:{claim.role_id}:{claim.claim_id}",
        projector_version=1,
    )
    if created:
        log_info(
            "story_knowledge_transferred",
            context={
                "package": package_id,
                "role": role_id,
                "from_role": claim.role_id,
                "claim": claim.claim_id,
                "tick": str(tick),
            },
        )
    return created


def transition_story_dialogue(
    package_id: str,
    role_id: str,
    *,
    expected_revision: int,
    provenance: dict[str, bool],
    participants: tuple[Any, ...] = (),
    tick: int = 0,
) -> StoryPhaseTransition:
    """Select and commit one role's phase from committed observation provenance.

    ``expected_revision`` is the revision the caller resolved its decision
    against; a mismatch raises :class:`StalePhaseRevision` with no write.
    ``provenance`` names only registered deterministic facts (a guarded
    escort/reunion fact raises). The selected phase is written with a monotonic
    revision, the role's permitted knowledge is recorded through the narrative
    owner, and any live session naming the role's actor is refreshed through the
    existing sole-writer session helper after the commit.
    """
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    if row.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        raise StoryDialogueError(f"package {package_id!r} is cancelled")
    definition = validate_scene_package(row.payload)
    role_dialogue = definition.role_dialogue(role_id)
    if role_dialogue is None:
        raise StoryRoleNotFound(f"role {role_id!r} has no dialogue definition")

    facts = resolve_observations(provenance)
    # The exclusive-result facts are not the caller's to assert: verify the
    # supplied value against the committed result state so a fabricated
    # ``reunion`` can never select the acknowledgment phase (escort-rendezvous
    # §7, design §"Explicit final-result arbitration").
    from .encounter_activation import committed_observations

    committed = committed_observations(package_id)
    for fact in ("reunion", "reunion_closure"):
        if fact in facts and facts[fact] is not committed.get(fact, False):
            raise StoryDialogueError(
                f"provenance {fact!r} contradicts the committed result state"
            )
    selected = select_dialogue_phase(role_dialogue, facts)

    current = scene_store.get_dialogue_phase(package_id, role_id)
    if current is not None and current.selected_phase == selected.phase_id:
        if current.revision != expected_revision:
            raise StalePhaseRevision(
                f"role {role_id!r} revision {current.revision} != expected "
                f"{expected_revision}"
            )
        return StoryPhaseTransition(
            package_id=package_id,
            role_id=role_id,
            phase_id=selected.phase_id,
            revision=current.revision,
            changed=False,
        )

    actor = _resolve_role_actor(package_id, role_id)
    with transaction.atomic():
        updated = scene_store.advance_dialogue_phase(
            row,
            role_id,
            selected.phase_id,
            expected_revision=expected_revision,
            tick=tick,
        )
        if updated is None:
            raise StalePhaseRevision(
                f"role {role_id!r} expected revision {expected_revision} is stale"
            )
        if actor is not None:
            _grant_role_knowledge(actor, definition, role_id, package_id, tick=tick)
    if actor is not None and participants:
        transaction.on_commit(
            lambda: _refresh_sessions(participants, actor, selected.greeting)
        )
    log_info(
        "story_dialogue_transitioned",
        context={
            "package": package_id,
            "role": role_id,
            "phase": selected.phase_id,
            "revision": str(updated.revision),
            "tick": str(tick),
        },
    )
    return StoryPhaseTransition(
        package_id=package_id,
        role_id=role_id,
        phase_id=selected.phase_id,
        revision=updated.revision,
        changed=True,
    )


def commit_reunion_participation(
    package_id: str,
    role_ids: tuple[str, ...],
    *,
    group_id: str,
    winner_quest_id: str,
    tick: int = 0,
) -> None:
    """Record a resolved group's participant knowledge and acknowledgment phase.

    For every participant role, the committed result is recorded as that role
    actor's own knowledge through the narrative owner (idempotent per
    package/group, so a replay records nothing new), and the role's dialogue
    advances to the acknowledgment phase its package declares for the committed
    ``reunion`` fact. A role with no dialogue definition is skipped; the
    transition re-derives ``reunion`` from the committed result state, so the
    caller asserting it is verified rather than trusted (escort-rendezvous §7).
    """
    from world.narrative.memory import record_memory

    row = scene_store.read_package(package_id)
    declared_dialogue = set()
    if row is not None:
        declared_dialogue = {
            entry.get("role_id")
            for entry in row.payload.get("dialogue", [])
            if isinstance(entry, dict)
        }
    for role_id in role_ids:
        actor = _resolve_role_actor(package_id, role_id)
        if actor is None:
            continue
        record_memory(
            owner_id=str(actor.pk),
            content={
                "package": package_id,
                "group": group_id,
                "result": winner_quest_id or "no_commission",
            },
            tick=tick,
            category="knowledge",
            knowledge_scope="witnessed",
            source_id=f"reunion:{package_id}:{group_id}",
            projector_version=1,
        )
        if role_id not in declared_dialogue:
            # A participant role that declares no dialogue has no phase to
            # advance; its committed result knowledge is still recorded.
            continue
        runtime = scene_store.get_dialogue_phase(package_id, role_id)
        try:
            transition_story_dialogue(
                package_id,
                role_id,
                expected_revision=runtime.revision if runtime is not None else 0,
                provenance={"reunion": True},
                tick=tick,
            )
        except StoryRoleNotFound:  # observability: ignore R2: a role with no dialogue definition has no phase to advance and its committed result knowledge is already recorded above
            continue


def _grant_role_knowledge(
    actor: Any,
    definition: Any,
    role_id: str,
    package_id: str,
    *,
    tick: int,
) -> None:
    """Re-record the role's own permitted knowledge through the narrative owner."""
    from world.narrative.memory import record_memory

    for claim in definition.knowledge:
        if claim.role_id != role_id:
            continue
        record_memory(
            owner_id=str(actor.pk),
            content={
                "claim_id": claim.claim_id,
                "claim": claim.text,
                "package": package_id,
                "role": role_id,
            },
            tick=tick,
            category="knowledge",
            knowledge_scope="witnessed",
            source_id=f"scene:{package_id}:{role_id}:{claim.claim_id}",
            projector_version=1,
        )


def _refresh_sessions(participants: tuple[Any, ...], actor: Any, greeting: str) -> None:
    """Refresh any live session naming the role's actor through its sole writer."""
    from world.rules.dialogue import live_dialogue_session, open_or_refresh_dialogue

    for participant in participants:
        session = live_dialogue_session(participant)
        if session is None or session.npc_id != int(actor.pk):
            continue
        open_or_refresh_dialogue(participant, actor, greeting)


__all__ = [
    "StalePhaseRevision",
    "StoryDialogueError",
    "StoryPhaseTransition",
    "StoryRoleNotFound",
    "transfer_story_knowledge",
    "transition_story_dialogue",
]
