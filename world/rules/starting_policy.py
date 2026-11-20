"""The single starting-allocation policy shared by every creation surface.

One deterministic resolver turns immutable lore bands into the exact
allocation policy a player sees: the lore bounds of every axis, the number of
points its cap admits, the pre-modifier value that cap yields, and the exact
point budget. The deterministic creation preflight, the draft wizard, the
creation panel presenter, the text wizard, the generative proposal validator,
preset activation and companion construction all read this module, so no
surface can carry its own copy of the arithmetic.

The policy is selected by the resolved race alone: a non-elf profile spends
one point per stat unit against the floor-of-half-spans budget, while an elf
spends points against a budget derived from its three physical spans and
interpolates magic power up to the creation cap *before* the subrace modifiers
apply. Custom creation and preset cards therefore share one policy.

The module is deliberately dependency-narrow: the immutable lore registries and
the pure identity seam only, no database, no Evennia import, and no module-level
mutable state, so the generative proposal validator can check every proposal
against the same policy activation enforces (the transport-boundary contract's
read-only exemption).
"""

from __future__ import annotations

from dataclasses import dataclass

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY, StatModifiers
from world.rules.creation_identity import resolve_race_and_subrace

# The seven allocatable starting axes, in the order every surface publishes.
# Mirrors ``world.rules.traits.GAUGE_KEYS + STATIC_KEYS`` (locked by a parity
# test in ``world/rules/tests/test_character_creation``); duplicated here so
# this policy module stays importable from the generative layer without pulling
# the trait-handler module.
GAUGE_AXES = ("hp", "mp", "sp")
PHYSICAL_AXES = ("atk_phys", "agility", "defense")
ALLOCATABLE_AXES = GAUGE_AXES + PHYSICAL_AXES + ("magic_power",)

ELF_RACE_KEY = "elf"

#: The elf magic-power ceiling. It is the same number as the race band's
#: ceiling: creation interpolates up to it and every authored value is bounded
#: by it. The band, not this constant, is the single source of the number.
ELF_MAGIC_CREATION_CAP = 200


def _half_up(numerator: int, denominator: int) -> int:
    """Divide two nonnegative integers rounding an exact half upward."""
    return (2 * numerator + denominator) // (2 * denominator)


@dataclass(frozen=True)
class StartingAxis:
    """One allocatable axis: its lore bounds and its exact point policy."""

    axis: str
    minimum: int
    maximum: int
    point_cap: int
    value_at_cap: int

    def value_for(self, points: int) -> int:
        """The pre-modifier value this many points produce."""
        if self.point_cap == 0:
            return self.minimum
        return self.minimum + _half_up(
            (self.value_at_cap - self.minimum) * points, self.point_cap
        )


@dataclass(frozen=True)
class StartingProfile:
    """One (race, subrace) profile: allocation policy plus static modifiers."""

    race: str
    subrace: str | None
    axes: tuple[StartingAxis, ...]
    static_modifiers: StatModifiers
    budget: int

    def axes_dict(self) -> dict[str, StartingAxis]:
        return {axis.axis: axis for axis in self.axes}


def _axis_for(
    axis: str,
    bounds: tuple[int, int],
    *,
    point_cap: int,
    value_at_cap: int,
) -> StartingAxis:
    lower, upper = bounds
    return StartingAxis(
        axis=axis,
        minimum=lower,
        maximum=upper,
        point_cap=point_cap,
        value_at_cap=value_at_cap,
    )


def _raw_increment_axes(
    bounds: dict[str, tuple[int, int]]
) -> tuple[StartingAxis, ...]:
    """Every axis spends one point per stat unit (every non-elf profile)."""
    return tuple(
        _axis_for(
            axis,
            bounds[axis],
            point_cap=bounds[axis][1] - bounds[axis][0],
            value_at_cap=bounds[axis][1],
        )
        for axis in ALLOCATABLE_AXES
    )


def _elf_axes(
    bounds: dict[str, tuple[int, int]]
) -> tuple[StartingAxis, ...]:
    """The elf policy: physical builds spend, magic interpolates.

    The gauges are fixed for an elf (their lore floor is the only value), the
    three physical axes keep the raw increment, and magic power interpolates
    from its lore floor to the creation cap across the whole budget. A profile
    whose physical spans are all zero has no budget, so magic admits no points
    and stays at its floor; a lore floor at or above the cap keeps the cap at
    the floor (``value_at_cap`` must stay inside the lore bounds every
    validator checks).
    """
    budget = sum(bounds[axis][1] - bounds[axis][0] for axis in PHYSICAL_AXES)
    axes: list[StartingAxis] = []
    for axis in ALLOCATABLE_AXES:
        if axis in GAUGE_AXES:
            axes.append(
                _axis_for(axis, bounds[axis], point_cap=0, value_at_cap=bounds[axis][0])
            )
        elif axis in PHYSICAL_AXES:
            axes.append(
                _axis_for(
                    axis,
                    bounds[axis],
                    point_cap=bounds[axis][1] - bounds[axis][0],
                    value_at_cap=bounds[axis][1],
                )
            )
        else:
            lower, upper = bounds[axis]
            value_at_cap = lower if budget == 0 else max(
                lower, min(ELF_MAGIC_CREATION_CAP, upper)
            )
            axes.append(
                _axis_for(
                    axis, bounds[axis], point_cap=budget, value_at_cap=value_at_cap
                )
            )
    return tuple(axes)


def resolve_starting_profile(
    race_key: str, subrace_key: str | None = None
) -> StartingProfile:
    """Resolve one allocation policy entirely from immutable lore.

    The selected race decides the policy: a non-elf profile spends raw
    increments against the floor-of-half-spans budget, while an elf spends a
    budget equal to its three physical spans and converts magic points to
    magic power. Callers do not choose a policy; custom creation, preset
    activation and companion construction all resolve the same race-derived
    profile.
    """
    race_key, subrace_key = resolve_race_and_subrace(race_key, subrace_key)
    race = RACE_REGISTRY[race_key]
    subrace = SUBRACE_REGISTRY[subrace_key] if subrace_key else None

    bounds: dict[str, tuple[int, int]] = {
        key: getattr(race.vital_baseline, key) for key in GAUGE_AXES
    }
    bounds.update(
        {key: getattr(race.static_baseline, key) for key in PHYSICAL_AXES + ("magic_power",)}
    )
    if subrace and subrace.vital_overrides:
        bounds.update(subrace.vital_overrides)
    modifiers = subrace.static_modifiers if subrace else StatModifiers()

    if race_key == ELF_RACE_KEY:
        axes = _elf_axes(bounds)
        budget = sum(bounds[axis][1] - bounds[axis][0] for axis in PHYSICAL_AXES)
    else:
        axes = _raw_increment_axes(bounds)
        budget = sum(upper - lower for lower, upper in bounds.values()) // 2
    return StartingProfile(race_key, subrace_key, axes, modifiers, budget)
