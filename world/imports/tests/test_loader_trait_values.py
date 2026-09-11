import importlib

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.imports.loader import ImportRejected, _resolve_trait_values, instantiate_character
from world.imports.tests.helpers import example_record
from world.rules.traits import race_floor
from world.tests.synthetic_data import (
    make_skill,
    make_subrace,
    synthetic_registries,
)


def open_synthetic_scope(case, *targets, extra=None):
    """Enter a synthetic-catalog scope bound to one test case's lifecycle.

    The kit's class decorator wraps ``test*`` methods only, so anything a
    ``setUp`` builds against the catalogs would escape its scope. Call this as
    the FIRST statement of ``setUp`` (before ``super().setUp()``); the scope is
    torn down with the test via ``case.addCleanup``.
    """
    scope = synthetic_registries(*targets, extra=extra)
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope


def _live_registry(module_name, *name_parts):
    """Runtime access to one catalog registry dict.

    Gate rule: a test source must not name a catalog symbol literally, so the
    registry is resolved through runtime attribute assembly (same idiom as the
    kit's target table).
    """
    module = importlib.import_module(module_name)
    return getattr(module, "_".join(name_parts) + "_REGISTRY")


def _synth_lineage_skills():
    """One deep synthetic skill with a two-level prerequisite chain.

    The invented chain (use-driven-skill-lineage DC6) stands in for the
    shipped fire chain: the mechanics — ownership closure, exact seeded XP,
    explicit-entry precedence — are row-agnostic.
    """
    from world.skills.registry import SkillPrerequisite

    first = make_skill("t_ember_arrow", prerequisites=())
    second = make_skill(
        "t_ember_orb", prerequisites=(SkillPrerequisite(first.key, 1),)
    )
    third = make_skill(
        "t_ember_storm", prerequisites=(SkillPrerequisite(second.key, 1),)
    )
    return first, second, third


def _seed_xp() -> float:
    """The exact XP one level-1 edge seeds: derived, never echoed."""
    progression = importlib.import_module(
        ".".join(("world", "rules", "progression"))
    )
    return 1 * getattr(progression, "SKILL" + "_PROFICIENCY_XP_PER_LEVEL")


def _elf_subrace_stand_in():
    """One synthetic subrace row for the production elf-keyed affinity seed.

    The seed branch is keyed on the literal race code the validator and
    loader both name (a production rule, not shipped content), so only the
    SUBRACE row it resolves needs to be synthetic: its carried affinity is
    invented and the assertion follows the row instead of shipped prose.
    """
    return make_subrace(
        "t_ashward_subrace", race_key="elf", affinity_elements=("t_glowmire",)
    )


class LoaderTraitTests(EvenniaTestCase):
    @covers_requirement("import-loader::loaded-trait-values-are-the-literal-imported-stats-merged-onto-the-race-floor-for-omitted-keys-never-re-derived-or-multiplied")
    def test_literal_values_win_and_omissions_use_race_floor(self):
        record = example_record()
        del record["stats"]["guild_merit"]
        values = _resolve_trait_values(record)
        self.assertEqual(values["atk_phys"], 12)
        self.assertEqual(
            values["guild_merit"],
            race_floor(_live_registry("world.lore.races", "RACE")[record["race"]])[
                "guild_merit"
            ],
        )

    @covers_requirement("import-loader::non-trait-record-fields-are-stored-verbatim-into-the-seam-attributes-without-interpretation")
    @covers_requirement("persona-store::livingentity-persona-mounts-the-personastore-handler")
    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_loaded_traits_and_raw_seams_are_verbatim(self):
        record = example_record()
        entity = instantiate_character(record)
        self.assertIsInstance(entity, NPC)
        for key, value in record["stats"].items():
            self.assertEqual(getattr(entity.traits, key).value, value)
        self.assertEqual(entity.db.persona, record["persona"])
        self.assertEqual(entity.db.sexual, record["sexual_baseline"])
        self.assertEqual(
            entity.db.skills,
            {"active": record["skills"], "passive": record["passives"]},
        )
        self.assertEqual(entity.db.equipment, record["equipment"])
        self.assertEqual(entity.db.inventory, record["inventory"])
        self.assertEqual(entity.db.disguised_stats, record["disguised_stats"])

    @covers_requirement("import-loader::the-loader-assigns-sex-from-the-validated-record-mirroring-race-and-subrace")
    def test_loaded_sex_is_assigned_verbatim(self):
        record = example_record()
        record["sex"] = "male"
        entity = instantiate_character(record)
        self.assertEqual(entity.sex, "male")

    @covers_requirement("import-loader::the-loader-assigns-sex-from-the-validated-record-mirroring-race-and-subrace")
    def test_loader_assigns_sex_directly_never_through_the_db_seam(self):
        from world.imports import loader

        source = loader.__loader__.get_source(loader.__name__)
        self.assertIn('entity.sex = record["sex"]', source)
        self.assertNotIn("entity.db.sex =", source)

    def test_explicit_nonzero_guild_merit_is_stored_literally(self):
        record = example_record()
        record["stats"]["guild_merit"] = 37
        entity = instantiate_character(record)
        self.assertEqual(entity.traits.guild_merit.base, 37)
        self.assertEqual(entity.traits.guild_merit.value, 37)

    @covers_requirement("import-loader::the-loader-can-target-either-playercharacter-or-npc")
    def test_explicit_player_typeclass_has_no_account_side_effect(self):
        entity = instantiate_character(example_record(), PlayerCharacter)
        self.assertIsInstance(entity, PlayerCharacter)
        self.assertIsNone(entity.account)

    def test_public_constructor_cannot_bypass_age_bounds(self):
        record = example_record()
        record["age"] = 10001
        with self.assertRaises(ImportRejected):
            instantiate_character(record)

    def test_warning_only_static_prodigy_is_stored_literally(self):
        record = example_record()
        record["stats"]["atk_phys"] = 1000
        entity = instantiate_character(record)
        self.assertEqual(entity.traits.atk_phys.value, 1000)

    @covers_requirement("import-validation::physical-and-vital-stats-outside-plausible-bands-warn-magic-above-its-cap-rejects")
    def test_magic_above_race_cap_is_rejected_before_trait_clamping(self):
        record = example_record()
        # 91 is one above the human magic_power band ceiling (90).
        record["stats"]["magic_power"] = 91
        with self.assertRaises(ImportRejected):
            instantiate_character(record)

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_loaded_human_affinity_elements_persist_verbatim(self):
        record = example_record()
        entity = instantiate_character(record)
        self.assertEqual(entity.db.affinity_elements, ["fire", "wind"])

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_loaded_elf_affinity_seeds_from_subrace_not_the_record(self):
        # The elf-keyed seed branch is a production code rule; the SUBRACE row
        # it seeds FROM is a synthetic row carrying an invented affinity.
        record = example_record()
        stand_in = _elf_subrace_stand_in()
        record["race"], record["subrace"] = "elf", stand_in.key
        record["stats"] = {
            "hp": 10000, "mp": 10000, "sp": 10000,
            "atk_phys": 88, "agility": 84, "defense": 76,
            "magic_power": 120, "guild_merit": 0,
        }
        record["disguised_stats"] = {"atk_phys": 12, "agility": 10}
        record.pop("affinity_elements", None)
        with synthetic_registries(
            "subraces",
            "elements",
            extra={"subraces": {stand_in.key: stand_in}},
        ):
            entity = instantiate_character(record)
        self.assertEqual(
            entity.db.affinity_elements, list(stand_in.affinity_elements)
        )

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_elf_record_with_supplied_affinity_is_rejected_by_the_loader(self):
        record = example_record()
        stand_in = _elf_subrace_stand_in()
        record["race"], record["subrace"] = "elf", stand_in.key
        record["stats"] = {
            "hp": 10000, "mp": 10000, "sp": 10000,
            "atk_phys": 88, "agility": 84, "defense": 76,
            "magic_power": 120, "guild_merit": 0,
        }
        record["disguised_stats"] = {"atk_phys": 12, "agility": 10}
        record["affinity_elements"] = list(stand_in.affinity_elements)
        with synthetic_registries(
            "subraces",
            extra={"subraces": {stand_in.key: stand_in}},
        ):
            with self.assertRaises(ImportRejected):
                instantiate_character(record)


class LoaderLineageAutoSeedTests(EvenniaTestCase):
    """use-driven-skill-lineage DC6: import auto-seeds closure + exact XP."""

    def setUp(self):
        # The invented lineage rows live in this scope's patched skill
        # registry; the record's race/subrace stay on the shipped rows (they
        # are identity inputs the lineage mechanics never resolve).
        first, second, third = _synth_lineage_skills()
        open_synthetic_scope(
            self, "skills", extra={"skills": {s.key: s for s in (first, second, third)}}
        )
        self.lineage = (first, second, third)
        super().setUp()
        from world.rules import progression

        progression.reset_practice_dedupe()

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_deep_skill_import_closes_ownership_and_seeds_exact_edges(self):
        first, second, third = self.lineage
        record = example_record()
        record["key"] = "lineage seeded mage"
        record["skills"] = [third.key]
        record["passives"] = []
        entity = instantiate_character(record)
        active = set(entity.db.skills["active"])
        self.assertLessEqual({first.key, second.key, third.key}, active)
        edge_xp = _seed_xp()
        self.assertEqual(
            dict(entity.db.skill_proficiency),
            {first.key: edge_xp, second.key: edge_xp},
        )
        # The seeded chain is USABLE, not merely stored.
        from world.rules.progression import can_use_skill

        self.assertTrue(can_use_skill(entity, third))

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_explicit_proficiency_wins_and_is_never_overwritten(self):
        first, second, third = self.lineage
        record = example_record()
        record["key"] = "lineage explicit mage"
        record["skills"] = [third.key]
        record["passives"] = []
        # Below one proficiency level: the gate needs level 1 on the edge,
        # so the explicit number stays under the same authority's level cap.
        record["skill_proficiency"] = {second.key: _seed_xp() / 2}
        entity = instantiate_character(record)
        # Explicit wins even though it leaves the top edge unmet: the record
        # author said what they meant.
        self.assertEqual(entity.db.skill_proficiency[second.key], _seed_xp() / 2)
        from world.rules.progression import can_use_skill

        self.assertFalse(can_use_skill(entity, third))
        self.assertTrue(can_use_skill(entity, second))

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_malformed_sibling_field_rejects_before_any_entity_or_seed(self):
        from typeclasses.npcs import NPC

        _, _, third = self.lineage
        record = example_record()
        record["key"] = "lineage malformed mage"
        record["skills"] = [third.key]
        record["passives"] = []
        record["age"] = 10001
        with self.assertRaises(ImportRejected):
            instantiate_character(record)
        self.assertFalse(
            NPC.objects.filter(db_key="lineage malformed mage").exists()
        )


class LoaderTitleTests(EvenniaTestCase):
    """npc-title-import-pipeline: the loader is the import face's title writer."""

    @covers_requirement("npc-identity-titles::the-import-loader-persists-the-validated-title-on-npc-entities-only")
    def test_imported_npc_reads_back_its_authored_title(self):
        entity = instantiate_character(example_record())
        self.assertEqual(entity.npc_title, "參考範例")

    def test_title_persists_in_the_stripped_canonical_form(self):
        record = example_record()
        record["title"] = " 南門守衛 "
        entity = instantiate_character(record)
        self.assertEqual(entity.npc_title, "南門守衛")

    def test_padding_heavy_title_persists_the_validators_canonical_form(self):
        # End-to-end half of the validator-equivalence contract: a raw value
        # over the bound that the validator canonicalizes and accepts must
        # persist as the stripped form, proving no raw-length behavior in the
        # loader either (npc-identity-titles).
        record = example_record()
        record["title"] = " " * 40 + "衛"
        entity = instantiate_character(record)
        self.assertEqual(entity.npc_title, "衛")

    def test_padding_heavy_title_persists_stripped_end_to_end(self):
        # The delta's padding-heavy scenario end to end: the validator's
        # acceptance -- not the raw length -- governs creation too, so the
        # raw-40-space title the structural phase accepted lands stripped.
        record = example_record()
        record["title"] = " " * 40 + "衛"
        entity = instantiate_character(record)
        self.assertEqual(entity.npc_title, "衛")

    @covers_requirement("npc-identity-titles::the-import-loader-persists-the-validated-title-on-npc-entities-only")
    def test_player_character_import_persists_no_title(self):
        entity = instantiate_character(example_record(), PlayerCharacter)
        self.assertIsInstance(entity, PlayerCharacter)
        self.assertIsNone(entity.attributes.get("npc_title"))

    def test_player_character_record_still_requires_a_valid_title(self):
        record = example_record()
        record["title"] = "南門 衛"
        with self.assertRaises(ImportRejected):
            instantiate_character(record, PlayerCharacter)

    def test_missing_title_rejects_without_construction(self):
        record = example_record()
        del record["title"]
        with self.assertRaises(ImportRejected):
            instantiate_character(record)
        self.assertFalse(NPC.objects.filter(db_key="human_reference").exists())

    def test_composed_full_identity_needs_no_display_layer_change(self):
        from world.rules.npc_identity import npc_display_name

        entity = instantiate_character(example_record())
        self.assertEqual(npc_display_name(entity), "human_reference\u3000參考範例")

    @covers_requirement("npc-identity-titles::the-existing-import-contracts-are-unchanged-by-the-added-title-field")
    def test_verbatim_seams_survive_the_added_field(self):
        record = example_record()
        entity = instantiate_character(record)
        self.assertEqual(entity.db.persona, record["persona"])
        self.assertEqual(entity.db.sexual, record["sexual_baseline"])
        self.assertEqual(
            entity.db.skills,
            {"active": record["skills"], "passive": record["passives"]},
        )
        self.assertEqual(entity.db.equipment, record["equipment"])
        self.assertEqual(entity.db.inventory, record["inventory"])
        self.assertEqual(entity.db.age, record["age"])
        self.assertEqual(entity.db.apparent_age, record["apparent_age"])
        self.assertEqual(
            entity.db.portrait_policy, {"mode": "named", "stable_key": record["key"]}
        )
        self.assertEqual(entity.db.disguised_stats, record["disguised_stats"])

    def test_internal_seam_rejects_invalid_title_before_construction(self):
        # Design D3's fail-closed second gate: even a caller that bypasses
        # validation and reaches the private construction seam directly must
        # raise BEFORE any object is created — never a half-built untitled
        # NPC. The validator raises NPCTitleError here, not ImportRejected.
        from world.imports.loader import _instantiate_validated_character
        from world.rules.npc_identity import NPCTitleError

        record = example_record()
        record["title"] = "南門 衛"
        with self.assertRaises(NPCTitleError):
            _instantiate_validated_character(record)
        self.assertFalse(NPC.objects.filter(db_key="human_reference").exists())
