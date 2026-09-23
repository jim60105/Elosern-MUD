"""Behaviour suite for the church rulebook slice and its two load gates.

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

import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from world.lore.church import RedeemRow
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


if __name__ == "__main__":
    import unittest

    unittest.main()