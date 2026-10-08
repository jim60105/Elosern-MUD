"""Behavior tests for the tier-band invariant of the species/variant registry.

Every tier, band, rank and profile value here is a file-local synthetic fixture
with invented values: no shipped species, variant, tier, grade, or number is
named, and the bands arrive through the validator's own injectable band face.
The shipped rows are checked by the registered data-contract test instead, so
this module can exercise every rejection without reading shipped lore data.
"""

import unittest

from tools.spec_traceability import covers_requirement

from world.lore.monster_species import (
    MonsterCombatProfile,
    MonsterSpecies,
    MonsterSpeciesRegistryError,
    MonsterVariant,
    _default_tier_band_face,
    validate_monster_species_registry,
)
from world.lore.monsters import MonsterStaticBand, MonsterTier

HABITAT = "t_fixture_hollow"
SPECIES = "t_fixture_species"
VARIANT = "t_fixture_variant"
TIER = "t_fixture_tier"
UNBANDED_TIER = "t_fixture_tier_unbanded"
RANK_LOW = "t_rank_low"
RANK_MID = "t_rank_mid"
RANK_HIGH = "t_rank_high"
RANK_ABOVE = "t_rank_above"

HP_BAND = (20, 40)
PHYSICAL_BAND = (2, 9)
AGILITY_BAND = (6, 13)
DEFENSE_BAND = (1, 4)
MAGIC_BAND = (0, 0)
RANK_RANGE = (RANK_LOW, RANK_HIGH)

# The invented grade vocabulary, in its invented order: the rank range above
# spans RANK_LOW..RANK_HIGH, and RANK_ABOVE sits beyond it.
GRADES = (RANK_LOW, RANK_MID, RANK_HIGH, RANK_ABOVE)

PROFILE_VALUES = {
    "hp": 30,
    "mp": 1,
    "sp": 1,
    "atk_phys": 5,
    "agility": 6,
    "defense": 4,
    "magic_power": 0,
}


def _profile(**overrides: object) -> MonsterCombatProfile:
    values = dict(PROFILE_VALUES)
    values.update(overrides)
    return MonsterCombatProfile(**values)  # type: ignore[arg-type]


def _species() -> MonsterSpecies:
    return MonsterSpecies(
        key=SPECIES,
        display_name_zh="試製物種",
        published_description_zh="試製物種敘述。",
        published_appearance_zh="試製物種外觀。",
        published_ecology_zh="試製物種生態。",
        habitat_tags=(HABITAT,),
        author_hidden_truth_zh="（試製私有真相註記）",
        author_explanation_zh="（試製私有解釋註記）",
        author_conjecture_zh="（試製私有未證實註記）",
        default_variant_key=VARIANT,
        ordinary_variant=True,
    )


def _variant(**overrides: object) -> MonsterVariant:
    values: dict[str, object] = {
        "key": VARIANT,
        "species_key": SPECIES,
        "display_name_zh": "試製變體",
        "description_zh": "試製變體敘述。",
        "threat_tier": TIER,
        "ordinary_variant": True,
        "combat_profile": _profile(),
        "danger_grade": RANK_MID,
    }
    values.update(overrides)
    return MonsterVariant(**values)  # type: ignore[arg-type]


def _faces(**overrides: object) -> dict[str, object]:
    """The injected validation faces: invented keys, bands, and ranks only."""
    faces: dict[str, object] = {
        "habitat_face": (HABITAT,),
        "tier_face": (TIER, UNBANDED_TIER),
        "grade_face": GRADES,
        "tier_band_face": {
            TIER: (HP_BAND, PHYSICAL_BAND, AGILITY_BAND, DEFENSE_BAND, MAGIC_BAND, RANK_RANGE),
        },
    }
    faces.update(overrides)
    return faces


def _tier(agility_band: tuple[int, int] | None = None) -> MonsterTier:
    """One invented tier with distinguishable physical bounds."""
    return MonsterTier(
        TIER,
        "試製層級",
        RANK_RANGE,
        MonsterStaticBand(
            atk_phys=PHYSICAL_BAND,
            agility=AGILITY_BAND if agility_band is None else agility_band,
            defense=DEFENSE_BAND,
            magic_power=MAGIC_BAND,
        ),
        HP_BAND,
        ("試製層級魔物",),
        "試製層級敘述。",
    )


class TierBandFaceProjectionTests(unittest.TestCase):
    """Requirement: the band face carries the tier's declared bands."""

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_an_asymmetric_tier_projects_its_own_bands(self):
        face = _default_tier_band_face({TIER: _tier()})
        self.assertEqual(
            face[TIER], (HP_BAND, PHYSICAL_BAND, AGILITY_BAND, DEFENSE_BAND, MAGIC_BAND, RANK_RANGE)
        )

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_changed_axis_is_preserved_by_projection(self):
        skewed = (PHYSICAL_BAND[0] + 4, PHYSICAL_BAND[1] + 4)
        face = _default_tier_band_face({TIER: _tier(agility_band=skewed)})
        self.assertEqual(face[TIER][2], skewed)
        self.assertEqual(face[TIER][1], PHYSICAL_BAND)


class TierBandInvariantTests(unittest.TestCase):
    """Requirement: a shipped rating lies inside the tier band it declares."""

    def _validate(self, variant: MonsterVariant, **face_overrides: object) -> None:
        validate_monster_species_registry(
            {SPECIES: _species()},
            {VARIANT: variant},
            **_faces(**face_overrides),
        )

    def _rejection(self, variant: MonsterVariant, **face_overrides: object) -> str:
        with self.assertRaises(MonsterSpeciesRegistryError) as caught:
            self._validate(variant, **face_overrides)
        return str(caught.exception)

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_an_in_band_profile_and_grade_are_accepted(self):
        self._validate(_variant())

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_value_exactly_on_a_band_edge_is_inside_the_band(self):
        self._validate(
            _variant(
                combat_profile=_profile(
                    hp=HP_BAND[1],
                    atk_phys=PHYSICAL_BAND[0],
                    agility=AGILITY_BAND[1],
                    defense=DEFENSE_BAND[0],
                    magic_power=MAGIC_BAND[1],
                ),
                danger_grade=RANK_HIGH,
            )
        )

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_hp_above_the_tier_band_is_rejected(self):
        self._rejection(_variant(combat_profile=_profile(hp=HP_BAND[1] + 1)))

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_hp_below_the_tier_band_is_rejected(self):
        self._rejection(_variant(combat_profile=_profile(hp=HP_BAND[0] - 1)))

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_each_physical_axis_outside_the_tier_band_is_rejected(self):
        for axis, band in (("atk_phys", PHYSICAL_BAND), ("agility", AGILITY_BAND), ("defense", DEFENSE_BAND)):
            for value in (band[0] - 1, band[1] + 1):
                with self.subTest(axis=axis, value=value):
                    message = self._rejection(
                        _variant(combat_profile=_profile(**{axis: value}))
                    )
                    self.assertIn(VARIANT, message)
                    self.assertIn(axis, message)
                    self.assertIn(str(value), message)

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_nonzero_magic_power_is_rejected_against_a_zero_band(self):
        for value in (1, MAGIC_BAND[1] + 5):
            with self.subTest(value=value):
                self._rejection(
                    _variant(combat_profile=_profile(magic_power=value))
                )

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_grade_outside_the_tier_rank_range_is_rejected(self):
        self._rejection(_variant(danger_grade=RANK_ABOVE))

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_variant_whose_tier_carries_no_band_row_is_rejected(self):
        message = self._rejection(_variant(threat_tier=UNBANDED_TIER))
        self.assertIn(UNBANDED_TIER, message)

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_a_rank_range_naming_an_unknown_rank_is_rejected(self):
        self._rejection(
            _variant(),
            tier_band_face={
                TIER: (HP_BAND, PHYSICAL_BAND, AGILITY_BAND, DEFENSE_BAND, MAGIC_BAND, (RANK_LOW, "t_rank_unknown")),
            },
        )

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_the_rejection_names_the_variant_the_axis_the_value_and_the_band(self):
        value = HP_BAND[1] + 1
        message = self._rejection(
            _variant(combat_profile=_profile(hp=value))
        )
        self.assertIn(VARIANT, message)
        self.assertIn("hp", message)
        self.assertIn(str(value), message)
        self.assertIn(str(HP_BAND), message)

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_the_pools_carry_no_band(self):
        # MP and SP have no tier band by design, so any authored pool validates
        # here; their approved zeros are pinned by the shipped-content contract.
        self._validate(
            _variant(combat_profile=_profile(mp=999, sp=999))
        )

    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_an_unbanded_tier_is_rejected_even_without_a_rating(self):
        # Face completeness is unconditional: the band face must carry every
        # declared tier, so a rating can never arrive with nowhere to go.
        message = self._rejection(
            _variant(
                threat_tier=UNBANDED_TIER,
                combat_profile=None,
                danger_grade=None,
            )
        )
        self.assertIn(UNBANDED_TIER, message)

    @covers_requirement("lore-registries::monstertier-registry-has-physical-stat-and-hp-bands-derived-from-guild-rank")
    @covers_requirement("monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band")
    def test_open_upper_bounds_accept_large_literals_and_keep_lower_and_magic_limits(self):
        bands = {TIER: ((1200, None), (60, None), (60, None), (60, None), MAGIC_BAND, RANK_RANGE)}
        profile = _profile(hp=5000, atk_phys=220, agility=190, defense=170)
        self._validate(_variant(combat_profile=profile), tier_band_face=bands)
        for axis, value in (("hp", 1199), ("atk_phys", 59), ("agility", 59), ("defense", 59), ("magic_power", 1)):
            with self.subTest(axis=axis):
                import dataclasses
                message = self._rejection(
                    _variant(combat_profile=dataclasses.replace(profile, **{axis: value})),
                    tier_band_face=bands,
                )
                self.assertIn(axis, message)

    @covers_requirement("lore-registries::monstertier-registry-has-physical-stat-and-hp-bands-derived-from-guild-rank")
    def test_endurance_does_not_require_a_physical_ratio(self):
        self._validate(_variant(combat_profile=_profile(hp=20, atk_phys=9, agility=13, defense=4)))


if __name__ == "__main__":
    unittest.main()
