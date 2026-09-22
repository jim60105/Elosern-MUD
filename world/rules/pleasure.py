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

import zlib
from typing import Any

from world.rules.sexual_act_effects import _EFFECTS_CONFIG
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.skill_ownership import owns_stored_skill


def apply_pleasure_gain(
    entity: Any, gain: int, *, stimulus: bool = True
) -> None:
    """Apply one participant's pleasure gain and the arousal-coupled cascade.

    ``stimulus=False`` marks a non-stimulus gauge movement (the 聖女容器
    聖光涓流 idle step, saintess-vessel D2b): the gauge write and the
    wetness-on-band-up cascade stay, while BOTH climax branches are skipped
    — the 接近→進行中 / 極限→接近 edges and the extension staging. Without
    it a holder legitimately parked at 接近 after a 極限 spike (decay never
    clears that phase) would be promoted into 進行中 by a cosmetic +1 at
    pleasure 15, i.e. the idle trickle would autonomously open a climax
    below the 85 gate. Every stimulus caller keeps the default; only the
    trickle opts out.

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
    extension stimulus (pleasure-model design §3.2/§3.4). ``stimulus=False``
    short-circuits both branches below.

    The extension trigger compares against ``gain``, the uncapped computed
    value, not the clamped applied delta: ``pleasure`` self-clamps at 100, so
    an entity already in 進行中 would almost never stage an extension if the
    post-clamp delta were the gate. ``_apply_climax_phase_set`` no-ops on any
    edge outside ``_VALID_CLIMAX_TRANSITIONS``, so both transition calls are
    unconditionally safe to attempt.

    A negative gain (a pleasure-reduction effect, item-effect-model design
    §5.6) mutates only the gauge: the climax-phase edges are skipped, because
    the ``was_at_critical_point`` branch as written fires on any call — a
    reduction landing on a participant at 接近 must not walk that participant
    into 進行中 (design D2b: suppressing arousal must not advance the climax
    state machine). ``gain == 0`` keeps the full path; the shipped
    divine-sexual-arts two-call trick deliberately re-runs the pre/post-mutation
    check with a zero gain to walk a second edge.
    """
    pre_arousal_ordinal = entity.sexual.arousal.value
    was_at_critical_point = entity.sexual.climax_phase.level == "接近"
    was_in_progress = entity.sexual.climax_phase.level == "進行中"

    entity.sexual.pleasure.base += gain

    if gain >= 0:
        if entity.sexual.arousal.value > pre_arousal_ordinal:
            entity.sexual.wetness.value += 1
        if stimulus:
            if entity.sexual.arousal.level == "極限":
                _apply_climax_phase_set(entity, "接近")
            if was_at_critical_point:
                _apply_climax_phase_set(entity, "進行中")
    if stimulus and was_in_progress and gain >= _EFFECTS_CONFIG.climax_extension_threshold:
        entity.sexual.stage_climax_extension()


def zero_pleasure(target: Any) -> None:
    """Set the target's pleasure gauge to zero."""
    target.sexual.pleasure.base = 0


# The idle band the 聖女容器 (saintess_vessel) holder's gauge is pinned to:
# 微興奮 floor (15) through the 中等 ceiling (59). Below the floor the step
# pins up; inside the band it takes one deterministic ±1 step; at or above
# the 高度 floor (60) it no-ops — ordinary decay owns the descent and the
# step re-arms on band re-entry.
_VESSEL_BAND_FLOOR = 15
_VESSEL_BAND_CEILING = 59


def saintess_trickle_step(entity: Any, resulting_tick: int) -> None:
    """Apply the 聖光涓流 idle fluctuation once for one world-clock advance.

    Called by ``world.rules.clock.advance`` exactly once per advance (NOT per
    settlement quantum), non-combat sources only, AFTER the buff/decay
    settlement loop and outside its pending-work guard — a fully idle holder
    has no other pending work and must still be pinned. Every write goes
    through ``apply_pleasure_gain`` with ``stimulus=False``: the gauge write
    and the arousal-coupled wetness cascade behave as for any stimulus, while
    the climax-phase edges never fire — the idle trickle must not open a
    climax below the 85 gate for a holder parked at 接近.

    The plus/minus direction is a stateless crc32 hash of the entity
    identity AND the full resulting world tick — no RNG, no dice — so an
    advance that fails and is retried recomputes the identical draw (the
    advance transaction has no RNG-state snapshot; dice here would not be
    replay-stable). Raw tick PARITY would be useless here: every shipped
    non-combat advance duration is even (move 30, cast 6, item 6, skip
    9000), so ``resulting_tick % 2`` never changes and the draw would be
    frozen per entity — the hash avalanche over the whole tick is what
    makes successive advances alternate. A clamped step whose delta
    collapses to zero (a − draw at the floor, a + draw at the ceiling)
    issues no writer call at all.
    """
    if not owns_stored_skill(entity, "saintess_vessel"):
        return
    pleasure = entity.sexual.pleasure.base
    if pleasure < _VESSEL_BAND_FLOOR:
        apply_pleasure_gain(
            entity, _VESSEL_BAND_FLOOR - pleasure, stimulus=False
        )
        return
    if pleasure > _VESSEL_BAND_CEILING:
        return
    identity = str(getattr(entity, "id", None) or getattr(entity, "key", entity))
    draw = zlib.crc32(f"{identity}:{resulting_tick}".encode("utf-8")) % 2
    step = 1 if draw else -1
    target = min(_VESSEL_BAND_CEILING, max(_VESSEL_BAND_FLOOR, pleasure + step))
    if target == pleasure:
        return
    apply_pleasure_gain(entity, target - pleasure, stimulus=False)
