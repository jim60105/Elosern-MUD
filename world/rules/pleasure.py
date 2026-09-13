"""The shared pleasure writers (item-effect-model design §5.6).

Every deterministic caller that raises or zeroes an entity's pleasure applies
its change through one of the two functions in this module — the signed gain
with its arousal-coupled cascade, and the forced reset to zero with none. The
module deliberately imports nothing from ``world.rules.action``: a caller that
is not a cast (an item, a future non-skill effect) must reach the canonical
writers without dragging in the cast pipeline.

The two writers stay separate because their semantics genuinely differ:
routing a zeroing through ``apply_pleasure_gain(entity, -current)`` would run
the gain path's ``was_at_critical_point`` branch and push a target sitting at
接近 into 進行中 — the opposite of what draining someone's pleasure to zero
means (design D2b). The only other sanctioned deterministic pleasure writers
are the rulebook engine (``sexual_transitions._apply_then``'s
``bounded_counter`` branch) and the clock decay (``sexual_state.decay_tick``);
neither is an effect-applier entry point.
"""

from typing import Any

from world.rules.sexual_act_effects import _EFFECTS_CONFIG
from world.rules.sexual_state import _apply_climax_phase_set


def apply_pleasure_gain(entity: Any, gain: int) -> None:
    """Apply one participant's pleasure gain and the arousal-coupled cascade.

    Replicates two ``sexual.yaml`` rules directly — ``wetness_follows_arousal``
    and the ``climax_gate``/``climax_phase_critical_point_to_in_progress``
    pair — because both are conditioned on a change ``apply_event()``'s own
    snapshot must observe within its own call, which a pleasure gain applied
    outside ``apply_event()`` cannot produce. The captures below must stay the
    first statements: the wetness bump compares the arousal ordinal before and
    after the mutation, the two-step 未達→接近→進行中 semantic depends on
    reading the pre-mutation climax phase before either transition runs, and
    the extension trigger fires only for a participant already in 進行中 when
    the effect applies — a participant this very call pushes from 接近 into
    進行中 has just started climaxing, it has not received a qualifying
    extension stimulus (pleasure-model design §3.2/§3.4).

    The extension trigger compares against ``gain``, the uncapped computed
    value, not the clamped applied delta: ``pleasure`` self-clamps at 100, so
    an entity already in 進行中 would almost never stage an extension if the
    post-clamp delta were the gate. ``_apply_climax_phase_set`` no-ops on any
    edge outside ``_VALID_CLIMAX_TRANSITIONS``, so both transition calls are
    unconditionally safe to attempt.
    """
    pre_arousal_ordinal = entity.sexual.arousal.value
    was_at_critical_point = entity.sexual.climax_phase.level == "接近"
    was_in_progress = entity.sexual.climax_phase.level == "進行中"

    entity.sexual.pleasure.base += gain

    if entity.sexual.arousal.value > pre_arousal_ordinal:
        entity.sexual.wetness.value += 1
    if entity.sexual.arousal.level == "極限":
        _apply_climax_phase_set(entity, "接近")
    if was_at_critical_point:
        _apply_climax_phase_set(entity, "進行中")

    if was_in_progress and gain >= _EFFECTS_CONFIG.climax_extension_threshold:
        entity.sexual.stage_climax_extension()


def zero_pleasure(target: Any) -> None:
    """Set the target's pleasure gauge to zero."""
    target.sexual.pleasure.base = 0
