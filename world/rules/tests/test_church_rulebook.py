"""Data-contract test: church rulebook cast-rail contract names its shipped rite rows

Behaviour suite for the church rulebook slice and its two load gates.

Every shipped row of ``church.yaml`` has exactly one ``test_rule_<id>``
(mirroring the ``combat_modifiers.yaml`` correspondence contract, audited
mechanically by ``test_rule_id_test_correspondence.py``). The gates — the
acceptance-curve monotonicity rule and the PASSIVE no-negativity polarity
rule — are exercised with planted bad rows, so the suite pins the mechanism,
not only the shipped tuning. The shipped-polarity guard enumerates the
catalogue rows rather than hardcoding keys so it stays green when a later
change appends Series rows.
"""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import yaml

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.lore.church import RedeemRow
from world.lore.church.places import resolve_church_place_keys
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.church import daily_cap_bonus
from world.rules.church_rulebook import (
    ACCEPT_ORDINAL_0_PERCENT,
    ACCEPT_TOP_ORDINAL_PERCENT,
    MITIGATION_TARGETS,
    ChurchRulebookError,
    PassiveEffectRow,
    get_church_rules,
    load_church_rules,
    validate_acceptance_curve,
    validate_passive_polarity,
)
from world.rules.rulebook.schema import (
    DuplicateRuleIdError,
    MissingRuleIdError,
    load_sectioned_rules,
)
from world.rules.player_messages import rejection_message
from world.rules.clock import WorldClock, _DAY_SECONDS
from world.rules.targeting import RoomActionContext

RULEBOOK_PATH = Path(__file__).parents[1] / "rulebook" / "church.yaml"

# The decided tuning finals (tasks 1.1/1.2): owner-pinned ordinal 0 = 50%,
# strictly monotonic to 100% at the top ordinal, proposal intermediates.
DECIDED_ACCEPTANCE = ((0, 50), (1, 65), (2, 80), (3, 90), (4, 100))
DECIDED_PRAY = (600, 40, 3)


def _church_body(**section_overrides):
    """Return a complete church.yaml mapping with per-section overrides."""
    # The passive_effects section mirrors the LIVE shipped rows (raw
    # ``{id, section, skill_key, effects}`` mappings, never the validator's
    # dataclass instances) so every temp-rulebook load passes the polarity
    # gate's one-to-one association against the shipped REDEEM_CATALOG.
    shipped_passive_rows = [
        {
            "id": effect.row_id,
            "section": "passive_effects",
            "skill_key": effect.skill_key,
            "effects": effect.effects,
        }
        for effect in get_church_rules().passive_effects
    ]
    body = {
        "acceptance": [
            {"id": "accept_ordinal_0", "section": "acceptance", "ordinal": 0, "accept_percent": 50},
            {"id": "accept_ordinal_1", "section": "acceptance", "ordinal": 1, "accept_percent": 65},
            {"id": "accept_ordinal_2", "section": "acceptance", "ordinal": 2, "accept_percent": 80},
            {"id": "accept_ordinal_3", "section": "acceptance", "ordinal": 3, "accept_percent": 90},
            {"id": "accept_ordinal_4", "section": "acceptance", "ordinal": 4, "accept_percent": 100},
        ],
        "pray": [{"id": "pray", "section": "pray", "duration_seconds": 600, "merit_per_pray": 40, "daily_cap": 3}],
        "accrual": [
            {"id": "accrual_pray_completed", "section": "accrual", "merit": 40, "daily_cap": 3},
            {"id": "accrual_offering_accepted", "section": "accrual", "per_row": True},
            {"id": "accrual_climax_while_enrolled", "section": "accrual", "merit": 10},
            *[
                {"id": k, "section": "accrual", **v}
                for k, v in get_church_rules().accrual.items()
                if k not in {"accrual_pray_completed", "accrual_offering_accepted", "accrual_climax_while_enrolled"}
            ],
        ],
        "offering": [
            {"id": "offering_payout_band", "section": "offering", "copper_lo": 20, "copper_hi": 80, "overrides": {}},
            {"id": "offering_enrollment_required", "section": "offering", "enrollment_required": True},
        ],
        "passive_effects": shipped_passive_rows,
    }
    body.update(section_overrides)
    return body


def _write_rules(sections=None):
    """Write a complete church.yaml to a temp file and return its path."""
    directory = tempfile.TemporaryDirectory()
    path = Path(directory.name) / "church.yaml"
    rows = []
    for section_rows in _church_body(**(sections or {})).values():
        rows.extend(section_rows)
    path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
    return path


class _TempFile(TestCase):
    """Convenience for tests that write throwaway rulebooks."""

    def setUp(self):
        super().setUp()
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)

    def _write(self, rows):
        path = Path(self._tempdir.name) / "church.yaml"
        path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
        return path


class ChurchRuleCorrespondenceRowsTests(TestCase):
    """The shipped slice is a load_rules-family sectioned table."""

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_shipped_slice_loads_through_the_sectioned_family(self):
        rows = load_sectioned_rules(RULEBOOK_PATH)
        self.assertTrue(rows)
        self.assertEqual(len({row.id for row in rows}), len(rows))
        self.assertEqual(
            {row.section for row in rows},
            {"acceptance", "pray", "accrual", "offering", "passive_effects"},
        )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_sectioned_loader_rejects_malformed_rows_naming_them(self):
        with tempfile.TemporaryDirectory() as directory:
            base = _church_body()
            path = Path(directory) / "church.yaml"
            rows = [row for rows in base.values() for row in rows]
            rows[0] = {"section": "acceptance", "ordinal": 0, "accept_percent": 50}
            path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
            with self.assertRaises(MissingRuleIdError):
                load_sectioned_rules(path)
            rows[0] = {
                "id": "accept_ordinal_0",
                "section": "acceptance",
                "ordinal": 0,
                "accept_percent": 50,
            }
            rows[-1] = {"id": "t_dup", "section": "acceptance", "accept_percent": 1}
            rows.append({"id": "accept_ordinal_0", "section": "pray"})
            path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
            with self.assertRaises(DuplicateRuleIdError):
                load_sectioned_rules(path)
            rows[-1] = {"id": "t_no_section"}
            path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "section"):
                load_sectioned_rules(path)


class ChurchTuningTests(TestCase):
    """The decided-and-recorded tuning finals (tasks 1.1/1.2)."""

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_rule_accept_ordinal_0(self):
        self.assertEqual(get_church_rules().acceptance[0], (0, ACCEPT_ORDINAL_0_PERCENT))

    def test_rule_accept_ordinal_1(self):
        self.assertEqual(get_church_rules().acceptance[1], (1, 65))

    def test_rule_accept_ordinal_2(self):
        self.assertEqual(get_church_rules().acceptance[2], (2, 80))

    def test_rule_accept_ordinal_3(self):
        self.assertEqual(get_church_rules().acceptance[3], (3, 90))

    def test_rule_accept_ordinal_4(self):
        self.assertEqual(
            get_church_rules().acceptance[4], (4, ACCEPT_TOP_ORDINAL_PERCENT)
        )

    def test_rule_pray(self):
        pray = get_church_rules().pray
        self.assertEqual(
            (pray.duration_seconds, pray.merit_per_pray, pray.daily_cap),
            DECIDED_PRAY,
        )

    def test_rule_accrual_pray_completed(self):
        self.assertEqual(
            get_church_rules().accrual["accrual_pray_completed"],
            {"merit": 40, "daily_cap": 3},
        )

    def test_rule_accrual_offering_accepted(self):
        # Per-row mechanism row: the per-row merit values ride the
        # OFFERING_CATALOG rows (design §4.3), not a literal here.
        self.assertEqual(
            get_church_rules().accrual["accrual_offering_accepted"], {"per_row": True}
        )

    def test_rule_accrual_climax_while_enrolled(self):
        self.assertEqual(
            get_church_rules().accrual["accrual_climax_while_enrolled"], {"merit": 10}
        )

    def test_rule_offering_payout_band(self):
        offering = get_church_rules().offering
        # The decided payout final (task 1.2): the integer band 20..80.
        self.assertEqual((offering.copper_lo, offering.copper_hi), (20, 80))
        self.assertLessEqual(offering.copper_lo, offering.copper_hi)
        self.assertIsInstance(offering.copper_lo, int)
        self.assertIsInstance(offering.copper_hi, int)
        self.assertEqual(offering.overrides, {})

    def test_rule_offering_enrollment_required(self):
        self.assertTrue(get_church_rules().offering.enrollment_required)

    def _identity_classifier_rows(self):
        """The Series A legacy-passive classification rows (identity
        multiplier; they carry no church-economy effect — their mechanics
        ride the pre-existing state-reaction rails). Selected structurally
        so these tests never name shipped catalogue keys."""
        return [
            effect
            for effect in get_church_rules().passive_effects
            if effect.effects == {"multiplier": 1.0}
        ]

    def test_rule_passive_pain_to_pleasure(self):
        self.assertGreaterEqual(len(self._identity_classifier_rows()), 3)
        self.assertEqual(self._identity_classifier_rows()[0].effects, {"multiplier": 1.0})

    def test_rule_passive_priestly_grace(self):
        self.assertGreaterEqual(len(self._identity_classifier_rows()), 3)
        self.assertEqual(self._identity_classifier_rows()[1].effects, {"multiplier": 1.0})

    def test_rule_passive_rapture_renewal(self):
        self.assertGreaterEqual(len(self._identity_classifier_rows()), 3)
        self.assertEqual(self._identity_classifier_rows()[2].effects, {"multiplier": 1.0})

    def test_rule_passive_vow_of_service(self):
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if "merit_percent" in effect.effects
        )
        # The decided vow_of_service finals (task 1.1): offering copper
        # +25%, offering/climax merit +10% — ledger multipliers only.
        self.assertEqual(row.effects, {"copper_percent": 25, "merit_percent": 10})

    def test_rule_rite_morning_devotion(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = get_church_rules().accrual[key]
        self.assertEqual(row["daily_cap"], 1)
        self.assertEqual(row["skill_key"], key)

    def test_rule_rite_shelter(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = get_church_rules().accrual[key]
        self.assertEqual(row["rest_bonus"], 25)
        self.assertEqual(row["skill_key"], key)

    def test_rule_rite_martial_blessing(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = get_church_rules().accrual[key]
        self.assertEqual(row["stat"], "defense")
        self.assertEqual(row["magnitude"], 10)
        self.assertEqual(row["cooldown_seconds"], 1800)
        self.assertEqual(row["skill_key"], key)

    def test_rule_passive_poverty_vow(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if effect.row_id == key
        )
        self.assertEqual(
            row.effects, {"copper_percent": 25, "pray_merit_percent": 25}
        )

    def test_rule_passive_obedience(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if effect.row_id == key
        )
        self.assertEqual(row.effects, {"multiplier": 2.0})

    def test_rule_passive_chastity_discipline(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if effect.row_id == key
        )
        self.assertEqual(row.effects, {"pray_merit_percent": 50})

    def test_rule_passive_temple_endurance(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if effect.row_id == key
        )
        self.assertEqual(
            row.effects,
            {"mitigation": {"high_exposure_defense_penalty": "25%"}},
        )

    def test_rule_passive_public_devotion(self):
        key = self._testMethodName.removeprefix("test_rule_")
        row = next(
            effect
            for effect in get_church_rules().passive_effects
            if effect.row_id == key
        )
        self.assertEqual(row.effects, {"merit_percent": 30})

    def test_shipped_acceptance_curve_is_the_decided_final(self):
        # The decide-and-record result (task 1.1): strictly monotonic, ordinal
        # 0 pinned at 50%, top ordinal pinned at 100%.
        self.assertEqual(get_church_rules().acceptance, DECIDED_ACCEPTANCE)
class AcceptanceCurveGateTests(_TempFile):
    """The loader monotonicity gate rejects bad curves naming the row."""

    def _write_acceptance(self, rows):
        rows = [
            {"section": "acceptance", **row}
            for row in rows
        ]
        body = _church_body(acceptance=rows)
        rows_flat = [row for section_rows in body.values() for row in section_rows]
        path = Path(self._tempdir.name) / "church.yaml"
        path.write_text(yaml.safe_dump(rows_flat, sort_keys=False), encoding="utf-8")
        return path

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_non_monotonic_curve_fails_naming_the_row(self):
        rows = [
            {"id": "accept_ordinal_0", "ordinal": 0, "accept_percent": 50},
            {"id": "accept_ordinal_1", "ordinal": 1, "accept_percent": 90},
            {"id": "accept_ordinal_2", "ordinal": 2, "accept_percent": 80},
            {"id": "accept_ordinal_3", "ordinal": 3, "accept_percent": 95},
            {"id": "accept_ordinal_4", "ordinal": 4, "accept_percent": 100},
        ]
        with self.assertRaisesRegex(ChurchRulebookError, "accept_ordinal_2"):
            load_church_rules(self._write_acceptance(rows))

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_ordinal_zero_not_50_percent_fails_naming_the_row(self):
        rows = [
            {"id": "accept_ordinal_0", "ordinal": 0, "accept_percent": 55},
            {"id": "accept_ordinal_1", "ordinal": 1, "accept_percent": 65},
            {"id": "accept_ordinal_2", "ordinal": 2, "accept_percent": 80},
            {"id": "accept_ordinal_3", "ordinal": 3, "accept_percent": 90},
            {"id": "accept_ordinal_4", "ordinal": 4, "accept_percent": 100},
        ]
        with self.assertRaisesRegex(ChurchRulebookError, "accept_ordinal_0"):
            load_church_rules(self._write_acceptance(rows))

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_top_ordinal_not_100_percent_fails_naming_the_row(self):
        rows = [
            {"id": "accept_ordinal_0", "ordinal": 0, "accept_percent": 50},
            {"id": "accept_ordinal_1", "ordinal": 1, "accept_percent": 65},
            {"id": "accept_ordinal_2", "ordinal": 2, "accept_percent": 80},
            {"id": "accept_ordinal_3", "ordinal": 3, "accept_percent": 90},
            {"id": "accept_ordinal_4", "ordinal": 4, "accept_percent": 95},
        ]
        with self.assertRaisesRegex(ChurchRulebookError, "accept_ordinal_4"):
            load_church_rules(self._write_acceptance(rows))

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_missing_ordinal_fails(self):
        rows = [
            {"id": "accept_ordinal_0", "ordinal": 0, "accept_percent": 50},
            {"id": "accept_ordinal_2", "ordinal": 2, "accept_percent": 80},
            {"id": "accept_ordinal_3", "ordinal": 3, "accept_percent": 90},
            {"id": "accept_ordinal_4", "ordinal": 4, "accept_percent": 100},
            # A fifth row that does not duplicate a covered ordinal: the
            # missing-ordinal check must fire, not the duplicate check.
            {"id": "accept_ordinal_6", "ordinal": 6, "accept_percent": 100},
        ]
        with self.assertRaisesRegex(ChurchRulebookError, "ordinal 1"):
            load_church_rules(self._write_acceptance(rows))


class PassivePolarityGateTests(TestCase):
    """The passive-no-negativity iron rule rejects planted bad rows."""

    def _catalogue(self, *rows: RedeemRow):
        return rows

    def _passive(self, skill_key="t_passive"):
        return RedeemRow(
            skill_key=skill_key, merit_price=100, tier="entry", polarity="passive"
        )

    def _effect(self, skill_key="t_passive", effects=None, row_id="t_effect_row"):
        return PassiveEffectRow(
            row_id=row_id, skill_key=skill_key, effects=effects or {}
        )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_negative_effect_value_fails_naming_both_keys(self):
        catalogue = self._catalogue(self._passive())
        with self.assertRaisesRegex(ChurchRulebookError, "t_passive"):
            validate_passive_polarity(
                catalogue,
                [
                    self._effect(
                        effects={"merit_percent": -10}, row_id="t_neg_row"
                    )
                ],
            )
        # 100% mitigation is legal boundary
        validate_passive_polarity(
            self._catalogue(self._passive()),
            [
                self._effect(
                    effects={"mitigation": {"high_exposure_defense_penalty": "100%"}}
                )
            ],
        )
        # 101% mitigation is rejected by the polarity gate
        with self.assertRaisesRegex(ChurchRulebookError, "mitigation"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [
                    self._effect(
                        effects={"mitigation": {"high_exposure_defense_penalty": "101%"}}
                    )
                ],
            )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_negative_percent_string_fails(self):
        with self.assertRaisesRegex(ChurchRulebookError, "copper_percent"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"copper_percent": "-25%"}, row_id="t_negpct_row")],
            )
        validate_passive_polarity(
            self._catalogue(self._passive()),
            [self._effect(effects={"merit_percent": "+10%"})],
        )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_unclassified_effect_key_fails(self):
        with self.assertRaisesRegex(ChurchRulebookError, "price_increase"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"price_increase": 25})],
            )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_multiplier_below_one_fails(self):
        with self.assertRaisesRegex(ChurchRulebookError, "multiplier"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"multiplier": 0})],
            )
        with self.assertRaisesRegex(ChurchRulebookError, "multiplier"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"multiplier": 0.5})],
            )
        with self.assertRaisesRegex(ChurchRulebookError, "multiplier"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"multiplier": float("nan")})],
            )
        with self.assertRaisesRegex(ChurchRulebookError, "multiplier"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"multiplier": float("inf")})],
            )
        validate_passive_polarity(
            self._catalogue(self._passive()),
            [self._effect(effects={"multiplier": 2})],
        )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_mitigation_of_an_existing_penalty_counts_positive(self):
        # temple_endurance-shaped effect: mitigating the SHIPPED defence
        # penalty (high_exposure_defense_penalty) is positive; an unknown
        # "penalty" is not an existing penalty and fails.
        self.assertIn("high_exposure_defense_penalty", MITIGATION_TARGETS)
        validate_passive_polarity(
            self._catalogue(self._passive()),
            [
                self._effect(
                    effects={
                        "mitigation": {"high_exposure_defense_penalty": "25%"}
                    }
                )
            ],
        )
        with self.assertRaisesRegex(ChurchRulebookError, "t_made_up_penalty"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"mitigation": {"t_made_up_penalty": 25}})],
            )
        with self.assertRaisesRegex(ChurchRulebookError, "mitigation"):
            validate_passive_polarity(
                self._catalogue(self._passive()),
                [self._effect(effects={"mitigation": {"high_exposure_defense_penalty": -5}})],
            )
        with self.assertRaisesRegex(ChurchRulebookError, "mitigation"):
            validate_passive_polarity(
                self._catalogue(self._passive()), [self._effect(effects={"mitigation": {}})]
            )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_passive_row_without_keyed_effect_row_fails(self):
        with self.assertRaisesRegex(ChurchRulebookError, "t_passive"):
            validate_passive_polarity(self._catalogue(self._passive()), [])

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_effect_row_for_non_passive_catalogue_row_fails(self):
        active = RedeemRow(
            skill_key="t_active", merit_price=100, tier="entry", polarity="active"
        )
        with self.assertRaisesRegex(ChurchRulebookError, "t_active"):
            validate_passive_polarity(
                self._catalogue(active),
                [self._effect(skill_key="t_active", effects={"merit_percent": 10})],
            )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_duplicate_keyed_effect_rows_fail(self):
        catalogue = self._catalogue(self._passive(), self._passive("t_passive_2"))
        with self.assertRaisesRegex(ChurchRulebookError, "duplicate|more than one"):
            validate_passive_polarity(
                catalogue,
                [
                    self._effect(effects={"merit_percent": 10}, row_id="t_row_a"),
                    self._effect(effects={"merit_percent": 5}, row_id="t_row_b"),
                ],
            )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_clean_passive_effect_set_passes(self):
        catalogue = self._catalogue(
            self._passive(),
            RedeemRow(
                skill_key="t_passive_2",
                merit_price=100,
                tier="mid",
                polarity="passive",
            ),
        )
        validate_passive_polarity(
            catalogue,
            [
                self._effect(
                    effects={
                        "merit_percent": 10,
                        "copper_percent": "+25%",
                        "multiplier": 1.5,
                    }
                ),
                self._effect(
                    skill_key="t_passive_2",
                    row_id="t_effect_row_2",
                    effects={"mitigation": {"high_exposure_defense_penalty": 10}},
                ),
            ],
        )

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_shipped_passive_rows_are_positive_polarity_only(self):
        # Data-contract guard over SHIPPED rows, written catalogue-driven
        # (never hardcoded) so it passes untouched when the order-catalogue
        # change later appends Series C. The effect rows come from the LIVE
        # rulebook slice: every shipped PASSIVE catalogue row has exactly one
        # keyed, classified pure-positive effect row.
        from world.lore.church import REDEEM_CATALOG

        passive = [row for row in REDEEM_CATALOG if row.polarity == "passive"]
        validate_passive_polarity(passive, get_church_rules().passive_effects)

    @covers_requirement(
        "church-ordination::series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside",
        "church-ordination::series-c-e-rule-rows-load-under-the-correspondence-and-polarity-gates",
    )
    def test_planted_downside_on_poverty_vow_is_rejected(self):
        poverty_key = next(p.skill_key for p in get_church_rules().passive_effects if "copper_percent" in p.effects and "pray_merit_percent" in p.effects)
        poverty = self._passive(skill_key=poverty_key)
        # Planted downside: price-increase / shop_price_increase is unclassified
        with self.assertRaisesRegex(ChurchRulebookError, poverty_key):
            validate_passive_polarity(
                self._catalogue(poverty),
                [self._effect(skill_key=poverty_key, effects={"price_increase": 20})],
            )
        # Negative copper_percent is rejected as negative
        with self.assertRaisesRegex(ChurchRulebookError, "negative"):
            validate_passive_polarity(
                self._catalogue(poverty),
                [self._effect(skill_key=poverty_key, effects={"copper_percent": -10})],
            )

    @covers_requirement(
        "church-ordination::series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside"
    )
    def test_obedience_doubles_merit_under_submission_status(self):
        from world.rules.church import scaled_merit_gain

        obedience_key = next(p.skill_key for p in get_church_rules().passive_effects if p.effects.get("multiplier", 0) > 1.0)

        class _MockEntity:
            def __init__(self, has_mark=False):
                self.skills = type("Skills", (), {"base_owned_keys": lambda self: (obedience_key,), "owned_keys": lambda self: (obedience_key,)})()
                self.attributes = type("Attrs", (), {"get": lambda self, key, default=None, category=None: frozenset({"actor_1"}) if has_mark and key == "submission_marks" else default})()

        unmarked = _MockEntity(has_mark=False)
        marked = _MockEntity(has_mark=True)
        # Without submission status: unchanged (x1)
        self.assertEqual(scaled_merit_gain(unmarked, 40), 40)
        # Under submission status: exactly doubled (x2)
        self.assertEqual(scaled_merit_gain(marked, 40), 80)

    @covers_requirement(
        "church-ordination::series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside"
    )
    def test_temple_endurance_mitigates_high_exposure_defense_penalty_by_25_percent(self):
        from unittest.mock import patch
        from world.rules.combat_modifiers import evaluate_combat_modifiers

        temple_key = next(p.skill_key for p in get_church_rules().passive_effects if "mitigation" in p.effects)

        class _MockEntity:
            def __init__(self, owns_temple=False):
                keys = (temple_key,) if owns_temple else ()
                self.skills = type("Skills", (), {
                    "owned_keys": lambda self: keys,
                    "base_owned_keys": lambda self: keys,
                    "conferred_grants": lambda self: (),
                    "effective_value": lambda self, k: 20,
                })()
                self.sexual = None
                self.db = type("Db", (), {"equipment": {}, "buffs": {}, "skills": {"passive": list(keys), "active": []}})()
                self.attributes = type("Attrs", (), {"get": lambda self, k, default=None, category=None: None})()

        non_holder = _MockEntity(owns_temple=False)
        holder = _MockEntity(owns_temple=True)
        with patch("world.rules.combat_modifiers.effective_exposure", return_value="高"):
            # Non-holder penalty is byte-identical -15
            self.assertEqual(evaluate_combat_modifiers(non_holder), {"defense": -15})
            # Holder penalty is 25% smaller in magnitude (-15 * 0.75 = -11.25)
            self.assertEqual(evaluate_combat_modifiers(holder), {"defense": -11.25})

    @covers_requirement(
        "church-ordination::series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside"
    )
    def test_public_devotion_public_venue_differential(self):
        from world.rules.church import scaled_merit_gain

        devotion_key = next(p.skill_key for p in get_church_rules().passive_effects if "merit_percent" in p.effects and "copper_percent" not in p.effects)

        class _MockEntity:
            def __init__(self, is_public=False):
                self.skills = type("Skills", (), {"base_owned_keys": lambda self: (devotion_key,), "owned_keys": lambda self: (devotion_key,)})()
                self.attributes = type("Attrs", (), {"get": lambda self, key, default=None, category=None: None})()
                self.location = type("Loc", (), {"tags": type("Tags", (), {"all": lambda self: ["public"] if is_public else []})()})()

        private_char = _MockEntity(is_public=False)
        public_char = _MockEntity(is_public=True)
        # In private venue: public_devotion does not apply
        self.assertEqual(scaled_merit_gain(private_char, 100), 100)
        # In public venue: +30% merit bonus applies (100 -> 130)
        self.assertEqual(scaled_merit_gain(public_char, 100), 130)


class ChurchRulebookShapeTests(_TempFile):
    """Section-shape rejections name the offending row."""

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_unknown_section_fails_naming_the_row(self):
        body = _church_body()
        body["acceptance"].append({"id": "t_bogus", "section": "bogus"})
        rows = [row for section_rows in body.values() for row in section_rows]
        path = self._write(rows)
        with self.assertRaisesRegex(ChurchRulebookError, "t_bogus"):
            load_church_rules(path)

    def test_missing_offering_rows_fail(self):
        body = _church_body()
        body["offering"] = [body["offering"][0]]
        rows = [row for section_rows in body.values() for row in section_rows]
        with self.assertRaisesRegex(ChurchRulebookError, "offering_enrollment_required"):
            load_church_rules(self._write(rows))

    def test_accrual_row_with_unregistered_skill_key_fails(self):
        body = _church_body()
        body["accrual"].append(
            {"id": "t_unknown_skill_accrual", "section": "accrual", "skill_key": "t_nonexistent_skill"}
        )
        rows = [row for section_rows in body.values() for row in section_rows]
        with self.assertRaisesRegex(ChurchRulebookError, "t_nonexistent_skill"):
            load_church_rules(self._write(rows))

    def test_malformed_accrual_row_fails(self):
        body = _church_body()
        body["accrual"].append(
            {"id": "t_bad_accrual", "section": "accrual", "merit": 0}
        )
        rows = [row for section_rows in body.values() for row in section_rows]
        with self.assertRaisesRegex(ChurchRulebookError, "t_bad_accrual"):
            load_church_rules(self._write(rows))

    def test_passive_effects_row_for_unknown_skill_fails_at_load(self):
        body = _church_body()
        body["passive_effects"] = [
            {
                "id": "t_orphan_effect",
                "section": "passive_effects",
                "skill_key": "t_orphan",
                "effects": {"merit_percent": 5},
            }
        ]
        rows = [row for section_rows in body.values() for row in section_rows]
        with self.assertRaisesRegex(ChurchRulebookError, "t_orphan"):
            load_church_rules(self._write(rows))


class ChurchSeriesECastTests(EvenniaTestCase):
    """The Series E holy rite utility rows on the unified cast rail."""

    @covers_requirement(
        "church-ordination::series-e-utility-rows-feed-the-core-loop"
    )
    def test_morning_devotion_lands_passive_and_refuses_cast_while_cap_bonus_stays_live(self):
        player = create_object(PlayerCharacter, key="t_morning_sister")
        player.race = "human"
        player.apply_race_baseline()
        player.db.skills = {"passive": ["rite_morning_devotion"], "active": []}
        player.db.church = {
            "merit": 100,
            "enrolled_tick": 0,
            "redeemed": ["rite_morning_devotion"],
            "blessing_last_tick": None,
            "daily": {"day": 0, "pray": 0},
        }
        self.assertEqual(daily_cap_bonus(player), 1)

        room = create_object(Room, key="t_room")
        player.location = room
        request = ActionRequest(
            actor=player,
            skill_key="rite_morning_devotion",
            targets=[player],
            context=RoomActionContext(room=room),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SKILL_NOT_ACTIVE)

    @covers_requirement(
        "church-ordination::series-e-utility-rows-feed-the-core-loop",
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer",
        "action-resolution-pipeline::the-church-rite-effect-handlers-reject-with-four-named-stable-reasons",
    )
    def test_martial_blessing_cast_cooldown_and_unenrolled_rejections(self):
        room = create_object(Room, key="t_bless_room")

        # 1. Unenrolled caster is rejected before staging
        unenrolled = create_object(PlayerCharacter, key="t_unenrolled")
        unenrolled.race = "human"
        unenrolled.apply_race_baseline()
        unenrolled.db.skills = {"active": ["rite_martial_blessing"], "passive": []}
        unenrolled.location = room
        req_unenrolled = ActionRequest(
            actor=unenrolled,
            skill_key="rite_martial_blessing",
            targets=[unenrolled],
            context=RoomActionContext(room=room),
        )
        res_unenrolled = ActionResolver.resolve(req_unenrolled)
        self.assertEqual(res_unenrolled.outcome, "rejected")
        self.assertEqual(res_unenrolled.reason, RejectReason.RITE_NOT_ENROLLED)

        # 2. Enrolled caster succeeds: mounts buff, updates cooldown stamp, emits rite_cast
        player = create_object(PlayerCharacter, key="t_blessed_sister")
        player.race = "human"
        player.apply_race_baseline()
        player.location = room
        player.db.skills = {"active": ["rite_martial_blessing"], "passive": []}
        player.db.church = {
            "merit": 100,
            "enrolled_tick": 0,
            "redeemed": ["rite_martial_blessing"],
            "blessing_last_tick": None,
            "daily": {"day": 0, "pray": 0},
        }
        clock = WorldClock(tick=1000)
        req = ActionRequest(
            actor=player,
            skill_key="rite_martial_blessing",
            targets=[player],
            context=RoomActionContext(room=room),
        )
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.church.log_info") as mock_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settlement = settle_out_of_combat_cast(req, clock=clock)

        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(player.db.church["blessing_last_tick"], 1000)
        self.assertTrue(player.db.buffs and "martial_blessing" in player.db.buffs)
        self.assertFalse(player.attributes.has("martial_blessing_last_tick"))

        # Event verified
        rite_calls = [c for c in mock_info.call_args_list if c.args and c.args[0] == "rite_cast"]
        self.assertEqual(len(rite_calls), 1)
        self.assertEqual(rite_calls[0].kwargs["context"]["rite"], "rite_martial_blessing")
        self.assertEqual(rite_calls[0].kwargs["context"]["char"], str(player))
        self.assertEqual(rite_calls[0].kwargs["context"]["tick"], 1000)

        # 3. Recast inside cooldown window is stable rejection
        recast_req = ActionRequest(
            actor=player,
            skill_key="rite_martial_blessing",
            targets=[player],
            context=RoomActionContext(room=room),
        )
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            recast_res = ActionResolver.resolve(recast_req)
        self.assertEqual(recast_res.outcome, "rejected")
        self.assertEqual(recast_res.reason, RejectReason.RITE_COOLDOWN_ACTIVE)

    @covers_requirement(
        "church-ordination::series-e-utility-rows-feed-the-core-loop",
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer",
        "action-resolution-pipeline::the-church-rite-effect-handlers-reject-with-four-named-stable-reasons",
    )
    def test_shelter_cast_venue_rest_bonus_and_day_rollover(self):
        church_room = create_object(Room, key="t_sanctuary_venue")
        church_place = next(iter(resolve_church_place_keys()))
        church_room.tags.add(church_place)

        plain_room = create_object(Room, key="t_plain_field")

        player = create_object(PlayerCharacter, key="t_sheltered_sister")
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.current = 50
        player.traits.sp.current = 50
        player.db.wallet = 100
        player.db.skills = {"active": ["rite_shelter"], "passive": []}
        player.db.church = {
            "merit": 100,
            "enrolled_tick": 0,
            "redeemed": ["rite_shelter"],
            "blessing_last_tick": None,
            "daily": {"day": 1, "pray": 0},
        }

        # 1. Outside church venue: rejected
        player.location = plain_room
        req_outside = ActionRequest(
            actor=player,
            skill_key="rite_shelter",
            targets=[player],
            context=RoomActionContext(room=plain_room),
        )
        res_outside = ActionResolver.resolve(req_outside)
        self.assertEqual(res_outside.outcome, "rejected")
        self.assertEqual(res_outside.reason, RejectReason.RITE_OUTSIDE_VENUE)

        # 2. Inside church venue: success
        player.location = church_room
        clock = WorldClock(tick=1 * _DAY_SECONDS + 500)
        req_inside = ActionRequest(
            actor=player,
            skill_key="rite_shelter",
            targets=[player],
            context=RoomActionContext(room=church_room),
        )
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.church.log_info") as mock_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settlement = settle_out_of_combat_cast(req_inside, clock=clock)

        self.assertEqual(settlement.result.outcome, "success")
        self.assertGreaterEqual(player.traits.hp.current, 75)
        self.assertGreaterEqual(player.traits.sp.current, 75)
        self.assertEqual(player.db.church["daily"].get("shelter"), 1)
        self.assertNotIn("shelter_rest_flag", player.db.church)
        self.assertEqual(player.db.church["merit"], 100)
        self.assertEqual(player.db.wallet, 100)

        rite_calls = [c for c in mock_info.call_args_list if c.args and c.args[0] == "rite_cast"]
        self.assertEqual(len(rite_calls), 1)
        self.assertEqual(rite_calls[0].kwargs["context"]["rite"], "rite_shelter")

        # 3. Same-day recast: rejected
        recast_req = ActionRequest(
            actor=player,
            skill_key="rite_shelter",
            targets=[player],
            context=RoomActionContext(room=church_room),
        )
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            recast_res = ActionResolver.resolve(recast_req)
        self.assertEqual(recast_res.outcome, "rejected")
        self.assertEqual(recast_res.reason, RejectReason.RITE_ALREADY_SHELTERED)

        # 4. Day rollover: advances to day 2, re-arms shelter
        next_day_clock = WorldClock(tick=2 * _DAY_SECONDS + 100)
        next_day_req = ActionRequest(
            actor=player,
            skill_key="rite_shelter",
            targets=[player],
            context=RoomActionContext(room=church_room),
        )
        with (
            patch("world.rules.clock.get_world_clock", return_value=next_day_clock),
            patch("world.rules.church.log_info") as mock_info2,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settlement2 = settle_out_of_combat_cast(next_day_req, clock=next_day_clock)

        self.assertEqual(settlement2.result.outcome, "success")
        self.assertEqual(player.db.church["daily"]["day"], 2)
        self.assertEqual(player.db.church["daily"]["shelter"], 1)

        # 5. Every rite rejection renders its fixed zh-TW line (player-message surface)
        for reason, line in (
            (RejectReason.RITE_NOT_ENROLLED, "你尚未入教，無法施展聖禮。"),
            (RejectReason.RITE_COOLDOWN_ACTIVE, "聖禮冷卻中，尚無法再次施展。"),
            (RejectReason.RITE_OUTSIDE_VENUE, "此處並非教會聖所，無法施展此聖禮。"),
            (RejectReason.RITE_ALREADY_SHELTERED, "今日已獲得聖所庇護，無法再次施展。"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(rejection_message(reason), line)

    @covers_requirement(
        "church-ordination::series-e-utility-rows-feed-the-core-loop",
        "battlefield-commit-surface::snapshotted-surfaces-gains-a-battlefield-surface-covering-battlefield-fled",
        "cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces",
    )
    def test_martial_blessing_inner_commit_failure_rolls_back_church_surface(self):
        church_room = create_object(Room, key="t_sanctuary_rb")
        player = create_object(PlayerCharacter, key="t_bless_rollback")
        player.race = "human"
        player.apply_race_baseline()
        player.location = church_room
        player.db.skills = {"active": ["rite_martial_blessing"], "passive": []}
        initial_ledger = {
            "merit": 100,
            "enrolled_tick": 0,
            "redeemed": ["rite_martial_blessing"],
            "blessing_last_tick": None,
            "daily": {"day": 1, "pray": 0},
        }
        player.db.church = deepcopy(initial_ledger)
        before_buffs = deepcopy(player.db.buffs)
        before_tick = 5000
        clock = WorldClock(tick=before_tick)

        req = ActionRequest(
            actor=player,
            skill_key="rite_martial_blessing",
            targets=[player],
            context=RoomActionContext(room=church_room),
        )

        with (
            patch("world.rules.buffs.apply_buff", side_effect=RuntimeError("injected buff failure")),
            patch("world.rules.church.log_info") as mock_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settlement = settle_out_of_combat_cast(req, clock=clock)

        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertEqual(settlement.result.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(player.db.church, initial_ledger)
        self.assertEqual(player.db.buffs, before_buffs)
        self.assertEqual(clock.tick, before_tick)
        events = [c.args[0] for c in mock_info.call_args_list if c.args]
        self.assertNotIn("rite_cast", events)

    @covers_requirement(
        "church-ordination::series-e-utility-rows-feed-the-core-loop",
        "battlefield-commit-surface::snapshotted-surfaces-gains-a-battlefield-surface-covering-battlefield-fled",
        "cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces",
    )
    def test_shelter_inner_commit_failure_rolls_back_church_surface(self):
        church_room = create_object(Room, key="t_sanctuary_rb2")
        church_place = next(iter(resolve_church_place_keys()))
        church_room.tags.add(church_place)

        player = create_object(PlayerCharacter, key="t_shelter_rollback")
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.current = 40
        player.traits.sp.current = 40
        player.location = church_room
        player.db.skills = {"active": ["rite_shelter"], "passive": []}
        initial_ledger = {
            "merit": 100,
            "enrolled_tick": 0,
            "redeemed": ["rite_shelter"],
            "blessing_last_tick": None,
            "daily": {"day": 1, "pray": 0},
        }
        player.db.church = deepcopy(initial_ledger)
        before_tick = 1 * _DAY_SECONDS + 200
        clock = WorldClock(tick=before_tick)

        req = ActionRequest(
            actor=player,
            skill_key="rite_shelter",
            targets=[player],
            context=RoomActionContext(room=church_room),
        )

        with (
            patch("world.rules.action.effects.church._apply_shelter_traits", side_effect=RuntimeError("injected trait failure")),
            patch("world.rules.church.log_info") as mock_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settlement = settle_out_of_combat_cast(req, clock=clock)

        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertEqual(settlement.result.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(player.db.church, initial_ledger)
        self.assertEqual(player.traits.hp.current, 40)
        self.assertEqual(player.traits.sp.current, 40)
        self.assertEqual(clock.tick, before_tick)
        events = [c.args[0] for c in mock_info.call_args_list if c.args]
        self.assertNotIn("rite_cast", events)


if __name__ == "__main__":
    import unittest

    unittest.main()
