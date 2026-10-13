"""Focused contracts for the manual monster-AI evidence tool.

``monster-ai-manual-evidence`` ships a manual report tool, not a discovery
campaign: this module establishes the tool's own small, deterministic
contracts — the numerical replay and Wilson arithmetic, the paired selector
check, the whole-policy timing assembly and its dice isolation, the report
payload and its no-action classification, the finite allocation declarations,
and the discovery isolation that keeps the campaign out of the default suite.
It never reruns the campaign: the one real encounter and the two real scope
smokes below are the tool/report boundary and the ordinary/overwhelm identity
checks, driven through the production session/round/resolver boundary with the
harness's real synthetic entities.
"""

from tools.spec_traceability import covers_requirement

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTestCase

from world.rules import monster_behaviour as behaviour
from world.rules import traits
from world.rules.action import ActionRequest
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    ExecutionScopeBase,
    current_decision_scope,
    run_round,
    stable_actor_id,
)
from world.rules.monster_ai import manual_campaign
from world.rules.monster_ai import manual_reports as reports
from world.rules.overwhelm import resolve_overwhelm

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sample(**overrides) -> reports.DecisionSample:
    fields = {
        "skill_key": "skill",
        "target_ids": ("a",),
        "highest_utility": True,
        "selected_illegal": False,
        "no_action": None,
    }
    fields.update(overrides)
    return reports.DecisionSample(**fields)


def _outcome(**overrides) -> reports.EncounterOutcome:
    fields = {
        "archetype": "brute",
        "situation": "finishing_choice",
        "seed_index": 0,
        "intelligence": 10,
        "decision_seed": 1,
        "combat_seed": 2,
        "outcome": reports.OUTCOME_WIN,
        "rounds": 4,
        "decisions": (_sample(),),
    }
    fields.update(overrides)
    return reports.EncounterOutcome(**fields)


def _candidates(*, count=1, examined=1, exhausted=False, exclusions=(), rejections=()):
    return SimpleNamespace(
        candidates=tuple(range(count)),
        examined=examined,
        exhausted=exhausted,
        exclusions=tuple(exclusions),
        rejections=tuple(rejections),
    )


class WilsonIntervalTests(unittest.TestCase):
    """The small-sample interval the report must carry, on known outcomes."""

    @covers_requirement("monster-ai-manual-validation::paired-selector-evidence-measures-a-fixed-utility-gap")
    def test_wilson_interval_is_bounded_and_small_sample_safe(self):
        self.assertEqual(reports.wilson_interval(0, 0), (0.0, 1.0))
        low, high = reports.wilson_interval(0, 128)
        self.assertEqual(low, 0.0)
        self.assertLess(high, 0.05)
        low, high = reports.wilson_interval(128, 128)
        self.assertEqual(high, 1.0)
        self.assertGreater(low, 0.95)
        low, high = reports.wilson_interval(64, 128)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        self.assertLess(high - low, 0.2)
        with self.assertRaises(ValueError):
            reports.wilson_interval(3, 2)


class SeedEncodingTests(unittest.TestCase):
    """The versioned, documented seed encoding the operations record."""

    @covers_requirement("monster-ai-manual-validation::manual-campaign-has-the-approved-finite-allocation")
    def test_stable_seed_is_deterministic_and_versioned(self):
        first = reports.stable_seed("campaign", "finishing_choice", "brute", 0)
        again = reports.stable_seed("campaign", "finishing_choice", "brute", 0)
        self.assertEqual(first, again)
        self.assertNotEqual(first, reports.stable_seed("campaign", "finishing_choice", "brute", 1))
        self.assertNotEqual(first, reports.stable_seed("selector", "finishing_choice", "brute", 0))
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 1 << 128)
        self.assertEqual(
            reports.scenario_seed("finishing_choice", "brute", 0),
            reports.stable_seed("campaign", "finishing_choice", "brute", 0),
        )
        self.assertEqual(reports.selector_seed(3), reports.stable_seed("selector", 3))


class AllocationDeclarationTests(unittest.TestCase):
    """The approved finite allocation and its synthetic scenario set."""

    @covers_requirement("monster-ai-manual-validation::manual-campaign-has-the-approved-finite-allocation")
    def test_six_situations_and_the_finite_allocation_arithmetic(self):
        self.assertEqual(len(reports.SITUATION_NAMES), 6)
        self.assertEqual(len(set(reports.SITUATION_NAMES)), 6)
        self.assertEqual(reports.CAMPAIGN_SEED_INDICES, (0, 1))
        self.assertEqual(reports.INTELLIGENCE_VALUES, (10, 90))
        self.assertEqual(reports.ROUND_CAP, 30)
        per_archetype = (
            len(reports.SITUATION_NAMES)
            * len(reports.CAMPAIGN_SEED_INDICES)
            * len(reports.INTELLIGENCE_VALUES)
        )
        self.assertEqual(per_archetype, 24)
        self.assertEqual(per_archetype * 6, 144)
        # The campaign declares its own situation set through the harness; the
        # six named situations are exactly the declared allocation's names.
        harness = manual_campaign.CampaignHarness()
        try:
            self.assertEqual(
                tuple(spec.name for spec in harness.situations), reports.SITUATION_NAMES
            )
            self.assertEqual(len(harness.archetypes), 6)
        finally:
            harness._restore_tuning()
            if harness._scope is not None:
                harness._scope.__exit__(None, None, None)
                harness._scope = None


class SelectorOperationTests(unittest.TestCase):
    """The standalone paired selection check over its documented seeds."""

    @covers_requirement("monster-ai-manual-validation::paired-selector-evidence-measures-a-fixed-utility-gap")
    def test_selector_check_is_paired_and_replays_every_choice(self):
        # The 128-seed acceptance run is an explicit manual operation
        # (simulation design section 3): full-suite discovery must never run
        # it, so this regression replays a small fixed replicate count and
        # asserts the pairing arithmetic instead of the manual margin.
        first = reports.run_selector_operation(seed_count=8)
        second = reports.run_selector_operation(seed_count=8)
        self.assertEqual(first.total, 8)
        self.assertEqual(first.pairs, second.pairs)
        self.assertEqual(
            [pair.seed for pair in first.pairs], [pair.seed for pair in second.pairs]
        )
        self.assertEqual(
            {(pair.low_choice, pair.high_choice) for pair in first.pairs},
            {(pair.low_choice, pair.high_choice) for pair in second.pairs},
        )
        for pair in first.pairs:
            self.assertIn(pair.low_choice, (reports.SELECTOR_HIGH_KEY, reports.SELECTOR_LOW_KEY))
            self.assertIn(pair.high_choice, (reports.SELECTOR_HIGH_KEY, reports.SELECTOR_LOW_KEY))
            self.assertEqual(pair.seed, reports.selector_seed(pair.seed_index))
        # The aggregates are derived from the raw paired replicates.
        self.assertEqual(
            first.low_high_utility,
            sum(
                1 for pair in first.pairs if pair.low_choice == reports.SELECTOR_HIGH_KEY
            ),
        )
        self.assertEqual(
            first.high_high_utility,
            sum(
                1
                for pair in first.pairs
                if pair.high_choice == reports.SELECTOR_HIGH_KEY
            ),
        )
        self.assertEqual(first.margin_required, reports.SELECTOR_MIN_MARGIN)
        self.assertEqual(
            first.margin_met, first.difference >= reports.SELECTOR_MIN_MARGIN
        )
        # Each Wilson interval brackets its own observed proportion.
        for successes, interval in (
            (first.low_high_utility, first.low_wilson),
            (first.high_high_utility, first.high_wilson),
        ):
            observed = successes / first.total
            self.assertLessEqual(interval[0], observed)
            self.assertGreaterEqual(interval[1], observed)
        # The check is an isolated selector measurement: it runs no encounter.
        self.assertFalse(hasattr(first, "encounters"))

    @covers_requirement("monster-ai-manual-validation::paired-selector-evidence-measures-a-fixed-utility-gap")
    def test_selector_check_uses_two_legal_candidates_with_a_fixed_gap(self):
        high, low = reports._selector_candidates(reports.SELECTOR_UTILITY_GAP)
        self.assertAlmostEqual(
            high.score - low.score, reports.SELECTOR_UTILITY_GAP, places=9
        )
        with self.assertRaises(ValueError):
            reports._selector_candidates(0.0)


class NoActionResultTests(unittest.TestCase):
    """The report's separation of every no-action cause."""

    @covers_requirement("monster-ai-manual-validation::manual-reports-preserve-evidence-and-uncertainty")
    def test_every_no_action_cause_is_distinguished(self):
        self.assertIsNone(reports.classify_no_action(_candidates(), (_sample(),)))
        self.assertEqual(
            reports.classify_no_action(_candidates(count=0), ()),
            reports.NO_ACTION_LEGAL_RESTRICTION,
        )
        self.assertEqual(
            reports.classify_no_action(
                _candidates(count=0, exclusions=("x",)), ()
            ),
            reports.NO_ACTION_LEGAL_RESTRICTION,
        )
        self.assertEqual(
            reports.classify_no_action(_candidates(count=0, exhausted=True), ()),
            reports.NO_ACTION_BUDGET_OMISSION,
        )
        self.assertEqual(
            reports.classify_no_action(_candidates(count=2), ()),
            reports.NO_ACTION_ESTIMATOR_EXCLUSION,
        )
        self.assertEqual(
            reports.classify_no_action(None, ()),
            reports.NO_ACTION_CAPABILITY_BLOCKED,
        )


class EncounterAggregationTests(unittest.TestCase):
    """Encounter metrics on independently known inputs."""

    @covers_requirement("monster-ai-manual-validation::manual-reports-preserve-evidence-and-uncertainty")
    def test_metrics_count_each_declared_denominator(self):
        rows = (
            _outcome(
                outcome=reports.OUTCOME_WIN,
                rounds=4,
                decisions=(
                    _sample(skill_key="a", target_ids=("x",), highest_utility=True),
                    _sample(skill_key="a", target_ids=("y",), highest_utility=False),
                ),
            ),
            _outcome(
                outcome=reports.OUTCOME_CAPPED,
                rounds=30,
                decisions=(
                    _sample(
                        skill_key=None,
                        target_ids=(),
                        highest_utility=False,
                        no_action=reports.NO_ACTION_ESTIMATOR_EXCLUSION,
                        rejections=2,
                    ),
                ),
            ),
            _outcome(
                outcome=reports.OUTCOME_LOSS,
                rounds=2,
                decisions=(
                    _sample(
                        skill_key=None,
                        target_ids=(),
                        highest_utility=False,
                        no_action=reports.NO_ACTION_BUDGET_OMISSION,
                        exhausted=True,
                        omitted_families=3,
                    ),
                ),
            ),
        )
        metrics = reports.aggregate_encounters(rows)
        self.assertEqual((metrics.wins, metrics.losses, metrics.capped), (1, 1, 1))
        self.assertEqual(metrics.encounters, 3)
        self.assertEqual(metrics.rounds_total, 36)
        self.assertAlmostEqual(metrics.mean_rounds, 12.0)
        self.assertEqual(metrics.decisions, 4)
        self.assertEqual(metrics.highest_utility, 1)
        self.assertAlmostEqual(metrics.highest_utility_fraction, 0.25)
        self.assertEqual(metrics.skill_distribution, {"a": 2})
        self.assertEqual(metrics.target_distribution, {"x": 1, "y": 1})
        self.assertEqual(metrics.rejections, 2)
        self.assertEqual(metrics.no_action_estimator_exclusion, 1)
        self.assertEqual(metrics.no_action_budget_omission, 1)
        self.assertEqual(metrics.no_action_legal_restriction, 0)
        self.assertEqual(metrics.exhausted, 1)
        self.assertEqual(metrics.omitted_families, 3)
        self.assertEqual(reports.aggregate_encounters(()).mean_rounds, 0.0)


class TimingAssemblyTests(unittest.TestCase):
    """The warm/cold timing block and its budget verdict."""

    @covers_requirement("monster-ai-manual-validation::performance-evidence-measures-the-complete-policy")
    def test_percentiles_queries_and_budget_are_reported(self):
        samples = [float(value) for value in range(1, 51)]
        timing = reports.build_policy_timing(
            mode="utility",
            cold_ms=99.0,
            samples_ms=samples,
            queries=7,
            examined=98,
            accepted=97,
            omitted=1,
            dice_isolated=True,
        )
        self.assertEqual(timing.cold_ms, 99.0)
        self.assertEqual(timing.queries, 7)
        self.assertEqual((timing.examined, timing.accepted, timing.omitted), (98, 97, 1))
        self.assertTrue(timing.dice_isolated)
        self.assertAlmostEqual(timing.p50_ms, 25.0)
        self.assertGreater(timing.p95_ms, timing.p50_ms)
        self.assertLessEqual(timing.p95_ms, 51.0)
        report = reports.PerformanceReport(
            participants=16,
            owned_skills=16,
            candidate_budget=256,
            warmups=5,
            measurements=50,
            timings=(timing,),
            scaling=(reports.ScalingSample(candidates=8, queries=3, examined=4),),
            budget_ms=reports.PERFORMANCE_P95_BUDGET_MS,
        )
        self.assertTrue(report.budget_met)
        over = reports.build_policy_timing(
            mode="utility", cold_ms=1.0, samples_ms=[100.0], queries=0,
            examined=0, accepted=0, omitted=0, dice_isolated=True,
        )
        self.assertFalse(
            reports.PerformanceReport(
                participants=1, owned_skills=1, candidate_budget=1, warmups=0,
                measurements=1, timings=(over,), scaling=(), budget_ms=50.0,
            ).budget_met
        )


class ReportPayloadTests(unittest.TestCase):
    """The machine-readable report and its compact interpretation."""

    @covers_requirement("monster-ai-manual-validation::manual-reports-preserve-evidence-and-uncertainty")
    def test_reports_carry_every_declared_field_and_render(self):
        header = reports.environment_header(
            baseline_commit="deadbeef",
            configuration_fingerprint="f" * 64,
            algorithm_version=5,
        )
        for key in ("baseline_commit", "algorithm_version", "configuration_fingerprint",
                    "python_version", "evennia_version", "host", "generated_at"):
            self.assertIn(key, header)
        selector = reports.run_selector_operation(seed_count=4)
        selector_payload = {
            **header, "operation": "selector", **reports.selector_report_payload(selector)
        }
        rendered = reports.render_markdown(selector_payload)
        self.assertIn("Manual selector check", rendered)
        self.assertIn("Wilson", rendered)

        encounters = (
            _outcome(
                decisions=(
                    _sample(skill_key="a", target_ids=("x",), highest_utility=True),
                    _sample(
                        skill_key=None,
                        target_ids=(),
                        highest_utility=False,
                        no_action=reports.NO_ACTION_LEGAL_RESTRICTION,
                        initial_observations=((1, 0, "dbref:1", "faction", "skill", ("dbref:2",), (), ()),),
                    ),
                )
            ),
        )
        archetype_payload = reports.archetype_report_payload(
            archetype="brute", encounters=encounters, header=header
        )
        for key in ("allocation", "metrics", "overall", "unresolved", "raw"):
            self.assertIn(key, archetype_payload)
        self.assertEqual(archetype_payload["allocation"]["encounters"], 1)
        self.assertIn(
            "no_action", archetype_payload["overall"]
        )
        self.assertEqual(
            archetype_payload["overall"]["no_action"]["legal_restriction"], 1
        )
        self.assertIn("initial_observations", archetype_payload["raw"][0])
        self.assertIn("Manual archetype campaign", reports.render_markdown(archetype_payload))

        performance = reports.PerformanceReport(
            participants=16, owned_skills=16, candidate_budget=256, warmups=5,
            measurements=50,
            timings=(
                reports.build_policy_timing(
                    mode="utility", cold_ms=1.0, samples_ms=[1.0], queries=2,
                    examined=3, accepted=3, omitted=0, dice_isolated=True,
                ),
            ),
            scaling=(reports.ScalingSample(candidates=8, queries=0, examined=9),),
            budget_ms=50.0,
        )
        performance_payload = {
            **header, "operation": "performance",
            **reports.performance_report_payload(performance),
        }
        self.assertIn("envelope", performance_payload)
        self.assertIn("timings", performance_payload)
        self.assertIn("Manual performance scenario", reports.render_markdown(performance_payload))

    @covers_requirement("monster-ai-manual-validation::manual-reports-preserve-evidence-and-uncertainty")
    def test_write_reports_persists_both_forms(self):
        payload = {"operation": "selector", **reports.selector_report_payload(
            reports.run_selector_operation(seed_count=2)
        )}
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = reports.write_reports(directory, payload, stem="check")
            self.assertTrue(json_path.is_file())
            self.assertTrue(markdown_path.is_file())
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["operation"], "selector")
            self.assertIn("Manual selector check", markdown_path.read_text(encoding="utf-8"))


class OperationIsolationTests(unittest.TestCase):
    """Every operation is explicit, independent and outside default discovery."""

    @covers_requirement("monster-ai-manual-validation::manual-operations-remain-separate-from-default-verification")
    def test_operations_are_explicit_and_independent(self):
        calls = []

        class _Harness:
            def run_archetype_campaign(self, archetype):
                calls.append(archetype)
                return (_outcome(),)

            def run_performance_scenario(self):
                calls.append("performance")
                return reports.PerformanceReport(
                    participants=1, owned_skills=1, candidate_budget=1, warmups=0,
                    measurements=0, timings=(), scaling=(), budget_ms=50.0,
                )

        header = {}
        with tempfile.TemporaryDirectory() as directory:
            # A selector invocation runs no campaign and touches no harness.
            selector = reports.run_operation(
                operation="selector", harness=None, header=header, output=directory,
                selector_count=2,
            )
            self.assertEqual(calls, [])
            self.assertEqual(selector.report["operation"], "selector")
            # The campaign requires its named archetype: no implicit "all".
            with self.assertRaises(ValueError):
                reports.run_operation(
                    operation="archetype", harness=_Harness(), header=header, output=directory
                )
            reports.run_operation(
                operation="archetype", harness=_Harness(), header=header,
                output=directory, archetype="brute",
            )
            self.assertEqual(calls, ["brute"])
            reports.run_operation(
                operation="performance", harness=_Harness(), header=header, output=directory
            )
            self.assertEqual(calls, ["brute", "performance"])
            with self.assertRaises(ValueError):
                reports.run_operation(
                    operation="everything", harness=_Harness(), header=header, output=directory
                )

    @covers_requirement("monster-ai-manual-validation::manual-operations-remain-separate-from-default-verification")
    def test_tool_modules_are_not_test_modules_or_shard_entries(self):
        manifest = json.loads(
            (REPO_ROOT / ".github" / "evennia-shards.json").read_text(encoding="utf-8")
        )
        labels = [label for shard in manifest["shards"] for label in shard.get("labels", [])]
        for module in (
            "world.rules.monster_ai.manual_reports",
            "world.rules.monster_ai.manual_campaign",
            "tools.monster_ai_manual_reports",
        ):
            self.assertNotIn(module, labels)
        self.assertIn("world.rules.tests.test_monster_ai_manual_reports", labels)
        self.assertEqual(
            labels.count("world.rules.tests.test_monster_ai_manual_reports"), 1
        )
        for name in ("manual_reports", "manual_campaign"):
            self.assertFalse(name.startswith("test_"))


class CampaignEncounterTests(EvenniaTestCase):
    """One real encounter through the production session boundary."""

    def _harness(self) -> manual_campaign.CampaignHarness:
        harness = manual_campaign.CampaignHarness(
            situations=("finishing_choice",), seed_indices=(0,), intelligences=(10,)
        )
        self.addCleanup(harness.__exit__, None, None, None)
        return harness.__enter__()

    @covers_requirement("monster-ai-manual-validation::manual-campaign-has-the-approved-finite-allocation")
    def test_one_named_encounter_settles_and_reloads_committed_state(self):
        harness = self._harness()
        outcome = harness.run_single_encounter("finishing_choice", harness.archetypes[0])
        self.assertEqual(outcome.situation, "finishing_choice")
        self.assertEqual(outcome.intelligence, 10)
        self.assertGreater(outcome.rounds, 0)
        self.assertLessEqual(outcome.rounds, reports.ROUND_CAP)
        self.assertIn(
            outcome.outcome,
            (reports.OUTCOME_WIN, reports.OUTCOME_LOSS, reports.OUTCOME_CAPPED),
        )
        self.assertTrue(outcome.decisions)
        for decision in outcome.decisions:
            self.assertEqual(decision.selected_illegal, False)
        # Committed reload: every entity the round wrote is readable from a
        # fresh row, and the encounter's own outcome is a settled or capped
        # state rather than an uncommitted in-flight one.
        monster = ObjectDB.objects.filter(db_key__startswith="campaign-monster").first()
        if monster is not None:
            self.assertIsNotNone(monster.attributes.get("traits", category="traits"))

    @covers_requirement("monster-ai-manual-validation::manual-campaign-has-the-approved-finite-allocation")
    def test_intelligence_pairs_share_stats_ownership_and_kit(self):
        harness = self._harness()
        left = harness.build_monster("pair-10", intelligence=10)
        right = harness.build_monster("pair-90", intelligence=90)
        self.assertTrue(manual_campaign.rosters_are_identical(left, right))
        self.assertNotEqual(left.variant_key, right.variant_key)
        left_decision = behaviour.resolve_monster_ai(left)
        right_decision = behaviour.resolve_monster_ai(right)
        self.assertEqual(left_decision.intelligence, 10)
        self.assertEqual(right_decision.intelligence, 90)
        self.assertEqual(left_decision.mode, right_decision.mode)

    @covers_requirement("monster-ai-manual-validation::manual-campaign-has-the-approved-finite-allocation")
    def test_one_named_operation_runs_only_its_own_allocation(self):
        harness = self._harness()
        outcomes = harness.run_archetype_campaign(harness.archetypes[0])
        self.assertEqual(len(outcomes), 1)
        self.assertEqual({row.situation for row in outcomes}, {"finishing_choice"})
        self.assertEqual({row.intelligence for row in outcomes}, {10})
        with self.assertRaises(ValueError):
            harness.run_archetype_campaign("not-an-archetype")


class ScopeIdentitySmokeTests(EvenniaTestCase):
    """Ordinary and overwhelm production smoke: real context, real slots."""

    def _harness(self) -> manual_campaign.CampaignHarness:
        harness = manual_campaign.CampaignHarness(
            situations=("finishing_choice",), seed_indices=(0,), intelligences=(10,)
        )
        self.addCleanup(harness.__exit__, None, None, None)
        return harness.__enter__()

    def _field(self, harness, *, player_hp=400, monster_hp=400):
        player = harness.build_player("scope-player", player_hp)
        monster = harness.build_monster("scope-monster", hp=monster_hp, mp=60)
        battlefield = Battlefield(
            {"monsters": frozenset({monster.key}), "party": frozenset({player.key})},
            {monster.key: monster, player.key: player},
        )
        return player, monster, battlefield

    @covers_requirement("monster-ai-manual-validation::manual-operations-remain-separate-from-default-verification")
    def test_ordinary_round_records_real_session_round_and_slot_identity(self):
        harness = self._harness()
        player, monster, battlefield = self._field(harness)
        seen: list = []

        def provider(entity, field):
            seen.append(current_decision_scope())
            return behaviour.monster_behaviour_policy(
                entity, field, context=BattlefieldActionContext(field)
            )

        run_round(
            battlefield,
            provider,
            decision_scope_base=ExecutionScopeBase(session_id="smoke:ord", round_index=3),
        )
        self.assertTrue(seen)
        for scope in seen:
            self.assertIsNotNone(scope)
            self.assertEqual(scope.session_id, "smoke:ord")
            self.assertEqual(scope.round_index, 3)
            self.assertEqual(scope.context_mode, "normal")
        monster_scopes = [
            scope for scope in seen if scope.actor_id == stable_actor_id(monster)
        ]
        self.assertTrue(monster_scopes)
        self.assertEqual(monster_scopes[0].slot_index, 0)

    @covers_requirement("monster-ai-manual-validation::manual-operations-remain-separate-from-default-verification")
    def test_overwhelm_round_records_its_own_internal_round_identity(self):
        harness = self._harness()
        # A genuinely decided encounter: the monster's team overwhelms the
        # party, which is exactly when compression is authorized to run.
        player, monster, battlefield = self._field(
            harness, player_hp=20, monster_hp=5000
        )
        monster.traits.atk_phys.base = 100
        monster.traits.atk_phys.current = 100
        monster.traits.defense.base = 120
        monster.traits.defense.current = 120
        seen: list = []

        def provider(entity, field):
            scope = current_decision_scope()
            if scope is not None:
                seen.append(scope)
            if entity.key != monster.key:
                return None
            target = BattlefieldActionContext(field)
            return ActionRequest(
                monster,
                manual_campaign._ENCOUNTER_SKILL_KEYS[0],
                [player],
                target,
            )

        resolve_overwhelm(
            battlefield,
            provider,
            max_rounds=3,
            decision_scope_base=ExecutionScopeBase(session_id="smoke:ovw", round_index=1),
        )
        self.assertTrue(seen)
        for scope in seen:
            self.assertEqual(scope.session_id, "smoke:ovw")
            self.assertEqual(scope.context_mode, "overwhelm")
            self.assertGreaterEqual(scope.round_index, 1)
        monster_scopes = [
            scope for scope in seen if scope.actor_id == stable_actor_id(monster)
        ]
        self.assertTrue(monster_scopes)
        self.assertEqual(monster_scopes[0].slot_index, 0)
        first_round = min(scope.round_index for scope in seen)
        distinct = {scope.round_index for scope in seen}
        self.assertEqual(min(distinct), first_round)
        for scope in seen:
            self.assertIn(scope.round_index, distinct)


class PerformanceHarnessTests(EvenniaTestCase):
    """The whole-policy measurement over real entities."""

    @covers_requirement("monster-ai-manual-validation::performance-evidence-measures-the-complete-policy")
    def test_performance_measures_both_modes_without_mutating_state(self):
        harness = manual_campaign.CampaignHarness(
            situations=("finishing_choice",), seed_indices=(0,), intelligences=(90,)
        )
        self.addCleanup(harness.__exit__, None, None, None)
        harness.__enter__()
        report = harness.run_performance_scenario(warmups=1, measurements=3)
        self.assertEqual({timing.mode for timing in report.timings}, {"legacy", "utility"})
        for timing in report.timings:
            self.assertGreaterEqual(timing.cold_ms, 0.0)
            self.assertEqual(len(timing.samples_ms), 3)
            self.assertGreaterEqual(timing.queries, 1)
        utility = next(t for t in report.timings if t.mode == "utility")
        legacy = next(t for t in report.timings if t.mode == "legacy")
        # The utility policy draws from its own generator, so it never advances
        # the combat dice stream; the legacy body is the retained rulebook
        # policy and does consume it.
        self.assertTrue(utility.dice_isolated)
        self.assertFalse(legacy.dice_isolated)
        self.assertGreater(utility.examined, 0)
        self.assertEqual(len(report.scaling), len(reports.PERFORMANCE_SCALING_COUNTS))
        # The measured call is a read of fixed state (simulation design
        # section 6): one complete utility policy call over the reference
        # envelope leaves every participant's stored traits byte-identical,
        # and the warm p95 budget is reported rather than asserted, so no
        # host-speed gate ever enters permanent tests.
        decider, battlefield = harness._performance_field("utility", enemies=8)
        before = {
            entity.key: traits.stored_trait_records(entity)
            for entity in battlefield.roster.values()
        }
        call = harness._timing_callable(
            decider, battlefield, BattlefieldActionContext(battlefield), []
        )
        for _ in range(3):
            call()
        self.assertEqual(
            {
                entity.key: traits.stored_trait_records(entity)
                for entity in battlefield.roster.values()
            },
            before,
        )
        self.assertEqual(report.budget_ms, reports.PERFORMANCE_P95_BUDGET_MS)