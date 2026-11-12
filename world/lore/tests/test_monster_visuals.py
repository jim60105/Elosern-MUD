"""Behavior tests for the monster visual-species registry (synthetic rows only).

The registry is exactly the projection of each complete combat species. These tests use a file-local synthetic species
so no shipped row is echoed, and they assert the registry's own closure rules
instead of pinning the authored roster.
"""

import unittest
from dataclasses import asdict, fields, replace

from world.lore.monster_species import MonsterSpecies
from world.lore.monster_visuals import (
    RESERVED_KEYS,
    adapt_combat_species,
    build_monster_visual_registry,
    is_registered_monster_visual_key,
)

from tools.spec_traceability import covers_requirement
from world.tests.synthetic_data import SYNTH_MONSTER_SPECIES, synthetic_registries


# Invented vocabulary: no shipped key, label or appearance string appears here.
_T_SPECIES = "t_visual_synth_wisp"
_T_VARIANT = "t_visual_synth_wisp_ordinary"
_LABEL = "合成幻靈"
_DESCRIPTION = "合成描述：供行為測試使用的合成條目。"
_APPEARANCE = "合成外觀：漂浮的合成微光與半透明的合成薄膜。"
_ECOLOGY = "合成生態：僅供測試使用的合成棲位描述。"
_HIDDEN = "合成作者私有：不可外流的合成真相。"
_EXPLANATION = "合成作者私有：合成列的解釋。"
_CONJECTURE = "合成作者私有：未經證實的合成猜想。"

# A declaration is appearance-only; a combat profile owns the numeric slots.
_DECLARATION_SLOTS = frozenset(
    {"stable_key", "display_label", "published_appearance_zh"}
)
_COMBAT_SLOTS = frozenset(
    {
        "hp",
        "mp",
        "sp",
        "atk_phys",
        "agility",
        "defense",
        "magic_power",
        "threat_tier",
        "combat_profile",
        "danger_grade",
        "species_key",
        "variant_key",
    }
)


def _species(key: str = _T_SPECIES) -> MonsterSpecies:
    return MonsterSpecies(
        key,
        _LABEL,
        _DESCRIPTION,
        _APPEARANCE,
        _ECOLOGY,
        (),
        _HIDDEN,
        _EXPLANATION,
        _CONJECTURE,
        _T_VARIANT,
        True,
    )


class VisualDeclarationShapeTests(unittest.TestCase):
    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_declarations_are_appearance_only_never_combat_profiles(self):
        registry = build_monster_visual_registry({_T_SPECIES: _species()})
        for key, declaration in registry.items():
            with self.subTest(key=key):
                declared = {field.name for field in fields(declaration)}
                self.assertEqual(declared, set(_DECLARATION_SLOTS))
                self.assertFalse(declared & _COMBAT_SLOTS)

    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_the_registry_is_exactly_the_combat_species_projection(self):
        first, second = f"{_T_SPECIES}_a", f"{_T_SPECIES}_b"
        combat = {first: _species(key=first), second: _species(key=second)}
        registry = build_monster_visual_registry(combat)
        self.assertEqual(set(registry), {first, second})
        for key, species in combat.items():
            with self.subTest(key=key):
                self.assertEqual(registry[key], adapt_combat_species(species))
        # A key no combat species holds is never a visual species.
        self.assertNotIn(f"{_T_SPECIES}_c", registry)

    def test_a_key_without_a_combat_species_is_not_registered(self):
        with synthetic_registries("monster_species"):
            for key in SYNTH_MONSTER_SPECIES:
                with self.subTest(key=key):
                    self.assertTrue(is_registered_monster_visual_key(key))
            self.assertFalse(is_registered_monster_visual_key(_T_SPECIES))


class CombatSpeciesProjectionTests(unittest.TestCase):
    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_a_complete_species_projects_only_its_public_appearance(self):
        species = _species()
        declaration = adapt_combat_species(species)
        self.assertEqual(declaration.stable_key, species.key)
        self.assertEqual(declaration.display_label, species.display_name_zh)
        self.assertEqual(
            declaration.published_appearance_zh, species.published_appearance_zh
        )
        # The projection never carries hidden truth, ecology or the longer
        # published description into the artwork prompt.
        rendered = repr(asdict(declaration))
        for excluded in (
            species.author_hidden_truth_zh,
            species.author_explanation_zh,
            species.author_conjecture_zh,
            species.published_ecology_zh,
            species.published_description_zh,
        ):
            self.assertNotIn(excluded, rendered)

    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_a_missing_public_appearance_falls_back_to_the_label_only(self):
        blank = replace(_species(), published_appearance_zh="")
        declaration = adapt_combat_species(blank)
        self.assertEqual(declaration.published_appearance_zh, blank.display_name_zh)
        self.assertNotIn(blank.author_hidden_truth_zh, declaration.published_appearance_zh)


class VisualRegistryClosureTests(unittest.TestCase):
    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_the_merge_projects_the_injected_registry_and_admits_its_key(self):
        registry = build_monster_visual_registry({_T_SPECIES: _species()})
        declaration = registry[_T_SPECIES]
        self.assertEqual(declaration.published_appearance_zh, _APPEARANCE)
        # Composition is live rather than a cached shipped snapshot: the same
        # key is absent when the injected registry omits it.
        self.assertNotIn(_T_SPECIES, build_monster_visual_registry({}))

    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_a_mapping_key_that_disagrees_with_its_row_is_an_authoring_error(self):
        # Two entries declaring one row key: the second cannot pass silently.
        other = f"{_T_SPECIES}_alias"
        with self.assertRaises(ValueError):
            build_monster_visual_registry(
                {_T_SPECIES: _species(), other: _species(key=_T_SPECIES)}
            )

    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_reserved_malformed_and_unknown_keys_are_never_admitted(self):
        reserved = sorted(RESERVED_KEYS)[0]
        # A declaration that reuses a retired tier name is rejected before any
        # prompt, queue job or image URL is produced.
        with self.assertRaises(ValueError):
            build_monster_visual_registry({reserved: _species(key=reserved)})
        for bad in (reserved, "", "t_visual/../escape", 12, None):
            with self.subTest(bad=bad):
                self.assertFalse(is_registered_monster_visual_key(bad))


if __name__ == "__main__":
    unittest.main()
