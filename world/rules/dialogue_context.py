"""Pure dialogue context resolution and validation.

Owns DialogueContext and resolve_dialogue_context per Shared contract v2.
Context ID is nullable before a session exists and is never allocated here.

Actor / owner / host boundaries
-------------------------------
``actor`` is the entity that speaks and carries the dialogue session. It is
the puppeted body: the player character itself, or a lawfully possessed
companion. ``owner`` is the player who owns the conversation: the acting
player character, or the commander behind a possessed companion. Everything
player-owned resolves through the owner -- host relationships, affinity and
reading -- while the acting body supplies its own portrait and race.
``host`` is always the conversation target and is never the actor or the
owner: addressing the possessed self or one's own body stays unavailable.

Possession authorization is complete here: the commander must resolve
through :func:`world.rules.party_scope.resolve_commander` (both mirrors and a
live owner-account driving session), the acting body must be that commander's
companion in both binding directions, the host must be co-located but a
different entity, and generated phase revisions must not be stale. Callers
keep their host-schedule gate; the deterministic selection boundary
(:func:`world.rules.dialogue.select_authored_topic`) rechecks it before any
effect.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    make_generated_host_key,
    make_static_host_key,
)

REASON_NOT_AUTHORIZED = "not_party_member"
REASON_STALE_PHASE = "stale_phase"
REASON_SCHEDULE_BLOCKED = "schedule_blocked"
REASON_SELF_HOST = "possessed_self"
REASON_OWNER_HOST = "owner_host"
REASON_NOT_CO_LOCATED = "not_co_located"
REASON_ACTOR_UNAVAILABLE = "actor_cannot_act"


class DialogueContextError(RuntimeError):
    """A dialogue context failed possession authorization.

    ``reason`` is a stable code; callers map it to their own refusal surface
    (the web standard ``possessed_talk`` line, the text refusal, or a disabled
    affordance). The error never carries or mutates state.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class DialogueContext:
    """Server-only dialogue execution context across static and generated sources."""

    actor: Any
    owner: Any
    host: Any
    host_key: str
    source_identity: StaticDialogueIdentity | GeneratedDialogueIdentity | None
    context_id: str | None
    phase_revision: int | str | None


def host_dialogue_binding(
    host: Any,
) -> tuple[str, StaticDialogueIdentity | GeneratedDialogueIdentity | None]:
    """The stable ``host_key`` and source identity of one host entity.

    Pure host read shared by the context resolver and the source-only host
    lookup used by presentation (which must enumerate a schedule-blocked or
    otherwise non-executable host without admitting an interaction).
    """
    from world.rules.dialogue import dialogue_key_for
    from world.rules.dialogue_sources import canonical_dialogue_bindings
    from world.rules.npc_persona import provenance_profile_key

    dialogue_key = dialogue_key_for(host)
    if not isinstance(dialogue_key, str):
        dialogue_key = None

    if dialogue_key is None:
        profile_key = provenance_profile_key(host) or getattr(
            host, "host_profile_key", None
        )
        host_key = make_static_host_key(
            str(profile_key) if profile_key else f"npc_{getattr(host, 'pk', 0)}"
        )
        return host_key, None

    if dialogue_key.startswith("scene_role:"):
        parts = dialogue_key.split(":")
        pkg_id = parts[1] if len(parts) > 1 else ""
        role_id = parts[2] if len(parts) > 2 else ""
        from world.rules.dialogue import dialogue_phase_revision

        phase_rev = dialogue_phase_revision(host)
        phase_id = f"phase_{phase_rev}" if phase_rev is not None else "phase_1"
        return (
            make_generated_host_key(pkg_id, role_id),
            GeneratedDialogueIdentity(pkg_id, role_id, phase_id),
        )

    bindings = canonical_dialogue_bindings()
    profile_key = bindings.get(dialogue_key) or getattr(host, "host_profile_key", None)
    if not profile_key:
        profile_key = dialogue_key
    return (
        make_static_host_key(profile_key),
        StaticDialogueIdentity(profile_key, dialogue_key),
    )


def session_control_owner(character: Any) -> Any | None:
    """The lawful player owner behind ``character``, or ``None``.

    A player character owns itself. Any other entity is an acting body only
    while it resolves through the possession authority boundary: the
    commander behind a lawfully possessed companion, with the companion
    binding valid in both directions. A forged or stale mirror resolves no
    owner and therefore no dialogue authority.
    """
    from typeclasses.characters import PlayerCharacter

    if isinstance(character, PlayerCharacter):
        return character

    from world.rules.party import bound_owner_of, is_companion
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        owner = resolve_commander(character)
    except PartyScopeError:
        return None
    except Exception:  # observability: ignore R2: a broken control read authorizes nothing; the refusal is the contract answer
        return None
    if not is_companion(character, owner):
        return None
    if bound_owner_of(character) is not owner:
        return None
    return owner


def control_key_for(actor: Any, owner: Any) -> str:
    """The complete control identity of one dialogue session.

    Owner, actor, driving account and possession ``since_tick`` together make
    the key: a new control context never reuses an old session even when the
    same owner/actor pair is re-established.
    """
    owner_id = int(getattr(owner, "pk", 0) or 0)
    actor_id = int(getattr(actor, "pk", 0) or 0)
    binding: dict[str, Any] = {}
    try:
        from world.rules.possession import current_possession

        binding = current_possession(owner) or {}
    except Exception:  # observability: ignore R2: an unreadable mirror yields the no-possession key and never authorizes a session
        binding = {}
    account_id = binding.get("account_id")
    if account_id is None:
        account_id = getattr(getattr(owner, "account", None), "pk", None)
    since_tick = binding.get("since_tick") or 0
    return f"{owner_id}:{actor_id}:{int(account_id or 0)}:{int(since_tick)}"


def _require_lawful_actor(actor: Any) -> Any:
    """Return the owner for ``actor`` or raise :class:`DialogueContextError`."""
    from typeclasses.characters import PlayerCharacter

    if isinstance(actor, PlayerCharacter):
        return actor

    owner = session_control_owner(actor)
    if owner is None:
        raise DialogueContextError(REASON_NOT_AUTHORIZED)

    from world.rules.fatigue import sleep_blocks_actions
    from world.rules.party_scope import is_knocked_out

    if sleep_blocks_actions(actor) or is_knocked_out(actor):
        raise DialogueContextError(REASON_ACTOR_UNAVAILABLE)
    return owner


def resolve_dialogue_context(
    actor: Any, host: Any, *, session: Any = None
) -> DialogueContext:
    """Resolve the dialogue context for an interacting actor and host.

    Pure reader/validator: never allocates context IDs or mutates state.
    Raises :class:`DialogueContextError` when a possessed (or otherwise
    non-player) acting body is not lawfully controlled, when the host is the
    acting body or its owner, when actor and host are not co-located, or when
    the stored session belongs to a different control identity.
    """
    from world.rules.dialogue import dialogue_phase_revision

    owner = _require_lawful_actor(actor)

    if host is actor:
        raise DialogueContextError(REASON_SELF_HOST)
    if owner is not None and host is owner:
        raise DialogueContextError(REASON_OWNER_HOST)
    actor_location = getattr(actor, "location", None)
    if actor_location is None or getattr(host, "location", None) is not actor_location:
        raise DialogueContextError(REASON_NOT_CO_LOCATED)

    host_key, source_identity = host_dialogue_binding(host)

    if session is None:
        from world.rules.dialogue import live_dialogue_session

        session = live_dialogue_session(actor)

    context_id: str | None = None
    context_phase: int | str | None = None

    if session is not None and getattr(session, "npc_id", None) == int(
        getattr(host, "pk", 0)
    ):
        same_control = getattr(session, "control_key", "") == control_key_for(
            actor, owner
        )
        current_rev = dialogue_phase_revision(host)
        session_rev = getattr(session, "phase_revision", None)
        generated = isinstance(source_identity, GeneratedDialogueIdentity)
        if same_control and not (generated and session_rev != current_rev):
            context_id = getattr(session, "context_id", None)
            context_phase = session_rev

    return DialogueContext(
        actor=actor,
        owner=owner,
        host=host,
        host_key=host_key,
        source_identity=source_identity,
        context_id=context_id,
        phase_revision=context_phase,
    )


__all__ = [
    "DialogueContext",
    "DialogueContextError",
    "REASON_ACTOR_UNAVAILABLE",
    "REASON_NOT_AUTHORIZED",
    "REASON_NOT_CO_LOCATED",
    "REASON_OWNER_HOST",
    "REASON_SCHEDULE_BLOCKED",
    "REASON_SELF_HOST",
    "REASON_STALE_PHASE",
    "control_key_for",
    "host_dialogue_binding",
    "resolve_dialogue_context",
    "session_control_owner",
]
