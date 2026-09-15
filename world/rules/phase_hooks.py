"""Phase-reaction dispatcher slot (light-climax-empowerment).

The dependency leaf between the phase-transition setter and the declarative
reaction engine. ``world.rules.sexual_state`` fires a phase edge without
importing the reaction module (which would drag the whole cast pipeline into
``world.rules.pleasure``'s import closure); ``world.rules.state_reactions``
publishes its dispatcher here at module load, and the production bootstrap
path force-imports it so registration is explicit, never lazy.

Imports nothing. Unregistered edge semantics: a phase transition proceeds
without reactions — empowerment is additive, and an absent reaction layer
must not block the canonical phase write.
"""

_PHASE_DISPATCHER = None


def register_phase_dispatcher(dispatcher) -> None:
    """Publish the phase-reaction callable (idempotent re-registration)."""
    global _PHASE_DISPATCHER
    _PHASE_DISPATCHER = dispatcher


def dispatch_phase_reaction(entity, from_phase: str, to_phase: str) -> None:
    """Route one canonical climax-phase edge to the registered dispatcher.

    Keyword arguments mirror ``state_reactions.dispatch_phase_reaction`` so
    the registered function needs no adapter. A no-op while no dispatcher is
    registered.
    """
    if _PHASE_DISPATCHER is None:
        return
    _PHASE_DISPATCHER(entity, from_phase=from_phase, to_phase=to_phase)


__all__ = ["register_phase_dispatcher", "dispatch_phase_reaction"]
