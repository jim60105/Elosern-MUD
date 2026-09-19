"""Sexual event/act effect declarations, including the divine-arts family.

Part of :mod:`world.skills.effects`; every name is re-exported from the
package root.
"""

from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class SexualEventEffect:
    """Resolve one rule-driven sexual transition by name."""

    event_name: str


@dataclass(frozen=True)
class ActorSexualEventEffect:
    """Resolve one rule-driven sexual transition on the performing actor only.

    The actor-scoped sibling of ``SexualEventEffect``: an act declaring a
    performer-scoped event (``self_exposure``, ``public_exposure``,
    ``watched_during_activity``, ``public_sexual_activity``) emits it through
    the ``sexual_event_actor:<name>`` string, and the cast-side handler
    applies the named event to the acting entity, never to a target.
    """

    event_name: str


@dataclass(frozen=True)
class TargetSexualEventEffect:
    """Resolve one rule-driven sexual transition on the cast's targets only.

    The target-scoped sibling of ``SexualEventEffect`` and
    ``ActorSexualEventEffect``: a hand-built row declaring a target-only
    event (the shipped ``divine_sexual_arts`` skill's ``stimulus_applied``)
    emits it through the ``sexual_event_target:<name>`` string, and the
    cast-side handler applies the named event to every resolved target,
    never to the acting entity. Recipient scope is decided statically by the
    effect prefix — never by an event-name lookup.
    """

    event_name: str


@dataclass(frozen=True)
class PleasureEffect:
    """Apply one sexual act's pleasure to every participant of its cast.

    The parsed segment is the acting ``SexualActDef``'s own key; every other
    parameter (base magnitude, body parts, actor ratio, participant count)
    is read from ``SEXUAL_ACT_REGISTRY[act_key]`` at cast time so no value is
    duplicated between the registry and the effect string.
    """

    act_key: str


@dataclass(frozen=True)
class SexualCounterEffect:
    """Increment the counters one sexual act declares on its participants.

    ``actor_counters`` land on the acting entity and
    ``participant_counters`` on every other participant; the counter names
    themselves are read from ``SEXUAL_ACT_REGISTRY[act_key]`` at cast time.
    """

    act_key: str


@dataclass(frozen=True)
class PairEventEffect:
    """Resolve one sex-conditional rule event from a cast's participant pair.

    The parsed segment is the acting ``SexualActDef``'s own key; the
    per-sex-pair event table is read from ``SEXUAL_ACT_REGISTRY[act_key]`` at
    cast time so no value is duplicated between the registry and the effect
    string. A cast whose participants match no declared pair resolves no
    event and stages no effect (the ``other``/unknown D-12 branch).
    """

    act_key: str


# 神之秘法 act effects (divine-sexual-arts-reuse): hand-built acts declare
# these instead of the ordinary pleasure:/sexual_counter: triad. Each is a
# general dispatch-table entry — no handler reads ``requires_divine_arts``
# or the caller's line.
@dataclass(frozen=True)
class DivinePleasureMaxEffect:
    """Set every resolved target's pleasure to its ceiling in one cast.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the target set comes from the cast's resolved targets,
    and the handler reuses the shipped ``apply_pleasure_gain`` twice
    (``gain=100`` then ``gain=0``) to walk the climax cycle into 進行中.
    """


@dataclass(frozen=True)
class ClimaxExtensionStageEffect:
    """Stage ``count`` consecutive climax extensions on every resolved target."""

    count: int


@dataclass(frozen=True)
class SexualDrainEffect:
    """Drain one target's pleasure into the caster's MP, SP, and HP.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler reads the target's pleasure itself.
    """


@dataclass(frozen=True)
class SaturateSensitivityEffect:
    """Pin every resolvable body part's sensitivity to the top level.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.saturate_sensitivity()``
    on each resolved non-actor target.
    """


@dataclass(frozen=True)
class ClampShameEffect:
    """Pin the target's shame at the vocabulary ceiling (成癮).

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.clamp_shame_to("成癮")``
    on each resolved non-actor target, eagerly rejecting a ``Monster`` target
    before staging anything.
    """


@dataclass(frozen=True)
class MarkSubmissionEffect:
    """Mark the target as permanently auto-complying toward the caster.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls
    ``target.sexual.mark_submission(str(actor.id))`` on each resolved
    non-actor target, keying the permanent mark by the caster's unique
    database id.
    """


@dataclass(frozen=True)
class RestorePurityEffect:
    """Restore the target's virgin flag without touching experience_types.

    The effect string's payload is the act's Chinese label, kept for
    readability only; the handler calls ``target.sexual.restore_purity()``
    on each resolved non-actor target.
    """


@dataclass(frozen=True)
class StimulusEffect:
    """Apply standard stimulus to actor, target, or both participants."""

    recipient: Literal["actor", "target", "both"]


@dataclass(frozen=True)
class PleasurePeakEffect:
    """Actor-bound peak effect advancing pleasure through canonical writer."""
    pass
