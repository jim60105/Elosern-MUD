"""The persistent ``SexualState`` handler mounted as ``entity.sexual``."""

from typing import Any

from evennia.contrib.rpg.traits import TraitHandler

from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    BODY_PARTS,
    GENERIC_BODY_PART,
    SENSITIVITY_LEVELS,
)

from world.rules.sexual_state.pleasure import PLEASURE_CONFIG
from world.rules.sexual_state.traits import (
    _ORDERED_FIELDS,
    _STATE_CATEGORY,
    _DerivedArousal,
    _SensitivityProxy,
    _generic_default_baseline,
    build_monster_sexual_baseline,
)
from world.rules.sexual_state.traits import OrderedLevelTrait
from world.rules.sexual_state.lifecycle import _LIFETIME_COUNTER_KEYS


class SexualState:
    """Persistent live handler mounted separately from an entity's base traits."""

    def __init__(self, entity):
        self._entity = entity
        self._traits = TraitHandler(entity, db_attribute_key="sexual_traits")
        self._sensitivity = _SensitivityProxy(self._traits)
        required = {*_ORDERED_FIELDS, "climax_today"}
        if required.issubset(self._traits.all()):
            return

        baseline = entity.db.sexual
        if baseline is not None:
            self._build_from_baseline(baseline)
        else:
            from typeclasses.monsters import Monster

            if isinstance(entity, Monster):
                self._build_from_baseline(build_monster_sexual_baseline())
                self.shame.min = 0
                self.shame.max = 0
                self.shame.value = 0
            else:
                self._build_from_baseline(_generic_default_baseline())

    def _build_from_baseline(self, baseline: dict[str, Any]) -> None:
        for field, levels in _ORDERED_FIELDS.items():
            level = baseline.get(field, levels[0])
            self._traits.add(
                field,
                trait_type="ordered_level",
                levels=levels,
                value=level,
            )
        baseline_level = baseline.get("arousal", AROUSAL_LEVELS[0])
        pleasure_floor = PLEASURE_CONFIG.floor_for_level(baseline_level)
        self._traits.add(
            "pleasure",
            trait_type="counter",
            base=pleasure_floor,
            min=0,
            max=100,
        )
        self._traits.add(
            "climax_today",
            trait_type="counter",
            base=int(baseline.get("climax_today", 0)),
            min=0,
        )
        for key in _LIFETIME_COUNTER_KEYS:
            self._traits.add(
                key,
                trait_type="counter",
                base=0,
                min=0,
            )
        for part, level in baseline.get("sensitivity", {}).items():
            self.sensitivity[part] = level
        self._entity.attributes.add(
            "virgin",
            bool(baseline.get("virgin", True)),
            category=_STATE_CATEGORY,
        )
        self._entity.attributes.add(
            "experience_types",
            frozenset(baseline.get("experience_types", ())),
            category=_STATE_CATEGORY,
        )

    @property
    def arousal(self) -> _DerivedArousal:
        ordinal = PLEASURE_CONFIG.ordinal_for(self.pleasure.value)
        return _DerivedArousal(ordinal, AROUSAL_LEVELS)

    @property
    def pleasure(self):
        """Return the bounded pleasure gauge counter trait (0..100)."""
        return self._traits.pleasure

    @property
    def wetness(self) -> OrderedLevelTrait:
        return self._traits.wetness

    @property
    def shame(self) -> OrderedLevelTrait:
        return self._traits.shame

    @property
    def exposure(self) -> OrderedLevelTrait:
        return self._traits.exposure

    @property
    def climax_phase(self) -> OrderedLevelTrait:
        return self._traits.climax_phase

    @property
    def climax_today(self) -> int:
        return int(self._traits.climax_today.value)

    def record_climax(self) -> None:
        """Increment the daily climax counter."""
        self._traits.climax_today.base += 1

    @property
    def climax_turns(self) -> int:
        """Return the consecutive settlement points spent in 進行中."""
        return int(
            self._entity.attributes.get(
                "climax_turns",
                default=0,
                category=_STATE_CATEGORY,
            )
        )

    @property
    def pending_climax_extension(self) -> int:
        """Return the staged-but-unconsumed climax-extension count."""
        return int(
            self._entity.attributes.get(
                "pending_climax_extension",
                default=0,
                category=_STATE_CATEGORY,
            )
        )

    def stage_climax_extension(self, count: int = 1) -> None:
        """Add ``count`` to the pending extension stage. The sole write path.

        ``count`` must be a positive integer; any other value raises
        ``ValueError`` without changing the counter, so a future act-effect
        caller cannot stage a value the settlement decision would silently
        treat as "no extension staged".
        """
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be a positive integer")
        self._entity.attributes.add(
            "pending_climax_extension",
            self.pending_climax_extension + count,
            category=_STATE_CATEGORY,
        )

    @property
    def masturbation_count(self) -> int:
        """Return the lifetime masturbation occurrence counter."""
        return int(self._traits.masturbation_count.value)

    @property
    def toy_use_count(self) -> int:
        """Return the lifetime toy-use occurrence counter."""
        return int(self._traits.toy_use_count.value)

    @property
    def exposure_act_count(self) -> int:
        """Return the lifetime exposure-act occurrence counter."""
        return int(self._traits.exposure_act_count.value)

    @property
    def watched_count(self) -> int:
        """Return the lifetime watched-while-active occurrence counter."""
        return int(self._traits.watched_count.value)

    @property
    def duo_act_count(self) -> int:
        """Return the lifetime two-person act occurrence counter."""
        return int(self._traits.duo_act_count.value)

    @property
    def group_act_count(self) -> int:
        """Return the lifetime group act occurrence counter."""
        return int(self._traits.group_act_count.value)

    @property
    def hostile_act_count(self) -> int:
        """Return the lifetime act-against-opponent occurrence counter."""
        return int(self._traits.hostile_act_count.value)

    @property
    def restraint_count(self) -> int:
        """Return the lifetime restraint-endurance occurrence counter."""
        return int(self._traits.restraint_count.value)

    @property
    def interspecies_act_count(self) -> int:
        """Return the lifetime interspecies act occurrence counter."""
        return int(self._traits.interspecies_act_count.value)

    @property
    def climax_count(self) -> int:
        """Return the lifetime climax occurrence counter."""
        return int(self._traits.climax_count.value)

    @property
    def climax_extension_count(self) -> int:
        """Return the lifetime climax-extension occurrence counter."""
        return int(self._traits.climax_extension_count.value)

    def record_masturbation(self) -> None:
        """Increment the lifetime masturbation counter by exactly one."""
        self._traits.masturbation_count.base += 1

    def record_toy_use(self) -> None:
        """Increment the lifetime toy-use counter by exactly one."""
        self._traits.toy_use_count.base += 1

    def record_exposure_act(self) -> None:
        """Increment the lifetime exposure-act counter by exactly one."""
        self._traits.exposure_act_count.base += 1

    def record_watched(self) -> None:
        """Increment the lifetime watched-while-active counter by exactly one."""
        self._traits.watched_count.base += 1

    def record_duo_act(self) -> None:
        """Increment the lifetime two-person act counter by exactly one."""
        self._traits.duo_act_count.base += 1

    def record_group_act(self) -> None:
        """Increment the lifetime group act counter by exactly one."""
        self._traits.group_act_count.base += 1

    def record_hostile_act(self) -> None:
        """Increment the lifetime act-against-opponent counter by exactly one."""
        self._traits.hostile_act_count.base += 1

    def record_restraint(self) -> None:
        """Increment the lifetime restraint-endurance counter by exactly one."""
        self._traits.restraint_count.base += 1

    def record_interspecies_act(self) -> None:
        """Increment the lifetime interspecies act counter by exactly one."""
        self._traits.interspecies_act_count.base += 1

    def record_climax_count(self) -> None:
        """Increment the lifetime climax counter by exactly one."""
        self._traits.climax_count.base += 1

    def record_climax_extension(self) -> None:
        """Increment the lifetime climax-extension counter by exactly one."""
        self._traits.climax_extension_count.base += 1

    @property
    def sensitivity(self) -> _SensitivityProxy:
        return self._sensitivity

    def saturate_sensitivity(self) -> None:
        """Pin every resolvable body part's sensitivity to the top level.

        Sets ``SENSITIVITY_LEVELS[-1]`` (敏感異常) on every ``BODY_PARTS``
        member for an ordinary entity, but on only ``GENERIC_BODY_PART`` for
        a ``Monster``: ``resolve_part`` collapses every Monster target to
        that one channel, so seeding named parts it can never resolve to
        would create trait state nothing ever reads. This is the sole write
        path for the saturation effect (divine-sexual-arts-mutators D-2).
        """
        from typeclasses.monsters import Monster

        if isinstance(self._entity, Monster):
            parts = (GENERIC_BODY_PART,)
        else:
            parts = BODY_PARTS
        for part in parts:
            self._sensitivity[part] = SENSITIVITY_LEVELS[-1]

    def clamp_shame_to(self, level: str) -> None:
        """Pin shame's bounds and current value to one level's ordinal.

        Reuses the exact ``OrderedLevelTrait`` bound-setter mechanism
        ``__init__`` applies to a fresh ``Monster``'s ``shame``
        (``min = max = floor``), at the requested level instead. The bound
        setters are not independent: ``min``'s setter requires
        ``0 <= value <= max`` and ``max``'s setter requires
        ``min <= value <= vocabulary_max``, each re-clamping the current
        value into the new range as a side effect. Widening the leading bound
        first is therefore safe in both directions: when the target ordinal
        is at or above the current ``max``, set ``max`` then ``min`` (the
        ``max`` write can never violate its precondition because
        ``current_min <= ordinal`` follows from ``ordinal >= current_max``);
        when it is below the current ``max``, set ``min`` then ``max`` (the
        ``min`` write can never violate its precondition because
        ``ordinal <= current_max`` follows from ``ordinal < current_max``).
        Every reachable prior bound state is covered, matching the mutator's
        general contract rather than only the 成癮 call this line ships.

        A ``Monster`` entity is rejected without mutating any state: its
        ``shame`` bounds are permanently pinned at the floor by
        construction, and re-pinning them would contradict the shipped
        ``sexual-state-handler`` baseline requirement.
        """
        from typeclasses.monsters import Monster

        if isinstance(self._entity, Monster):
            raise ValueError(
                "a Monster's shame bounds are permanently pinned at the floor"
            )
        ordinal = self.shame._ordinal_of(level)
        if ordinal >= self.shame.max:
            self.shame.max = ordinal
            self.shame.min = ordinal
        else:
            self.shame.min = ordinal
            self.shame.max = ordinal

    @property
    def virgin(self) -> bool:
        return self._entity.attributes.get(
            "virgin",
            default=True,
            category=_STATE_CATEGORY,
        )

    @virgin.setter
    def virgin(self, value: bool) -> None:
        if not self.virgin:
            return
        self._entity.attributes.add(
            "virgin",
            bool(value),
            category=_STATE_CATEGORY,
        )

    def restore_purity(self) -> None:
        """Restore the virgin flag by writing the attribute directly.

        Deliberately bypasses the public ``virgin`` setter, which is
        unconditionally a no-op once ``False`` — the one-way guarantee the
        ``sexual-state-handler`` requirement scopes to that public setter
        stays intact, and every ordinary rule path still writes ``virgin``
        exclusively through it. ``experience_types`` is untouched (the body
        is restored, the memory is not). Calling this on an already-virgin
        entity is a no-op: the write is idempotent by construction
        (divine-sexual-arts-mutators D-4).
        """
        self._entity.attributes.add(
            "virgin",
            True,
            category=_STATE_CATEGORY,
        )

    @property
    def experience_types(self) -> frozenset[str]:
        return frozenset(
            self._entity.attributes.get(
                "experience_types",
                default=(),
                category=_STATE_CATEGORY,
            )
        )

    def add_experience_type(self, key: str) -> None:
        """Add one experience key without permitting replacement or removal."""
        self._entity.attributes.add(
            "experience_types",
            self.experience_types | {key},
            category=_STATE_CATEGORY,
        )

    @property
    def submission_marks(self) -> frozenset[str]:
        """Return the append-only set of caster identities this entity submits to.

        Stored in the same ``sexual_state`` attribute category as ``virgin``
        and ``experience_types``. An entity with no prior
        ``mark_submission()`` call reads as an empty frozenset, with no
        baseline-import seeding required.
        """
        return frozenset(
            self._entity.attributes.get(
                "submission_marks",
                default=(),
                category=_STATE_CATEGORY,
            )
        )

    def mark_submission(self, caster_key: str) -> None:
        """Add one caster identity without removing any previously-added key.

        The sole mutator for ``submission_marks``: each call unions in
        exactly one ``caster_key`` and never removes, mirroring
        ``add_experience_type``'s append-only discipline.
        """
        self._entity.attributes.add(
            "submission_marks",
            self.submission_marks | {caster_key},
            category=_STATE_CATEGORY,
        )

    def unlocked_act_keys(self) -> frozenset[str]:
        """Return every act whose counter thresholds this entity has met.

        Direct ownership of any skill carrying ``SexualMasteryEffect``
        instead returns the entire catalogue. Ownership is read through
        ``base_owned_keys()``, never through ``owned_keys()`` — which would
        recurse — and never through ``conferred_grants()``, keeping the
        mastery override direct-ownership only. The rule implementation
        lives in the catalogue package so the no-create ``owned_keys()``
        read shares it exactly.
        """
        from world.skills.sexual_acts import unlocked_act_keys_for

        return unlocked_act_keys_for(
            self._entity.skills.base_owned_keys(),
            {name: getattr(self, name) for name in _LIFETIME_COUNTER_KEYS},
        )
