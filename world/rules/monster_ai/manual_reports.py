"""Manual acceptance reports for the monster combat AI (monster-ai-manual-evidence).

This module is manual acceptance evidence, never a default verification step.
Nothing here runs at startup, in the default test suite, in the contract gates
or in CI: every operation is explicit and independent, invoked by hand through
``tools/monster_ai_manual_reports.py`` against an isolated scratch database
with the network/model services disabled. The focused, deterministic contracts
of the tool itself live in ``world.rules.tests.test_monster_ai_manual_reports``
and never rerun the campaign.

The layer in this module is deliberately free of ORM access: it declares the
campaign allocation, encodes the documented seeds, computes the paired
proportions with their Wilson intervals, aggregates encounter metrics,
classifies every no-action cause and renders the machine-readable JSON and its
compact Markdown interpretation. The Evennia-side execution boundary (real
synthetic entities, real sessions, real settlement and committed reload) lives
in :mod:`world.rules.monster_ai.manual_campaign`, which drives this layer
through the small engine protocols below so the report arithmetic stays
testable without a database.

Report contract (simulation design section 5): baseline commit, algorithm and
configuration fingerprints, Python/Evennia versions, host/clock details for
performance, the synthetic scenario declarations, the documented seeds, the
initial observation memory, the intelligence settings, raw paired results,
approximation flags, candidate-budget omissions and unresolved encounters.

Every encounter keeps its materialized scenario declaration and a per-decision
replay record (the decision's effective selector seed, temperature,
configuration fingerprint, effective and session execution identities, the
scored plans it sampled from, its selected plan, its measured
examined/accepted/omitted proposal counters and its own initial observation
snapshot). Target metrics are keyed by encounter-local role and concentrated
per encounter before aggregation. The normalized detailed decision trace is an
explicit opt-in export (``detailed_trace``), never part of the compact report.
"""

from __future__ import annotations

import json
import platform
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any

from world.rules.monster_ai.candidates import CandidateIdentity, Candidate
from world.rules.monster_ai.models import PlannedAction
from world.rules.monster_ai.selection import select_candidate, selection_temperature
from world.rules.monster_ai.utility import ScoredCandidate

#: The version of this module's own seed encoding. Bump it whenever the
#: encoded payload changes, so a recorded seed can never be mistaken for a
#: different encoding (mirrors ``SELECTION_SEED_VERSION``).
SEED_ENCODING_VERSION = 1

#: The six distinct synthetic situations the allocation requires (simulation
#: design section 2). Each is exercised twice at both intelligence values.
SITUATION_NAMES: tuple[str, ...] = (
    "finishing_choice",
    "area_versus_single",
    "resource_exhaustion",
    "mandatory_targeting",
    "support_and_focus",
    "long_lifecycle",
)

#: The two documented campaign seed indices (allocation: two fixed seeds).
CAMPAIGN_SEED_INDICES: tuple[int, ...] = (0, 1)
#: The paired intelligence values (allocation: intelligence 10 and 90).
INTELLIGENCE_VALUES: tuple[int, ...] = (10, 90)
#: The safety bound of one encounter, in actual rounds (simulation design
#: section 2). Reaching it is reported as capped/unresolved, never terminal.
ROUND_CAP = 30

#: The standalone selection check: 128 documented injected seeds (section 3).
SELECTOR_SEED_COUNT = 128
#: The fixed utility gap of the check's exactly two legal candidates.
SELECTOR_UTILITY_GAP = 0.5
#: Acceptance: high-intelligence highest-utility frequency must exceed low by
#: at least this many percentage points.
SELECTOR_MIN_MARGIN = 0.15
#: The two candidate names the paired check compares (stable ordering).
SELECTOR_HIGH_KEY = "highest"
SELECTOR_LOW_KEY = "lowest"

#: The performance envelope (section 6): 16 live participants, up to 16 owned
#: active skills per deciding actor and a 256-candidate budget.
PERFORMANCE_PARTICIPANTS = 16
PERFORMANCE_OWNED_SKILLS = 16
PERFORMANCE_CANDIDATE_BUDGET = 256
#: Five warm-ups then 50 measured decisions, with one separate cold call.
PERFORMANCE_WARMUPS = 5
PERFORMANCE_MEASUREMENTS = 50
#: The initial warm utility p95 budget, in milliseconds.
PERFORMANCE_P95_BUDGET_MS = 50.0
#: The two modes the performance operation measures.
PERFORMANCE_MODES: tuple[str, ...] = ("legacy", "utility")
#: The examined-proposal budgets the scaling probe compares on ONE fixed
#: battlefield: the enumeration work the decision is allowed varies while the
#: actor/participant data, the roster and the state do not.
PERFORMANCE_SCALING_BUDGETS: tuple[int, ...] = (16, 64, 256)

#: The 95% normal quantile the Wilson interval is computed at.
WILSON_Z = 1.959963984540054


def stable_seed(kind: str, *parts: Any) -> int:
    """Return one documented, versioned seed of this tool's own encoding.

    A canonical JSON list -- fixed field order, no unordered container --
    hashed with SHA-256 and truncated to its first 128 bits, exactly like the
    selection seed. The encoding is stable across processes, so a recorded
    seed reproduces its operation anywhere.
    """
    payload = [SEED_ENCODING_VERSION, kind, *parts]
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return int.from_bytes(sha256(encoded.encode("utf-8")).digest()[:16], "big")


def scenario_seed(situation: str, archetype: str, seed_index: int) -> int:
    """Return the documented campaign seed of one encounter."""
    return stable_seed("campaign", situation, archetype, int(seed_index))


#: The documented prefix of one manual encounter's session identity: the
#: manual selection seam's own scenario identity, never the durable
#: ``hostile:<pk>:<tick>`` identity a scratch database would invent.
MANUAL_SESSION_PREFIX = "manual"
#: The documented prefix of one decision's encounter-local actor identity.
MANUAL_ACTOR_PREFIX = "role"


def manual_session_id(situation: str, archetype: str, seed_index: int) -> str:
    """Return the documented session identity one encounter decides under.

    The identity names the scenario (situation, archetype, documented seed
    index) and NOT the intelligence, so a paired pair of variants decides
    under one shared session identity; the encounter's own durable record is
    rewritten to it before the first round, so the round engine, the
    session-owned observation memory and the decision scope all agree on it.
    """
    return f"{MANUAL_SESSION_PREFIX}:{situation}:{archetype}:{int(seed_index)}"


def manual_actor_id(role: str) -> str:
    """Return the documented actor identity of one encounter-local role.

    A decision's scope actor is its encounter-local role (``monster-0``,
    ``player``), not a dbref the scratch database happened to allocate, so
    corresponding paired decisions carry the same actor input.
    """
    return f"{MANUAL_ACTOR_PREFIX}:{role}"


def selector_seed(seed_index: int) -> int:
    """Return the documented injected seed of one selector-check replicate."""
    return stable_seed("selector", int(seed_index))


def wilson_interval(successes: int, total: int, *, z: float = WILSON_Z) -> tuple[float, float]:
    """Return the two-sided Wilson score interval of one proportion.

    The interval is the small-sample one the report must carry: with zero
    trials it is the uninformative ``(0.0, 1.0)``, and a zero or complete
    count still yields a non-degenerate interval rather than the naive
    ``p_hat +/- 0``.
    """
    if total <= 0:
        return (0.0, 1.0)
    if successes < 0 or successes > total:
        raise ValueError(f"successes must be within 0..{total}, got {successes!r}")
    p_hat = successes / total
    denominator = 1.0 + z * z / total
    center = (p_hat + z * z / (2 * total)) / denominator
    margin = (
        z
        * sqrt((p_hat * (1.0 - p_hat) + z * z / (4 * total)) / total)
        / denominator
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def paired_difference(low_successes: int, high_successes: int, total: int) -> float:
    """Return the paired proportion difference (high minus low)."""
    if total <= 0:
        return 0.0
    return (high_successes - low_successes) / total


# ---------------------------------------------------------------------------
# Two-candidate selector check (simulation design section 3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SelectorPair:
    """One injected seed's paired choices across both intelligence values."""

    seed_index: int
    seed: int
    low_choice: str
    high_choice: str


@dataclass(frozen=True, slots=True)
class SelectorReport:
    """The standalone selection check's complete, JSON-safe result."""

    pairs: tuple[SelectorPair, ...]
    low_high_utility: int
    high_high_utility: int
    total: int
    low_probability: float
    high_probability: float
    low_wilson: tuple[float, float]
    high_wilson: tuple[float, float]
    difference: float
    margin_required: float
    margin_met: bool
    low_temperature: float = 0.0
    high_temperature: float = 0.0
    candidate_order: tuple[str, ...] = ()


def _selector_candidates(gap: float) -> tuple[ScoredCandidate, ScoredCandidate]:
    """Return the two legal candidates differing by exactly ``gap`` utility.

    Both are real :class:`Candidate` values with stable identities, put in the
    canonical selection order (skill key, target ids, scale) so the check
    compares the production selection function over a fixed ordering. The high
    candidate carries the full score and the low one the score minus the gap;
    every other feature is zero, so the gap IS the utility difference.
    """
    if gap <= 0:
        raise ValueError(f"the selector utility gap must be positive, got {gap!r}")

    def _scored(skill_key: str, score: float) -> ScoredCandidate:
        identity = CandidateIdentity(skill_key=skill_key, scale=1.0, target_ids=())
        candidate = Candidate(
            identity=identity,
            plan=PlannedAction(skill_key=skill_key, scale=1.0, target_ids=()),
        )
        return ScoredCandidate(candidate=candidate, score=score, damage=0.0,
                               healing=0.0, control=0.0, focus=0.0,
                               preference=0.0, finishing=0.0, cost=0.0,
                               waste=0.0, limits=())

    high = _scored(SELECTOR_HIGH_KEY, 1.0)
    low = _scored(SELECTOR_LOW_KEY, 1.0 - gap)
    return high, low


def run_selector_operation(
    *,
    seed_count: int = SELECTOR_SEED_COUNT,
    gap: float = SELECTOR_UTILITY_GAP,
    intelligences: Sequence[int] = INTELLIGENCE_VALUES,
) -> SelectorReport:
    """Run the recorded standalone selection check over the documented seeds.

    Exactly two legal candidates, a fixed utility gap and the SAME seeds
    injected at both intelligence values: the production selection function
    samples each pairing with an independent generator seeded from the
    documented seeded identity, so the comparison is paired.
    """
    low_intelligence, high_intelligence = tuple(intelligences)
    high, low = _selector_candidates(gap)
    ordered = (high, low)
    low_temperature = selection_temperature(low_intelligence)
    high_temperature = selection_temperature(high_intelligence)
    pairs: list[SelectorPair] = []
    low_hits = high_hits = 0
    for seed_index in range(seed_count):
        seed = selector_seed(seed_index)
        low_choice = select_candidate(ordered, temperature=low_temperature, seed=seed)
        high_choice = select_candidate(ordered, temperature=high_temperature, seed=seed)
        low_high = low_choice.identity.skill_key == SELECTOR_HIGH_KEY
        high_high = high_choice.identity.skill_key == SELECTOR_HIGH_KEY
        low_hits += int(low_high)
        high_hits += int(high_high)
        pairs.append(
            SelectorPair(
                seed_index=seed_index,
                seed=seed,
                low_choice=low_choice.identity.skill_key,
                high_choice=high_choice.identity.skill_key,
            )
        )
    total = len(pairs)
    difference = paired_difference(low_hits, high_hits, total)
    return SelectorReport(
        pairs=tuple(pairs),
        low_high_utility=low_hits,
        high_high_utility=high_hits,
        total=total,
        low_probability=(low_hits / total) if total else 0.0,
        high_probability=(high_hits / total) if total else 0.0,
        low_wilson=wilson_interval(low_hits, total),
        high_wilson=wilson_interval(high_hits, total),
        difference=difference,
        margin_required=SELECTOR_MIN_MARGIN,
        margin_met=difference >= SELECTOR_MIN_MARGIN,
        low_temperature=low_temperature,
        high_temperature=high_temperature,
        candidate_order=tuple(item.identity.skill_key for item in ordered),
    )


# ---------------------------------------------------------------------------
# Encounter metrics (simulation design sections 2 and 5)
# ---------------------------------------------------------------------------
#: One decision that proposed no action, by the boundary that produced it.
NO_ACTION_LEGAL_RESTRICTION = "legal_restriction"
NO_ACTION_ESTIMATOR_EXCLUSION = "estimator_exclusion"
NO_ACTION_BUDGET_OMISSION = "budget_omission"
NO_ACTION_CAPABILITY_BLOCKED = "capability_blocked"

#: Terminal classification of one encounter.
OUTCOME_WIN = "win"
OUTCOME_LOSS = "loss"
OUTCOME_CAPPED = "capped"


def classify_no_action(candidates: Any, scored: Sequence[Any]) -> str | None:
    """Return the named cause of one decision's no-action boundary, or ``None``.

    The three causes the report must keep separate (simulation design section
    5) are a legitimate legal restriction, an unsupported/refused estimator
    exclusion and a candidate-budget omission. A decision that scored at least
    one candidate took an action and returns ``None``.
    """
    if scored:
        return None
    if candidates is None:
        return NO_ACTION_CAPABILITY_BLOCKED
    if not candidates.candidates:
        if candidates.exhausted:
            return NO_ACTION_BUDGET_OMISSION
        return NO_ACTION_LEGAL_RESTRICTION
    return NO_ACTION_ESTIMATOR_EXCLUSION


@dataclass(frozen=True, slots=True)
class DecisionSample:
    """One recorded monster decision: its choice AND its replay inputs.

    Besides the metrics the report aggregates, every decision carries the
    inputs its selection actually used, so one decision can be replayed from
    the report alone: the effective selector ``seed``, the ``temperature``,
    the configuration fingerprint the seed was derived with, the effective
    execution identity (``scope``, the manual seam's own scope) beside the
    session's own identity (``session_scope``), the scored ``plans`` that were
    sampled from, the ``selected_plan``, and the decision's own initial
    observation snapshot. ``examined``/``accepted``/``omitted_estimates``/
    ``omitted_families``/``omitted_targets`` are the decision's measured
    proposal counters, so enumeration work is never inferred from the
    accepted set.
    """

    skill_key: str | None = None
    target_ids: tuple[str, ...] = ()
    highest_utility: bool = False
    selected_illegal: bool = False
    no_action: str | None = None
    index: int = 0
    actor_role: str = ""
    target_roles: tuple[str, ...] = ()
    seed: int = 0
    temperature: float = 0.0
    configuration_fingerprint: str = ""
    scope: tuple[str, int, str, int, str] = ("", 0, "", 0, "normal")
    session_scope: tuple[str, int, str, int, str] = ("", 0, "", 0, "normal")
    plans: tuple[Mapping[str, Any], ...] = ()
    selected_plan: Mapping[str, Any] | None = None
    examined: int = 0
    accepted: int = 0
    rejections: int = 0
    exclusions: int = 0
    omitted_estimates: int = 0
    omitted_families: int = 0
    omitted_targets: int = 0
    exhausted: bool = False
    approximation_flags: tuple[str, ...] = ()
    initial_observations: tuple[tuple[Any, ...], ...] = ()
    trace: Mapping[str, Any] | None = None

    def to_payload(self, *, include_trace: bool = False) -> dict[str, Any]:
        """Return this decision's replay record as a JSON-safe mapping.

        The opt-in detailed trace is the normalized
        :meth:`~world.rules.monster_ai.trace.DecisionTrace.to_payload`
        projection, which never carries queued or private intent.
        """
        record: dict[str, Any] = {
            "index": self.index,
            "seed": self.seed,
            "temperature": self.temperature,
            "configuration_fingerprint": self.configuration_fingerprint,
            "scope": _scope_payload(self.scope),
            "session_scope": _scope_payload(self.session_scope),
            "actor_role": self.actor_role,
            "skill_key": self.skill_key,
            "target_roles": list(self.target_roles),
            "target_ids": list(self.target_ids),
            "highest_utility": self.highest_utility,
            "selected_illegal": self.selected_illegal,
            "no_action": self.no_action,
            "examined": self.examined,
            "accepted": self.accepted,
            "rejections": self.rejections,
            "exclusions": self.exclusions,
            "omitted_estimates": self.omitted_estimates,
            "omitted_families": self.omitted_families,
            "omitted_targets": self.omitted_targets,
            "exhausted": self.exhausted,
            "approximation_flags": list(self.approximation_flags),
            "plans": [dict(plan) for plan in self.plans],
            "selected_plan": None if self.selected_plan is None else dict(self.selected_plan),
            "observations": [list(record) for record in self.initial_observations],
        }
        if include_trace and self.trace is not None:
            record["trace"] = self.trace
        return record


def _scope_payload(scope: tuple[str, int, str, int, str]) -> dict[str, Any]:
    """Return one ``(session, round, actor, slot, mode)`` scope as a mapping."""
    session_id, round_index, actor_id, slot_index, context_mode = scope
    return {
        "session": session_id,
        "round": round_index,
        "actor": actor_id,
        "slot": slot_index,
        "context_mode": context_mode,
    }


@dataclass(frozen=True, slots=True)
class ScenarioDeclaration:
    """One situation's materialized declaration, exactly as the run built it.

    Maximum and initial HP are separate fields, so an intentionally injured
    opponent is a declared (maximum, initial) pair rather than a low maximum
    pretend-healthy one. Every entity field is a plain scalar or tuple: the
    declaration can never carry a live entity.
    """

    name: str
    monsters: int
    monsters_hp: tuple[int, ...]
    monsters_hp_max: tuple[int, ...]
    monster_mp: int
    monster_atk: int
    initiator_hp: int
    initiator_hp_max: int
    companion_hp: tuple[int, ...]
    companion_hp_max: tuple[int, ...]
    seal_opponents: int
    displaced_opponents: int
    seal_key: str
    positional_key: str
    driver_skill_key: str
    monster_skills: tuple[str, ...]
    support_skills: tuple[str, ...] = ()
    monster_effect: str | None = None
    allied_support: bool = False

    def to_payload(self) -> dict[str, Any]:
        """Return this declaration as a JSON-safe mapping."""
        return {
            "name": self.name,
            "monsters": self.monsters,
            "monsters_hp": list(self.monsters_hp),
            "monsters_hp_max": list(self.monsters_hp_max),
            "monster_mp": self.monster_mp,
            "monster_atk": self.monster_atk,
            "initiator_hp": self.initiator_hp,
            "initiator_hp_max": self.initiator_hp_max,
            "companion_hp": list(self.companion_hp),
            "companion_hp_max": list(self.companion_hp_max),
            "seal_opponents": self.seal_opponents,
            "displaced_opponents": self.displaced_opponents,
            "seal_key": self.seal_key,
            "positional_key": self.positional_key,
            "driver_skill_key": self.driver_skill_key,
            "monster_skills": list(self.monster_skills),
            "support_skills": list(self.support_skills),
            "monster_effect": self.monster_effect,
            "allied_support": self.allied_support,
        }


@dataclass(frozen=True, slots=True)
class EncounterOutcome:
    """One encounter's outcome, its declaration and the decisions it recorded.

    ``scenario_seed`` is the documented scenario/archetype seed encoding of
    this encounter and ``combat_seed`` the process dice seed derived from it;
    neither is presented as a decision's selector seed, which every decision
    records for itself. ``session_id`` is the documented manual identity the
    encounter decided under and ``origin_session_id`` the durable identity the
    scratch database's own engagement computed before it was rewritten.
    """

    archetype: str
    situation: str
    seed_index: int
    intelligence: int
    outcome: str
    rounds: int
    decisions: tuple[DecisionSample, ...]
    scenario_seed: int = 0
    combat_seed: int = 0
    session_id: str = ""
    origin_session_id: str = ""
    scenario: ScenarioDeclaration | None = None
    roles: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EncounterConcentration:
    """One encounter's target concentration over its encounter-local roles.

    The counts are keyed by the encountering roles the decisions named
    (``player``, ``companion-1``, ``monster-0``) rather than by dbrefs a
    scratch database happened to allocate, so focus on one opponent role is
    distinguishable from choices spread across unrelated entities -- both
    within one encounter and across a batch.
    """

    archetype: str
    situation: str
    seed_index: int
    intelligence: int
    roles: Mapping[str, int]
    targeted_decisions: int
    top_role: str | None
    top_share: float

    def to_payload(self) -> dict[str, Any]:
        """Return this encounter's concentration as a JSON-safe mapping."""
        return {
            "situation": self.situation,
            "seed_index": self.seed_index,
            "intelligence": self.intelligence,
            "roles": dict(self.roles),
            "targeted_decisions": self.targeted_decisions,
            "top_role": self.top_role,
            "top_share": self.top_share,
        }


@dataclass(frozen=True, slots=True)
class EncounterMetrics:
    """One encounter's aggregated, report-ready metrics."""

    wins: int
    losses: int
    capped: int
    rounds_total: int
    encounters: int
    decisions: int
    highest_utility: int
    selected_illegal: int
    skill_distribution: Mapping[str, int]
    target_distribution: Mapping[str, int]
    rejections: int
    exclusions: int
    omitted_estimates: int
    omitted_families: int
    exhausted: int
    no_action_legal_restriction: int
    no_action_estimator_exclusion: int
    no_action_budget_omission: int
    no_action_capability_blocked: int
    approximation_flags: tuple[str, ...]
    concentration: tuple[EncounterConcentration, ...] = ()

    @property
    def mean_rounds(self) -> float:
        """The mean round count over the encounters the metric covers."""
        return (self.rounds_total / self.encounters) if self.encounters else 0.0

    @property
    def highest_utility_fraction(self) -> float:
        """The fraction of decisions whose choice had the highest utility."""
        return (self.highest_utility / self.decisions) if self.decisions else 0.0

    @property
    def mean_target_concentration(self) -> float:
        """The mean per-encounter top-role share over encounters with targets."""
        focused = [item.top_share for item in self.concentration if item.targeted_decisions]
        return (sum(focused) / len(focused)) if focused else 0.0

    @property
    def concentrated_encounters(self) -> int:
        """How many encounters put at least half their choices on one role."""
        return sum(
            1
            for item in self.concentration
            if item.targeted_decisions and item.top_share >= 0.5
        )


def _concentration(row: EncounterOutcome) -> EncounterConcentration:
    """Return one encounter's encounter-local target concentration."""
    roles: dict[str, int] = {}
    for decision in row.decisions:
        for role in decision.target_roles:
            roles[role] = roles.get(role, 0) + 1
    decisions = sum(1 for decision in row.decisions if decision.target_roles)
    if not roles:
        return EncounterConcentration(
            archetype=row.archetype,
            situation=row.situation,
            seed_index=row.seed_index,
            intelligence=row.intelligence,
            roles={},
            targeted_decisions=0,
            top_role=None,
            top_share=0.0,
        )
    top_role, top_count = sorted(roles.items(), key=lambda item: (-item[1], item[0]))[0]
    return EncounterConcentration(
        archetype=row.archetype,
        situation=row.situation,
        seed_index=row.seed_index,
        intelligence=row.intelligence,
        roles=dict(sorted(roles.items())),
        targeted_decisions=decisions,
        top_role=top_role,
        top_share=top_count / decisions if decisions else 0.0,
    )


def aggregate_encounters(outcomes: Iterable[EncounterOutcome]) -> EncounterMetrics:
    """Aggregate a batch of encounters into one report-ready metric block.

    Target counts are keyed by the encounter-local role a decision named, and
    the per-encounter concentration is computed before aggregation, so a
    batch's target distribution can never be read as repeated focus on one
    opponent when the dbrefs merely came from different encounters.
    """
    rows = tuple(outcomes)
    skills: dict[str, int] = {}
    targets: dict[str, int] = {}
    flags: list[str] = []
    counters = {
        "wins": 0, "losses": 0, "capped": 0, "rounds": 0, "decisions": 0,
        "highest": 0, "illegal": 0, "rejections": 0, "exclusions": 0,
        "omitted_estimates": 0, "omitted_families": 0, "exhausted": 0,
        "legal": 0, "estimator": 0, "budget": 0, "blocked": 0,
    }
    for row in rows:
        counters["rounds"] += row.rounds
        if row.outcome == OUTCOME_WIN:
            counters["wins"] += 1
        elif row.outcome == OUTCOME_LOSS:
            counters["losses"] += 1
        else:
            counters["capped"] += 1
        for decision in row.decisions:
            counters["decisions"] += 1
            counters["highest"] += int(decision.highest_utility)
            counters["illegal"] += int(decision.selected_illegal)
            counters["rejections"] += decision.rejections
            counters["exclusions"] += decision.exclusions
            counters["omitted_estimates"] += decision.omitted_estimates
            counters["omitted_families"] += decision.omitted_families
            counters["exhausted"] += int(decision.exhausted)
            flags.extend(decision.approximation_flags)
            if decision.skill_key is not None:
                skills[decision.skill_key] = skills.get(decision.skill_key, 0) + 1
            for role in decision.target_roles:
                targets[role] = targets.get(role, 0) + 1
            if decision.no_action == NO_ACTION_LEGAL_RESTRICTION:
                counters["legal"] += 1
            elif decision.no_action == NO_ACTION_ESTIMATOR_EXCLUSION:
                counters["estimator"] += 1
            elif decision.no_action == NO_ACTION_BUDGET_OMISSION:
                counters["budget"] += 1
            elif decision.no_action == NO_ACTION_CAPABILITY_BLOCKED:
                counters["blocked"] += 1
    return EncounterMetrics(
        wins=counters["wins"],
        losses=counters["losses"],
        capped=counters["capped"],
        rounds_total=counters["rounds"],
        encounters=len(rows),
        decisions=counters["decisions"],
        highest_utility=counters["highest"],
        selected_illegal=counters["illegal"],
        skill_distribution=dict(sorted(skills.items())),
        target_distribution=dict(sorted(targets.items())),
        rejections=counters["rejections"],
        exclusions=counters["exclusions"],
        omitted_estimates=counters["omitted_estimates"],
        omitted_families=counters["omitted_families"],
        exhausted=counters["exhausted"],
        no_action_legal_restriction=counters["legal"],
        no_action_estimator_exclusion=counters["estimator"],
        no_action_budget_omission=counters["budget"],
        no_action_capability_blocked=counters["blocked"],
        approximation_flags=tuple(sorted(set(flags))),
        concentration=tuple(_concentration(row) for row in rows),
    )


# ---------------------------------------------------------------------------
# Performance metrics (simulation design section 6)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class PolicyTiming:
    """One mode's warm complete-policy timing and work counters."""

    mode: str
    cold_ms: float
    samples_ms: tuple[float, ...]
    p50_ms: float
    p95_ms: float
    queries: int
    examined: int
    accepted: int
    omitted: int
    dice_isolated: bool
    budget_ms: float


@dataclass(frozen=True, slots=True)
class ScalingSample:
    """One examined-proposal-budget probe on ONE fixed battlefield.

    The probe varies only the decision's examined-proposal budget on the
    reference roster's own actor/participant data, and reports the measured
    work: ORM ``queries``, the ``examined`` proposals (accepted candidates
    plus rejections plus mandatory-filter exclusions), the ``accepted`` plans
    that reached scoring and the proposals the budget ``omitted``.
    """

    budget: int
    queries: int
    examined: int
    accepted: int
    omitted: int


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    """The whole-policy performance scenario's complete result."""

    participants: int
    owned_skills: int
    candidate_budget: int
    warmups: int
    measurements: int
    timings: tuple[PolicyTiming, ...]
    scaling: tuple[ScalingSample, ...]
    budget_ms: float

    @property
    def budget_met(self) -> bool:
        """Whether every measured mode stayed inside the warm p95 budget."""
        return all(timing.p95_ms <= self.budget_ms for timing in self.timings)


def _percentile(values: Sequence[float], fraction: float) -> float:
    """Return the nearest-rank percentile of one finite sample."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[rank]


def build_policy_timing(
    *,
    mode: str,
    cold_ms: float,
    samples_ms: Sequence[float],
    queries: int,
    examined: int,
    accepted: int,
    omitted: int,
    dice_isolated: bool,
    budget_ms: float = PERFORMANCE_P95_BUDGET_MS,
) -> PolicyTiming:
    """Assemble one mode's timing block from its measured samples."""
    samples = tuple(float(value) for value in samples_ms)
    return PolicyTiming(
        mode=mode,
        cold_ms=float(cold_ms),
        samples_ms=samples,
        p50_ms=_percentile(samples, 0.50),
        p95_ms=_percentile(samples, 0.95),
        queries=int(queries),
        examined=int(examined),
        accepted=int(accepted),
        omitted=int(omitted),
        dice_isolated=bool(dice_isolated),
        budget_ms=float(budget_ms),
    )


# ---------------------------------------------------------------------------
# Report assembly, rendering and writing
# ---------------------------------------------------------------------------
def environment_header(*, baseline_commit: str, configuration_fingerprint: str,
                       algorithm_version: int) -> dict[str, Any]:
    """Return the report header every operation shares.

    The baseline commit, both fingerprints, the Python/Evennia versions and
    the host wall-clock identity: the reproducibility facts a later reader
    needs to place one manual report beside another.
    """
    import evennia

    # The installed package publishes its version as ``__version__`` (the
    # historical ``VERSION`` attribute is absent), so the header records the
    # real dependency version instead of an "unknown" placeholder.
    version = getattr(evennia, "__version__", None) or getattr(
        evennia, "VERSION", "unknown"
    )
    return {
        "schema": "monster-ai-manual-evidence/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": baseline_commit,
        "algorithm_version": algorithm_version,
        "configuration_fingerprint": configuration_fingerprint,
        "python_version": platform.python_version(),
        "evennia_version": str(version),
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "clock": "monotonic",
        },
    }


def selector_report_payload(report: SelectorReport) -> dict[str, Any]:
    """Return one selector check as a JSON-safe mapping."""
    return {
        "candidates": {
            SELECTOR_HIGH_KEY: SELECTOR_HIGH_KEY,
            SELECTOR_LOW_KEY: SELECTOR_LOW_KEY,
            "utility_gap": SELECTOR_UTILITY_GAP,
            "canonical_order": list(report.candidate_order),
        },
        "intelligences": list(INTELLIGENCE_VALUES),
        "temperatures": {
            "low": report.low_temperature,
            "high": report.high_temperature,
        },
        "seed_encoding_version": SEED_ENCODING_VERSION,
        "seeds": [pair.seed_index for pair in report.pairs],
        "replicates": [
            {
                "seed_index": pair.seed_index,
                "seed": pair.seed,
                "low_choice": pair.low_choice,
                "high_choice": pair.high_choice,
            }
            for pair in report.pairs
        ],
        "counts": {
            "low": report.low_high_utility,
            "high": report.high_high_utility,
            "total": report.total,
        },
        "proportions": {
            "low": report.low_probability,
            "high": report.high_probability,
        },
        "wilson": {
            "low": list(report.low_wilson),
            "high": list(report.high_wilson),
        },
        "paired_difference": report.difference,
        "margin_required": report.margin_required,
        "margin_met": report.margin_met,
    }


def encounter_metrics_payload(metrics: EncounterMetrics) -> dict[str, Any]:
    """Return one encounter metric block as a JSON-safe mapping."""
    return {
        "encounters": metrics.encounters,
        "wins": metrics.wins,
        "losses": metrics.losses,
        "capped": metrics.capped,
        "rounds_total": metrics.rounds_total,
        "mean_rounds": metrics.mean_rounds,
        "mean_rounds_denominator": metrics.encounters,
        "decisions": metrics.decisions,
        "highest_utility": metrics.highest_utility,
        "highest_utility_fraction": metrics.highest_utility_fraction,
        "skill_distribution": dict(metrics.skill_distribution),
        "target_distribution": dict(metrics.target_distribution),
        "target_concentration": {
            "encounters": [item.to_payload() for item in metrics.concentration],
            "mean_top_role_share": metrics.mean_target_concentration,
            "concentrated_encounters": metrics.concentrated_encounters,
        },
        "rejections": metrics.rejections,
        "exclusions": metrics.exclusions,
        "omitted_estimates": metrics.omitted_estimates,
        "omitted_families": metrics.omitted_families,
        "exhausted": metrics.exhausted,
        "selected_illegal": metrics.selected_illegal,
        "no_action": {
            NO_ACTION_LEGAL_RESTRICTION: metrics.no_action_legal_restriction,
            NO_ACTION_ESTIMATOR_EXCLUSION: metrics.no_action_estimator_exclusion,
            NO_ACTION_BUDGET_OMISSION: metrics.no_action_budget_omission,
            NO_ACTION_CAPABILITY_BLOCKED: metrics.no_action_capability_blocked,
        },
        "approximation_flags": list(metrics.approximation_flags),
    }


def performance_report_payload(report: PerformanceReport) -> dict[str, Any]:
    """Return one performance scenario as a JSON-safe mapping."""
    return {
        "envelope": {
            "participants": report.participants,
            "owned_skills": report.owned_skills,
            "candidate_budget": report.candidate_budget,
            "warmups": report.warmups,
            "measurements": report.measurements,
            "budget_ms": report.budget_ms,
        },
        "timings": [
            {
                "mode": timing.mode,
                "cold_ms": timing.cold_ms,
                "p50_ms": timing.p50_ms,
                "p95_ms": timing.p95_ms,
                "queries": timing.queries,
                "examined": timing.examined,
                "accepted": timing.accepted,
                "omitted": timing.omitted,
                "dice_isolated": timing.dice_isolated,
                "samples_ms": list(timing.samples_ms),
            }
            for timing in report.timings
        ],
        "scaling": [
            {
                "budget": item.budget,
                "queries": item.queries,
                "examined": item.examined,
                "accepted": item.accepted,
                "omitted": item.omitted,
            }
            for item in report.scaling
        ],
        "budget_met": report.budget_met,
    }


def archetype_report_payload(
    *,
    archetype: str,
    encounters: Sequence[EncounterOutcome],
    header: Mapping[str, Any],
    include_traces: bool = False,
) -> dict[str, Any]:
    """Return one named archetype campaign as a JSON-safe mapping.

    The report serializes the materialized scenario declarations the run
    built, and every encounter keeps a per-decision replay record (effective
    seed, execution identity, sampled plans, selected plan and the decision's
    own initial observation snapshot). ``include_traces`` adds the opt-in
    normalized decision trace to each record; the default report stays the
    compact machine-readable evidence.
    """
    grouped: dict[tuple[str, int], EncounterMetrics] = {}
    for situation in SITUATION_NAMES:
        for intelligence in INTELLIGENCE_VALUES:
            rows = [
                row
                for row in encounters
                if row.situation == situation and row.intelligence == intelligence
            ]
            grouped[(situation, intelligence)] = aggregate_encounters(rows)
    scenarios: dict[str, Any] = {}
    for row in encounters:
        if row.scenario is not None and row.scenario.name not in scenarios:
            scenarios[row.scenario.name] = row.scenario.to_payload()
    raw = [
        {
            "situation": row.situation,
            "seed_index": row.seed_index,
            "scenario_seed": row.scenario_seed,
            "combat_seed": row.combat_seed,
            "intelligence": row.intelligence,
            "session_id": row.session_id,
            "engine_session_id": row.origin_session_id,
            "outcome": row.outcome,
            "rounds": row.rounds,
            "scenario": None if row.scenario is None else row.scenario.name,
            "roles": dict(row.roles),
            "decisions": len(row.decisions),
            "highest_utility": sum(1 for item in row.decisions if item.highest_utility),
            "selected_illegal": sum(1 for item in row.decisions if item.selected_illegal),
            "no_action": {
                NO_ACTION_LEGAL_RESTRICTION: sum(
                    1 for item in row.decisions if item.no_action == NO_ACTION_LEGAL_RESTRICTION
                ),
                NO_ACTION_ESTIMATOR_EXCLUSION: sum(
                    1 for item in row.decisions if item.no_action == NO_ACTION_ESTIMATOR_EXCLUSION
                ),
                NO_ACTION_BUDGET_OMISSION: sum(
                    1 for item in row.decisions if item.no_action == NO_ACTION_BUDGET_OMISSION
                ),
            },
            "decision_records": [
                item.to_payload(include_trace=include_traces) for item in row.decisions
            ],
        }
        for row in encounters
    ]
    return {
        **dict(header),
        "operation": "archetype",
        "archetype": archetype,
        "allocation": {
            "situations": list(SITUATION_NAMES),
            "seeds": list(CAMPAIGN_SEED_INDICES),
            "intelligences": list(INTELLIGENCE_VALUES),
            "encounters": len(encounters),
            "round_cap": ROUND_CAP,
        },
        "manual_selection_seam": {
            "session_identity": f"{MANUAL_SESSION_PREFIX}:<situation>:<archetype>:<seed_index>",
            "actor_identity": f"{MANUAL_ACTOR_PREFIX}:<encounter-role>",
            "seed_inputs": [
                "session id",
                "actual round index",
                "actor id",
                "action slot",
                "configuration fingerprint",
            ],
            "paired_intelligence_shared_inputs": [
                "session id",
                "round index",
                "actor id",
                "action slot",
            ],
        },
        "scenarios": scenarios,
        "metrics": {
            f"{situation}@{intelligence}": encounter_metrics_payload(metrics)
            for (situation, intelligence), metrics in grouped.items()
        },
        "overall": encounter_metrics_payload(aggregate_encounters(encounters)),
        "unresolved": [
            {
                "situation": row.situation,
                "seed_index": row.seed_index,
                "intelligence": row.intelligence,
                "rounds": row.rounds,
            }
            for row in encounters
            if row.outcome == OUTCOME_CAPPED
        ],
        "raw": raw,
    }


def trace_export_payload(
    *, archetype: str, encounters: Sequence[EncounterOutcome]
) -> dict[str, Any]:
    """Return the opt-in detailed-trace export of one archetype campaign.

    Every recorded decision's normalized
    :meth:`~world.rules.monster_ai.trace.DecisionTrace.to_payload` projection,
    identified by the encounter and decision identity it belongs to. The
    projection is the decision's own read-only record -- observations, plans,
    rejections, counters and the selected plan -- and never a queued or
    private intent.
    """
    records: list[dict[str, Any]] = []
    for row in encounters:
        for decision in row.decisions:
            if decision.trace is None:
                continue
            records.append(
                {
                    "situation": row.situation,
                    "seed_index": row.seed_index,
                    "intelligence": row.intelligence,
                    "session_id": row.session_id,
                    "decision_index": decision.index,
                    "seed": decision.seed,
                    "scope": _scope_payload(decision.scope),
                    "trace": decision.trace,
                }
            )
    return {
        "schema": "monster-ai-manual-evidence/1",
        "operation": "traces",
        "archetype": archetype,
        "decisions": records,
    }


def write_trace_export(directory: Path | str, payload: Mapping[str, Any], *, stem: str) -> Path:
    """Write the opt-in detailed-trace export beside one report and return its path."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{stem}-traces.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _selector_markdown(report: dict[str, Any]) -> list[str]:
    counts = report["counts"]
    difference = report["paired_difference"]
    verdict = "met" if report["margin_met"] else "NOT met"
    return [
        "# Manual selector check (monster-ai-manual-evidence)",
        "",
        f"- Baseline commit: `{report.get('baseline_commit', 'unknown')}`",
        f"- Algorithm version: {report.get('algorithm_version')}",
        f"- Configuration fingerprint: `{report.get('configuration_fingerprint')}`",
        f"- Seeds: {counts['total']} documented injected seeds at intelligence "
        f"{report['intelligences']}",
        f"- Utility gap: {report['candidates']['utility_gap']}",
        "",
        "| intelligence | highest-utility count | proportion | Wilson 95% |",
        "| --- | ---: | ---: | --- |",
        f"| {report['intelligences'][0]} | {counts['low']} | {report['proportions']['low']:.3f} | "
        f"[{report['wilson']['low'][0]:.3f}, {report['wilson']['low'][1]:.3f}] |",
        f"| {report['intelligences'][1]} | {counts['high']} | {report['proportions']['high']:.3f} | "
        f"[{report['wilson']['high'][0]:.3f}, {report['wilson']['high'][1]:.3f}] |",
        "",
        f"Paired difference (high - low): **{difference:.3f}** "
        f"(required >= {report['margin_required']:.2f}): {verdict}.",
        "",
        "This is an isolated selector measurement, not an encounter win-rate "
        "result. Identical seeds, input and configuration reproduce every "
        "chosen candidate.",
    ]


def _encounters_markdown(report: dict[str, Any]) -> list[str]:
    overall = report["overall"]
    lines = [
        f"# Manual archetype campaign: `{report['archetype']}` (monster-ai-manual-evidence)",
        "",
        f"- Baseline commit: `{report.get('baseline_commit', 'unknown')}`",
        f"- Configuration fingerprint: `{report.get('configuration_fingerprint')}`",
        f"- Allocation: {report['allocation']['encounters']} encounters "
        f"({report['allocation']['situations']} situations x "
        f"{len(report['allocation']['seeds'])} seeds x "
        f"{len(report['allocation']['intelligences'])} intelligence values), round cap "
        f"{report['allocation']['round_cap']}",
        "",
        f"Overall: {overall['wins']} win / {overall['losses']} loss / "
        f"{overall['capped']} capped, mean rounds {overall['mean_rounds']:.2f} "
        f"(denominator {overall['mean_rounds_denominator']} encounters), "
        f"highest-utility fraction {overall['highest_utility_fraction']:.3f}, "
        f"selected illegal {overall['selected_illegal']}.",
        "",
        "No-action causes (legal restriction / estimator exclusion / budget "
        f"omission): {overall['no_action']['legal_restriction']} / "
        f"{overall['no_action']['estimator_exclusion']} / "
        f"{overall['no_action']['budget_omission']}.",
        "",
        "Target concentration over encounter-local roles: mean top-role share "
        f"{overall['target_concentration']['mean_top_role_share']:.3f}, "
        f"{overall['target_concentration']['concentrated_encounters']} encounter(s) "
        "put at least half their choices on one role. Every decision's effective "
        "seed, execution identity, sampled plans, selected plan and initial "
        "observation snapshot are recorded in `raw[].decision_records`.",
        "",
        "| situation | intelligence | win/loss/capped | mean rounds | highest-utility |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for key, metrics in report["metrics"].items():
        situation, intelligence = key.rsplit("@", 1)
        lines.append(
            f"| {situation} | {intelligence} | {metrics['wins']}/{metrics['losses']}/"
            f"{metrics['capped']} | {metrics['mean_rounds']:.2f} | "
            f"{metrics['highest_utility_fraction']:.3f} |"
        )
    lines += [
        "",
        f"Unresolved (capped) encounters: {len(report['unresolved'])}. "
        "Two seeds per situation cannot certify balance; the acceptance claims "
        "are valid execution, replay, distinct profiles and intelligence "
        "affecting decision quality while stats stay identical.",
    ]
    return lines


def _performance_markdown(report: dict[str, Any]) -> list[str]:
    envelope = report["envelope"]
    host = report.get("host") or {}
    lines = [
        "# Manual performance scenario (monster-ai-manual-evidence)",
        "",
        f"- Baseline commit: `{report.get('baseline_commit', 'unknown')}`",
        f"- Configuration fingerprint: `{report.get('configuration_fingerprint')}`",
        f"- Host: `{host.get('node', 'unknown')}` / {host.get('platform', 'unknown')} "
        f"(clock {host.get('clock', 'monotonic')})",
        f"- Envelope: {envelope['participants']} participants, up to "
        f"{envelope['owned_skills']} owned active skills, candidate budget "
        f"{envelope['candidate_budget']}; {envelope['warmups']} warm-ups then "
        f"{envelope['measurements']} measurements per mode, one cold call",
        "",
        "| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for timing in report["timings"]:
        lines.append(
            f"| {timing['mode']} | {timing['cold_ms']:.2f} | {timing['p50_ms']:.2f} | "
            f"{timing['p95_ms']:.2f} | {timing['queries']} | {timing['examined']} | "
            f"{timing['accepted']} | {timing['omitted']} | {timing['dice_isolated']} |"
        )
    lines += [
        "",
        f"Warm p95 budget {envelope['budget_ms']:.0f} ms: "
        f"{'met' if report['budget_met'] else 'NOT met'}.",
        "",
        "| examined-proposal budget | queries | examined | accepted | omitted |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report["scaling"]:
        lines.append(
            f"| {item['budget']} | {item['queries']} | {item['examined']} | "
            f"{item['accepted']} | {item['omitted']} |"
        )
    lines += [
        "",
        "One fixed reference battlefield is probed at three examined-proposal "
        "budgets: `examined` counts every proposal the decision examined "
        "(accepted candidates, rejections and mandatory-filter exclusions) and "
        "`omitted` the proposals the budget left unexamined. Query work may "
        "scale with the initial participant/owned-skill read but never with "
        "the proposals a decision examined or omitted. This is a manual "
        "measurement on the recorded host, never a permanent timing assertion.",
    ]
    return lines


def render_markdown(report: Mapping[str, Any]) -> str:
    """Return the compact Markdown interpretation of one report payload."""
    operation = report.get("operation")
    if operation == "selector":
        lines = _selector_markdown(report)
    elif operation == "archetype":
        lines = _encounters_markdown(report)
    elif operation == "performance":
        lines = _performance_markdown(report)
    else:
        raise ValueError(f"unknown report operation: {operation!r}")
    return "\n".join(lines) + "\n"


def write_reports(directory: Path | str, report: Mapping[str, Any], *, stem: str) -> tuple[Path, Path]:
    """Write one report's JSON and Markdown forms, returning both paths.

    The JSON is the machine-readable evidence; the Markdown is its compact
    interpretation. Both land beside each other under the caller's scratch
    directory so a manual run never touches a tracked artifact by accident.
    """
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / f"{stem}.json"
    markdown_path = target / f"{stem}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


# ---------------------------------------------------------------------------
# Operation orchestration
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class OperationResult:
    """One operation's report payload and its written report paths."""

    report: Mapping[str, Any]
    paths: tuple[Path, ...] = field(default=())


SelectorEngine = Callable[..., SelectorReport]
PerformanceEngine = Callable[[], PerformanceReport]
ArchetypeEngine = Callable[..., Sequence[EncounterOutcome]]


def run_operation(
    *,
    operation: str,
    harness: Any = None,
    header: Mapping[str, Any],
    output: Path | str,
    archetype: str | None = None,
    selector_count: int = SELECTOR_SEED_COUNT,
    detailed_trace: bool = False,
) -> OperationResult:
    """Run exactly one explicit operation and write its report.

    A single invocation never implicitly runs the other operations or every
    archetype: the selector check, one named archetype campaign and the
    performance scenario are independent, and the named archetype is required
    for the campaign. ``detailed_trace`` is the opt-in trace export: it never
    enlarges the compact report's arithmetic, it writes the campaign's
    normalized per-decision traces as their own JSON document beside it.
    """
    paths: tuple[Path, ...] = ()
    if operation == "selector":
        result = run_selector_operation(seed_count=selector_count)
        payload = {**dict(header), "operation": "selector", **selector_report_payload(result)}
        stem = "selector-check"
    elif operation == "archetype":
        if not archetype:
            raise ValueError("the archetype operation requires --archetype NAME")
        outcomes = harness.run_archetype_campaign(archetype)
        payload = archetype_report_payload(
            archetype=archetype, encounters=outcomes, header=header
        )
        stem = f"archetype-{archetype}"
        paths = write_reports(output, payload, stem=stem)
        if detailed_trace:
            paths = paths + (
                write_trace_export(
                    output,
                    trace_export_payload(archetype=archetype, encounters=outcomes),
                    stem=stem,
                ),
            )
        return OperationResult(report=payload, paths=paths)
    elif operation == "performance":
        result = harness.run_performance_scenario()
        payload = {**dict(header), "operation": "performance", **performance_report_payload(result)}
        stem = "performance"
    else:
        raise ValueError(f"unknown operation: {operation!r}")
    paths = write_reports(output, payload, stem=stem)
    return OperationResult(report=payload, paths=paths)