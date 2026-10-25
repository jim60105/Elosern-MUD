"""Pure dialogue context resolution and validation.

Owns DialogueContext and resolve_dialogue_context per Shared contract v2.
Context ID is nullable before a session exists and is never allocated here.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    make_generated_host_key,
    make_static_host_key,
)


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


def resolve_dialogue_context(
    actor: Any, host: Any, *, session: Any = None
) -> DialogueContext:
    """Resolve the dialogue context for an interacting actor and host.

    Pure reader/validator: never allocates context IDs or mutates state.
    """
    from world.rules.dialogue import (
        dialogue_key_for,
        dialogue_phase_revision,
        live_dialogue_session,
    )
    from world.rules.dialogue_sources import canonical_dialogue_bindings
    from world.rules.npc_persona import provenance_profile_key

    # Ordinary player: owner is actor.
    owner = actor

    dialogue_key = dialogue_key_for(host)
    source_identity: StaticDialogueIdentity | GeneratedDialogueIdentity | None = None
    host_key: str

    if dialogue_key is None:
        profile_key = provenance_profile_key(host) or getattr(
            host, "host_profile_key", None
        )
        host_key = make_static_host_key(
            str(profile_key) if profile_key else f"npc_{getattr(host, 'pk', 0)}"
        )
        source_identity = None
    elif dialogue_key.startswith("scene_role:"):
        parts = dialogue_key.split(":")
        pkg_id = parts[1] if len(parts) > 1 else ""
        role_id = parts[2] if len(parts) > 2 else ""
        phase_rev = dialogue_phase_revision(host)
        phase_id = f"phase_{phase_rev}" if phase_rev is not None else "phase_1"
        host_key = make_generated_host_key(pkg_id, role_id)
        source_identity = GeneratedDialogueIdentity(pkg_id, role_id, phase_id)
    else:
        # Static host
        bindings = canonical_dialogue_bindings()
        profile_key = bindings.get(dialogue_key) or getattr(
            host, "host_profile_key", None
        )
        if not profile_key:
            profile_key = dialogue_key
        host_key = make_static_host_key(profile_key)
        source_identity = StaticDialogueIdentity(profile_key, dialogue_key)

    if session is None:
        session = live_dialogue_session(actor)

    context_id: str | None = None
    phase_revision: int | str | None = None

    if session is not None and getattr(session, "npc_id", None) == int(getattr(host, "pk", 0)):
        # Validate that phase revision has not changed for generated host
        current_rev = dialogue_phase_revision(host)
        session_rev = getattr(session, "phase_revision", None)
        if dialogue_key and dialogue_key.startswith("scene_role:") and session_rev != current_rev:
            context_id = None
            phase_revision = None
        else:
            context_id = getattr(session, "context_id", None)
            phase_revision = session_rev

    return DialogueContext(
        actor=actor,
        owner=owner,
        host=host,
        host_key=host_key,
        source_identity=source_identity,
        context_id=context_id,
        phase_revision=phase_revision,
    )


__all__ = [
    "DialogueContext",
    "resolve_dialogue_context",
]
