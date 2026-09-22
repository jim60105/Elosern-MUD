"""Data-contract test: frozen church catalogues and the derived church-place venue set

The shipped OFFERING_CATALOG seeds resolve against the live sexual-act
catalogue, REDEEM_CATALOG ships as a validated empty shell with its row
validator rejecting planted malformed rows by name, `saintess_vessel` never
enters the redemption catalogue, and the church-place set is derived
fail-closed from the place registry's authored `church` kwargs.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch

from world.lore.church import (
    OFFERING_CATALOG,
    REDEEM_CATALOG,
    ChurchLoreError,
    OfferingRow,
    RedeemRow,
    validate_offering_rows,
    validate_redeem_rows,
)
from world.lore.church.places import (
    CHURCH_PLACES,
    CHURCH_VENUE_KEY,
    resolve_church_place_keys,
)
from world.lore.settlements.places import PLACE_REGISTRY


class OfferingCatalogueTests(TestCase):
    @covers_requirement(
        "church-ordination::the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows"
    )
    def test_shipped_offering_seeds_resolve_against_the_act_catalogue(self):
        from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
        from world.skills.sexual_acts import unlocked_act_keys_for

        self.assertTrue(OFFERING_CATALOG)
        ownable = unlocked_act_keys_for(owned_keys=(), counter_values={})
        for row in OFFERING_CATALOG:
            with self.subTest(offering=row.key):
                self.assertIn(row.act_key, SEXUAL_ACT_REGISTRY)
                # Seed rows are the currently-ownable acts (a fresh character
                # owns them through the empty-unlock seed gates): the accrual
                # change's row menu projects over current ownership, so a seed
                # row must never reference an act a fresh character cannot own.
                self.assertIn(row.act_key, ownable)

    @covers_requirement(
        "church-ordination::the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows"
    )
    def test_validator_rejects_planted_malformed_rows_by_name(self):
        def row(**overrides):
            return replace(
                OfferingRow(key="t_off", act_key="t_act", merit=5),
                **overrides,
            )

        cases = (
            (row(key=""), "key"),
            (row(act_key=""), "act_key"),
            (row(merit=0), "merit"),
            (row(merit=True), "merit"),
            (row(copper=-1), "copper"),
            (row(min_lineage=""), "min_lineage"),
        )
        for planted, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(
                ChurchLoreError, fragment
            ):
                validate_offering_rows((planted,))
        with self.assertRaisesRegex(ChurchLoreError, "duplicate"):
            validate_offering_rows(
                (row(), row(key="t_off", act_key="t_other"))
            )


class RedeemCatalogueShellTests(TestCase):
    @covers_requirement(
        "church-ordination::the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows"
    )
    def test_shipped_shell_is_validated_and_empty(self):
        # The validated EMPTY shell: no placeholder prices, and the vessel
        # appears nowhere in it (the negative-set contract).
        self.assertEqual(REDEEM_CATALOG, ())
        validate_redeem_rows(REDEEM_CATALOG)
        self.assertNotIn(
            "saintess_vessel", {row.skill_key for row in REDEEM_CATALOG}
        )

    @covers_requirement(
        "church-ordination::the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows"
    )
    def test_validator_rejects_planted_malformed_rows_by_name(self):
        def row(**overrides):
            return replace(
                RedeemRow(skill_key="t_skill", merit_price=100, tier="entry", polarity="passive"),
                **overrides,
            )

        cases = (
            (row(skill_key=""), "skill_key"),
            (row(merit_price=0), "placeholder"),
            (row(merit_price=-5), "placeholder"),
            (row(merit_price=True), "integer"),
            (row(tier="epic"), "tier"),
            (row(polarity="neutral"), "polarity"),
            (row(prereq_keys=("",)), "prereq"),
            (row(prereq_keys=(7,)), "prereq"),
            (row(prereq_keys=("t_skill", "t_skill")), "duplicated"),
            (row(prereq_keys=("lineage:elf",)), "lineage"),
            (row(prereq_keys=("t_saintess_lineage",)), "lineage"),
        )
        for planted, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(
                ChurchLoreError, fragment
            ):
                validate_redeem_rows((planted,))
        with self.assertRaisesRegex(ChurchLoreError, "duplicate redemption"):
            validate_redeem_rows(
                (row(), row(skill_key="t_skill", merit_price=50, tier="mid"))
            )


class ChurchPlaceDerivationTests(TestCase):
    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_the_derived_church_set_is_non_empty_complete_and_ordered(self):
        self.assertEqual(CHURCH_PLACES, ("altoria_temple", "altoria_sanctum"))
        self.assertEqual(set(CHURCH_PLACES), {"altoria_temple", "altoria_sanctum"})

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_a_conflicting_church_flag_fails_closed_at_derivation(self):
        temple = PLACE_REGISTRY["altoria_temple"]
        conflicting = replace(
            temple,
            key="t_conflicting_church_place",
            service_id="t_conflicting_church_place",
            authored_kwargs=(("church", "dark_church"),),
        )
        with patch.dict(PLACE_REGISTRY, {"t_conflicting_church_place": conflicting}):
            with self.assertRaisesRegex(ValueError, "t_conflicting_church_place"):
                resolve_church_place_keys()
        # The canonical identity itself names the church the venue belongs to.
        self.assertEqual(CHURCH_VENUE_KEY, "light_church")

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_a_duplicate_church_flag_on_one_place_fails_closed(self):
        # The delta's fail-closed rule covers DUPLICATE authoring too: a place
        # listing the flag twice must raise regardless of whether the two
        # values agree — dict() would silently keep the last one.
        temple = PLACE_REGISTRY["altoria_temple"]
        for pairs in (
            (("church", "light_church"), ("church", "light_church")),
            (("church", "dark_church"), ("church", "light_church")),
            (("church", "light_church"), ("church", "dark_church")),
        ):
            with self.subTest(pairs=pairs):
                duplicate = replace(
                    temple,
                    key="t_duplicate_church_place",
                    service_id="t_duplicate_church_place",
                    authored_kwargs=pairs,
                )
                with patch.dict(
                    PLACE_REGISTRY, {"t_duplicate_church_place": duplicate}
                ):
                    with self.assertRaisesRegex(ValueError, "more than once"):
                        resolve_church_place_keys()


if __name__ == "__main__":
    import unittest

    unittest.main()