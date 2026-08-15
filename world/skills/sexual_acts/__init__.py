"""The sexual act catalogue sidecar registry.

Each line module exports one tuple constant of rows built by
``_act_family()``; this package merges every line's rows into
``SEXUAL_ACT_REGISTRY`` and registers each paired ``SkillDef`` into the
shared ``world.skills.registry.SKILL_REGISTRY`` under the same key. The
registration is deliberately an update to that dict, not a replacement:
``world.skills.registry`` finishes constructing ``SKILL_REGISTRY`` before
this module's import starts, so any later import of this package adds the
act rows without racing the base registry.
"""

from collections.abc import Iterable, Mapping

from world.skills.effects import SexualMasteryEffect
from world.skills.registry import SKILL_REGISTRY, SkillDef

from world.skills.sexual_acts._builder import SexualActDef, _act_family

from . import combat, divine, interspecies, partner, shame, solo

SEXUAL_ACT_REGISTRY: dict[str, SexualActDef] = {}


def _register_rows(
    rows: Iterable[tuple[SkillDef, SexualActDef]],
) -> None:
    """Register one batch of paired rows into both registries.

    Fails closed on any key disagreement, any duplicate within the
    catalogue, and any collision with a pre-existing ``SKILL_REGISTRY``
    entry — a catalogue row must never silently overwrite an existing
    skill definition.
    """
    for skill, act in rows:
        if skill.key != act.key:
            raise ValueError(
                f"act row keys disagree: SkillDef {skill.key!r} vs "
                f"SexualActDef {act.key!r}"
            )
        if act.key in SEXUAL_ACT_REGISTRY:
            raise ValueError(f"duplicate act key {act.key!r}")
        if skill.key in SKILL_REGISTRY:
            raise ValueError(
                f"act key {skill.key!r} collides with an existing "
                "SKILL_REGISTRY entry"
            )
        SEXUAL_ACT_REGISTRY[act.key] = act
        SKILL_REGISTRY[skill.key] = skill


_register_rows(
    (
        *solo.SOLO_ACTS,
        *shame.SHAME_ACTS,
        *partner.PARTNER_ACTS,
        *combat.COMBAT_ACTS,
        *interspecies.INTERSPECIES_ACTS,
        *divine.DIVINE_ACTS,
    )
)


def unlocked_act_keys_for(
    owned_keys: Iterable[str],
    counter_values: Mapping[str, int],
) -> frozenset[str]:
    """Return every catalogue key the given ownership and counters unlock.

    The single implementation of both unlock rules — the per-act counter
    threshold gate and the ``SexualMasteryEffect`` blanket unlock — so the
    materialized ``SexualState`` query and the no-create ``owned_keys()``
    read can never drift. ``counter_values`` may omit names: an omitted
    counter reads as zero, which is exactly an unmaterialized entity's
    state. Direct ownership is read from the passed ``owned_keys`` set only;
    conferred grants never satisfy the blanket unlock.

    The ``if key in SKILL_REGISTRY`` guard must stay immediately after the
    first ``for`` clause: generator clauses run in written order, so placing
    the guard last would dereference ``SKILL_REGISTRY[key]`` before checking
    it, raising ``KeyError`` for any innate key (such as ``flee``, which
    registers only as ``world.rules.disengage``'s import side effect) that
    the owned set names.
    """
    mastery = any(
        isinstance(effect, SexualMasteryEffect)
        for key in owned_keys
        if key in SKILL_REGISTRY
        for effect in SKILL_REGISTRY[key].parsed_effects
    )
    if mastery:
        return frozenset(SEXUAL_ACT_REGISTRY)
    return frozenset(
        key
        for key, act in SEXUAL_ACT_REGISTRY.items()
        if all(
            counter_values.get(counter, 0) >= threshold
            for counter, threshold in act.unlock.items()
        )
    )


__all__ = [
    "SEXUAL_ACT_REGISTRY",
    "SexualActDef",
    "_act_family",
    "_register_rows",
    "unlocked_act_keys_for",
]
