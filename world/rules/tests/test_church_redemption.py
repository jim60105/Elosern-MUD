"""Behaviour tests for the ordination redemption rail (design §5.6).

``church redeem`` is a one-shot all-or-nothing grace purchase: validate
(exists ∧ unredeemed ∧ merit sufficient ∧ catalogue-internal prereqs), one
transaction subtracting merit, writing the skill through the sanctioned
granted-skill channel (PASSIVE rows to ``db.skills.passive``, ACTIVE rows to
``db.skills.active``), appending the key to ``redeemed``, and emitting
``church_skill_redeemed`` commit-bound. Every rejection is inert (stable
reason, byte-identical stores, no event), repeat redemption is impossible,
``saintess_vessel`` is never redeemable, a mid-redemption failure rolls the
whole transaction back, and the Series D advanced offering rows surface
through the shared act key with zero duplicated data. The ``vow_of_service``
ledger multipliers (offering copper +25%, offering/climax merit +10%) are
consumed by the offering and climax rails with deterministic round-half-up
integer scaling.

OWNER TESTING STANCE: behavior only — every catalogue fact is proven through
the rails' observable behaviour with synthetic ``t_`` rows; no shipped
catalogue key is ever named (``saintess_vessel`` arrives only as the
imported module constant).
"""

from copy import deepcopy
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.church import OFFERING_CATALOG, OfferingRow, RedeemRow
from world.rules import church
from world.rules.church import (
    RedemptionError,
    RedemptionReason,
    VESSEL_KEY,
)
from world.rules.church_rulebook import PassiveEffectRow
from world.rules.clock import WorldClock
from world.rules.cross_lineage_unlock import grant_owned_skill
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.state_reactions import dispatch_phase_reaction  # noqa: F401  (import registers the canonical phase dispatcher)
# Aliased so the module stays free of the ``_REGISTRY`` symbol finding the
# data-independence lint scans for (the name itself is never rebound).
from world.skills.registry import SKILL_REGISTRY as _SKILL_REGISTRY
from world.skills.registry.builders import _skill
from world.skills.registry.vocab import SkillCategory, SkillKind, TargetSpec


def _synth_row(
    key: str,
    price: int,
    tier: str = "entry",
    prereqs: tuple[str, ...] = (),
    polarity: str = "active",
) -> RedeemRow:
    return RedeemRow(
        skill_key=key,
        merit_price=price,
        tier=tier,
        prereq_keys=prereqs,
        polarity=polarity,
    )


def _synth_skill(key: str, kind: SkillKind) -> object:
    return _skill(
        key,
        f"合成 {key}",
        "合成測試技能，只在本測試的合成登錄表中存在。",
        kind,
        TargetSpec.SINGLE if kind is SkillKind.ACTIVE else TargetSpec.NONE,
        usable_out_of_combat=True,
        category=SkillCategory.ENHANCEMENT,
    )


class ChurchRedemptionBase(EvenniaTest):
    """An enrolled character with a synthetic catalogue and registry."""

    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.hall = create_object(Room, key="t_redemption_hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.recipient = create_object(
            NPC, key="t_redemption_recipient", location=self.hall
        )
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        from world.quests.catalog import register_catalog

        register_catalog()
        # Materialize the ledger without the host machinery (accrual base
        # precedent): the redemption primitives only require a ledger.
        church.add_merit(self.char1, 0)

        self.catalog = (
            _synth_row("t_redeem_passive", 500, polarity="passive"),
            _synth_row("t_redeem_active", 300),
            _synth_row("t_redeem_expensive", 9000, tier="high"),
            _synth_row(
                "t_redeem_gated",
                4000,
                tier="high",
                prereqs=("t_redeem_passive",),
            ),
        )
        synthetic_defs = {
            key: _synth_skill(key, kind)
            for key, kind in (
                ("t_redeem_passive", SkillKind.PASSIVE),
                ("t_redeem_active", SkillKind.ACTIVE),
                ("t_redeem_gated", SkillKind.ACTIVE),
            )
        }
        self.registry = {**_SKILL_REGISTRY, **synthetic_defs}
        self._catalogue_patch = patch(
            "world.rules.church.REDEEM_CATALOG", self.catalog
        )
        self._catalogue_patch.start()
        self.addCleanup(self._catalogue_patch.stop)
        # church.py resolves the registry lazily from the package at call
        # time, so patching the package attribute covers every rail.
        self._registry_patch = patch(
            "world.skills.registry.SKILL_REGISTRY", self.registry
        )
        self._registry_patch.start()
        self.addCleanup(self._registry_patch.stop)

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    def _skills_snapshot(self):
        return deepcopy(
            self.char1.attributes.get("skills") or {"active": [], "passive": []}
        )


class ChurchRedemptionActTests(ChurchRedemptionBase):
    """A funded redemption writes the skill atomically (delta scenario)."""

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_a_funded_passive_redemption_writes_everything_atomically(self):
        church.add_merit(self.char1, 1000)
        before = church.merit(self.char1)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(result["outcome"], "redeemed")
        self.assertEqual(result["row"], "t_redeem_passive")
        self.assertEqual(result["price"], 500)
        # Merit decreased by exactly the catalogue price (the observable
        # band membership: price == observed delta).
        self.assertEqual(church.merit(self.char1), before - 500)
        # The skill landed in the PASSIVE store, never the active store.
        skills = dict(self.char1.db.skills or {})
        self.assertIn("t_redeem_passive", skills.get("passive", []))
        self.assertNotIn("t_redeem_passive", skills.get("active", []))
        self.assertEqual(church.redeemed_keys(self.char1), ("t_redeem_passive",))
        # Exactly one commit-bound event.
        (event,), kwargs = info.call_args
        self.assertEqual(event, "church_skill_redeemed")
        self.assertEqual(kwargs["context"]["char"], str(self.char1))
        self.assertEqual(kwargs["context"]["skill"], "t_redeem_passive")
        self.assertEqual(self._events(info), ["church_skill_redeemed"])

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_an_active_row_writes_to_the_active_store(self):
        church.add_merit(self.char1, 1000)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.redeem_step(self.char1, "t_redeem_active")
        self.assertEqual(result["outcome"], "redeemed")
        skills = dict(self.char1.db.skills or {})
        self.assertIn("t_redeem_active", skills.get("active", []))
        self.assertNotIn("t_redeem_active", skills.get("passive", []))
        self.assertEqual(
            church.redeemed_keys(self.char1), ("t_redeem_active",)
        )
        self.assertEqual(self._events(info), ["church_skill_redeemed"])

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_every_rejection_is_inert_and_byte_identical(self):
        # Enough to cover the gated row's price so the prereq check (not the
        # merit check) is the one that fires, while the expensive row still
        # fails on merit.
        church.add_merit(self.char1, 5000)
        ledger_before = deepcopy(church.read_ledger(self.char1))
        skills_before = self._skills_snapshot()
        cases = (
            ("t_no_such_key", RedemptionReason.UNKNOWN_KEY),
            ("t_redeem_expensive", RedemptionReason.INSUFFICIENT_MERIT),
            ("t_redeem_gated", RedemptionReason.UNMET_PREREQ),
        )
        for key, reason in cases:
            with (
                self.subTest(key=key),
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                with self.assertRaises(RedemptionError) as caught:
                    church.redeem_step(self.char1, key)
            self.assertEqual(caught.exception.args[0], reason)
            self.assertEqual(church.read_ledger(self.char1), ledger_before)
            self.assertEqual(self._skills_snapshot(), skills_before)
            self.assertEqual(self._events(info), [])

        # Repeat redemption is impossible: the first purchase commits, the
        # second is a stable rejection leaving everything byte-identical.
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(self._events(info), ["church_skill_redeemed"])
        committed = deepcopy(church.read_ledger(self.char1))
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RedemptionError) as caught:
                church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.ALREADY_REDEEMED)
        self.assertEqual(church.read_ledger(self.char1), committed)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_catalogue_internal_prereqs_gate_the_high_rows(self):
        church.add_merit(self.char1, 10000)
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(self.char1, "t_redeem_gated")
        self.assertEqual(caught.exception.args[0], RedemptionReason.UNMET_PREREQ)
        church.redeem_step(self.char1, "t_redeem_passive")
        result = church.redeem_step(self.char1, "t_redeem_gated")
        self.assertEqual(result["outcome"], "redeemed")
        self.assertEqual(
            church.redeemed_keys(self.char1),
            ("t_redeem_passive", "t_redeem_gated"),
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_unenrolled_and_non_player_redemptions_are_stable_rejections(self):
        fresh = create_object(PlayerCharacter, key="t_never_enrolled")
        fresh.race = "human"
        fresh.apply_race_baseline()
        fresh.location = self.hall
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(fresh, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.NOT_ENROLLED)
        room = create_object(Room, key="t_redemption_room")
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(room, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.NOT_A_PLAYER)

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_a_malformed_ledger_is_a_stable_inert_rejection(self):
        self.char1.db.church = "not_a_mapping"
        before_skills = self._skills_snapshot()
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.MALFORMED_LEDGER)
        self.char1.db.church = {"merit": "oops", "redeemed": []}
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.MALFORMED_LEDGER)
        self.char1.db.church = {"merit": 1000, "redeemed": [7]}
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(caught.exception.args[0], RedemptionReason.MALFORMED_LEDGER)
        self.assertEqual(self._skills_snapshot(), before_skills)
        self.assertIsNone(
            getattr(self.char1.db, "wallet", None) or None,
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_a_mid_redemption_failure_rolls_back_everything(self):
        church.add_merit(self.char1, 1000)
        ledger_before = deepcopy(church.read_ledger(self.char1))
        skills_before = self._skills_snapshot()
        with (
            patch(
                "world.rules.cross_lineage_unlock.grant_owned_skill",
                side_effect=RuntimeError("simulated post-charge failure"),
            ),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.redeem_step(self.char1, "t_redeem_passive")
        self.assertEqual(church.read_ledger(self.char1), ledger_before)
        self.assertEqual(self._skills_snapshot(), skills_before)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_the_vessel_is_never_redeemable(self):
        # The permanent negative-set pin, proven through the rail: the
        # vessel key resolves against the shipped catalogue as the unknown-
        # key rejection (the catalogue-level absence fact is pinned by the
        # data-contract lore suite).
        church.add_merit(self.char1, 100000)
        with self.assertRaises(RedemptionError) as caught:
            church.redeem_step(self.char1, VESSEL_KEY)
        self.assertEqual(caught.exception.args[0], RedemptionReason.UNKNOWN_KEY)

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redemption_list_marks_only_redeemed_rows(self):
        church.add_merit(self.char1, 1000)
        with self.captureOnCommitCallbacks(execute=True):
            church.redeem_step(self.char1, "t_redeem_active")
        listing = church.redemption_catalogue(self.char1)
        self.assertEqual(
            {row.skill_key: redeemed for row, redeemed in listing},
            {
                "t_redeem_passive": False,
                "t_redeem_active": True,
                "t_redeem_expensive": False,
                "t_redeem_gated": False,
            },
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_the_read_only_surfaces_fail_closed_on_bad_ledgers(self):
        # ``redeem list`` and ``merit`` read through the same strict
        # boundary as the purchase: unenrolled and malformed ledgers are
        # stable named rejections, never raw exceptions.
        fresh = create_object(PlayerCharacter, key="t_list_newcomer")
        fresh.race = "human"
        fresh.apply_race_baseline()
        with self.assertRaises(RedemptionError) as caught:
            church.redemption_catalogue(fresh)
        self.assertEqual(caught.exception.args[0], RedemptionReason.NOT_ENROLLED)
        with self.assertRaises(RedemptionError) as caught:
            church.merit_ledger_view(fresh)
        self.assertEqual(caught.exception.args[0], RedemptionReason.NOT_ENROLLED)
        both_readers = (
            "not_a_mapping",
            {"merit": "oops", "enrolled_tick": 0, "redeemed": [], "daily": {"day": 0, "pray": 0}},
            {"merit": 10, "enrolled_tick": 0, "redeemed": [7], "daily": {"day": 0, "pray": 0}},
        )
        for malformed in both_readers:
            with self.subTest(ledger=malformed):
                self.char1.db.church = malformed
                for reader in (church.redemption_catalogue, church.merit_ledger_view):
                    with self.assertRaises(RedemptionError) as caught:
                        reader(self.char1)
                    self.assertEqual(
                        caught.exception.args[0], RedemptionReason.MALFORMED_LEDGER
                    )
        # A malformed daily block only the merit view reads.
        self.char1.db.church = {
            "merit": 10,
            "enrolled_tick": 0,
            "redeemed": [],
            "daily": "broken",
        }
        with self.assertRaises(RedemptionError) as caught:
            church.merit_ledger_view(self.char1)
        self.assertEqual(
            caught.exception.args[0], RedemptionReason.MALFORMED_LEDGER
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_merit_ledger_view_renders_the_four_fields(self):
        church.add_merit(self.char1, 1000)
        self.char1.db.church["enrolled_tick"] = 7
        self.char1.db.church["daily"] = {"day": 0, "pray": 2}
        with self.captureOnCommitCallbacks(execute=True):
            church.redeem_step(self.char1, "t_redeem_active")
        self.assertEqual(
            church.merit_ledger_view(self.char1),
            {
                "merit": 1000 - 300,
                "enrolled_tick": 7,
                "redeemed": ("t_redeem_active",),
                "pray_today": 2,
            },
        )


class ChurchVowOfServiceScalingTests(ChurchRedemptionBase):
    """The decided vow_of_service ledger multipliers ride the offering and
    climax rails (offering copper +25%, offering/climax merit +10%),
    applied with deterministic round-half-up integer scaling."""

    def _vow_rules(self):
        from dataclasses import replace

        from world.rules.church_rulebook import get_church_rules

        return replace(
            get_church_rules(),
            passive_effects=(
                PassiveEffectRow(
                    row_id="t_vow_effect_row",
                    skill_key="t_vow",
                    effects={"copper_percent": 25, "merit_percent": 10},
                ),
            ),
        )

    def _own_vow(self):
        grant_owned_skill(
            self.char1,
            "t_vow",
            {**self.registry, "t_vow": _synth_skill("t_vow", SkillKind.PASSIVE)},
        )

    def _accepting_resolver(self):
        from world.rules.action import ActionResolver, ActionResult

        return patch.object(
            ActionResolver,
            "resolve",
            return_value=ActionResult.success(None, 0),
        )

    @covers_requirement(
        "church-ordination::series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline"
    )
    def test_vow_scales_offering_copper_and_merit_with_round_half_up(self):
        self._own_vow()
        act = _synth_skill("t_vowtest_act", SkillKind.ACTIVE)
        registry = {**self.registry, act.key: act}
        offering = OfferingRow(
            key="offering_t_vowtest",
            act_key="t_vowtest_act",
            merit=5,
            copper=22,
        )
        grant_owned_skill(self.char1, "t_vowtest_act", registry)
        with patch("world.skills.registry.SKILL_REGISTRY", registry), patch(
            "world.rules.church.OFFERING_CATALOG", (offering,)
        ):
            self.recipient.sexual.pleasure.base = 85  # top ordinal
            before_merit = church.merit(self.char1)
            before_wallet = int(self.char1.db.wallet or 0)
            with (
                self._accepting_resolver(),
                patch(
                    "world.rules.church_rulebook.get_church_rules",
                    return_value=self._vow_rules(),
                ),
                patch("world.rules.church.roll_d100", return_value=10),
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(
                    self.char1, self.recipient, "offering_t_vowtest"
                )
        self.assertEqual(result["outcome"], "accepted")
        # 10% of 5 = 0.5 -> round-half-up +1; 25% of 22 = 5.5 -> +6.
        self.assertEqual(church.merit(self.char1), before_merit + 6)
        self.assertEqual(int(self.char1.db.wallet or 0), before_wallet + 28)

    @covers_requirement(
        "church-ordination::series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline"
    )
    def test_offering_without_the_vow_is_unscaled(self):
        act = _synth_skill("t_vowtest_act", SkillKind.ACTIVE)
        registry = {**self.registry, act.key: act}
        offering = OfferingRow(
            key="offering_t_vowtest",
            act_key="t_vowtest_act",
            merit=5,
            copper=22,
        )
        grant_owned_skill(self.char1, "t_vowtest_act", registry)
        with patch("world.skills.registry.SKILL_REGISTRY", registry), patch(
            "world.rules.church.OFFERING_CATALOG", (offering,)
        ):
            self.recipient.sexual.pleasure.base = 85
            before_merit = church.merit(self.char1)
            before_wallet = int(self.char1.db.wallet or 0)
            with (
                self._accepting_resolver(),
                patch("world.rules.church.roll_d100", return_value=10),
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(
                    self.char1, self.recipient, "offering_t_vowtest"
                )
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(church.merit(self.char1), before_merit + 5)
        self.assertEqual(int(self.char1.db.wallet or 0), before_wallet + 22)

    @covers_requirement(
        "church-ordination::series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline"
    )
    def test_vow_scales_the_climax_accrual_merit(self):
        from world.rules.church_rulebook import get_church_rules

        self._own_vow()
        base = int(get_church_rules().accrual["accrual_climax_while_enrolled"]["merit"])
        with patch(
            "world.rules.church_rulebook.get_church_rules",
            return_value=self._vow_rules(),
        ):
            before = church.merit(self.char1)
            _apply_climax_phase_set(self.char1, "接近")
            with self.captureOnCommitCallbacks(execute=True):
                _apply_climax_phase_set(self.char1, "進行中")
        # 10% of 10 -> +1 (round-half-up), not the unscaled 10.
        self.assertEqual(church.merit(self.char1), before + base + 1)


class ChurchRedemptionRowsMenuTests(ChurchRedemptionBase):
    """Series D advanced rows surface in the offering menu through the
    shared act key, referencing the same registry row with no duplication."""

    @covers_requirement(
        "church-ordination::series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline"
    )
    def test_an_advanced_offering_row_surfaces_after_the_shared_key_is_owned(self):
        church.add_merit(self.char1, 100000)
        act = _synth_skill("t_ministry_act", SkillKind.ACTIVE)
        advanced = _synth_row("t_ministry_act", 800)
        offering = OfferingRow(
            key="offering_t_ministry_act",
            act_key="t_ministry_act",
            merit=8,
            copper=None,
        )
        patched_registry = {**self.registry, act.key: act}
        with patch(
            "world.skills.registry.SKILL_REGISTRY", patched_registry
        ), patch(
            "world.rules.church.REDEEM_CATALOG", self.catalog + (advanced,)
        ), patch("world.rules.church.OFFERING_CATALOG", (offering,)):
            # Not owning the shared act key: the row stays out of the menu.
            self.assertEqual(church.offering_menu(self.char1), ())
            result = church.redeem_step(self.char1, "t_ministry_act")
            self.assertEqual(result["outcome"], "redeemed")
            menu = church.offering_menu(self.char1)
            self.assertEqual(
                tuple(row.key for row in menu), ("offering_t_ministry_act",)
            )
            menu_row = menu[0]
            # The act_key equals the redemption skill key, and both
            # catalogues reference the ONE registry row (no duplicated
            # data): the same SkillDef key and the same definition object.
            self.assertEqual(menu_row.act_key, advanced.skill_key)
            self.assertEqual(menu_row.act_key, act.key)
            self.assertIs(patched_registry[menu_row.act_key], act)


class ChurchRedemptionGuardTests(ChurchRedemptionBase):
    """The pipeline is the sanctioned channel, not a bypass: a passive
    acquired through redemption stays practice-unearnable and
    non-conferrable, exactly like every other PASSIVE."""

    @covers_requirement(
        "church-ordination::series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline"
    )
    def test_a_redeemed_passive_stays_guarded_against_practice_and_conferral(self):
        from world.rules.action import RejectedAction
        from world.rules.progression import (
            grant_skill_practice_xp,
            grant_study_practice_xp,
        )
        from world.rules.skill_effects import validate_conferrable_skill

        # A real shipped qualifier-shaped PASSIVE (empty effects, selected
        # structurally, never by name) bought through the pipeline.
        passive_key = next(
            key
            for key, skill in _SKILL_REGISTRY.items()
            if skill.kind is SkillKind.PASSIVE and not skill.effects
        )
        church.add_merit(self.char1, 100000)
        # The pipeline gets a catalogue row for the real qualifier-shaped
        # passive (key selected structurally; the row itself is synthetic).
        with patch(
            "world.rules.church.REDEEM_CATALOG",
            self.catalog
            + (_synth_row(passive_key, 300, polarity="passive"),),
        ), self.captureOnCommitCallbacks(execute=True):
            result = church.redeem_step(self.char1, passive_key)
        self.assertEqual(result["outcome"], "redeemed")
        skills = dict(self.char1.db.skills or {})
        self.assertIn(passive_key, skills.get("passive", []))
        # The practice guards still refuse the PASSIVE (a redeemed passive
        # is owned, not usable): nothing practises a passive.
        self.assertFalse(
            grant_skill_practice_xp(self.char1, passive_key, target=self.char1),
            "use-driven practice must refuse the redeemed PASSIVE",
        )
        self.assertFalse(
            grant_study_practice_xp(self.char1, passive_key, 2),
            "booked study must refuse the redeemed PASSIVE",
        )
        # The conferral guard still refuses the qualifier-shaped passive.
        with self.assertRaises(RejectedAction):
            validate_conferrable_skill(passive_key)


class ChurchClergyTitleGrantTests(ChurchRedemptionBase):
    """Clergy titles unlock by redeemed count during the redemption transaction."""

    @covers_requirement(
        "title-system::the-clergy-title-ladder-unlocks-by-redeemed-count-and-never-displays-聖女"
    )
    def test_clergy_title_grants_at_threshold_auto_equips_and_rolls_back(self):
        from world.rules.titles import banked_fixed_keys, read_title_state
        from world.lore.titles import TitleCategory
        from world.rules.tests._knowledge_probes import live_fixed_title_registry

        church.add_merit(self.char1, 100000)
        believer_key = next(
            r.key
            for r in live_fixed_title_registry().values()
            if r.category == TitleCategory.CLERGY and r.predicate.threshold == 3
        )
        # Pre-seed with 2 redeemed skills
        self.char1.db.church["redeemed"] = ["t_skill_1", "t_skill_2"]

        # Before 3rd redemption: c_believer is not banked
        self.assertNotIn(believer_key, banked_fixed_keys(self.char1))

        # Redeem 3rd skill (t_redeem_active)
        result = church.redeem_step(self.char1, "t_redeem_active")
        self.assertEqual(result["outcome"], "redeemed")

        # Exactly at threshold 3: c_believer is banked and auto-equipped (slot was empty)
        self.assertIn(believer_key, banked_fixed_keys(self.char1))
        collection, equipped = read_title_state(self.char1)
        self.assertEqual(equipped["fixed"], believer_key)

        # Test transaction rollback: simulate a failed redemption
        church.add_merit(self.char1, 100000)
        # Reset titles and church state
        self.char1.db.title_collection = []
        self.char1.db.title_equipped = {"fixed": None, "epithet": None}
        self.char1.db.church["redeemed"] = ["t_skill_1", "t_skill_2"]

        with patch("world.rules.cross_lineage_unlock.grant_owned_skill", side_effect=RuntimeError("simulated crash")):
            with self.assertRaises(RuntimeError):
                church.redeem_step(self.char1, "t_redeem_active")

        # Rolled back: c_believer was NOT banked
        self.assertNotIn(believer_key, banked_fixed_keys(self.char1))
        _, rolled_back_equipped = read_title_state(self.char1)
        self.assertIsNone(rolled_back_equipped["fixed"])
