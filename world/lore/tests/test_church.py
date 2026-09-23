"""Data-contract test: frozen church catalogues, the derived church-place venue set, and the church lore/status realignment contract

The shipped OFFERING_CATALOG seeds resolve against the live sexual-act
catalogue, the shipped REDEEM_CATALOG rows validate through the row
validator (which rejects planted malformed rows by name), `saintess_vessel`
never enters the redemption catalogue, and the church-place set is derived
fail-closed from the place registry's authored `church` kwargs. The lore
documents are realigned with the shipped mechanics: the once-per-generation
Saintess framing is retired in favour of the no-uniqueness enrollment grant,
and the 神殿／聖所 ministry counter carries the 〔已實作〕 status tag.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from pathlib import Path
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

REPO_ROOT = Path(__file__).resolve().parents[3]

# The once-per-generation donated-princess framing, retired by this change:
# a search across the lore documents must find none of these phrasings.
_RETIRED_FRAMINGS = (
    "每代由王國王室獻任的公主",
    "王室每代獻任的公主",
    "每代獻一女",
)


class OfferingCatalogueTests(TestCase):
    @covers_requirement(
        "church-ordination::the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows"
    )
    def test_shipped_offering_seeds_resolve_against_the_act_catalogue(self):
        from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
        from world.skills.sexual_acts import unlocked_act_keys_for
        from world.skills.registry import SKILL_REGISTRY

        self.assertTrue(OFFERING_CATALOG)
        ownable = unlocked_act_keys_for(owned_keys=(), counter_values={})
        for row in OFFERING_CATALOG:
            with self.subTest(offering=row.key):
                if row.act_key in SEXUAL_ACT_REGISTRY:
                    # Seed rows are the currently-ownable acts (a fresh
                    # character owns them through the empty-unlock seed
                    # gates): the accrual change's row menu projects over
                    # current ownership, so a seed row must never reference
                    # an act a fresh character cannot own.
                    self.assertIn(row.act_key, ownable)
                else:
                    # Advanced Series D ministry rows (implement-church-
                    # redemption) resolve against the redemption catalogue's
                    # own SKILL_REGISTRY row by the shared act key — the
                    # same registry row serves both catalogues with zero
                    # duplicated data (design §4.2/§5.5).
                    self.assertIn(row.act_key, SKILL_REGISTRY)

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
    def test_shipped_catalogue_is_validated_and_vessel_absent(self):
        # The 16 Series A/B/D rows land with implement-church-redemption
        # (Series C/E with the order-catalogue change). The lasting pins:
        # the shipped set validates through the row validator, and the
        # vessel appears nowhere in it (the permanent negative-set
        # contract) at any price.
        self.assertTrue(REDEEM_CATALOG)
        validate_redeem_rows(REDEEM_CATALOG)
        self.assertNotIn(
            "saintess_vessel", {row.skill_key for row in REDEEM_CATALOG}
        )

    @covers_requirement(
        "church-ordination::series-c-e-rule-rows-load-under-the-correspondence-and-polarity-gates",
        "church-ordination::series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside",
        "church-ordination::series-e-utility-rows-feed-the-core-loop",
    )
    def test_catalogue_completes_at_24_rows_without_lineage_or_vessel(self):
        from world.skills.registry import SKILL_REGISTRY

        # Exactly 24 rows total (16 Series A/B/D + 8 Series C/E)
        self.assertEqual(len(REDEEM_CATALOG), 24)
        keys = [row.skill_key for row in REDEEM_CATALOG]
        # No duplicates
        self.assertEqual(len(set(keys)), 24)
        # saintess_vessel absent
        self.assertNotIn("saintess_vessel", set(keys))
        # Every key exists in SKILL_REGISTRY and is non-lineage (no lineage_key)
        for key in keys:
            with self.subTest(key=key):
                self.assertIn(key, SKILL_REGISTRY)
                skill = SKILL_REGISTRY[key]
                self.assertIsNone(getattr(skill, "lineage_key", None))
        # Validate through row validator
        validate_redeem_rows(REDEEM_CATALOG)

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


class ChurchLoreRealignmentTests(TestCase):
    """The lore documents state the no-uniqueness office and current status."""

    def _read(self, relative: str) -> str:
        return (REPO_ROOT / relative).read_text(encoding="utf-8")

    @covers_requirement(
        "church-ordination::lore-documents-state-the-no-uniqueness-office-and-current-status"
    )
    def test_the_religion_overview_states_the_no_uniqueness_enrollment_framing(self):
        section = self._read("docs/lore/overview.md")
        self.assertIn("任何女性王族後裔皆可獻與教會", section)
        self.assertIn("於入教儀式中祝聖", section)
        self.assertNotIn("每代由王國王室獻任的公主", section)

    @covers_requirement(
        "church-ordination::lore-documents-state-the-no-uniqueness-office-and-current-status"
    )
    def test_the_light_tree_footnote_reflects_the_enrollment_grant(self):
        footnote = self._read("docs/lore/skill-trees/light.md")
        self.assertIn("入教儀式中祝聖的容器職位", footnote)
        self.assertIn("無唯一性", footnote)
        self.assertIn("〔已實作〕被動 `saintess_vessel`", footnote)
        self.assertNotIn("王室每代獻任的公主", footnote)
        self.assertNotIn("頭銜隨之移交", footnote)

    @covers_requirement(
        "church-ordination::lore-documents-state-the-no-uniqueness-office-and-current-status"
    )
    def test_the_temple_section_status_tag_tracks_the_landing(self):
        section = self._read("docs/lore/settlement-locations.md")
        self.assertIn("〔已實作〕`church join`", section)
        self.assertIn("入教／洗禮", section)

    @covers_requirement(
        "church-ordination::lore-documents-state-the-no-uniqueness-office-and-current-status"
    )
    def test_the_retired_once_per_generation_framing_appears_nowhere(self):
        offenders: list[str] = []
        for path in (REPO_ROOT / "docs" / "lore").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for claim in _RETIRED_FRAMINGS:
                if claim in text:
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT).as_posix()}:{claim}"
                    )
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    import unittest

    unittest.main()