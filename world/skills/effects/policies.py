"""Immutable policy and magnitude records shared by resolved effects.

Part of :mod:`world.skills.effects`; every name is re-exported from the
package root.
"""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from world.skills.effects.passives import EffectAudience, _known_buff_keys

class StateMagnitudeSubject(StrEnum):
    """Subject whose state ordinal determines the magnitude."""

    ACTOR = "actor"
    TARGET = "target"


_SUPPORTED_MAGNITUDE_FIELDS = frozenset({"arousal", "effective_exposure", "exposure"})


@dataclass(frozen=True)
class StateMagnitude:
    """Bounded state-derived magnitude from an explicitly declared subject and field."""

    subject: StateMagnitudeSubject
    field: str
    base: float
    per_ordinal: float
    maximum: float | None = None
    marker: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.subject, str):
            try:
                subj = StateMagnitudeSubject(self.subject)
            except ValueError as error:
                raise ValueError(
                    f"invalid StateMagnitude subject {self.subject!r}; "
                    f"must be one of {list(StateMagnitudeSubject)}"
                ) from error
            object.__setattr__(self, "subject", subj)
        elif not isinstance(self.subject, StateMagnitudeSubject):
            raise ValueError(
                f"StateMagnitude subject must be a StateMagnitudeSubject, got {self.subject!r}"
            )

        if not isinstance(self.field, str) or self.field not in _SUPPORTED_MAGNITUDE_FIELDS:
            raise ValueError(
                f"unsupported StateMagnitude field {self.field!r}; "
                f"must be one of {sorted(_SUPPORTED_MAGNITUDE_FIELDS)}"
            )

        for name, val in (("base", self.base), ("per_ordinal", self.per_ordinal)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"StateMagnitude {name} must be a non-negative finite number, got {val!r}")
            f_val = float(val)
            if not isfinite(f_val) or f_val < 0:
                raise ValueError(f"StateMagnitude {name} must be a non-negative finite number, got {val!r}")
            object.__setattr__(self, name, f_val)

        if self.maximum is not None:
            if isinstance(self.maximum, bool) or not isinstance(self.maximum, (int, float)):
                raise ValueError(f"StateMagnitude maximum must be a finite number >= base, got {self.maximum!r}")
            f_max = float(self.maximum)
            if not isfinite(f_max) or f_max < self.base:
                raise ValueError(
                    f"StateMagnitude maximum must be a finite number >= base ({self.base}), got {self.maximum!r}"
                )
            object.__setattr__(self, "maximum", f_max)

        if self.marker is not None:
            if isinstance(self.marker, bool) or not isinstance(self.marker, str) or not self.marker.strip():
                raise ValueError(
                    f"StateMagnitude marker must be a non-empty string, got {self.marker!r}"
                )
            if self.maximum is None:
                raise ValueError("StateMagnitude with marker requires maximum to be specified")
            if self.maximum <= 0:
                raise ValueError(
                    f"StateMagnitude with marker requires positive maximum, got {self.maximum!r}"
                )


@dataclass(frozen=True)
class InteractionPolicy:
    """Immutable contact and interaction metadata for skill effects."""

    contact: bool = True
    distinct_participants: bool = True
    target_capable: bool = False
    resistible: bool = False

    def __post_init__(self) -> None:
        for name in ("contact", "distinct_participants", "target_capable", "resistible"):
            val = getattr(self, name)
            if not isinstance(val, bool):
                raise ValueError(f"InteractionPolicy {name} must be a bool, got {val!r}")


@dataclass(frozen=True)
class DamagePolicy:
    """Immutable conditional damage policy metadata for a skill effect.

    When predicate is non-empty, matching targets receive the attack_multiplier
    (applied once even if multiple predicate facts match) and bypass defense
    if bypass_defense is True.

    max_hp_fraction is a devastation rider: when non-zero, floor(max_hp * max_hp_fraction)
    is added after defense subtraction on any successful hit, regardless of whether
    a predicate is configured or matched. On a miss, zero total damage is dealt.

    Extra strikes may be configured in two shapes:
    - Evidence-conditional: repeat_when names a recognized action evidence kind,
      requiring extra_strikes=1 (resolved only when the target carries fresh evidence).
    - Unconditional: extra_strikes in (1, 2) with repeat_when=None (always resolves the
      extra strikes on successful action resolution).
    In either shape, total_strikes = 1 + extra_strikes when active (evidence-conditional
    stays exactly one; predicate-free admits one or two; total = 1 + N).
    """

    predicate: tuple[str, ...] = ()
    attack_multiplier: float = 1.0
    bypass_defense: bool = False
    unconditional_defense_bypass: bool = False
    max_hp_fraction: float = 0.0
    repeat_when: str | None = None
    extra_strikes: int = 0

    def __init__(
        self,
        predicate: Sequence[str] | None = None,
        attack_multiplier: float = 1.0,
        bypass_defense: bool = False,
        max_hp_fraction: float = 0.0,
        *,
        target_facts: Sequence[str] | None = None,
        conditional_multiplier: float | None = None,
        conditional_defense_bypass: bool | None = None,
        unconditional_defense_bypass: bool = False,
        repeat_when: str | None = None,
        extra_strikes: int | None = None,
    ) -> None:
        if predicate is None and target_facts is not None:
            predicate = target_facts
        elif predicate is None:
            predicate = ()

        if conditional_multiplier is not None:
            attack_multiplier = conditional_multiplier
        if conditional_defense_bypass is not None:
            bypass_defense = conditional_defense_bypass

        if extra_strikes is None:
            extra_strikes = 1 if repeat_when is not None else 0

        object.__setattr__(self, "predicate", predicate)
        object.__setattr__(self, "attack_multiplier", attack_multiplier)
        object.__setattr__(self, "bypass_defense", bypass_defense)
        object.__setattr__(self, "unconditional_defense_bypass", unconditional_defense_bypass)
        object.__setattr__(self, "max_hp_fraction", max_hp_fraction)
        object.__setattr__(self, "repeat_when", repeat_when)
        object.__setattr__(self, "extra_strikes", extra_strikes)
        self.__post_init__()

    @property
    def target_facts(self) -> tuple[str, ...]:
        return self.predicate

    @property
    def conditional_multiplier(self) -> float:
        return self.attack_multiplier

    def __post_init__(self) -> None:
        if isinstance(self.predicate, (str, bytes)) or not isinstance(
            self.predicate, Iterable
        ):
            raise ValueError(
                f"DamagePolicy predicate must be a sequence of strings, got {type(self.predicate).__name__}"
            )
        from world.lore.elements import ELEMENT_REGISTRY
        from world.lore.combat_traits import COMBAT_TRAITS_VOCABULARY

        validated_predicate: list[str] = []
        seen: set[str] = set()
        for entry in self.predicate:
            if not isinstance(entry, str):
                raise ValueError(
                    f"DamagePolicy predicate entry must be a string, got {type(entry).__name__}: {entry!r}"
                )
            if entry in seen:
                raise ValueError(
                    f"duplicate DamagePolicy predicate entry: {entry!r}"
                )
            if ":" in entry:
                parts = entry.split(":", 1)
                if parts[0] == "buff":
                    if parts[1] not in _known_buff_keys():
                        raise ValueError(
                            f"unknown DamagePolicy predicate buff definition {parts[1]!r}; must be in BUFF_DEFINITIONS"
                        )
                else:
                    raise ValueError(
                        f"DamagePolicy predicate entries must be bare registry keys, not namespaced: {entry!r}"
                    )
            else:
                if entry not in ELEMENT_REGISTRY and entry not in COMBAT_TRAITS_VOCABULARY:
                    raise ValueError(
                        f"unknown DamagePolicy predicate fact {entry!r}; must be in ELEMENT_REGISTRY or COMBAT_TRAITS_VOCABULARY"
                    )
            seen.add(entry)
            validated_predicate.append(entry)
        canon_pred = tuple(validated_predicate)
        object.__setattr__(self, "predicate", canon_pred)

        if isinstance(self.attack_multiplier, bool) or not isinstance(
            self.attack_multiplier, (int, float)
        ):
            raise ValueError(
                f"DamagePolicy attack_multiplier must be a finite positive number, got {self.attack_multiplier!r}"
            )
        try:
            mult = float(self.attack_multiplier)
        except OverflowError as error:
            raise ValueError(
                f"DamagePolicy attack_multiplier must be a finite positive number, got {self.attack_multiplier!r}"
            ) from error
        if not isfinite(mult) or mult <= 0:
            raise ValueError(
                f"DamagePolicy attack_multiplier must be a finite positive number, got {self.attack_multiplier!r}"
            )
        object.__setattr__(self, "attack_multiplier", mult)

        if not isinstance(self.bypass_defense, bool):
            raise ValueError(
                f"DamagePolicy bypass_defense must be a bool, got {type(self.bypass_defense).__name__}"
            )

        if not isinstance(self.unconditional_defense_bypass, bool):
            raise ValueError(
                f"DamagePolicy unconditional_defense_bypass must be a bool, got {type(self.unconditional_defense_bypass).__name__}"
            )

        if self.unconditional_defense_bypass and self.bypass_defense:
            raise ValueError(
                "DamagePolicy cannot declare both bypass_defense=True and unconditional_defense_bypass=True"
            )

        if isinstance(self.max_hp_fraction, bool) or not isinstance(
            self.max_hp_fraction, (int, float)
        ):
            raise ValueError(
                f"DamagePolicy max_hp_fraction must be a finite number between 0.0 and 1.0, got {self.max_hp_fraction!r}"
            )
        try:
            frac = float(self.max_hp_fraction)
        except OverflowError as error:
            raise ValueError(
                f"DamagePolicy max_hp_fraction must be a finite number between 0.0 and 1.0, got {self.max_hp_fraction!r}"
            ) from error
        if not isfinite(frac) or not (0.0 <= frac <= 1.0):
            raise ValueError(
                f"DamagePolicy max_hp_fraction must be a finite number between 0.0 and 1.0, got {self.max_hp_fraction!r}"
            )
        object.__setattr__(self, "max_hp_fraction", frac)

        if not canon_pred:
            if mult != 1.0:
                raise ValueError(
                    f"DamagePolicy specifies attack_multiplier={mult} but has an empty predicate"
                )

        if self.repeat_when is not None:
            if not isinstance(self.repeat_when, str):
                raise ValueError(
                    f"DamagePolicy repeat_when must be a string or None, got {type(self.repeat_when).__name__}"
                )
            from world.lore.action_evidence import EVIDENCE_KINDS

            if self.repeat_when not in EVIDENCE_KINDS:
                raise ValueError(
                    f"unknown DamagePolicy repeat_when predicate {self.repeat_when!r}; "
                    f"must be in {sorted(EVIDENCE_KINDS)}"
                )

        if isinstance(self.extra_strikes, bool) or not isinstance(self.extra_strikes, int):
            raise ValueError(
                f"DamagePolicy extra_strikes must be an int, got {type(self.extra_strikes).__name__}"
            )
        if self.extra_strikes not in (0, 1, 2):
            raise ValueError(
                f"DamagePolicy extra_strikes must be in (0, 1, 2), got {self.extra_strikes}"
            )
        if self.repeat_when is not None and self.extra_strikes != 1:
            raise ValueError(
                "DamagePolicy with repeat_when requires extra_strikes=1"
            )


@dataclass(frozen=True)
class EffectPolicy:
    """Immutable per-occurrence policy metadata for a skill effect."""

    coefficient: float = 1.0
    audience: EffectAudience = EffectAudience.SELECTED
    damage: DamagePolicy | None = None
    magnitude: StateMagnitude | None = None
    interaction: InteractionPolicy | None = None
    stimulus_bonus: StateMagnitude | None = None
    transfer: "GaugeTransferPolicy | None" = None
    audience_condition: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.coefficient, bool) or not isinstance(
            self.coefficient, (int, float)
        ):
            raise ValueError(
                f"EffectPolicy coefficient must be a finite positive number, got {self.coefficient!r}"
            )
        try:
            val = float(self.coefficient)
        except OverflowError as error:
            raise ValueError(
                f"EffectPolicy coefficient must be a finite positive number, got {self.coefficient!r}"
            ) from error
        if not isfinite(val) or val <= 0:
            raise ValueError(
                f"EffectPolicy coefficient must be a finite positive number, got {self.coefficient!r}"
            )
        object.__setattr__(self, "coefficient", val)

        if isinstance(self.audience, bool) or not isinstance(
            self.audience, (str, EffectAudience)
        ):
            raise ValueError(
                f"EffectPolicy audience must be an EffectAudience, got {self.audience!r}"
            )
        try:
            aud = EffectAudience(self.audience)
        except ValueError as error:
            raise ValueError(
                f"EffectPolicy audience must be an EffectAudience, got {self.audience!r}"
            ) from error
        object.__setattr__(self, "audience", aud)

        if self.damage is not None and not isinstance(self.damage, DamagePolicy):
            raise ValueError(
                f"EffectPolicy damage must be a DamagePolicy or None, got {self.damage!r}"
            )
        if self.magnitude is not None and not isinstance(self.magnitude, StateMagnitude):
            raise ValueError(
                f"EffectPolicy magnitude must be a StateMagnitude or None, got {self.magnitude!r}"
            )
        if self.interaction is not None and not isinstance(self.interaction, InteractionPolicy):
            raise ValueError(
                f"EffectPolicy interaction must be an InteractionPolicy or None, got {self.interaction!r}"
            )
        if self.stimulus_bonus is not None and not isinstance(self.stimulus_bonus, StateMagnitude):
            raise ValueError(
                f"EffectPolicy stimulus_bonus must be a StateMagnitude or None, got {self.stimulus_bonus!r}"
            )
        if self.transfer is not None and not isinstance(self.transfer, GaugeTransferPolicy):
            raise ValueError(
                f"EffectPolicy transfer must be a GaugeTransferPolicy or None, got {self.transfer!r}"
            )
        if self.audience_condition is not None:
            raw_cond = self.audience_condition
            valid_facts = {"mp_max_zero", "mp_positive"}
            if isinstance(raw_cond, str):
                if raw_cond not in valid_facts:
                    raise ValueError(
                        f"unknown audience_condition fact {raw_cond!r}; must be in {sorted(valid_facts)}"
                    )
                canon_cond = raw_cond
            elif isinstance(raw_cond, Mapping):
                unknown = set(raw_cond.keys()) - valid_facts
                if unknown:
                    raise ValueError(
                        f"unknown audience_condition fact {sorted(unknown)[0]!r}; must be in {sorted(valid_facts)}"
                    )
                active = [k for k, v in raw_cond.items() if v]
                if "mp_max_zero" in active and "mp_positive" in active:
                    raise ValueError(
                        "contradictory audience_condition: cannot declare both mp_max_zero and mp_positive"
                    )
                if not active:
                    canon_cond = None
                else:
                    canon_cond = active[0]
            elif isinstance(raw_cond, Iterable) and not isinstance(raw_cond, (bytes,)):
                cond_list = list(raw_cond)
                unknown = set(cond_list) - valid_facts
                if unknown:
                    raise ValueError(
                        f"unknown audience_condition fact {sorted(unknown)[0]!r}; must be in {sorted(valid_facts)}"
                    )
                if "mp_max_zero" in cond_list and "mp_positive" in cond_list:
                    raise ValueError(
                        "contradictory audience_condition: cannot declare both mp_max_zero and mp_positive"
                    )
                if not cond_list:
                    canon_cond = None
                else:
                    canon_cond = cond_list[0]
            else:
                raise ValueError(
                    f"audience_condition must be a string, mapping, or sequence, got {type(raw_cond).__name__}"
                )
            object.__setattr__(self, "audience_condition", canon_cond)


@dataclass(frozen=True)
class GaugeTransferPolicy:
    """Immutable per-occurrence policy metadata for a gauge transfer effect."""

    caster_recovery_share: float = 0.0
    restore_bonus_per_stack: tuple[tuple[str, int], ...] = ()

    def __init__(
        self,
        caster_recovery_share: float = 0.0,
        restore_bonus_per_stack: Any = (),
    ) -> None:
        object.__setattr__(self, "caster_recovery_share", caster_recovery_share)
        object.__setattr__(self, "restore_bonus_per_stack", restore_bonus_per_stack)
        self.__post_init__()

    def __post_init__(self) -> None:
        if isinstance(self.caster_recovery_share, bool) or not isinstance(
            self.caster_recovery_share, (int, float)
        ):
            raise ValueError(
                f"GaugeTransferPolicy caster_recovery_share must be a finite number between 0.0 and 1.0, got {self.caster_recovery_share!r}"
            )
        try:
            share = float(self.caster_recovery_share)
        except OverflowError as error:
            raise ValueError(
                f"GaugeTransferPolicy caster_recovery_share must be a finite number between 0.0 and 1.0, got {self.caster_recovery_share!r}"
            ) from error
        if not isfinite(share) or not (0.0 <= share <= 1.0):
            raise ValueError(
                f"GaugeTransferPolicy caster_recovery_share must be a finite number between 0.0 and 1.0, got {self.caster_recovery_share!r}"
            )
        object.__setattr__(self, "caster_recovery_share", share)

        valid_keys = _known_buff_keys()

        canon_bonuses: list[tuple[str, int]] = []
        raw_bonus = self.restore_bonus_per_stack
        if raw_bonus is None:
            raw_bonus = ()
        if isinstance(raw_bonus, Mapping):
            items = list(raw_bonus.items())
        elif (
            isinstance(raw_bonus, (list, tuple))
            and len(raw_bonus) == 2
            and isinstance(raw_bonus[0], (list, tuple, set, frozenset))
        ):
            keys, amount = raw_bonus
            items = [(k, amount) for k in keys]
        elif isinstance(raw_bonus, Iterable) and not isinstance(raw_bonus, (str, bytes)):
            items = list(raw_bonus)
        else:
            raise ValueError(
                f"GaugeTransferPolicy restore_bonus_per_stack must be an iterable or mapping, got {type(raw_bonus).__name__}"
            )

        for item in items:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                key, amt = item
            else:
                raise ValueError(
                    f"restore_bonus_per_stack entry must be a (key, amount) pair, got {item!r}"
                )
            if not isinstance(key, str):
                raise ValueError(f"buff key must be a string, got {key!r}")
            if key not in valid_keys:
                raise ValueError(
                    f"unknown buff key {key!r} in restore_bonus_per_stack; must exist in buff definitions"
                )
            if isinstance(amt, bool) or not isinstance(amt, int) or amt <= 0:
                raise ValueError(
                    f"restore_bonus_per_stack amount must be a positive integer, got {amt!r}"
                )
            canon_bonuses.append((key, amt))

        object.__setattr__(self, "restore_bonus_per_stack", tuple(canon_bonuses))


@dataclass(frozen=True)
class ResolvedEffect:
    """Trusted server-bound effect context synthesized during action resolution."""

    policy: EffectPolicy
    source_skill: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, EffectPolicy):
            raise ValueError(
                f"ResolvedEffect policy must be an EffectPolicy, got {self.policy!r}"
            )
