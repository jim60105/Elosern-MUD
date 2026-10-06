"""Behavior tests for the tier-band invariant of the species/variant registry.

Every tier, band, rank and profile value here is a file-local synthetic fixture
with invented values: no shipped species, variant, tier, grade, or number is
named, and the bands arrive through the validator's own injectable band face.
The shipped rows are checked by the registered data-contract test instead, so
this module can exercise every rejection without reading shipped lore data.
"""

import unittest

from world.lore.monster_species import (
    MonsterCombatProfile,
    MonsterSpecies,
    MonsterSpeciesRegistryError,
    MonsterVariant,
    validate_monster_species_registry,
)

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
            TIER: (HP_BAND, PHYSICAL_BAND, MAGIC_BAND, RANK_RANGE),
        },
    }
    faces.update(overrides)
    return faces


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

    def test_an_in_band_profile_and_grade_are_accepted(self):
        self._validate(_variant())

    def test_a_value_exactly_on_a_band_edge_is_inside_the_band(self):
        self._validate(
            _variant(
                combat_profile=_profile(
                    hp=HP_BAND[1],
                    atk_phys=PHYSICAL_BAND[0],
                    agility=PHYSICAL_BAND[1],
                    defense=PHYSICAL_BAND[0],
                    magic_power=MAGIC_BAND[1],
                ),
                danger_grade=RANK_HIGH,
            )
        )

    def test_hp_above_the_tier_band_is_rejected(self):
        self._rejection(_variant(combat_profile=_profile(hp=HP_BAND[1] + 1)))

    def test_hp_below_the_tier_band_is_rejected(self):
        self._rejection(_variant(combat_profile=_profile(hp=HP_BAND[0] - 1)))

    def test_each_physical_axis_outside_the_tier_band_is_rejected(self):
        for axis in ("atk_phys", "agility", "defense"):
            for value in (PHYSICAL_BAND[0] - 1, PHYSICAL_BAND[1] + 1):
                with self.subTest(axis=axis, value=value):
                    self._rejection(
                        _variant(combat_profile=_profile(**{axis: value}))
                    )

    def test_a_nonzero_magic_power_is_rejected_against_a_zero_band(self):
        for value in (1, MAGIC_BAND[1] + 5):
            with self.subTest(value=value):
                self._rejection(
                    _variant(combat_profile=_profile(magic_power=value))
                )

    def test_a_grade_outside_the_tier_rank_range_is_rejected(self):
        self._rejection(_variant(danger_grade=RANK_ABOVE))

    def test_a_variant_whose_tier_carries_no_band_row_is_rejected(self):
        message = self._rejection(_variant(threat_tier=UNBANDED_TIER))
        self.assertIn(UNBANDED_TIER, message)

    def test_a_rank_range_naming_an_unknown_rank_is_rejected(self):
        self._rejection(
            _variant(),
            tier_band_face={
                TIER: (HP_BAND, PHYSICAL_BAND, MAGIC_BAND, (RANK_LOW, "t_rank_unknown")),
            },
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

    def test_the_pools_carry_no_band(self):
        # MP and SP have no tier band by design, so any authored pool validates
        # here; their approved zeros are pinned by the shipped-content contract.
        self._validate(
            _variant(combat_profile=_profile(mp=999, sp=999))
        )

    def test_a_variant_without_a_profile_or_grade_is_not_band_checked(self):
        # A tier key that only an injected vocabulary knows has no shipped band
        # to read; a variant carrying neither slot is therefore not judged.
        self._validate(
            _variant(
                threat_tier=UNBANDED_TIER,
                combat_profile=None,
                danger_grade=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
