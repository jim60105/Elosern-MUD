"""Sole writer of onboarding state and the arrival/guide service (onboarding-guide D3).

Every write to a player character's ``onboarded``, ``onboarding_beat``,
``guide_progress``, and ``first_arrival_seen`` attributes routes through this
module. The immutable beat/dialogue/corridor data lives in ``world/onboarding``,
which never imports this module — the dependency direction is
``rules -> onboarding`` only, preserving the single-writer invariant.
"""

from typing import Any

from evennia.utils.logger import log_warn

from typeclasses.components import OnboardingGuide
from typeclasses.npcs import NPC
from world.maps.bootstrap import SOUTH_GATE_XYZ
from world.onboarding.guide import (
    GuideProgress,
    OnboardingSnapshot,
    arrival_scene,
    dialogue_has_keyword,
    guide_should_prompt,
    next_beat_output,
    room_entry_decision,
)
from world.onboarding.guide_dialogue import GUARD_DIALOGUE_KEY
from world.onboarding.scenes import (
    GUIDANCE_BEAT_ID,
    GUILD_EXTERIOR_ROOM_KEY,
    LOOK_BEAT_ID,
    SOUTH_GATE_ROOM_KEY,
)

GUARD_NPC_KEY = "南門守衛"
GUARD_NPC_TAG = "onboarding_guard"
GUARD_NPC_DESC = (
    "一位身披輕甲的王都守衛，站在南門拱門下，打量著每一位新到的旅人。"
)
_DEGRADATION_NOTICE = (
    "（南門目前無法抵達，你留在了原地。世界仍歡迎你的到來。）"
)


def _room_key(character: Any) -> str | None:
    location = getattr(character, "location", None)
    return getattr(location, "key", None)


def _is_guard(npc: Any) -> bool:
    return (
        getattr(npc, "components", None) is not None
        and npc.components.has(OnboardingGuide.name)
    )


def snapshot_for(character: Any) -> OnboardingSnapshot:
    """Build the read-only onboarding snapshot from a player character."""
    progress = GuideProgress.from_storage(
        getattr(character, "guide_progress", None) or None
    )
    return OnboardingSnapshot(
        onboarded=bool(getattr(character, "onboarded", False)),
        onboarding_beat=getattr(character, "onboarding_beat", None),
        guide_progress=progress,
        first_arrival_seen=bool(getattr(character, "first_arrival_seen", False)),
        location_key=_room_key(character),
    )


def _write_progress(character: Any, progress: GuideProgress | None) -> None:
    character.guide_progress = (
        progress.to_storage() if progress is not None else {}
    )


def _south_gate():
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    return XYZRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()


def relocate_to_starting_location(character: Any) -> None:
    """Best-effort relocation of a freshly activated shell to 南門.

    Performed ONLY after a successful activation commit, through the existing
    movement path with move hooks disabled: it never rolls activation back,
    never advances the world clock, never emits a player-move EventLog, and
    never triggers the room-entry observer or an automatic look (it is not a
    player action). If 南門 is missing, the move fails, or the move raises, the
    shell stays put and the player receives a degradation notice instead of the
    arrival welcome — activation itself is never rolled back.
    """
    try:
        south_gate = _south_gate()
        if south_gate is None:
            character.msg(_DEGRADATION_NOTICE)
            return
        if character.location is not south_gate:
            moved = character.move_to(south_gate, quiet=True, move_hooks=False)
            if not moved:
                character.msg(_DEGRADATION_NOTICE)
                return
    except Exception as error:
        from evennia.utils.logger import log_warn

        log_warn(f"relocate_to_starting_location: relocation failed: {error}")
        character.msg(_DEGRADATION_NOTICE)
        return
    character.msg(
        f"歡迎，{character.key}。你踏上了伊洛瑟恩大陸的土地。"
    )


def maybe_play_arrival(character: Any) -> bool:
    """Play the arrival scene when appropriate.

    Plays only for an onboarding character at the South Gate whose arrival beat
    has not been completed. Invoked after relocation, from the extended
    ``Account.at_post_login``, and from the South Gate room-entry observer.
    Returns whether the scene was played.
    """
    snapshot = snapshot_for(character)
    beats = arrival_scene(snapshot)
    if beats is None:
        return False
    prose = "\n".join(beat.prose for beat in beats)
    character.msg(prose)
    character.onboarding_beat = LOOK_BEAT_ID
    if snapshot.guide_progress is None:
        _write_progress(character, GuideProgress.active())
    return True


def advance_beat(character: Any) -> str | None:
    """Advance the current beat and return the continuation prose, if any.

    Only the ``look`` beat has a continuation (the guidance beat), and only
    while the character stands at the South Gate. The service guards on room +
    state, so a look elsewhere never advances.
    """
    snapshot = snapshot_for(character)
    if snapshot.onboarded:
        return None
    if snapshot.location_key != SOUTH_GATE_ROOM_KEY:
        return None
    output = next_beat_output(snapshot)
    if output is None:
        return None
    character.onboarding_beat = output.beat.beat_id
    if snapshot.onboarding_beat == LOOK_BEAT_ID:
        character.first_arrival_seen = True
    return output.beat.prose


def mark_guide_skipped(character: Any) -> None:
    """Record the guide as skipped without setting ``onboarded``."""
    progress = GuideProgress.from_storage(
        getattr(character, "guide_progress", None) or None
    ) or GuideProgress.active()
    _write_progress(
        character,
        GuideProgress(state="skipped", seen_keywords=progress.seen_keywords),
    )


def set_onboarded(character: Any) -> None:
    """Mark the first-day journey complete; no further guidance fires."""
    character.onboarded = True


def observe_room_entry(character: Any) -> None:
    """The single room-entry observer for onboarding state.

    A deviation into a room outside ``GUIDED_CORRIDOR`` marks the guide skipped;
    arrival at 冒險者公會外 completes guidance. Reaching the South Gate triggers
    the arrival scene through ``maybe_play_arrival``. All room-key checks live
    here.
    """
    if getattr(character, "onboarded", False):
        return
    room_key = _room_key(character)
    if room_key is None:
        return
    snapshot = snapshot_for(character)
    decision = room_entry_decision(snapshot, room_key)
    if decision == "completed":
        progress = GuideProgress.from_storage(
            getattr(character, "guide_progress", None) or None
        ) or GuideProgress.active()
        _write_progress(
            character,
            GuideProgress(state="completed", seen_keywords=progress.seen_keywords),
        )
        character.onboarding_beat = None
        character.first_arrival_seen = True
        return
    if decision == "skipped":
        mark_guide_skipped(character)
        return
    if room_key == SOUTH_GATE_ROOM_KEY:
        maybe_play_arrival(character)


def is_guide_host(npc: Any) -> bool:
    """Whether ``npc`` carries the onboarding guide dialogue component."""
    return _is_guard(npc)


def talk_response(npc: Any, character: Any, keyword: str) -> str | None:
    """Return the authored response for ``keyword`` on ``npc``.

    ``npc`` must be a dialogue host (``OnboardingGuide`` or
    ``ScriptedDialogue``); an NPC without one returns ``None`` so the command
    can produce the no-response line. Unknown keywords yield the
    no-understanding line and cause NO state change. A known keyword on an
    ``OnboardingGuide`` host is recorded on the player's ``guide_progress``;
    scripted dialogue hosts never write state.
    """
    from world.rules.dialogue import dialogue_response as resolve_response

    if not is_guide_host(npc):
        return resolve_response(npc, keyword)
    component = npc.components.get(OnboardingGuide.get_component_slot())
    dialogue_key = component.dialogue_key or GUARD_DIALOGUE_KEY
    response = resolve_response(npc, keyword)
    if not dialogue_has_keyword(dialogue_key, keyword):
        return response
    progress = GuideProgress.from_storage(
        getattr(character, "guide_progress", None) or None
    )
    if progress is not None:
        _write_progress(character, progress.with_keyword(keyword))
    return response


def current_guide_prompt(character: Any) -> str | None:
    """Return the guard's active guidance line, if the guide should prompt."""
    snapshot = snapshot_for(character)
    if not guide_should_prompt(snapshot):
        return None
    if snapshot.onboarding_beat == GUIDANCE_BEAT_ID:
        from world.onboarding.scenes import BEAT_REGISTRY

        return BEAT_REGISTRY[GUIDANCE_BEAT_ID].prose
    return None


def sync_guard_npc() -> None:
    """Idempotently create exactly one adult guide guard at the South Gate.

    Mirrors the guild-economy sync pattern: a stable key/tag makes repeated
    startup reuse the same NPC. The guard persists an adult identity
    (``age`` and ``apparent_age`` both >= 18). If 南門 is missing, logs a
    warning and skips — guidance degrades but arrival does not.
    """
    from evennia.utils.create import create_object
    from evennia.utils.search import search_object_by_tag

    south_gate = _south_gate()
    if south_gate is None:
        log_warn(
            "sync_guard_npc: South Gate room at "
            f"{SOUTH_GATE_XYZ} not found; skipping guard creation."
        )
        return
    guards = search_object_by_tag(GUARD_NPC_TAG)
    if guards:
        guard = guards[0]
        guard.db.desc = GUARD_NPC_DESC
        if guard.location is not south_gate:
            guard.location = south_gate
        _repair_guard_identity(guard)
        if not guard.components.has(OnboardingGuide.name):
            guard.components.add(
                OnboardingGuide.create(guard, dialogue_key=GUARD_DIALOGUE_KEY)
            )
        return
    guard = create_object(
        NPC,
        key=GUARD_NPC_KEY,
        location=south_gate,
        tags=[GUARD_NPC_TAG],
    )
    guard.db.desc = GUARD_NPC_DESC
    guard.race = "human"
    guard.apply_race_baseline()
    _repair_guard_identity(guard)
    guard.components.add(
        OnboardingGuide.create(guard, dialogue_key=GUARD_DIALOGUE_KEY)
    )


def _repair_guard_identity(guard: Any) -> None:
    """Ensure the guard persists an adult identity (age, apparent_age >= 18)."""
    for key in ("age", "apparent_age"):
        current = guard.attributes.get(key)
        if current is None or int(current) < 18:
            guard.attributes.add(key, 18)


def guard_adult_identity(guard: Any) -> tuple[int, int]:
    """Return the guard's persisted (age, apparent_age) for the sync test."""
    return (
        int(guard.attributes.get("age", 0) or 0),
        int(guard.attributes.get("apparent_age", 0) or 0),
    )
