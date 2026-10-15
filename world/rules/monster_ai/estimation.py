"""Analytic, settlement-faithful estimation of one plan's health effects.

Effect estimation answers, for one legal candidate plan and without running
settlement: which recipients lose how much projected health, how much useful
health is restored, how likely the plan is to finish a hostile recipient, how
much of its nominal effect is wasted against remaining capacity, and what
fraction of the actor's spendable pools it charges. It rolls no dice, invokes
no effect handler, pays no cost, installs no buff and emits no event; every
number comes from the shared scalar arithmetic in
:mod:`world.rules.combat.scalars` and from the decision-local no-create reads.

Five properties are load-bearing, and each is the reason a naive estimator is
wrong:

**The d100 range is averaged analytically, at settlement's own topology.** One
strike's outcome is the finite set of 100 d100 faces mapped through the shared
to-hit margin, multiplier ladder and strike amount. A damage occurrence with
``extra_strikes`` rolls each of its strikes separately (settlement rolls inside
its strike loop), so the occurrence's per-recipient outcome is the distribution
of the sum of its modeled strikes. The occurrence additionally owns ONE
per-recipient hit gate: settlement records a recipient as hit by the occurrence
when any of its strikes landed, and every effect declaring ``requires_hit_from``
that occurrence reads that one recorded gate instead of rolling again. A
dependent effect is therefore evaluated once, weighted by the probability its
one gate opened, and never given a second independent roll.

**Capacity is applied inside every outcome, not to an average.** A projection
advances a recipient's remaining-health branch distribution: each modeled amount
is clamped by the health actually left on that branch, a crossing is absorbing,
and a recipient's stored health floors at its own nonlethal floor. Averaging
first and clamping afterwards would systematically overstate a multi-strike
occurrence's expected loss.

**Order is settlement's commit order, not its staging order.** Settlement stages
every effect and then applies those staged effects in list order; the effect
pendings come first and the actor's resource deduction is appended *last*, after
every effect. A heal, moreover, has its restoration capped at *staging* time
against the recipient's pre-action health gap, so an effect that damages a
full-health recipient in the same action does not hand a later heal a fresh
allowance. Both facts are modeled here. The attack design's prose that payment
precedes effects does not match settlement, and settlement wins -- except that
the payment itself is projected rather than ignored: the actor's *health*
payment is applied to its projected health before the ordered effects, so a
skill spending health before healing itself is never valued as if the actor
still held it, and the amount is a real loss of the actor's own side.

**Control is a marginal projection, never a face value.** A mounted buff or
debuff is worth what it changes: the shared modifier engine evaluates the
recipient's bundle now and with that one effect mounted, and the difference --
over one next action opportunity -- is what the plan's control feature
reports. A mount that is already active, is dominated by what the recipient
already holds, is capped by the merge, or lands on a recipient who cannot act
inside its window is worth exactly zero; a mount whose projected modifiers
include a key this model cannot value contributes its supported part and says
so through ``limits``. A generic effect name establishes nothing.

**Uncertainty is explicit.** Every limit the model could not represent is named
in ``limits``, and every unmodeled effect that contributed nothing to the health
features is named in ``diagnostics``; an unvaluable harm is refused outright
rather than zeroed.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import (
    agility_with_bundle,
    attack_with_bundle,
    build_no_create_condition_context,
    defense_with_bundle,
    evaluate_combat_modifiers_no_create,
    matched_combat_modifiers,
)
from world.rules.combat.scalars import (
    damage_multiplier,
    damage_rider,
    heal_amount,
    hit_margin,
    staged_restoration,
    strike_amount,
    strike_lands,
)
from world.rules.monster_ai.candidates import (
    KIND_FRIENDLY,
    Candidate,
    CandidateIdentity,
    CandidateSet,
    decision_pool,
    group_members,
    hostile_domain,
)
from world.rules.monster_ai.models import DecisionSnapshot, DivertLimit, stable_identity
from world.rules.monster_ai.snapshot import DecisionReads
from world.rules.progression import scaled_magnitude
from world.rules.target_facts import matches_target_predicate
from world.rules.targeting import Relation
from world.skills.effects import (
    BuffApplyEffect,
    CleanseEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DamageEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    EffectPolicy,
    FlavorEffect,
    GaugeTransferEffect,
    GrowthRateEffect,
    HealEffect,
    RiteBlessingEffect,
    RiteShelterEffect,
    RuleTableEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SessionStampEffect,
    WeaponStyleEffect,
)
from world.skills.registry import SkillDef

#: The d100 face count: every supported strike's range is exactly this set.
_D100_FACES = 100
#: The equivalent probability of one d100 face.
_FACE_PROBABILITY = 1.0 / _D100_FACES

#: The parsed effects this estimator models as a health or resource outcome.
#: Every other effect class contributes zero and is reported instead of valued.
_MODELED_EFFECTS = (DamageEffect, HealEffect, SelfHealEffect, GaugeTransferEffect)
#: The parsed effects settlement binds to the actor whatever audience policy
#: they declare, so their one mutation recipient is the actor.
_ACTOR_BOUND_EFFECTS = (SelfHealEffect, SelfBuffApplyEffect)
#: The parsed effects whose payload names a buff definition whose declared
#: polarity decides whether the effect helps or hurts its recipient.
_BUFF_REFERENCE_EFFECTS = (BuffApplyEffect, RiteBlessingEffect, SelfBuffApplyEffect)
#: The parsed effect classes positively known to help their recipient. The
#: table is closed on purpose: an unmodeled effect absent from it is *not*
#: known to be harmless, so the classifier refuses it on the actor's own side
#: instead of valuing an unknown outcome at zero.
_BENIGN_EFFECTS = (
    CleanseEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    FlavorEffect,
    GrowthRateEffect,
    RiteShelterEffect,
    RuleTableEffect,
    SessionStampEffect,
    WeaponStyleEffect,
)
#: The buff polarity that hurts its holder.
_DEBUFF_POLARITY = "debuff"
#: The buff polarity that helps its holder.
_BUFF_POLARITY = "buff"

#: The merged-bundle key that changes how many actions a participant may take.
_CONTROL_ACTION_KEY = "actions_per_turn"
#: The merged-bundle keys whose *absence* means a unit rather than zero, because
#: their settlement reader falls back to one: an unassigned action allowance is
#: the capability projection's own default, and an unassigned gauge-regeneration
#: scale means full regeneration (``clock._settle_gauge_regen`` reads
#: ``f"{gauge}_regen_scale"`` with a ``1.0`` default, and a zero scale is what
#: stops the regeneration entirely). Comparing either as an absent zero would
#: make the mount that assigns it indistinguishable from no rule at all.
_CONTROL_UNIT_DEFAULTS: dict[str, float] = {_CONTROL_ACTION_KEY: 1.0}
#: The suffix a merged-bundle key carries when it scales one gauge's
#: regeneration, whose absence therefore means the unit.
_CONTROL_UNIT_DEFAULT_SUFFIX = "_regen_scale"
#: The merged-bundle keys that change a participant's offensive magnitude.
_CONTROL_ATTACK_KEYS = ("atk_phys", "magic_power")
#: The merged-bundle keys that change how often a participant's offense lands.
_CONTROL_HIT_KEYS = ("accuracy", "agility", "agility_flat")
#: The merged-bundle key that changes the health a participant prevents.
_CONTROL_DEFENSE_KEYS = ("defense",)
#: The percentage-shaped merged-bundle keys that change a participant's
#: resource *cost*, where a reduction is the increase.
_CONTROL_COST_PERCENT_KEYS = ("mp_cost", "sp_cost")
#: The percentage-shaped merged-bundle keys that change a participant's
#: output, where an increase is the increase.
_CONTROL_OUTPUT_PERCENT_KEYS = ("heal_gain",)
#: The absolute-shaped merged-bundle keys that change the same economy.
_CONTROL_ECONOMY_ABSOLUTE_KEYS = (
    "blessing_arousal_scale",
    "mp_regen_scale",
    "recovery_arousal_scale",
    "recovery_share_bonus",
)
#: Every merged-bundle key the control model can value.
_CONTROL_KEYS = frozenset(
    (
        _CONTROL_ACTION_KEY,
        *_CONTROL_ATTACK_KEYS,
        *_CONTROL_HIT_KEYS,
        *_CONTROL_DEFENSE_KEYS,
        *_CONTROL_COST_PERCENT_KEYS,
        *_CONTROL_OUTPUT_PERCENT_KEYS,
        *_CONTROL_ECONOMY_ABSOLUTE_KEYS,
    )
)
#: The merged-bundle keys that describe a rule rather than a modifier.
_CONTROL_BOOKKEEPING_KEYS = frozenset({"chance"})
#: The empty mount set: the bundle a participant reads with no buff at all,
#: which isolates what its own active mounts already contribute.
_NO_MOUNTS: frozenset[str] = frozenset()


class EffectDirection(StrEnum):
    """Which way one bounded feature's magnitude counts in utility."""

    BENEFIT = "benefit"
    HARM = "harm"


class ApproximationClass(StrEnum):
    """How faithful one estimate is to settlement.

    ``EXACT`` means every modeled outcome is settlement's own arithmetic on the
    state the decision read. ``CONSERVATIVE`` means at least one modeled outcome
    is a labeled bound or an omission, so the reported value may sit below what
    settlement could produce.
    """

    EXACT = "exact"
    CONSERVATIVE = "conservative"


class EstimationLimit(StrEnum):
    """One named limit of the model, reported rather than concealed."""

    #: Reaction outcomes are not represented: a landed hit can counter-damage or
    #: mark the actor, and nothing here models it.
    HIT_REACTIONS_UNMODELED = "hit_reactions_unmodeled"
    #: A damage occurrence's evidence-conditional extra strike is not credited:
    #: it resolves only when the recipient carries fresh action evidence, which
    #: a decision's own reads do not project.
    EVIDENCE_STRIKE_UNCREDITED = "evidence_strike_uncredited"
    #: A conditional effect was weighted by the probability its one prerequisite
    #: gate opened, because the joint state of that gate and the effect's own
    #: pools is not tracked branch by branch.
    GATED_EFFECT_WEIGHTED = "gated_effect_weighted"
    #: A conditional effect was omitted because the occurrence it depends on
    #: already changed the very state that effect would act on, so crediting it
    #: on every branch would overstate the plan.
    GATED_EFFECT_OMITTED = "gated_effect_omitted"
    #: An unmodeled effect could change a recipient's health over time.
    OVER_TIME_EFFECT_UNMODELED = "over_time_effect_unmodeled"
    #: An unmodeled effect that could only ever help the actor's side
    #: contributed zero instead of an invented value.
    UNMODELED_BENEFIT_ZERO = "unmodeled_benefit_zero"
    #: A modeled occurrence's potency is a state-derived magnitude the decision
    #: reads cannot project, so nothing was invented in its place.
    STATE_MAGNITUDE_UNMODELED = "state_magnitude_unmodeled"
    #: A recipient's lethal crossing floors its stored health at one.
    NONLETHAL_FLOOR_APPLIED = "nonlethal_floor_applied"
    #: An active damage-diversion budget absorbed part of a strike.
    DIVERSION_ABSORBED = "diversion_absorbed"
    #: A health-gauge diversion pays its absorbed amount through the ordinary
    #: health write, so it does not shield the recipient's health at all.
    DIVERSION_UNSHIELDED_HEALTH = "diversion_unshielded_health"
    #: Several strikes of one occurrence drew on one diversion budget, so the
    #: modeled absorption is an upper bound rather than a branch-exact sum.
    DIVERSION_SHARED_BUDGET = "diversion_shared_budget"
    #: A stack-counted restore bonus was omitted instead of being invented.
    RESTORE_BONUS_OMITTED = "restore_bonus_omitted"
    #: A mounted effect's projected modifiers include a key this model cannot
    #: value, so that part contributed zero instead of an invented amount.
    CONTROL_MODIFIER_UNSUPPORTED = "control_modifier_unsupported"
    #: A mounted effect projected no supported marginal change -- it is already
    #: active, an equivalent or stronger effect already holds, or the merge
    #: capped it -- so its marginal value is zero rather than its face value.
    CONTROL_ZERO_MARGINAL = "control_zero_marginal"
    #: A control beneficiary has no action opportunity inside the effect's
    #: modeled window (expired, or with no action left to take), so nothing was
    #: credited.
    CONTROL_NO_OPPORTUNITY = "control_no_opportunity"
    #: A chance-bearing rule was weighted by the probability it applies instead
    #: of being valued as a certain denial.
    CONTROL_CHANCE_WEIGHTED = "control_chance_weighted"


class InvalidEstimateReason(StrEnum):
    """Why one candidate has no estimate at all.

    Both values are typed invalid states: the caller diagnoses them and excludes
    the candidate, and neither is ever replaced by a zero.
    """

    #: A potentially harmful outcome the model cannot represent lands on the
    #: actor's own side, or measurably helps a hostile side.
    UNSUPPORTED_HARMFUL_OUTCOME = "unsupported_harmful_outcome"
    #: A read or a derived feature was not a finite number.
    NON_FINITE_FEATURE = "non_finite_feature"


@dataclass(frozen=True, slots=True)
class HealthFeature:
    """One bounded, signed health feature.

    ``magnitude`` is the feature's absolute value, always finite and clamped to
    the closed unit interval, so no projection can claim more than a whole
    faction's capacity. ``direction`` states which way it counts: a benefit adds
    the magnitude to utility, a harm subtracts it. ``value`` is the signed form
    a score consumes, which makes enemy damage and allied healing positive and
    ally damage and enemy healing negative by construction.
    """

    magnitude: float
    direction: EffectDirection

    @property
    def value(self) -> float:
        """Return the signed feature a utility score consumes."""
        if self.direction is EffectDirection.HARM:
            return -self.magnitude
        return self.magnitude


@dataclass(frozen=True, slots=True)
class RecipientProjection:
    """One recipient's projected health outcome under this plan.

    ``damage`` and ``healing`` are the *actual* projected health changes,
    already capped by remaining capacity and by the recipient's floor, while
    ``nominal_damage`` and ``nominal_healing`` are what the plan tried to apply:
    the pair is what tells a wasted overkill or a capped heal from a fully used
    effect. ``finishing`` is the modeled probability that this recipient is
    knocked out or defeated by the plan.
    """

    identity: str
    relation: Relation
    damage: float
    healing: float
    nominal_damage: float
    nominal_healing: float
    finishing: float


@dataclass(frozen=True, slots=True)
class ResourceProjection:
    """One participant's projected net pool change under this plan.

    ``deltas`` is the net change of each spendable pool the plan touched, in
    stable gauge order: a negative value is consumption, a positive one is
    recovery. It is what makes a drain's credit and the actor's payment visible
    beside the health features, so nothing downstream has to re-run the pool
    arithmetic to find out what the plan does to a gauge.
    """

    identity: str
    deltas: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class ControlProjection:
    """One recipient's projected marginal control value under this plan.

    Every field is a beneficial change, so it is zero when the mounted effect
    takes nothing away from (or adds nothing to) that quantity, and it is the
    difference between the recipient's modifier bundle now and with this one
    effect mounted over the recipient's next action opportunity:

    - ``opportunity`` is the change in the recipient's available action
      opportunities, in opportunities;
    - ``offense`` is the change in the recipient's per-opportunity offensive
      health impact, in unmitigated damage points;
    - ``defense`` is the change in the health the recipient prevents, in
      damage points per incoming strike;
    - ``economy`` is the change in the recipient's resource and output economy
      as a fraction.

    Each is only the *beneficial* part of its quantity, against a hostile
    recipient for the actor's own side and for a friendly recipient for its own
    side; a not-yet-mounted effect whose direction is mixed therefore
    contributes its helpful half rather than a net figure. The plan's own
    bounded control feature normalizes these sums by the faction the change
    helps or threatens.
    """

    identity: str
    relation: Relation
    opportunity: float
    offense: float
    defense: float
    economy: float


@dataclass(frozen=True, slots=True)
class PlanEstimate:
    """One candidate plan's complete, decision-local estimate.

    Every field is a scalar or an immutable tuple, so a score built on an
    estimate can never mutate it. ``classification``, ``limits`` and
    ``diagnostics`` are the honest report of how faithful the numbers are.
    """

    identity: CandidateIdentity
    recipients: tuple[RecipientProjection, ...] = ()
    resources: tuple[ResourceProjection, ...] = ()
    damage: HealthFeature = field(
        default_factory=lambda: HealthFeature(0.0, EffectDirection.BENEFIT)
    )
    healing: HealthFeature = field(
        default_factory=lambda: HealthFeature(0.0, EffectDirection.BENEFIT)
    )
    waste: HealthFeature = field(
        default_factory=lambda: HealthFeature(0.0, EffectDirection.HARM)
    )
    control: HealthFeature = field(
        default_factory=lambda: HealthFeature(0.0, EffectDirection.BENEFIT)
    )
    finishing: float = 0.0
    cost: float = 0.0
    controls: tuple[ControlProjection, ...] = ()
    classification: ApproximationClass = ApproximationClass.EXACT
    limits: tuple[EstimationLimit, ...] = ()
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InvalidEstimate:
    """One candidate the estimator refuses to value, with its typed reason."""

    identity: CandidateIdentity
    reason: InvalidEstimateReason
    detail: str


@dataclass(frozen=True, slots=True)
class EstimateSet:
    """One decision's per-candidate estimates, in the candidate ring's order."""

    estimates: tuple[PlanEstimate | InvalidEstimate, ...] = ()


class _NonFinite(Exception):
    """A read or derived number was not finite; turned into a typed state."""


def _finite(value: Any, what: str) -> float:
    """Return ``value`` as a finite float, or raise the typed boundary.

    The check happens where a number enters the arithmetic -- not only after the
    features are assembled -- because a non-finite gauge value would otherwise
    raise inside an integer conversion instead of arriving as the typed invalid
    state the contract requires.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _NonFinite(f"{what} is not a number: {value!r}")
    result = float(value)
    if not isfinite(result):
        raise _NonFinite(f"{what} is not finite: {result!r}")
    return result


def _clamped(value: float) -> float:
    """Clamp one bounded feature magnitude into the closed unit interval."""
    if not isfinite(value):
        raise _NonFinite(f"feature is not finite: {value!r}")
    return min(1.0, max(0.0, value))


def _feature(value: float, *, harm: bool = False) -> HealthFeature:
    """Return one bounded signed feature from a signed magnitude."""
    magnitude = _clamped(abs(value))
    if harm or value < 0:
        return HealthFeature(magnitude, EffectDirection.HARM)
    return HealthFeature(magnitude, EffectDirection.BENEFIT)


def _polarity(effect: Any) -> str | None:
    """Return the declared polarity of one buff reference, or ``None``."""
    if not isinstance(effect, _BUFF_REFERENCE_EFFECTS):
        return None
    definition = BUFF_DEFINITIONS.get(effect.buff_key)
    return None if definition is None else definition.polarity


def _harmful_to_recipient(effect: Any, polarity: str | None) -> bool:
    """Return whether one effect takes something away from its recipient."""
    if isinstance(effect, DamageEffect):
        return True
    if isinstance(effect, GaugeTransferEffect):
        return effect.direction == "drain"
    return polarity == _DEBUFF_POLARITY


def _is_benign(effect: Any, polarity: str | None) -> bool:
    """Return whether one effect is positively known to help its recipient.

    Only the closed :data:`_BENIGN_EFFECTS` table, a restore, and a
    ``buff``-polarity reference answer yes. Everything else is unknown, which
    the classifier treats conservatively on the actor's own side.
    """
    if isinstance(effect, GaugeTransferEffect):
        return effect.direction == "restore"
    if polarity is not None:
        return polarity == _BUFF_POLARITY
    return isinstance(effect, _BENIGN_EFFECTS)


def _control_number(value: Any) -> float | None:
    """Return one merged-bundle value as a number, or ``None`` when it is not.

    A modifier is either a real number or a signed percentage string (the rule
    table's ``agility: "-15%"`` shape), which is returned in percentage points
    so a caller decides whether it is a magnitude or a fraction.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        return result if isfinite(result) else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            try:
                result = float(stripped[:-1])
            except ValueError:
                return None
            return result if isfinite(result) else None
    return None


def _control_unit_default(key: str) -> float:
    """Return what one merged-bundle key's absence means to settlement.

    Zero for an ordinary additive modifier, and one for the keys whose reader
    falls back to the unit (:data:`_CONTROL_UNIT_DEFAULTS` plus the
    gauge-regeneration scale family).
    """
    if key in _CONTROL_UNIT_DEFAULTS:
        return _CONTROL_UNIT_DEFAULTS[key]
    if key.endswith(_CONTROL_UNIT_DEFAULT_SUFFIX):
        return 1.0
    return 0.0


def _control_delta(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> tuple[dict[str, float], bool]:
    """Return one hypothetical mount's modifier difference and its gaps.

    Every key either bundle carries is compared: a supported key's difference
    is the model's own input, and a key the model cannot value that *changed*
    is reported so the caller records the limitation instead of silently
    valuing the mount at its supported part alone.

    Absent keys compare as the value that absence means, which for an absolute
    action allowance or a gauge-regeneration scale is the unit its settlement
    reader falls back to (:data:`_CONTROL_UNIT_DEFAULTS`), not zero. Comparing
    either as zero would make the mount that assigns it indistinguishable from
    having no rule at all.
    """
    delta: dict[str, float] = {}
    unsupported = False
    for key in sorted(set(before) | set(after)):
        if key in _CONTROL_BOOKKEEPING_KEYS:
            continue
        absent = _control_unit_default(key)
        first = _control_number(before.get(key, absent))
        second = _control_number(after.get(key, absent))
        if first is None or second is None:
            if before.get(key) != after.get(key):
                unsupported = True
            continue
        if first == second:
            continue
        if key in _CONTROL_KEYS:
            delta[key] = second - first
        else:
            unsupported = True
    return delta, unsupported


def _control_mount_probability(
    before: Sequence[tuple[str, Mapping[str, Any]]],
    after: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[float, bool]:
    """Return the probability one mount's own action lock actually applies.

    The rule table's ``chance`` makes a lock probabilistic (the lightning
    micro-stuns are the shipped example), and settlement's own reader decides
    it rule by rule: every matched rule assigning ``actions_per_turn: 0``
    without a ``chance`` is a certain skip, and otherwise the skip fires with
    the *largest* declared chance (``combat.rounds``). The probability here is
    therefore read from the matching half of the same engine, one rule at a
    time, over exactly the rules this mount newly satisfies -- never from an
    additive merge total, which could turn two probabilistic locks into a
    certainty the consumer would never roll for.

    The returned flag says whether this mount's own lock was the probabilistic
    kind, so the caller reports the limitation. A mount that adds no zero-action
    rule is certain, and so is one whose lock rule declares no probability.
    """
    held = {rule_id for rule_id, _adjustments in before}
    locks = [
        adjustments
        for rule_id, adjustments in after
        if rule_id not in held and adjustments.get("actions_per_turn") == 0
    ]
    if not locks:
        return 1.0, False
    if any("chance" not in adjustments for adjustments in locks):
        return 1.0, False
    chances = [
        int(min(100.0, max(0.0, _control_number(adjustments.get("chance")) or 0.0)))
        for adjustments in locks
    ]
    return min(1.0, max(chances) / _D100_FACES), True


def _control_economy(delta: Mapping[str, float]) -> float:
    """Return one modifier difference's combined resource and output economy.

    A percentage-shaped key counts as its fraction (a ten-percent cost
    reduction is a tenth of the pool it saves) and an absolute-shaped key as
    itself. The result states how much *better off* the recipient is, so a
    reduced cost and a raised output or recovery all come out positive and the
    caller applies the recipient's own direction.
    """
    total = 0.0
    for key in _CONTROL_COST_PERCENT_KEYS:
        total -= delta.get(key, 0.0) / _D100_FACES
    for key in _CONTROL_OUTPUT_PERCENT_KEYS:
        total += delta.get(key, 0.0) / _D100_FACES
    for key in _CONTROL_ECONOMY_ABSOLUTE_KEYS:
        total += delta.get(key, 0.0)
    return total


def _bounded_unit(value: float) -> float:
    """Return one signed quantity clamped into the closed unit interval."""
    if not isfinite(value):
        raise _NonFinite(f"a control quantity is not finite: {value!r}")
    return min(1.0, max(-1.0, value))


def _dominated(
    delta: Mapping[str, float], held: Mapping[str, float]
) -> set[str]:
    """Return the modifier keys an already-held mount outweighs.

    ``held`` is what the recipient's *own active mounts* already contribute to
    each key, so a key whose held contribution is larger in the same direction
    is one this mount cannot usefully add to: it is not a marginal improvement
    over what the recipient already carries. A held contribution of the
    opposite direction, or none at all, never dominates.
    """
    return {
        key
        for key, change in delta.items()
        if (held.get(key, 0.0) * change > 0)
        and abs(held.get(key, 0.0)) > abs(change)
    }


def estimate_candidates(
    candidates: CandidateSet,
    *,
    snapshot: DecisionSnapshot,
    actor: Any,
    context: Any,
    roster: Mapping[str, Any],
    reads: DecisionReads | None = None,
) -> EstimateSet:
    """Estimate every candidate of one decision's enumerated set.

    ``candidates`` is the producer's bounded, deduplicated legal set, and each
    candidate carries the routing the producer established, so no plan's
    recipients are re-derived here. One read set is created when the caller
    supplies none and is shared by every candidate, exactly as enumeration
    shares one.
    """
    decision = _Decision(
        snapshot=snapshot,
        actor=actor,
        context=context,
        roster=roster,
        reads=DecisionReads() if reads is None else reads,
    )
    return EstimateSet(
        estimates=tuple(
            decision.estimate(candidate) for candidate in candidates.candidates
        )
    )


def estimate_plan(
    candidate: Candidate,
    *,
    snapshot: DecisionSnapshot,
    actor: Any,
    context: Any,
    roster: Mapping[str, Any],
    reads: DecisionReads | None = None,
) -> PlanEstimate | InvalidEstimate:
    """Estimate one candidate plan on its own."""
    return _Decision(
        snapshot=snapshot,
        actor=actor,
        context=context,
        roster=roster,
        reads=DecisionReads() if reads is None else reads,
    ).estimate(candidate)


@dataclass(slots=True)
class _Participant:
    """One participant's pre-action estimation inputs, read and validated once."""

    entity: Any
    identity: str
    relation: Relation
    hp: float
    max_hp: float
    floor: float
    gauges: dict[str, float]
    maxima: dict[str, float]
    effective: dict[str, float]
    modifiers: dict[str, Any]
    divert: tuple[DivertLimit, ...]

    @property
    def capacity(self) -> float:
        """Return how much health this participant can lose before its floor."""
        return max(self.hp - self.floor, 0.0)


@dataclass(slots=True)
class _Ledger:
    """One recipient's whole-plan projection and its accounting."""

    participant: _Participant
    recipient: "_Recipient"
    nominal_damage: float = 0.0
    nominal_healing: float = 0.0
    paid_loss: float = 0.0
    paid_healing: float = 0.0


@dataclass(slots=True)
class _Recipient:
    """One recipient's branch-exact remaining-health projection.

    ``states`` maps ``(capped cumulative loss, crossed)`` to probability: every
    branch stays in integer arithmetic, equivalent branches merge exactly, and a
    crossing is a flag rather than a value, so a recipient already out of the
    fight can never be credited as finished a second time. The stored health one
    branch holds is its pre-action health minus its capped loss, which is the
    floored value settlement would store.
    """

    participant: _Participant
    states: dict[tuple[int, bool], float]

    @classmethod
    def start(cls, participant: _Participant) -> "_Recipient":
        return cls(participant=participant, states={(0, False): 1.0})

    def copy(self) -> "_Recipient":
        return _Recipient(participant=self.participant, states=dict(self.states))

    def stored(self, loss: int) -> float:
        """Return the stored health one branch's capped loss leaves."""
        return self.participant.hp - loss

    def expected_health(self) -> float:
        """Return the expected stored health across every branch."""
        total = 0.0
        for (loss, _crossed), probability in self.states.items():
            total += self.stored(loss) * probability
        return total

    def expected_capacity_loss(self) -> float:
        """Return the expected health lost, capped by the recipient's floor.

        The cap is what stops a depleted recipient absorbing further loss, so a
        later effect can never count the same health point twice.
        """
        return self.expected_loss(self.participant.capacity)

    def expected_loss(self, limit: float) -> float:
        """Return the expected loss this distribution holds under one cap.

        The cap is the operation's own floor: direct damage floors a nonlethal
        recipient at one stored point, while a health-gauge diversion pays
        through the ordinary health write and may take the last point as well.
        """
        total = 0.0
        for (loss, _crossed), probability in self.states.items():
            total += min(loss, max(limit, 0.0)) * probability
        return total

    def finishing(self) -> float:
        """Return the probability this recipient has crossed out of the fight."""
        total = 0.0
        for (_loss, crossed), probability in self.states.items():
            if crossed:
                total += probability
        return total

    def apply_loss(self, amount: int, limit: float) -> None:
        """Apply one modeled amount inside every branch with the given loss cap.

        The crossing test is settlement's own pre-floor one: a living branch
        whose projected health reaches zero or below is out of the fight. The
        loss cap is where its stored health lands -- one point for a nonlethal
        recipient -- and a health-gauge diversion, which pays through the
        ordinary health write, raises that cap to the recipient's whole health.
        """
        if amount <= 0:
            return
        advanced: dict[tuple[int, bool], float] = {}
        for (loss, crossed), probability in self.states.items():
            crossed_now = crossed or self.stored(loss) - amount <= 0
            key = (int(min(loss + amount, max(limit, 0.0))), crossed_now)
            advanced[key] = advanced.get(key, 0.0) + probability
        self.states = advanced

    def apply_heal(self, amount: int, full_loss: float) -> None:
        """Apply one staged restoration inside every branch that can take it.

        A restored recipient is never revived: a branch whose stored health is
        zero or below keeps it, while a nonlethal recipient's floored branch is
        a living value and takes the restoration like any other. ``full_loss``
        is the loss that leaves a branch at its full health -- negative when the
        recipient starts below its maximum -- so a restoration can never push a
        branch past that maximum, and a heal below the pre-action health is
        credited in full.
        """
        if amount <= 0:
            return
        healed: dict[tuple[int, bool], float] = {}
        for (loss, crossed), probability in self.states.items():
            if self.stored(loss) <= 0:
                key = (loss, crossed)
            else:
                key = (max(int(full_loss), loss - amount), crossed)
            healed[key] = healed.get(key, 0.0) + probability
        self.states = healed

    def mix(self, branches: Sequence[tuple[float, "_Recipient"]]) -> None:
        """Replace this projection by the probability-weighted union of branches.

        Every branch is a full copy of this projection advanced by one outcome
        and the weights sum to one, because a spread's outcomes partition the
        probability space: advancing them one after another would multiply the
        untouched remainder into every step and lose most of the mass.
        """
        blended: dict[tuple[int, bool], float] = {}
        for weight, branch in branches:
            if weight <= 0:
                continue
            for key, probability in branch.states.items():
                blended[key] = blended.get(key, 0.0) + probability * weight
        self.states = {key: value for key, value in blended.items() if value > 0}


class _Decision:
    """One decision's estimation context, built once and reused per candidate."""

    def __init__(
        self,
        *,
        snapshot: DecisionSnapshot,
        actor: Any,
        context: Any,
        roster: Mapping[str, Any],
        reads: DecisionReads,
    ) -> None:
        self.actor = actor
        self.context = context
        self.reads = reads
        self.snapshot = snapshot
        event_context = getattr(context, "event_context", {}) or {}
        self.nonlethal = bool(event_context.get("nonlethal", False))
        self.nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
        self.pool = decision_pool(snapshot, actor, dict(roster), context)
        self.enemies = hostile_domain(snapshot, self.pool)
        self.allies = group_members(KIND_FRIENDLY, snapshot, self.pool)
        self._participants: dict[str, _Participant] = {}
        self._pools: dict[str, dict[str, float]] = {}
        self._paid: dict[tuple[str, str], float] = {}
        self._gates: dict[int, dict[str, float]] = {}
        self._controls: list[ControlProjection] = []
        self._control_bundles: dict[tuple[str, frozenset[str]], Mapping[str, Any]] = {}
        self._matched: dict[
            tuple[str, frozenset[str]], tuple[tuple[str, Mapping[str, Any]], ...]
        ] = {}
        self._limits: set[EstimationLimit] = set()
        self._diagnostics: set[str] = set()

    # -- reads ---------------------------------------------------------------

    def participant(self, entity: Any) -> _Participant:
        """Return one participant's validated pre-action inputs, read once."""
        identity = stable_identity(entity)
        if identity not in self._participants:
            self._participants[identity] = _participant_reads(
                entity=entity,
                relation=self.context.relation_to(self.actor, entity),
                reads=self.reads,
                nonlethal=self.nonlethal,
                nonlethal_keys=self.nonlethal_keys,
            )
        return self._participants[identity]

    def pools(self, participant: _Participant) -> dict[str, float]:
        """Return one participant's projected pools, seeded from its stored ones."""
        if participant.identity not in self._pools:
            self._pools[participant.identity] = dict(participant.gauges)
        return self._pools[participant.identity]

    def faction_capacity(self, relation: Relation) -> float:
        """Return one faction's eligible live maximum-health sum, floored at one."""
        members = self.enemies if relation is Relation.ENEMY else self.allies
        total = 0.0
        for entity in members:
            total += self.participant(entity).max_hp
        return max(_finite(total, "faction capacity"), 1.0)

    # -- classification ------------------------------------------------------

    def classify(self, skill: SkillDef, recipients: tuple[Any, ...]) -> str | None:
        """Return the exclusion detail for one plan, or ``None`` when it is valueable.

        The closed classification is the only place this module decides what a
        plan's effects mean, and it is deliberately conservative about the
        effects it does not model. A modeled health or resource effect is
        estimated. An unmodeled effect is valued at zero only when it is
        positively known to be benign for its recipient: on the actor's own side
        that makes it a harmless benefit, and on a hostile side it makes it a
        benefit the plan hands to the enemy, which is refused. An unmodeled
        effect that is not positively benign is refused on the actor's own side,
        because treating an unknown outcome aimed at a friend as harmless would
        be a fabrication, and is valued at zero on a hostile side, where it
        cannot hurt the actor's side at all.
        """
        for ordinal, effect in enumerate(skill.parsed_effects):
            policy = skill.effect_policies[ordinal]
            targets = self._effect_recipients(
                effect, self._routed_for(recipients, ordinal)
            )
            if isinstance(effect, _MODELED_EFFECTS):
                if policy.magnitude is not None:
                    if _harmful_to_recipient(effect, _polarity(effect)):
                        return (
                            f"{skill.effects[ordinal]} has an unprojectable state magnitude"
                        )
                    for target in targets:
                        participant = self.participant(target)
                        if participant.relation is Relation.ENEMY:
                            return (
                                f"{skill.effects[ordinal]} heals a hostile "
                                "recipient by an unprojectable magnitude"
                            )
                    self._limits.add(EstimationLimit.STATE_MAGNITUDE_UNMODELED)
                    self._diagnostics.add(
                        f"{skill.effects[ordinal]} magnitude not modeled"
                    )
                    continue
                if isinstance(effect, GaugeTransferEffect):
                    harmful = effect.direction == "drain"
                    for target in targets:
                        participant = self.participant(target)
                        own_side = participant.relation in (
                            Relation.SELF,
                            Relation.ALLY,
                        )
                        if harmful and own_side and effect.gauge != "hp":
                            return (
                                f"{skill.effects[ordinal]} drains {effect.gauge} "
                                "from a friendly recipient"
                            )
                continue
            if isinstance(effect, _BUFF_REFERENCE_EFFECTS):
                exclusion = self._classify_mount(skill, ordinal, effect, targets)
                if exclusion is not None:
                    return exclusion
                continue
            polarity = _polarity(effect)
            benign = _is_benign(effect, polarity)
            for target in targets:
                participant = self.participant(target)
                own_side = participant.relation in (Relation.SELF, Relation.ALLY)
                if own_side and not benign:
                    return (
                        f"{skill.effects[ordinal]} has an unvaluable outcome "
                        "for a friendly recipient"
                    )
                if not own_side and benign:
                    return f"{skill.effects[ordinal]} benefits a hostile recipient"
            if targets:
                self._note_unmodeled(skill, ordinal)
        return None

    def _classify_mount(
        self,
        skill: SkillDef,
        ordinal: int,
        effect: Any,
        targets: tuple[Any, ...],
    ) -> str | None:
        """Return the exclusion detail of one buff/control mount, or ``None``.

        A mount is now valued from its definition's own polarity and the
        modifier rules the mounted key would newly satisfy, so the two
        exclusions that keep an unknown outcome off the wrong side of the
        battlefield are unchanged -- a ``debuff`` mount on the actor's own side
        and a ``buff`` mount on a hostile side are still refused -- while a
        mount that can be valued is no longer reported as an unmodeled zero.
        """
        definition = BUFF_DEFINITIONS.get(effect.buff_key)
        if definition is None:
            return f"{skill.effects[ordinal]} names an unknown definition"
        for target in targets:
            participant = self.participant(target)
            own_side = participant.relation in (Relation.SELF, Relation.ALLY)
            if own_side and definition.polarity == _DEBUFF_POLARITY:
                return (
                    f"{skill.effects[ordinal]} has an unvaluable outcome "
                    "for a friendly recipient"
                )
            if not own_side and definition.polarity == _BUFF_POLARITY:
                return f"{skill.effects[ordinal]} benefits a hostile recipient"
        if not targets:
            return None
        self._diagnostics.add(f"{skill.effects[ordinal]} control projected")
        if isinstance(definition.modifiers.get("rate"), Mapping):
            self._limits.add(EstimationLimit.OVER_TIME_EFFECT_UNMODELED)
            self._diagnostics.add(f"{skill.effects[ordinal]} is an over-time effect")
        return None

    def _note_unmodeled(self, skill: SkillDef, ordinal: int) -> None:
        """Record one unmodeled effect's zero contribution and its limit label.

        Only an effect outside the mount classes reaches here: a buff/control
        mount is valued by :meth:`_classify_mount` and :meth:`_apply_control`.
        """
        self._diagnostics.add(f"{skill.effects[ordinal]} not modeled")
        self._limits.add(EstimationLimit.UNMODELED_BENEFIT_ZERO)

    # -- effect recipient binding -------------------------------------------

    def _effect_recipients(
        self, effect: Any, routed: tuple[Any, ...]
    ) -> tuple[Any, ...]:
        """Return the entities one effect actually mutates.

        Audience routing says which submitted recipients an effect reaches; it
        does not say who the effect binds. ``self_heal`` and ``self_buff_apply``
        mutate the actor whatever their audience policy says, exactly as
        settlement binds them, so the actor is their one recipient here too.
        """
        if isinstance(effect, _ACTOR_BOUND_EFFECTS):
            return (self.actor,)
        return routed

    @staticmethod
    def _routed_for(routed: Any, ordinal: int) -> tuple[Any, ...]:
        """Return one effect's routed recipients, or an empty tuple."""
        if not routed or ordinal >= len(routed):
            return ()
        return tuple(routed[ordinal])

    # -- the estimate --------------------------------------------------------

    def estimate(self, candidate: Candidate) -> PlanEstimate | InvalidEstimate:
        """Estimate one candidate plan, or report the typed reason it has none."""
        self._pools = {}
        self._paid = {}
        self._controls = []
        self._limits = set()
        self._diagnostics = set()
        skill = self.reads.skill(candidate.plan.skill_key)
        try:
            if skill is None:
                raise _NonFinite(f"unknown skill {candidate.plan.skill_key!r}")
            exclusion = self.classify(skill, candidate.routed or ())
            if exclusion is not None:
                return InvalidEstimate(
                    candidate.identity,
                    InvalidEstimateReason.UNSUPPORTED_HARMFUL_OUTCOME,
                    exclusion,
                )
            return self._project(candidate, skill)
        except _NonFinite as invalid:
            return InvalidEstimate(
                candidate.identity,
                InvalidEstimateReason.NON_FINITE_FEATURE,
                str(invalid),
            )

    def _project(self, candidate: Candidate, skill: SkillDef) -> PlanEstimate:
        """Walk one plan in commit order and assemble its features.

        Settlement applies the staged effects first and the actor's resource
        deduction *last*, so every non-health pool is projected the same way: a
        recovery is clamped by its own pool bound before the cost is taken out
        of that pool. The actor's *health* payment is projected before the
        ordered effects, because the resource the action spends is gone by the
        time settlement commits it: a plan that pays health is therefore never
        valued as if the actor still held it, while settlement's own
        staging-time restoration cap is untouched (the healer is still staged
        against the pre-action gap settlement reads).
        """
        routed = candidate.routed or ()
        ledgers = self._ledgers(skill, routed)
        cost = self.reads.costs(self.actor, skill, candidate.plan.scale)
        self._project_health_payment(ledgers, cost)
        self._settle(skill, routed, ledgers, _finite(candidate.plan.scale, "scale"))
        self._pay_cost(cost)
        return self._assemble(candidate, ledgers, cost)

    def _project_health_payment(
        self, ledgers: dict[str, _Ledger], cost: Mapping[str, int]
    ) -> None:
        """Charge the actor's own health payment onto its projected health.

        The charged amount is a real projected loss of the actor's own side, so
        it is recorded on the actor's ledger exactly like any other loss and
        never as a nominal effect or as waste: nothing was applied to anybody,
        the actor simply no longer holds that health when the effects run.
        """
        amount = int(cost.get("hp", 0))
        if amount <= 0:
            return
        actor = self.participant(self.actor)
        ledger = self._ledger_for(ledgers, actor)
        before = ledger.recipient.expected_capacity_loss()
        branch = ledger.recipient.copy()
        branch.apply_loss(amount, actor.hp)
        ledger.recipient.mix([(1.0, branch)])
        ledger.paid_loss += ledger.recipient.expected_capacity_loss() - before
        self._sync_health(ledger)

    def _pay_cost(self, cost: Mapping[str, int]) -> None:
        """Deduct the actor's charged amounts from its projected pools.

        A charged health pool was already projected onto the actor's health by
        :meth:`_project_health_payment`, so only the remaining pools are taken
        out here.
        """
        pools = self.pools(self.participant(self.actor))
        for resource_key, amount in cost.items():
            if resource_key == "hp":
                continue
            if resource_key in pools:
                pools[resource_key] = max(
                    0.0, pools[resource_key] - float(amount)
                )

    def _ledgers(
        self, skill: SkillDef, routed: tuple[tuple[Any, ...], ...]
    ) -> dict[str, _Ledger]:
        """Seed one ledger per recipient this plan can touch."""
        ledgers: dict[str, _Ledger] = {}
        for ordinal, effect in enumerate(skill.parsed_effects):
            for target in self._effect_recipients(
                effect, self._routed_for(routed, ordinal)
            ):
                participant = self.participant(target)
                ledgers.setdefault(
                    participant.identity,
                    _Ledger(participant, _Recipient.start(participant)),
                )
        return ledgers

    def _ledger_for(
        self, ledgers: dict[str, _Ledger], participant: _Participant
    ) -> _Ledger:
        """Return one participant's ledger, creating it when an effect reaches it."""
        return ledgers.setdefault(
            participant.identity,
            _Ledger(participant, _Recipient.start(participant)),
        )

    def _settle(
        self,
        skill: SkillDef,
        routed: tuple[tuple[Any, ...], ...],
        ledgers: dict[str, _Ledger],
        scale: float,
    ) -> None:
        """Apply every effect's contribution in settlement's commit order.

        ``scale`` is the plan's authored cast magnitude: settlement stages every
        damage and heal amount through it, so the estimate must too.
        """
        gates: dict[int, dict[str, float]] = {}
        self._gates = gates
        for ordinal, effect in enumerate(skill.parsed_effects):
            policy = skill.effect_policies[ordinal]
            if isinstance(effect, _MODELED_EFFECTS) and policy.magnitude is not None:
                continue
            routed_targets = self._routed_for(routed, ordinal)
            targets = self._effect_recipients(effect, routed_targets)
            weights = self._gate_weights(policy, gates)
            if isinstance(effect, DamageEffect):
                gates[ordinal] = self._apply_damage(
                    effect, policy, targets, ledgers, weights, scale
                )
            elif isinstance(effect, (HealEffect, SelfHealEffect)):
                self._apply_heal(
                    effect,
                    policy,
                    targets,
                    routed_targets,
                    ledgers,
                    weights,
                    scale,
                )
            elif isinstance(effect, GaugeTransferEffect):
                self._apply_transfer(effect, policy, targets, ledgers, weights)
            elif isinstance(effect, _BUFF_REFERENCE_EFFECTS):
                self._apply_control(effect, targets, weights)

    def _gate_weights(
        self, policy: EffectPolicy, gates: Mapping[int, Mapping[str, float]]
    ) -> dict[str, float] | None:
        """Return one dependent effect's per-recipient gate probabilities.

        ``None`` means the effect carries no prerequisite, so every recipient is
        reached with certainty. A prerequisite names the *occurrence* whose own
        recorded hit gate it reads, so the returned weights are that
        occurrence's probabilities: the one shared gate, used once.
        """
        source = policy.requires_hit_from
        if source is None:
            return None
        return dict(gates.get(source, {}))

    def _weight(self, weights: Mapping[str, float] | None, identity: str) -> float:
        """Return one recipient's reached-probability for a gated effect."""
        if weights is None:
            return 1.0
        weight = min(1.0, max(0.0, _finite(weights.get(identity, 0.0), "gate")))
        if weight < 1.0:
            self._limits.add(EstimationLimit.GATED_EFFECT_WEIGHTED)
        return weight

    def _execution_weight(
        self, weights: Mapping[str, float] | None, routed: tuple[Any, ...]
    ) -> float:
        """Return the probability an actor-bound effect's handler actually runs.

        Settlement filters an effect's *routed* recipients by the source
        occurrence's recorded hits and invokes the handler whenever any of them
        survived that filter; a handler that binds the actor (the two self-bound
        effects) therefore runs with the probability that at least one routed
        recipient qualified, and never with the actor's own gate weight -- the
        actor is not a recipient the prerequisite filtered.
        """
        if weights is None:
            return 1.0
        miss = 1.0
        for target in routed:
            miss *= 1.0 - self._weight(
                weights, self.participant(target).identity
            )
        return max(0.0, min(1.0, 1.0 - miss))

    # -- damage --------------------------------------------------------------

    def _apply_damage(
        self,
        effect: DamageEffect,
        policy: EffectPolicy,
        targets: tuple[Any, ...],
        ledgers: dict[str, _Ledger],
        weights: Mapping[str, float] | None,
        scale: float,
    ) -> dict[str, float]:
        """Advance each recipient through one damage occurrence.

        Returns the occurrence's own hit gate: the per-recipient probability
        that it landed at least one strike, which every dependent effect of this
        occurrence reads instead of rolling again.
        """
        damage_policy = policy.damage
        strikes = 1
        if damage_policy is not None and damage_policy.extra_strikes > 0:
            if damage_policy.repeat_when is None:
                strikes = 1 + damage_policy.extra_strikes
            else:
                self._limits.add(EstimationLimit.EVIDENCE_STRIKE_UNCREDITED)
        self._limits.add(EstimationLimit.HIT_REACTIONS_UNMODELED)
        gate: dict[str, float] = {}
        for target in targets:
            participant = self.participant(target)
            weight = self._weight(weights, participant.identity)
            if weight <= 0:
                continue
            if weights is not None and weight < 1.0:
                # The occurrence this effect depends on already moved this very
                # recipient's health, so crediting the effect on every branch it
                # never reached would overstate the plan. Omit it and say so.
                self._limits.add(EstimationLimit.GATED_EFFECT_OMITTED)
                continue
            ledger = self._ledger_for(ledgers, participant)
            outcomes = self._strike_outcomes(effect, policy, participant, scale)
            gate[participant.identity] = weight * (
                1.0 - outcomes.get(0, 0.0) ** strikes
            )
            applied, spent = self._diverted(participant, outcomes, strikes)
            nominal = strikes * sum(
                amount * probability for amount, probability in outcomes.items()
            )
            ledger.paid_loss += self._advance(
                ledger, applied, strikes, participant, spent, weight
            )
            self._spend(participant, spent)
            ledger.nominal_damage += nominal * weight
            if participant.floor > 0 and ledger.paid_loss > 0:
                self._limits.add(EstimationLimit.NONLETHAL_FLOOR_APPLIED)
        return gate

    def _strike_outcomes(
        self,
        effect: DamageEffect,
        policy: EffectPolicy,
        participant: _Participant,
        scale: float,
    ) -> dict[int, float]:
        """Return one strike's analytic amount distribution for one recipient.

        The 100 d100 faces are mapped through the shared to-hit margin, the
        shared multiplier ladder and the shared strike amount, so the modeled
        range is settlement's own arithmetic rather than a restatement of it. A
        missed face contributes the zero amount and is a legitimate outcome.
        """
        actor = self.participant(self.actor)
        attack_key = "atk_phys" if effect.school == "physical" else "magic_power"
        weapon_multiplier = (
            _finite(self.reads.weapon_multiplier(self.actor), "actor.weapon_multiplier")
            if effect.school == "physical"
            else 1.0
        )
        attack = _finite(
            attack_with_bundle(
                self._real(actor, attack_key),
                actor.modifiers,
                attack_key,
            ),
            "adjusted attack",
        )
        accuracy = _finite(actor.modifiers.get("accuracy", 0), "actor.accuracy")
        agility = _finite(
            agility_with_bundle(self._real(actor, "agility"), actor.modifiers),
            "adjusted agility",
        )
        defender_agility = _finite(
            agility_with_bundle(
                self._real(participant, "agility"), participant.modifiers
            ),
            "adjusted defender agility",
        )
        defense = _finite(
            defense_with_bundle(
                self._real(participant, "defense"), participant.modifiers
            ),
            "adjusted defense",
        )
        damage_policy = policy.damage
        matched_multiplier = 1.0
        rider_fraction = 0.0
        if damage_policy is not None:
            matched = matches_target_predicate(
                participant.entity, damage_policy.predicate, readings=self.reads
            )
            matched_multiplier = damage_policy.attack_multiplier if matched else 1.0
            rider_fraction = damage_policy.max_hp_fraction
            if damage_policy.unconditional_defense_bypass or (
                damage_policy.bypass_defense
                and (matched or not damage_policy.predicate)
            ):
                defense = 0.0
        rider = damage_rider(participant.max_hp, rider_fraction)
        coefficient = _finite(policy.coefficient, "coefficient")
        outcomes: dict[int, float] = {}
        for face in range(1, _D100_FACES + 1):
            margin = hit_margin(
                face,
                attacker_agility=agility,
                attacker_accuracy=accuracy,
                defender_agility=defender_agility,
            )
            if not strike_lands(margin):
                outcomes[0] = outcomes.get(0, 0.0) + _FACE_PROBABILITY
                continue
            amount = strike_amount(
                attack=attack,
                multiplier=damage_multiplier(face, margin),
                coefficient=coefficient,
                defense=defense,
                rider=rider,
                matched_multiplier=matched_multiplier,
                scale=scale,
                weapon_multiplier=weapon_multiplier,
            )
            outcomes[amount] = outcomes.get(amount, 0.0) + _FACE_PROBABILITY
        return outcomes

    def _real(self, participant: _Participant, trait_key: str) -> float:
        """Return one participant's effective static trait, validated finite."""
        return _finite(
            participant.effective.get(trait_key, 0.0),
            f"{participant.identity}.{trait_key}",
        )

    def _diverted(
        self,
        participant: _Participant,
        outcomes: Mapping[int, float],
        strikes: int,
    ) -> tuple[dict[int, float], dict[str, int]]:
        """Return one occurrence's per-face residual and its expected diversion.

        Settlement stages each landing strike separately and subtracts what a
        diversion instance absorbs from *that* strike's residual before the
        strike is applied, so the absorbed amount belongs to a face rather than
        to an average. A health-gauge diversion pays its absorbed amount through
        the ordinary health write, which shields no health at all, so it is
        charged against the instance's budget and reported but never subtracted
        from the residual.

        Every occurrence stages against the *persisted* budget and the live pool
        it read, keeping only its own occurrence-local ledger; the payment
        itself is settled separately in commit order, so this history is not
        spent twice.
        """
        if not participant.divert:
            return ({amount: probability for amount, probability in outcomes.items()}, {})
        if strikes > 1:
            self._limits.add(EstimationLimit.DIVERSION_SHARED_BUDGET)
        residual: dict[int, float] = {}
        staged_instances: dict[str, float] = {}
        staged_gauges: dict[str, float] = {}
        expected: dict[str, float] = {}
        shielded = False
        for amount, probability in outcomes.items():
            remaining = amount
            for limit in participant.divert:
                if remaining <= 0:
                    break
                absorbed = self._absorb(
                    participant, limit, remaining, staged_instances, staged_gauges
                )
                if absorbed <= 0:
                    continue
                expected[limit.instance_key] = (
                    expected.get(limit.instance_key, 0.0) + absorbed * probability
                )
                staged_instances[limit.instance_key] = (
                    staged_instances.get(limit.instance_key, 0.0) + absorbed
                )
                staged_gauges[limit.gauge] = (
                    staged_gauges.get(limit.gauge, 0.0) + absorbed
                )
                if limit.gauge == "hp":
                    self._limits.add(EstimationLimit.DIVERSION_UNSHIELDED_HEALTH)
                    continue
                shielded = True
                remaining -= absorbed
            residual[max(remaining, 0)] = (
                residual.get(max(remaining, 0), 0.0) + probability
            )
        if shielded:
            self._limits.add(EstimationLimit.DIVERSION_ABSORBED)
        return residual, {
            key: int(round(value)) for key, value in expected.items() if value > 0
        }

    def _absorb(
        self,
        participant: _Participant,
        limit: DivertLimit,
        residual: int,
        staged_instances: Mapping[str, float],
        staged_gauges: Mapping[str, float],
    ) -> int:
        """Return how much of one strike's residual one instance absorbs.

        The instance's own order in settlement decides which budget binds
        first, and the absorbed amount is clamped by what the instance's cap
        still allows and by what the pool it would be paid from still holds --
        both measured against what settlement read when it staged this
        occurrence, plus this occurrence's own staged spending.
        """
        remaining_cap = limit.remaining_cap - staged_instances.get(
            limit.instance_key, 0.0
        )
        available = participant.gauges.get(limit.gauge, 0.0) - staged_gauges.get(
            limit.gauge, 0.0
        )
        return max(
            0,
            int(
                min(
                    round(residual * limit.fraction),
                    max(int(remaining_cap), 0),
                    max(int(available), 0),
                )
            ),
        )

    def _spend(
        self, participant: _Participant, spent: Mapping[str, int]
    ) -> None:
        """Pay one occurrence's staged diversion at commit, in order.

        The budget is keyed by the holder as well as the instance, because an
        instance key is local to one entity's own cache. The payment is clamped
        by what the instance's cap still allows after the payments this action
        has already made and by what the paid pool holds at this point in
        commit order: a shield cannot absorb what the action already spent.
        """
        pools = self.pools(participant)
        for limit in participant.divert:
            staged = spent.get(limit.instance_key, 0)
            if staged <= 0:
                continue
            key = (participant.identity, limit.instance_key)
            remaining_cap = limit.remaining_cap - self._paid.get(key, 0.0)
            paid = max(0, min(staged, int(max(remaining_cap, 0.0))))
            if limit.gauge != "hp":
                paid = min(paid, int(max(pools.get(limit.gauge, 0.0), 0.0)))
            if paid <= 0:
                continue
            self._paid[key] = self._paid.get(key, 0.0) + paid
            if limit.gauge in pools and limit.gauge != "hp":
                pools[limit.gauge] = max(0.0, pools[limit.gauge] - float(paid))

    def _advance(
        self,
        ledger: _Ledger,
        applied: Mapping[int, float],
        strikes: int,
        participant: _Participant,
        spent: Mapping[str, int],
        weight: float,
    ) -> float:
        """Advance one recipient through one occurrence's modeled strikes.

        Capacity and the recipient's floor are enforced inside every face's
        branch, so an occurrence that needs two strikes to cross a recipient is
        credited with the crossing and never with twice the capped loss. A
        health-gauge diversion raises the cap to the recipient's whole health,
        because its payment carries no nonlethal floor -- and the extra loss
        that floor-free payment accounts for is returned with the accounted
        loss, so the ledger, the health pool and the finishing projection agree.
        """
        limit = participant.capacity
        spilled = False
        for limit_spec in participant.divert:
            if limit_spec.gauge == "hp" and spent.get(limit_spec.instance_key):
                limit = participant.hp
                spilled = True
        before = ledger.recipient.expected_capacity_loss()
        for _strike in range(strikes):
            branches: list[tuple[float, _Recipient]] = [
                (1.0 - weight, ledger.recipient.copy())
            ]
            for amount, probability in applied.items():
                branch = ledger.recipient.copy()
                branch.apply_loss(int(amount), limit)
                branches.append((probability * weight, branch))
            ledger.recipient.mix(branches)
        self._sync_health(ledger)
        accounted = ledger.recipient.expected_capacity_loss() - before
        if spilled:
            accounted += ledger.recipient.expected_loss(
                participant.hp
            ) - ledger.recipient.expected_capacity_loss()
        return accounted

    def _sync_health(self, ledger: _Ledger) -> None:
        """Keep one participant's projected health pool on its branch expectation.

        The pool view is what a later drain or diversion clamps against, while
        the branch distribution is what the health features measure; letting the
        two drift would let the same health be spent twice.
        """
        pools = self.pools(ledger.participant)
        if "hp" in pools:
            pools["hp"] = max(0.0, ledger.recipient.expected_health())

    # -- healing -------------------------------------------------------------

    def _apply_heal(
        self,
        effect: HealEffect | SelfHealEffect,
        policy: EffectPolicy,
        targets: tuple[Any, ...],
        routed: tuple[Any, ...],
        ledgers: dict[str, _Ledger],
        weights: Mapping[str, float] | None,
        scale: float,
    ) -> None:
        """Advance each recipient by one heal's staged restoration.

        Settlement stages the restoration against the recipient's health gap
        *before* any part of the action commits, so the allowance is that
        pre-action gap however much damage the same action deals first; the
        staged magnitude carries the plan's authored scale. An actor-bound heal
        runs when any *routed* recipient survived the prerequisite filter and
        then mutates the actor, so its weight comes from the routed set.
        """
        actor = self.participant(self.actor)
        magnitude = attack_with_bundle(
            self._real(actor, "magic_power"), actor.modifiers, "magic_power"
        )
        if isinstance(effect, SelfHealEffect) and effect.basis == "missing_fraction":
            gap = max(0.0, actor.max_hp - actor.hp) if actor.hp > 0 else 0.0
            base = int(round(gap * _finite(effect.fraction, "fraction")))
            staged_full = scaled_magnitude(base, scale) if base > 0 else 0
        else:
            staged_full = heal_amount(
                magic_power=magnitude,
                coefficient=_finite(policy.coefficient, "coefficient"),
                heal_gain=actor.modifiers.get("heal_gain"),
                scale=scale,
            )
        bound = isinstance(effect, _ACTOR_BOUND_EFFECTS)
        execution = (
            self._execution_weight(weights, routed) if bound else 1.0
        )
        if bound and execution <= 0:
            return
        for target in targets:
            participant = self.participant(target)
            weight = (
                execution
                if bound
                else self._weight(weights, participant.identity)
            )
            if weight <= 0:
                continue
            ledger = self._ledger_for(ledgers, participant)
            staged = staged_restoration(
                amount=staged_full,
                current=participant.hp,
                maximum=participant.max_hp,
            )
            full_loss = participant.hp - participant.max_hp
            before = ledger.recipient.expected_health()
            branch = ledger.recipient.copy()
            branch.apply_heal(staged, full_loss)
            ledger.recipient.mix(
                [(weight, branch), (1.0 - weight, ledger.recipient.copy())]
            )
            ledger.nominal_healing += staged_full * weight
            ledger.paid_healing += ledger.recipient.expected_health() - before
            self._sync_health(ledger)

    # -- gauge transfers -----------------------------------------------------

    def _apply_transfer(
        self,
        effect: GaugeTransferEffect,
        policy: EffectPolicy,
        targets: tuple[Any, ...],
        ledgers: dict[str, _Ledger],
        weights: Mapping[str, float] | None,
    ) -> None:
        """Advance one gauge transfer's pool and health arithmetic.

        A drain takes what the recipient's projected pool actually holds,
        weighted by the gate that opened it, and credits the actor a share of
        the *aggregated* actual removal -- settlement sums every recipient's
        removal and rounds the share once -- so recovery can never exceed the
        loss that produced it. A health drain also removes projected health from
        its recipient and credits the actor's health with the same share.
        """
        if effect.direction == "restore":
            if policy.transfer is not None and policy.transfer.restore_bonus_per_stack:
                self._limits.add(EstimationLimit.RESTORE_BONUS_OMITTED)
            for target in targets:
                participant = self.participant(target)
                self._restore(
                    participant,
                    effect,
                    self._weight(weights, participant.identity),
                )
            return
        share = 0.0
        if policy.transfer is not None:
            share = _finite(policy.transfer.caster_recovery_share, "recovery share")
        bonus = _finite(
            self.participant(self.actor).modifiers.get("recovery_share_bonus", 0.0),
            "recovery_share_bonus",
        )
        effective = min(1.0, share + bonus)
        for target in targets:
            participant = self.participant(target)
            weight = self._weight(weights, participant.identity)
            if weight <= 0:
                continue
            if effect.gauge == "hp" and weights is not None and weight < 1.0:
                # The occurrence this drain depends on already moved this
                # recipient's health, so crediting the drain on branches it
                # never reached would overstate it: omit it and say so.
                self._limits.add(EstimationLimit.GATED_EFFECT_OMITTED)
                continue
            self._transfer_one(effect, effective, participant, ledgers, weight)

    def _transfer_one(
        self,
        effect: GaugeTransferEffect,
        share: float,
        participant: _Participant,
        ledgers: dict[str, _Ledger],
        weight: float,
    ) -> None:
        """Take one drain from one recipient and credit the actor its share.

        The request is re-derived from the recipient's pool at this point in
        commit order, exactly as settlement re-reads it when the staged closure
        runs, so a pool an earlier effect already emptied cannot be drained
        twice. The removal is what the recipient's projected state actually
        gives up -- the pool's own reduction for a gauge drain, the projected
        health loss for a health drain, which a floor or earlier damage can
        leave far below the request -- and each qualifying recipient is settled
        on its own, so one recipient's closed gate never cancels another's
        removal.
        """
        pools = self.pools(participant)
        current = max(pools.get(effect.gauge, 0.0), 0.0)
        if effect.magnitude_mode == "fixed":
            requested = _finite(effect.magnitude, "magnitude")
        elif effect.magnitude_mode == "fraction":
            requested = round(current * _finite(effect.magnitude, "magnitude"))
        else:
            requested = current
        held = max(0, min(int(requested), int(current)))
        if held <= 0:
            return
        if effect.gauge != "hp":
            pools[effect.gauge] = max(0.0, current - held * weight)
            self._recover(effect, held, share, weight, ledgers)
            return
        ledger = self._ledger_for(ledgers, participant)
        before = ledger.recipient.expected_capacity_loss()
        branch = ledger.recipient.copy()
        branch.apply_loss(held, participant.capacity)
        ledger.recipient.mix(
            [(weight, branch), (1.0 - weight, ledger.recipient.copy())]
        )
        lost = ledger.recipient.expected_capacity_loss() - before
        ledger.nominal_damage += float(held) * weight
        ledger.paid_loss += lost
        self._recover(effect, int(round(lost)), share, weight, ledgers)

    def _restore(
        self,
        participant: _Participant,
        effect: GaugeTransferEffect,
        weight: float,
    ) -> None:
        """Add one restore's amount to the recipient's projected gauge."""
        if weight <= 0:
            return
        pools = self.pools(participant)
        current = max(pools.get("mp", 0.0), 0.0)
        maximum = _finite(
            participant.maxima.get("mp", current), f"{participant.identity}.mp.max"
        )
        if effect.magnitude_mode == "fixed":
            amount = _finite(effect.magnitude, "magnitude")
        elif effect.magnitude_mode == "fraction":
            amount = round(current * _finite(effect.magnitude, "magnitude"))
        else:
            amount = max(0.0, maximum - current)
        pools["mp"] = min(maximum, current + amount * weight)

    def _recover(
        self,
        effect: GaugeTransferEffect,
        removal: int,
        share: float,
        weight: float,
        ledgers: dict[str, _Ledger],
    ) -> None:
        """Pay the actor the share of one drain's actual removal.

        The share is rounded once on the integer removal settlement would sum,
        and only then weighted by the prerequisite gate, so the rounding applies
        to the value settlement rounds rather than to its expectation. The room
        the recovery can occupy is applied *before* that weighting -- a pool
        absorbs a credit into its own bound, and a recipient is never revived --
        so an expected recovery can never exceed the space that actually exists.
        """
        if share <= 0 or weight <= 0 or removal <= 0:
            return
        actor = self.participant(self.actor)
        amount = min(removal, round(removal * share))
        if amount <= 0:
            return
        gauge = effect.gauge
        if gauge == "hp":
            if actor.hp <= 0:
                return
            ledger = self._ledger_for(ledgers, actor)
            amount = min(amount, int(max(actor.max_hp - actor.hp, 0.0)))
            if amount <= 0:
                return
            before = ledger.recipient.expected_health()
            branch = ledger.recipient.copy()
            branch.apply_heal(amount, actor.hp - actor.max_hp)
            ledger.recipient.mix(
                [(weight, branch), (1.0 - weight, ledger.recipient.copy())]
            )
            ledger.nominal_healing += float(amount) * weight
            ledger.paid_healing += ledger.recipient.expected_health() - before
            self._sync_health(ledger)
            return
        pools = self.pools(actor)
        current = max(pools.get(gauge, 0.0), 0.0)
        maximum = _finite(actor.maxima.get(gauge, current), f"actor.{gauge}.max")
        room = max(maximum - current, 0.0)
        pools[gauge] = min(maximum, current + min(float(amount), room) * weight)


    # -- control -------------------------------------------------------------

    def _apply_control(
        self,
        effect: Any,
        targets: tuple[Any, ...],
        weights: Mapping[str, float] | None,
    ) -> None:
        """Value one buff/control mount over each recipient's next opportunity.

        The definition comes from the owning registry; a reference the registry
        does not carry contributes nothing and says so. Each recipient's value
        is the marginal difference between its modifier bundle *now* and with
        this one effect mounted, so a mount that is already active, is
        dominated by what the recipient already holds, or is capped by the
        merge is worth exactly zero instead of its face value.
        """
        definition = BUFF_DEFINITIONS.get(effect.buff_key)
        if definition is None:
            self._limits.add(EstimationLimit.CONTROL_MODIFIER_UNSUPPORTED)
            self._diagnostics.add(f"control definition {effect.buff_key!r} is unknown")
            return
        for target in targets:
            participant = self.participant(target)
            weight = self._weight(weights, participant.identity)
            if weight <= 0:
                continue
            self._controls.append(
                self._control_projection(participant, definition, weight)
            )

    def _control_projection(
        self, participant: _Participant, definition: Any, weight: float
    ) -> ControlProjection:
        """Return one recipient's marginal control value under one definition.

        The horizon is the recipient's one next action opportunity: a mount the
        recipient cannot act under, one already mounted, and one whose effect
        has run out are each worth nothing rather than a repeated full value.
        So is a mount whose projected change an already-active mount of the
        same key outweighs, because it adds nothing the recipient does not
        already hold. A mount whose key the model cannot value contributes its
        supported part and reports the gap instead of inventing one.
        """
        identity = participant.identity
        relation = participant.relation
        empty = ControlProjection(identity, relation, 0.0, 0.0, 0.0, 0.0)
        entity = participant.entity
        duration = definition.duration
        if duration is not None and int(duration) <= 0:
            self._limits.add(EstimationLimit.CONTROL_NO_OPPORTUNITY)
            self._diagnostics.add(f"{definition.key} has expired on {identity}")
            return empty
        if definition.key in self.reads.buff_keys(entity):
            self._limits.add(EstimationLimit.CONTROL_ZERO_MARGINAL)
            self._diagnostics.add(f"{definition.key} is already active on {identity}")
            return empty
        facts = self.snapshot.participant(identity)
        if (
            facts is None
            or not facts.alive
            or not facts.present
            or not facts.in_range
            or self.reads.capability(entity).actions_per_turn <= 0
        ):
            self._limits.add(EstimationLimit.CONTROL_NO_OPPORTUNITY)
            self._diagnostics.add(f"{identity} has no opportunity before expiry")
            return empty
        active = self.reads.buff_keys(entity)
        before = self.reads.modifiers(entity)
        after = self._hypothetical_modifiers(
            entity, identity, active | {definition.key}
        )
        delta, unsupported = _control_delta(before, after)
        if unsupported:
            self._limits.add(EstimationLimit.CONTROL_MODIFIER_UNSUPPORTED)
            self._diagnostics.add(f"{definition.key} projects an unmodeled modifier")
        held = _control_delta(
            self._hypothetical_modifiers(entity, identity, _NO_MOUNTS), before
        )[0]
        dominated = _dominated(delta, held)
        if dominated:
            self._diagnostics.add(
                f"{definition.key} adds nothing over what {identity} already holds"
            )
            delta = {key: value for key, value in delta.items() if key not in dominated}
        if not delta:
            self._limits.add(EstimationLimit.CONTROL_ZERO_MARGINAL)
            self._diagnostics.add(f"{definition.key} changes no supported modifier")
            return empty
        probability, probabilistic = _control_mount_probability(
            self._matched_rules(entity, identity, active),
            self._matched_rules(entity, identity, active | {definition.key}),
        )
        if probabilistic:
            self._limits.add(EstimationLimit.CONTROL_CHANCE_WEIGHTED)
        scale = weight * probability
        hostility = -1.0 if relation is Relation.ENEMY else 1.0
        before_attack, before_hit = self._control_offense(participant, before)
        after_attack, after_hit = self._control_offense(participant, after)
        offense = (after_attack - before_attack) + before_attack * _bounded_unit(
            (after_hit - before_hit) / _D100_FACES
        )
        defense = defense_with_bundle(
            self._real(participant, "defense"), after
        ) - defense_with_bundle(self._real(participant, "defense"), before)
        economy = _control_economy(delta)
        return ControlProjection(
            identity=identity,
            relation=relation,
            opportunity=scale
            * max(0.0, hostility * delta.get(_CONTROL_ACTION_KEY, 0.0)),
            offense=scale * max(0.0, hostility * offense),
            defense=scale * max(0.0, hostility * defense),
            economy=scale * max(0.0, hostility * economy),
        )

    def _control_offense(
        self, participant: _Participant, modifiers: Mapping[str, Any]
    ) -> tuple[float, float]:
        """Return one participant's attack magnitude and to-hit score.

        ``attack`` is the higher of the two attack traits after its own flat
        bundle addend, and ``hit`` is the accuracy plus adjusted agility the
        shared to-hit margin consumes. Neither is turned into a damage
        probability: a decision does not project the opponent's own agility or
        mitigation, so the pair stands for what a changed hit score scales
        rather than for a claimed outcome.
        """
        attack = max(
            max(
                attack_with_bundle(self._real(participant, key), modifiers, key)
                for key in _CONTROL_ATTACK_KEYS
            ),
            0.0,
        )
        hit = _finite(modifiers.get("accuracy", 0), "accuracy") + agility_with_bundle(
            self._real(participant, "agility"), modifiers
        )
        return attack, hit

    def _hypothetical_modifiers(
        self, entity: Any, identity: str, keys: frozenset[str]
    ) -> Mapping[str, Any]:
        """Return one hypothetical active-buff bundle, evaluated once per key set.

        The shared modifier engine evaluates it with the same merge authority
        the recipient's real bundle uses -- grant scaling, restriction ceilings
        and the equipment fold included -- so a projection can never disagree
        with what settlement reads once the effect is mounted.
        """
        cache_key = (identity, keys)
        if cache_key not in self._control_bundles:
            self._control_bundles[cache_key] = evaluate_combat_modifiers_no_create(
                entity, active_buffs=keys
            )
        return self._control_bundles[cache_key]

    def _matched_rules(
        self, entity: Any, identity: str, keys: frozenset[str]
    ) -> tuple[tuple[str, Mapping[str, Any]], ...]:
        """Return one hypothetical mount set's per-rule matches, read once.

        The matching half of the same engine the merged bundle comes from, kept
        rule by rule so a rule that declares a probability can be weighted by
        settlement's own reading of it instead of by an additive merge total.
        """
        cache_key = (identity, keys)
        if cache_key not in self._matched:
            context = build_no_create_condition_context(entity)
            context["active_buffs"] = keys
            self._matched[cache_key] = matched_combat_modifiers(
                entity, context=context
            )
        return self._matched[cache_key]

    def _baseline_opportunities(self, relation: Relation) -> float:
        """Return one faction's eligible baseline action opportunities.

        The denominator the opportunity term is normalized by: every eligible
        member's current action allowance, which already folds whatever locks
        it carries. A faction with none left is floored at one, so a fully
        locked side contributes no denial rather than dividing by zero.
        """
        members = self.enemies if relation is Relation.ENEMY else self.allies
        total = 0.0
        for entity in members:
            total += max(
                float(self.reads.capability(entity).actions_per_turn), 0.0
            )
        return max(total, 1.0)


    # -- features ------------------------------------------------------------

    def _assemble(
        self,
        candidate: Candidate,
        ledgers: dict[str, _Ledger],
        cost: Mapping[str, int],
    ) -> PlanEstimate:
        """Assemble one plan's bounded, signed features from its ledgers."""
        enemy_capacity = self.faction_capacity(Relation.ENEMY)
        ally_capacity = self.faction_capacity(Relation.ALLY)
        enemy_loss = 0.0
        own_loss = 0.0
        own_restore = 0.0
        enemy_restore = 0.0
        nominal = 0.0
        wasted = 0.0
        finishing = 0.0
        for ledger in ledgers.values():
            hostile = ledger.participant.relation is Relation.ENEMY
            if hostile:
                enemy_loss += ledger.paid_loss
                enemy_restore += ledger.paid_healing
                finishing += ledger.recipient.finishing()
            else:
                own_loss += ledger.paid_loss
                own_restore += ledger.paid_healing
            nominal += ledger.nominal_damage + ledger.nominal_healing
            wasted += max(
                0.0,
                ledger.nominal_damage
                + ledger.nominal_healing
                - ledger.paid_loss
                - ledger.paid_healing,
            )
        count = len(self.enemies)
        return PlanEstimate(
            identity=candidate.identity,
            recipients=self._recipient_projections(ledgers),
            resources=self._resource_projections(),
            damage=_feature(enemy_loss / enemy_capacity - own_loss / ally_capacity),
            healing=_feature(
                own_restore / ally_capacity - enemy_restore / enemy_capacity
            ),
            waste=_feature(wasted / nominal if nominal > 0 else 0.0, harm=True),
            control=_feature(self._control_feature(enemy_capacity, ally_capacity)),
            finishing=_clamped(finishing / count if count else 0.0),
            cost=self._cost_feature(cost),
            classification=(
                ApproximationClass.CONSERVATIVE
                if self._limits
                else ApproximationClass.EXACT
            ),
            limits=tuple(sorted(self._limits)),
            diagnostics=tuple(sorted(self._diagnostics)),
            controls=tuple(self._controls),
        )

    def _control_feature(self, enemy_capacity: float, ally_capacity: float) -> float:
        """Return this plan's bounded marginal control over one opportunity.

        Each recipient contributes the beneficial part of its own projection,
        and each sum is normalized the way the health features are: the
        opportunity term by the faction's own baseline opportunities, and the
        offensive, defensive and economy terms by the faction capacity the
        change helps or threatens. The result is bounded by the feature itself,
        so no mount can claim more than a whole faction's worth of value.
        """
        if not self._controls:
            return 0.0
        hostile = [
            item for item in self._controls if item.relation is Relation.ENEMY
        ]
        friendly = [
            item for item in self._controls if item.relation is not Relation.ENEMY
        ]
        return (
            sum(item.opportunity for item in hostile)
            / self._baseline_opportunities(Relation.ENEMY)
            + sum(item.opportunity for item in friendly)
            / self._baseline_opportunities(Relation.ALLY)
            + sum(item.offense for item in hostile) / ally_capacity
            + sum(item.offense for item in friendly) / enemy_capacity
            + sum(item.defense for item in hostile) / enemy_capacity
            + sum(item.defense for item in friendly) / ally_capacity
            + sum(item.economy for item in self._controls)
        )

    def _resource_projections(self) -> tuple[ResourceProjection, ...]:
        """Return every touched participant's projected net pool change.

        Only pools that actually moved are reported, so a plan that touches
        nothing resource-wise carries no resource row at all.
        """
        projections: list[ResourceProjection] = []
        for identity in sorted(self._pools):
            participant = self._participants[identity]
            current = self._pools[identity]
            deltas: list[tuple[str, float]] = []
            for gauge_key in sorted(current):
                change = round(
                    current[gauge_key] - participant.gauges.get(gauge_key, 0.0), 6
                )
                if change != 0:
                    deltas.append((gauge_key, change))
            if deltas:
                projections.append(ResourceProjection(identity, tuple(deltas)))
        return tuple(projections)

    def _recipient_projections(
        self, ledgers: Mapping[str, _Ledger]
    ) -> tuple[RecipientProjection, ...]:
        """Return each recipient's projected outcome in stable identity order."""
        projections = [
            RecipientProjection(
                identity=ledger.participant.identity,
                relation=ledger.participant.relation,
                damage=ledger.paid_loss,
                healing=ledger.paid_healing,
                nominal_damage=ledger.nominal_damage,
                nominal_healing=ledger.nominal_healing,
                finishing=ledger.recipient.finishing(),
            )
            for ledger in ledgers.values()
        ]
        return tuple(sorted(projections, key=lambda item: item.identity))

    def _cost_feature(self, cost: Mapping[str, int]) -> float:
        """Return the mean charged fraction of the actor's spendable pools.

        Every pool the skill charges is measured against the value it holds when
        the decision is made, and a pool with no spendable value contributes
        zero rather than an infinite fraction.
        """
        fractions: list[float] = []
        for resource_key, amount in cost.items():
            current = _finite(
                self.reads.trait_value(self.actor, resource_key),
                f"actor.{resource_key}",
            )
            if current <= 0:
                fractions.append(0.0)
                continue
            fractions.append(min(1.0, max(0.0, float(amount) / current)))
        if not fractions:
            return 0.0
        return _clamped(sum(fractions) / len(fractions))


def _participant_reads(
    *,
    entity: Any,
    relation: Relation,
    reads: DecisionReads,
    nonlethal: bool,
    nonlethal_keys: frozenset[str],
) -> _Participant:
    """Read one participant's estimation inputs through the no-create reader.

    The floor is settlement's own per-recipient policy: a session-wide
    nonlethal flag protects every recipient, a per-entity key set protects the
    named ones, and everyone else floors at zero.
    """
    identity = stable_identity(entity)
    key = str(getattr(entity, "key", ""))
    resources = reads.resources(entity)
    gauges = {
        gauge_key: _finite(current, f"{identity}.{gauge_key}")
        for gauge_key, (current, _maximum) in resources.items()
    }
    maxima = {
        gauge_key: _finite(maximum, f"{identity}.{gauge_key}.max")
        for gauge_key, (_current, maximum) in resources.items()
    }
    effective = {
        trait_key: _finite(value, f"{identity}.{trait_key}")
        for trait_key, value in reads.effective_traits(entity).items()
    }
    modifiers = dict(reads.modifiers(entity))
    for modifier_key in ("atk_phys", "magic_power", "defense", "accuracy", "agility_flat"):
        if modifier_key in modifiers:
            _finite(modifiers[modifier_key], f"{identity}.{modifier_key}")
    return _Participant(
        entity=entity,
        identity=identity,
        relation=relation,
        hp=gauges.get("hp", 0.0),
        max_hp=maxima.get("hp", gauges.get("hp", 0.0)),
        floor=1.0 if nonlethal or key in nonlethal_keys else 0.0,
        gauges=gauges,
        maxima=maxima,
        effective=effective,
        modifiers=modifiers,
        divert=reads.divert_limits(entity),
    )
