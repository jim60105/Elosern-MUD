"""Production encounter eligibility and activation at exploration boundaries.

One deterministic boundary serves every production trigger: post-publication for
a connected owner, settled room entry, wilderness-coordinate travel, reconnect,
startup of connected owners and a declared prerequisite change. It consumes the
saved package/owner through the indexed owner reference, the actual lawful
exploring actor's authoritative position, and the current tick, and then calls
upstream :func:`world.quests.encounters.activate_scene_encounter` -- which owns
its transaction and revalidates locator, prerequisites and actor availability.
This module never supplies an invented observation mapping and never writes
scene state itself.

Two properties matter for the callers on the movement path:

* it **never raises**: a completed move must never be cancelled because an
  unrelated store of a published package refused activation. A refusal is a
  named non-success (the upstream ``EncounterUnavailable`` reason) reported
  through the observability facade and skipped.
* it is **independent of acceptance**: eligibility for the daughter and the
  mother encounter is evaluated per declared locator, so either order works
  before any commission is accepted.

Only the owner's own published packages are read, indexed by owner, so an
ordinary movement never scans every player or every generated scene.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from world.observability import log_info, log_warn

from . import scene_store
from .encounter_activation import EncounterUnavailable, activate_scene_encounter
from .encounters import ScenePackageNotFound, ensure_package_views

__all__ = [
    "activate_pending_encounters",
    "pending_encounters",
    "resolve_exploring_owner",
]


def _resolve(pk: Any) -> Any:
    from evennia.objects.models import ObjectDB

    try:
        clean = int(pk)
    except (TypeError, ValueError):
        # observability: ignore R2: a non-numeric ownership marker is unresolvable
        return None
    return ObjectDB.objects.filter(pk=clean).first()


def resolve_exploring_owner(actor: Any) -> Any | None:
    """The original owning player for the actor currently in lawful control.

    Possession changes control, not ownership: an account driving its own bound
    companion still owns the work and the scenes, while the *position* used for
    eligibility is the possessed actor's actual location. A missing or unlawful
    ownership marker resolves to ``None``, which activates nothing.
    """
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    if possessed_by is not None:
        return _resolve(possessed_by)
    from typeclasses.characters import PlayerCharacter

    if isinstance(actor, PlayerCharacter):
        return actor
    from world.rules.party import bound_owner_of

    return bound_owner_of(actor)


def _locator_matches(encounter: dict[str, Any], room: Any) -> bool:
    """Whether one declared encounter locator covers this authoritative room.

    Read through the upstream locator compiler, so the boundary cannot drift
    from the contract the activation boundary itself revalidates: an anchor must
    name the room's own key, a grid cell must match the room's coordinates, and
    an instance encounter is reachable from wherever the player stands (the
    activation boundary resolves the instance room itself).
    """
    if room is None:
        return False
    try:
        from world.quests.compile.fields import _compile_location
        from world.quests.definitions import DestinationKind

        locator = _compile_location(encounter.get("locator"))
    except Exception:  # observability: ignore R2: an unreadable stored locator never activates anything
        return False
    if locator.kind is DestinationKind.ANCHOR:
        return getattr(room, "anchor_key", None) == locator.anchor_key
    if locator.kind is DestinationKind.GRID:
        coordinates = getattr(room, "coordinates", None) or getattr(room, "xyz", None)
        if coordinates is None:
            # The room cannot name its own cell; let the authoritative
            # activation boundary decide rather than guess.
            return True
        try:
            return (int(coordinates[0]), int(coordinates[1])) == (
                int(locator.xyz[0]),
                int(locator.xyz[1]),
            )
        except (TypeError, ValueError, IndexError):
            # observability: ignore R2: an uncomparable cell falls through to the activation boundary
            return True
    return True


def pending_encounters(
    owner: Any,
    *,
    room: Any = None,
    prerequisite_fact: str | None = None,
) -> tuple[tuple[str, str], ...]:
    """The ``(package_id, scene_id)`` pairs eligible at one actual position.

    Indexed by owner; a scene already activated or cancelled for this owner is
    skipped so a repeat entry never reattempts a committed activation.
    """
    if owner is None or room is None:
        return ()
    eligible: list[tuple[str, str]] = []
    for row in scene_store.packages_for_owner(str(owner.pk)):
        for encounter in row.payload.get("encounters") or []:
            if not isinstance(encounter, dict):
                continue
            scene_id = encounter.get("scene_id")
            if not isinstance(scene_id, str) or not scene_id:
                continue
            if prerequisite_fact is not None and not _declares_prerequisite(
                encounter, prerequisite_fact
            ):
                continue
            if not _locator_matches(encounter, room):
                continue
            existing = scene_store.get_encounter(row.package_id, scene_id, int(owner.pk))
            if existing is not None and existing.state != scene_store.ENCOUNTER_PENDING:
                continue
            eligible.append((row.package_id, scene_id))
    return tuple(eligible)


def _declares_prerequisite(encounter: dict[str, Any], fact: str) -> bool:
    """Whether one declared encounter's prerequisites depend on ``fact``."""
    for condition in encounter.get("prerequisites") or []:
        if isinstance(condition, dict) and fact in condition:
            return True
    return False


def activate_pending_encounters(
    actor: Any,
    *,
    room: Any = None,
    tick: int = 0,
    prerequisite_fact: str | None = None,
) -> tuple[Any, ...]:
    """Activate every encounter eligible at this boundary; never raise.

    Returns the committed activations (the ones that created something). A
    refusal is reported and skipped: the caller's own transaction -- a settled
    movement, an arrival, a reconnect or startup -- is never cancelled by an
    unrelated scene store's refusal.
    """
    try:
        owner = resolve_exploring_owner(actor)
        position = room if room is not None else getattr(actor, "location", None)
        if owner is None or position is None:
            return ()
        committed: list[Any] = []
        for package_id, scene_id in pending_encounters(
            owner, room=position, prerequisite_fact=prerequisite_fact
        ):
            try:
                # A committed package whose process-local views were lost to an
                # outer-scope rollback is restored before this player could fail
                # to resolve its definition.
                ensure_package_views(package_id)
                # Each candidate runs inside its own savepoint: a failure that
                # poisons the surrounding movement transaction (a statement
                # error, or an integrity error escaping the activation
                # boundary) rolls back to this savepoint instead of aborting
                # the committed move that triggered the check.
                with transaction.atomic():
                    activation = activate_scene_encounter(
                        owner, package_id, scene_id, room=position, tick=int(tick)
                    )
            except (ScenePackageNotFound, EncounterUnavailable) as error:
                log_warn(
                    "scene_encounter_activation_refused",
                    context={
                        "char": str(getattr(owner, "pk", "")),
                        "package": package_id,
                        "scene": scene_id,
                        "reason": str(getattr(error, "reason", error)),
                        "tick": str(tick),
                    },
                )
                continue
            except Exception as error:
                # One store's technical failure must not stop the remaining
                # eligible scenes; the savepoint above already rolled it back.
                log_warn(
                    "scene_encounter_activation_failed",
                    context={
                        "char": str(getattr(owner, "pk", "")),
                        "package": package_id,
                        "scene": scene_id,
                        "tick": str(tick),
                    },
                    exc=error,
                )
                continue
            if activation.created:
                committed.append(activation)
                log_info(
                    "scene_encounter_activated_from_boundary",
                    context={
                        "char": str(getattr(owner, "pk", "")),
                        "package": package_id,
                        "scene": scene_id,
                        "room": str(getattr(position, "pk", "")),
                        "tick": str(tick),
                    },
                )
        if committed:
            _refresh_after_commit(owner)
        return tuple(committed)
    except Exception as error:
        # A published package is a projection onto the world; a failure to
        # project it must never undo the committed movement or arrival that
        # triggered the check. The reason is recorded for the operator.
        log_warn(
            "scene_encounter_activation_failed",
            context={
                "char": str(getattr(actor, "pk", "")),
                "tick": str(tick),
            },
            exc=error,
        )
        return ()


def _refresh_after_commit(owner: Any) -> None:
    """Refresh the existing action-option projection once activation commits."""

    def refresh() -> None:
        from typeclasses.characters import _schedule_action_options_after_move

        _schedule_action_options_after_move(owner)

    transaction.on_commit(refresh)


def activate_for_move(actor: Any, *, tick: int | None = None) -> tuple[Any, ...]:
    """Room-entry activation for one relocation, at the charged tick.

    A relocation that already runs inside the settled movement receipt (the
    traversal boundary) must not activate again: that boundary activates once,
    after the movement settles and after the clock charge, so activating from
    the mid-traversal move hook would settle at the wrong tick. A relocation
    outside that boundary (a direct ``move_to``, a gate traversal, a reconnect
    placement) has no charge of its own, so the current clock tick is the
    authoritative one.
    """
    from .escort_events import in_escort_boundary

    if in_escort_boundary():
        return ()
    if tick is None:
        from world.rules.clock import get_world_clock

        tick = int(get_world_clock().tick)
    return activate_pending_encounters(
        actor, room=getattr(actor, "location", None), tick=int(tick)
    )


def puppeted_characters() -> list[Any]:
    """Every currently puppeted character, in session order."""
    import evennia

    characters: list[Any] = []
    for session in evennia.SESSION_HANDLER.get_sessions(include_unloggedin=False):
        puppet = getattr(session, "puppet", None)
        if puppet is not None:
            characters.append(puppet)
    return characters


def sync_connected_owners(
    *, tick: int | None = None, characters: Any = None
) -> tuple[Any, ...]:
    """Reconnect/startup synchronization for every connected owner.

    Reads the saved owner through the current controlled actor's actual
    position and activates whatever the owner's published packages declare
    there -- including a publication whose fan-out was lost while nobody was
    connected. It activates nothing for an owner with no connected session, and
    it never invents an appearance for an offline owner.
    """
    connected = list(characters) if characters is not None else puppeted_characters()
    activated: list[Any] = []
    for character in connected:
        activated.extend(activate_for_move(character, tick=tick))
        # Reconnect also reads the owner's latest durable work status: an
        # offline owner keeps its work, and a returning one is told the truth
        # about it through ordinary output (dream-story-dispatch §8).
        from world.narrative import dispatch_status

        dispatch_status.deliver_status(character)
    return tuple(activated)
