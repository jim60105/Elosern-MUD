"""Behavior tests: the closed resident vocabulary validates authored rows.

Every row is constructed under a scoped synthetic race registry so the test
carries no shipped band or subrace identity. The regression value is the row
contract itself: a key, an in-band literal stat set, a race-permitted sex and a
unique membership in the assembled registry.
"""

from dataclasses import replace
import unittest

from world.lore.races import StaticBand, Vitals
from world.lore.residents import (
    Resident,
    ResidentRegistryError,
    assemble_resident_registry,
)
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_SUBRACES,
    synthetic_registries,
)

_STATS = {
    "hp": 10000,
    "mp": 10000,
    "sp": 10000,
    "atk_phys": 80,
    "agility": 81,
    "defense": 82,
    "magic_power": 150,
}


def _elf_rows():
    """Fixture-owned race and branch rows under the production-style keys."""
    race = replace(
        SYNTH_RACES["t_duskmari"],
        key="elf",
        allowed_sexes=("female",),
        vital_baseline=Vitals(hp=(10000, 10000), mp=(10000, 10000), sp=(10000, 10000)),
        static_baseline=StaticBand(
            atk_phys=(70, 95),
            agility=(70, 95),
            defense=(70, 95),
            magic_power=(100, 200),
        ),
    )
    branch = replace(
        SYNTH_SUBRACES["t_duskmari_evensong"],
        key="t_elf_branch",
        race_key="elf",
    )
    return {"elf": race}, {"t_elf_branch": branch}


class ResidentVocabularyTests(unittest.TestCase):
    """One authored row is accepted only when every closed field resolves."""

    def _scope(self):
        races, branches = _elf_rows()
        return synthetic_registries(
            "races", "subraces", extra={"races": races, "subraces": branches}
        )

    def _row(self, **overrides):
        fields = {
            "key": "t_resident_a",
            "name": "t-resident-a",
            "profile_key": "t_resident_a",
            "race": "elf",
            "subrace": "t_elf_branch",
            "sex": "female",
            "stats": dict(_STATS),
            "home_room": "t_home",
        }
        fields.update(overrides)
        return Resident(**fields)

    def test_a_valid_row_exposes_its_literal_values(self):
        with self._scope():
            row = self._row()
            self.assertEqual(dict(row.stats), _STATS)
            self.assertEqual(row.schedule_template, "resident")
            self.assertIsNone(row.dialogue_key)

    def test_an_out_of_band_stat_is_rejected_by_key_and_axis(self):
        with self._scope():
            stats = dict(_STATS, atk_phys=96)
            with self.assertRaises(ResidentRegistryError) as caught:
                self._row(stats=stats)
            message = str(caught.exception)
            self.assertIn("t_resident_a", message)
            self.assertIn("atk_phys", message)
            self.assertIn("70..95", message)

    def test_a_race_forbidden_sex_is_rejected(self):
        with self._scope():
            with self.assertRaises(ResidentRegistryError) as caught:
                self._row(sex="male")
            self.assertIn("t_resident_a", str(caught.exception))
            self.assertIn("male", str(caught.exception))

    def test_a_duplicate_key_across_slices_is_rejected_naming_both(self):
        with self._scope():
            first = self._row()
            second = self._row(name="t-resident-b", home_room="t_home_b")
            with self.assertRaises(ResidentRegistryError) as caught:
                assemble_resident_registry(
                    [("t_slice_a", (first,)), ("t_slice_b", (second,))]
                )
            message = str(caught.exception)
            self.assertIn("t_resident_a", message)
            self.assertIn("t_slice_a", message)
            self.assertIn("t_slice_b", message)

    def test_a_row_missing_a_stat_is_rejected(self):
        with self._scope():
            stats = dict(_STATS)
            del stats["magic_power"]
            with self.assertRaises(ResidentRegistryError) as caught:
                self._row(stats=stats)
            self.assertIn("magic_power", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
