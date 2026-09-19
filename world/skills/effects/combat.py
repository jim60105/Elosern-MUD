"""Combat/cleanse/heal/disengage/gauge-transfer effect declarations.

Part of :mod:`world.skills.effects`; every name is re-exported from the
package root.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

@dataclass(frozen=True)
class DamageEffect:
    """Deal damage of one element and school (``physical``/``magic``).

    ``element`` is ``None`` for the reserved ``damage:none:<school>`` token,
    which declares the absence of an element rather than a registry lookup.
    """

    element: str | None
    school: str


@dataclass(frozen=True)
class CleanseEffect:
    """Remove every active debuff-polarity buff from each target.

    The parsed segment is the scope (``cleanse:status`` removes all debuff-
    classified active buffs); selective per-buff cleansing is unbuilt.
    """

    scope: Literal["status"]


@dataclass(frozen=True)
class HealEffect:
    """Restore HP to every resolved target, capped at each target's maximum."""

    shape: Literal["single", "area"]


@dataclass(frozen=True)
class SelfHealEffect:
    """Restore the acting entity's HP, capped at the caster's maximum."""

    basis: Literal["stat", "missing_fraction"] = "stat"
    fraction: float | None = None

    def __post_init__(self) -> None:
        if self.basis == "stat":
            if self.fraction is not None:
                raise ValueError(
                    f"stat self_heal takes no fraction argument, got {self.fraction!r}"
                )
        elif self.basis == "missing_fraction":
            if isinstance(self.fraction, bool) or not isinstance(
                self.fraction, (int, float)
            ):
                raise ValueError(
                    f"missing_fraction must be a number, got {self.fraction!r}"
                )
            frac = float(self.fraction)
            if not isfinite(frac) or not (0.0 < frac <= 1.0):
                raise ValueError(
                    f"missing_fraction must be finite in (0, 1], got {self.fraction!r}"
                )
            object.__setattr__(self, "fraction", frac)
        else:
            raise ValueError(
                f"SelfHealEffect basis must be 'stat' or 'missing_fraction', got {self.basis!r}"
            )

@dataclass(frozen=True)
class DisengageEffect:
    """Attempt a disengage; the mode names the flavor (e.g. ``self``)."""

    mode: str


@dataclass(frozen=True)
class GaugeTransferEffect:
    """A typed gauge transfer effect (drain or restore)."""

    gauge: str
    direction: str
    magnitude_mode: str
    magnitude: float | int | None = None

    def __post_init__(self) -> None:
        if self.gauge not in ("mp", "hp"):
            raise ValueError(
                f"GaugeTransferEffect gauge must be 'mp' or 'hp', got {self.gauge!r} (sp is rejected until a consumer exists)"
            )
        if self.direction not in ("drain", "restore"):
            raise ValueError(
                f"GaugeTransferEffect direction must be 'drain' or 'restore', got {self.direction!r}"
            )
        if self.gauge == "hp" and self.direction != "drain":
            raise ValueError(
                f"hp gauge supports drain only, got {self.direction!r} (HP restoration is the heal effect's exclusive verb)"
            )
        if self.magnitude_mode not in ("fixed", "fraction", "all"):
            raise ValueError(
                f"GaugeTransferEffect magnitude_mode must be 'fixed', 'fraction', or 'all', got {self.magnitude_mode!r}"
            )
        if self.magnitude_mode == "fixed":
            if isinstance(self.magnitude, bool) or not isinstance(self.magnitude, int):
                raise ValueError(
                    f"fixed transfer magnitude must be an integer, got {self.magnitude!r}"
                )
            if self.magnitude <= 0:
                raise ValueError(
                    f"fixed transfer magnitude must be positive, got {self.magnitude!r}"
                )
        elif self.magnitude_mode == "fraction":
            if isinstance(self.magnitude, bool) or not isinstance(self.magnitude, (int, float)):
                raise ValueError(
                    f"fraction transfer magnitude must be a number, got {self.magnitude!r}"
                )
            mag = float(self.magnitude)
            if not isfinite(mag) or not (0.0 < mag <= 1.0):
                raise ValueError(
                    f"fraction transfer magnitude must be finite in (0, 1], got {self.magnitude!r}"
                )
            object.__setattr__(self, "magnitude", mag)
        elif self.magnitude_mode == "all":
            if self.magnitude is not None:
                raise ValueError(
                    f"'all' transfer magnitude mode takes no magnitude argument, got {self.magnitude!r}"
                )
