"""Synthetic labeled calibration sets for deterministic narrative attention.

Attention never calls a model and never writes state, so calibration is a pure,
offline evaluation: labeled candidate/context inputs (ground truth) are ranked
by :func:`world.narrative.attention.rank_attention` and the measured order,
component values, reason codes and focus bounds are recorded.

The committed ``attention_calibration_report.json`` is the durable record of the
calibrated weights/limits for W3 (``python -m
world.narrative.attention_calibration``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from world.narrative.attention import (
    DEFAULT_ATTENTION_CONFIG,
    REASON_BELOW_FOCUS_LIMIT,
    REASON_IN_COOLDOWN,
    REASON_LOCATION_UNREACHABLE,
    REASON_NOT_EXECUTABLE,
    REASON_NOT_INVESTED,
    REASON_SCHEDULE_BLOCKED,
    REASON_SELECTED,
    SOURCE_REQUEST,
    SOURCE_THREAD,
    AttentionCandidate,
    AttentionConfig,
    AttentionContext,
    EngagementSignals,
    rank_attention,
)

REPORT_VERSION = "attention_calibration_v1"
DEFAULT_REPORT_PATH = Path(__file__).with_name("attention_calibration_report.json")

# A fixed reference instant so the calibration is fully deterministic.
NOW_TICK = 1_000_000
OWNER = "101"
OWNER_LOCATION = "room:hall"


@dataclass(frozen=True)
class LabeledAttentionCase:
    """One synthetic labeled case: inputs plus expected eligible/focus results."""

    case_id: str
    description: str
    context: AttentionContext
    candidates: tuple[AttentionCandidate, ...]
    expected_selected: tuple[str, ...] = ()
    expected_excluded: tuple[tuple[str, str], ...] = ()
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG


@dataclass(frozen=True)
class AttentionCaseResult:
    """The measured outcome of one calibration case."""

    case_id: str
    description: str
    actual_selected: tuple[str, ...]
    actual_ranked: tuple[str, ...]
    actual_excluded: tuple[tuple[str, str], ...]
    reason_counts: tuple[tuple[str, int], ...]
    components: tuple[tuple[str, float], ...]
    order_matches: bool
    selections_match: bool
    exclusions_match: bool


@dataclass(frozen=True)
class AttentionCalibrationMetrics:
    """Aggregate calibration metrics across every labeled case."""

    total_cases: int
    cases_matched: int
    focus_precision: float
    focus_recall: float
    exclusions_matched: int
    exclusions_expected: int


@dataclass(frozen=True)
class AttentionCalibrationReport:
    """The committed calibration report."""

    report_version: str
    config_version: str
    focus_limit: int
    weights: dict[str, Any]
    engagement_weights: dict[str, Any]
    saturation: dict[str, Any]
    cases: tuple[AttentionCaseResult, ...]
    metrics: AttentionCalibrationMetrics
    notes: tuple[str, ...] = field(default_factory=tuple)


def _context(
    *,
    blocked: tuple[str, ...] = (),
    reachable: tuple[str, ...] = (),
) -> AttentionContext:
    return AttentionContext(
        owner_id=OWNER,
        now_tick=NOW_TICK,
        owner_location=OWNER_LOCATION,
        reachable_locations=frozenset(reachable),
        blocked_participants=frozenset(blocked),
    )


def _thread(
    candidate_id: str,
    *,
    invested: bool = True,
    confirmed: bool = False,
    knowledge: bool = True,
    authoritative: bool = True,
    capability: str = "dialogue",
    required_location: str = OWNER_LOCATION,
    unresolved_stakes: int = 1,
    relationship: int = 0,
    deadline_tick: Optional[int] = None,
    engagement: Optional[EngagementSignals] = None,
    repetition: int = 0,
    last_activity_tick: Optional[int] = None,
    participants: tuple[str, ...] = ("201",),
    salience: int = 0,
    source_kind: str = SOURCE_THREAD,
) -> AttentionCandidate:
    return AttentionCandidate(
        candidate_id=candidate_id,
        source_kind=source_kind,
        source_ref=candidate_id.split(":", 1)[1],
        revision=1,
        origin="event:synthetic:calibration",
        participants=participants,
        invested=invested,
        confirmed=confirmed,
        knowledge=knowledge,
        authoritative=authoritative,
        required_location=required_location,
        capability=capability,
        unresolved_stakes=unresolved_stakes,
        relationship=relationship,
        deadline_tick=deadline_tick,
        engagement=engagement or EngagementSignals(),
        repetition=repetition,
        last_activity_tick=last_activity_tick,
        salience=salience,
    )


def _request(
    submission_key: str,
    *,
    authoritative: bool = True,
    submitted_tick: int = NOW_TICK - 2 * 3600,
) -> AttentionCandidate:
    return AttentionCandidate(
        candidate_id=f"request:{submission_key}",
        source_kind=SOURCE_REQUEST,
        source_ref=submission_key,
        revision=1,
        origin="confirmed_request",
        participants=(OWNER,),
        invested=False,
        confirmed=True,
        knowledge=True,
        authoritative=authoritative,
        required_location="",
        capability="quest",
        last_activity_tick=submitted_tick,
    )


ACTIVE = EngagementSignals(
    dialogue_initiations=3, sustained_correspondence=2, clue_questions=1, participation=1
)
PASSIVE = EngagementSignals(passive_receipts=5)


ATTENTION_CALIBRATION_CASES: tuple[LabeledAttentionCase, ...] = (
    LabeledAttentionCase(
        case_id="unrelated_high_salience_ineligible",
        description=(
            "A high-salience automatic candidate with no invested source or confirmed "
            "request is ineligible before ranking."
        ),
        context=_context(),
        candidates=(
            _thread(
                "thread:unrelated",
                invested=False,
                confirmed=False,
                unresolved_stakes=3,
                salience=9,
            ),
        ),
        expected_selected=(),
        expected_excluded=(("thread:unrelated", REASON_NOT_INVESTED),),
    ),
    LabeledAttentionCase(
        case_id="location_unreachable_excluded",
        description=(
            "An urgent candidate whose required location is unreachable is excluded "
            "regardless of its score."
        ),
        context=_context(reachable=("room:annex",)),
        candidates=(
            _thread(
                "thread:far",
                required_location="room:distant",
                unresolved_stakes=3,
                deadline_tick=NOW_TICK + 60,
            ),
        ),
        expected_selected=(),
        expected_excluded=(("thread:far", REASON_LOCATION_UNREACHABLE),),
    ),
    LabeledAttentionCase(
        case_id="schedule_blocked_excluded",
        description="A candidate whose participant NPC is busy is excluded before scoring.",
        context=_context(blocked=("201",)),
        candidates=(_thread("thread:busy", unresolved_stakes=3),),
        expected_selected=(),
        expected_excluded=(("thread:busy", REASON_SCHEDULE_BLOCKED),),
    ),
    LabeledAttentionCase(
        case_id="capability_not_executable_excluded",
        description=(
            "A candidate whose capability has no deterministic owner is excluded "
            "regardless of its score."
        ),
        context=_context(),
        candidates=(
            _thread("thread:dragon", capability="summon_dragon", unresolved_stakes=3),
        ),
        expected_selected=(),
        expected_excluded=(("thread:dragon", REASON_NOT_EXECUTABLE),),
    ),
    LabeledAttentionCase(
        case_id="confirmed_request_eligible",
        description=(
            "A valid explicitly confirmed request is eligible as player-originated "
            "direction without invested history."
        ),
        context=_context(),
        candidates=(_request("draft_synthetic:v1"),),
        expected_selected=("request:draft_synthetic:v1",),
    ),
    LabeledAttentionCase(
        case_id="superseded_request_excluded",
        description=(
            "An older confirmed version superseded by a newer confirmed version is "
            "excluded so only the authoritative direction competes."
        ),
        context=_context(),
        candidates=(
            _request("draft_synthetic:v1", authoritative=False),
            _request("draft_synthetic:v2"),
        ),
        expected_selected=("request:draft_synthetic:v2",),
        expected_excluded=(("request:draft_synthetic:v1", "superseded_request"),),
    ),
    LabeledAttentionCase(
        case_id="active_engagement_outweighs_passive_receipt",
        description=(
            "With every other component identical, initiated visits/questions and sent "
            "correspondence outrank a thread with only passive receipt."
        ),
        context=_context(),
        candidates=(
            _thread("thread:passive", engagement=PASSIVE),
            _thread("thread:active", engagement=ACTIVE),
        ),
        expected_selected=("thread:active", "thread:passive"),
    ),
    LabeledAttentionCase(
        case_id="cooldown_penalises_recent_activity",
        description=(
            "At equal stakes, a thread developed inside the cooldown window ranks below "
            "one that has rested."
        ),
        context=_context(),
        candidates=(
            _thread("thread:fresh", last_activity_tick=NOW_TICK - 60),
            _thread("thread:rested", last_activity_tick=NOW_TICK - 7200),
        ),
        expected_selected=("thread:rested", "thread:fresh"),
    ),
    LabeledAttentionCase(
        case_id="deterministic_tie_break",
        description="Identical scores order by candidate identity for a stable offline result.",
        context=_context(),
        candidates=(
            _thread("thread:beta"),
            _thread("thread:alpha"),
        ),
        expected_selected=("thread:alpha", "thread:beta"),
    ),
    LabeledAttentionCase(
        case_id="focus_limit_bounds_selection_only",
        description=(
            "The focus limit trims the selected set only; eligible candidates stay ranked "
            "and unselected story state is preserved."
        ),
        context=_context(),
        candidates=(
            _thread("thread:c1", unresolved_stakes=3),
            _thread("thread:c2", unresolved_stakes=3),
            _thread("thread:c3", unresolved_stakes=2),
            _thread("thread:c4", unresolved_stakes=1),
            _thread("thread:c5", unresolved_stakes=1),
            _thread("thread:c6", invested=False),
        ),
        expected_selected=("thread:c1", "thread:c2"),
        expected_excluded=(("thread:c6", REASON_NOT_INVESTED),),
        config=AttentionConfig(focus_limit=2),
    ),
    LabeledAttentionCase(
        case_id="heavy_recent_activity_yields_to_rested_thread",
        description=(
            "Cooldown and repetition penalties deliberately outweigh a higher stake for a "
            "just-developed thread, so attention does not repeat it: the rested, lower-stake "
            "thread ranks first. This distinction is intentional, not a bug."
        ),
        context=_context(),
        candidates=(
            _thread(
                "thread:heavy",
                unresolved_stakes=3,
                repetition=4,
                last_activity_tick=NOW_TICK - 10,
            ),
            _thread("thread:rested_low", unresolved_stakes=1, last_activity_tick=None),
        ),
        expected_selected=("thread:rested_low", "thread:heavy"),
    ),
    LabeledAttentionCase(
        case_id="aging_request_yields_to_rested_thread",
        description=(
            "A just-submitted confirmed request carries its own cooldown, so an actively "
            "invested, rested thread at the same stake still ranks first."
        ),
        context=_context(),
        candidates=(
            _request("draft_synthetic:v9", submitted_tick=NOW_TICK),
            _thread("thread:rested", required_location="", unresolved_stakes=0),
        ),
        expected_selected=("thread:rested", "request:draft_synthetic:v9"),
    ),
)


def run_calibration(
    config: AttentionConfig = DEFAULT_ATTENTION_CONFIG,
) -> AttentionCalibrationReport:
    """Rank every labeled case and measure the calibrated behavior."""
    results: list[AttentionCaseResult] = []
    matched = 0
    matched_selected = 0
    expected_selected_total = 0
    actual_selected_total = 0
    exclusions_matched = 0
    exclusions_expected = 0

    for case in ATTENTION_CALIBRATION_CASES:
        effective = case.config if case.config != DEFAULT_ATTENTION_CONFIG else config
        decision = rank_attention(case.candidates, case.context, effective)
        actual_selected = tuple(item.candidate.candidate_id for item in decision.selected)
        actual_ranked = tuple(item.candidate.candidate_id for item in decision.ranked)
        actual_excluded = tuple(
            (exclusion.candidate.candidate_id, reason)
            for exclusion in decision.excluded
            for reason in exclusion.reasons
        )
        expected_order = case.expected_selected
        order_matches = actual_selected == expected_order and (
            not expected_order or actual_ranked[: len(expected_order)] == expected_order
        )
        selections_match = set(actual_selected) == set(expected_order)
        exclusions_ok = all(pair in actual_excluded for pair in case.expected_excluded)
        if order_matches and exclusions_ok:
            matched += 1
        matched_selected += len(set(actual_selected) & set(expected_order))
        expected_selected_total += len(expected_order)
        actual_selected_total += len(actual_selected)
        exclusions_matched += sum(1 for pair in case.expected_excluded if pair in actual_excluded)
        exclusions_expected += len(case.expected_excluded)

        components: list[tuple[str, float]] = []
        for selection in decision.ranked:
            for component in selection.components:
                components.append((f"{selection.candidate.candidate_id}:{component.name}", component.raw))

        results.append(
            AttentionCaseResult(
                case_id=case.case_id,
                description=case.description,
                actual_selected=actual_selected,
                actual_ranked=actual_ranked,
                actual_excluded=actual_excluded,
                reason_counts=decision.reason_counts,
                components=tuple(components),
                order_matches=order_matches,
                selections_match=selections_match,
                exclusions_match=exclusions_ok,
            )
        )

    precision = (matched_selected / actual_selected_total) if actual_selected_total else 1.0
    recall = (matched_selected / expected_selected_total) if expected_selected_total else 1.0
    metrics = AttentionCalibrationMetrics(
        total_cases=len(ATTENTION_CALIBRATION_CASES),
        cases_matched=matched,
        focus_precision=round(precision, 4),
        focus_recall=round(recall, 4),
        exclusions_matched=exclusions_matched,
        exclusions_expected=exclusions_expected,
    )
    weights = asdict(config.weights)
    return AttentionCalibrationReport(
        report_version=REPORT_VERSION,
        config_version=config.version,
        focus_limit=config.focus_limit,
        weights=weights,
        engagement_weights=asdict(config.engagement_weights),
        saturation={
            "stakes_saturation": config.stakes_saturation,
            "engagement_saturation": config.engagement_saturation,
            "relationship_saturation": config.relationship_saturation,
            "deadline_horizon_ticks": config.deadline_horizon_ticks,
            "repetition_saturation": config.repetition_saturation,
            "cooldown_ticks": config.cooldown_ticks,
        },
        cases=tuple(results),
        metrics=metrics,
        notes=(
            "Attention is pure and offline: no model call, no state write.",
            "repetition and cooldown both derive from durable thread activity "
            "(development ticks and link creation ticks); their penalties are "
            "deliberately allowed to outweigh a higher stake for a just-developed thread.",
            "passive receipt (collection/reading) is recorded but contributes zero to the "
            "engagement score.",
        ),
    )


def save_report(report: AttentionCalibrationReport, filepath: Path) -> None:
    """Serialize the calibration report to JSON deterministically."""
    data = asdict(report)
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reason_labels() -> tuple[str, ...]:
    return (
        REASON_SELECTED,
        REASON_BELOW_FOCUS_LIMIT,
        REASON_IN_COOLDOWN,
        REASON_NOT_INVESTED,
        REASON_SCHEDULE_BLOCKED,
        REASON_NOT_EXECUTABLE,
        REASON_LOCATION_UNREACHABLE,
    )


if __name__ == "__main__":  # pragma: no cover - manual calibration entry point
    calibration = run_calibration()
    save_report(calibration, DEFAULT_REPORT_PATH)
    print(
        f"cases={calibration.metrics.cases_matched}/{calibration.metrics.total_cases} "
        f"report={DEFAULT_REPORT_PATH}"
    )
    print(f"reason labels: {', '.join(_reason_labels())}")
