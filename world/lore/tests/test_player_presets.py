"""Tests for immutable registration presets."""

import unittest

from tools.spec_traceability import covers_requirement

from world.lore.player_presets import (
    PLAYER_PRESET_REGISTRY,
    PlayerPreset,
    StartingCompanion,
)
from world.lore.races import RACE_REGISTRY
from world.rules.character_creation import resolve_starting_profile
from world.skills.registry import SKILL_REGISTRY, SkillKind


class PlayerPresetTests(unittest.TestCase):
    def test_catalog_covers_every_race_with_valid_allocations(self):
        self.assertEqual(
            {preset.race for preset in PLAYER_PRESET_REGISTRY.values()},
            set(RACE_REGISTRY),
        )
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                self.assertIsInstance(preset, PlayerPreset)
                profile = resolve_starting_profile(preset.race, preset.subrace)
                allocations = preset.allocation_dict()
                self.assertEqual(sum(allocations.values()), profile.budget)
                for key, (lower, upper) in profile.bounds:
                    self.assertLessEqual(allocations[key], upper - lower)

    def test_catalog_ships_exactly_eight_template_characters(self):
        self.assertEqual(len(PLAYER_PRESET_REGISTRY), 8)
        self.assertEqual(
            list(PLAYER_PRESET_REGISTRY),
            [
                "human_wanderer",
                "foxkin_scout",
                "elf_guardian",
                "violet_altoria",
                "lidzia_rosenthal",
                "yuka_darknight",
                "yuna_darknight",
                "elosia_shadowmoon",
            ],
        )

    def test_every_preset_skill_resolves_with_matching_kind(self):
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                for key in preset.active_skills:
                    self.assertEqual(SKILL_REGISTRY[key].kind, SkillKind.ACTIVE)
                for key in preset.passive_skills:
                    self.assertEqual(SKILL_REGISTRY[key].kind, SkillKind.PASSIVE)

    def test_divine_arts_skills_only_on_divine_affinity_races(self):
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                race = RACE_REGISTRY[preset.race]
                for key in (*preset.active_skills, *preset.passive_skills):
                    if SKILL_REGISTRY[key].requires_divine_arts:
                        self.assertTrue(race.can_use_divine_arts)

    def test_shipped_starting_kits_are_the_approved_loadouts(self):
        expected = {
            "human_wanderer": (
                ("plain_sword", 1), ("leather_armor", 1),
                ("guild_recruit_badge", 1), ("healing_potion", 2),
                ("healing_herb", 2),
            ),
            "foxkin_scout": (
                ("hunters_longbow", 1), ("hunting_throwing_axe", 1),
                ("leather_armor", 1), ("wolf_fang_necklace", 1),
                ("healing_potion", 1), ("healing_herb", 3),
            ),
            "elf_guardian": (
                ("knight_blade", 1), ("iron_shield", 1),
                ("chainmail", 1), ("pilgrim_medallion", 1),
                ("healing_potion", 1),
            ),
            "violet_altoria": (
                ("elven_traditional_robe", 1), ("royal_signet_ring", 1),
                ("royal_heirloom_pendant", 1),
            ),
            "lidzia_rosenthal": (
                ("rose_crest_rapier", 1), ("black_maid_dress", 1),
                ("silver_feather_earring", 1),
            ),
            "yuka_darknight": (
                ("shadow_blade", 1), ("shadow_blade_echo", 1),
                ("dark_elf_ninja_garb", 1),
            ),
            "yuna_darknight": (("dark_elf_kimono", 1),),
            "elosia_shadowmoon": (("elven_traditional_robe", 1), ("crescent_earring", 1)),
        }
        for preset_key, items in expected.items():
            with self.subTest(preset_key=preset_key):
                preset = PLAYER_PRESET_REGISTRY[preset_key]
                self.assertEqual(preset.starting_items, items)
                self.assertEqual(
                    preset.inventory_list(),
                    [
                        item_key
                        for item_key, quantity in items
                        for _ in range(quantity)
                    ],
                )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_starting_item_validation_rejects_unknown_duplicate_and_bad_quantity(self):
        from world.lore.player_presets import _validate_preset_starting_items

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (make(starting_items=(("not_an_item", 1),)), "unknown item"),
            (
                make(starting_items=(("healing_potion", 1), ("healing_potion", 1))),
                "duplicate item",
            ),
            (make(starting_items=(("healing_potion", 0),)), "non-positive quantity"),
            (make(starting_items=(("healing_potion", "2"),)), "non-positive quantity"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_starting_items({"x": preset})
        _validate_preset_starting_items(
            {"x": make(starting_items=(("healing_potion", 2), ("plain_sword", 1)))}
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_starting_equipment_validation_rejects_the_five_invalid_declarations(self):
        from world.lore.player_presets import _validate_preset_starting_equipment

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
                starting_items=(("plain_sword", 1), ("hunters_longbow", 1),
                                ("leather_armor", 1), ("healing_potion", 2),
                                ("wolf_fang_necklace", 1),
                                ("pilgrim_medallion", 1),
                                ("protective_ring", 1), ("prism_charm", 1),
                                ("storage_pouch", 1), ("gliding_cloak", 1)),
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (
                make(starting_equipment=("knight_blade",)),
                "absent from its starting_items",
            ),
            (
                make(starting_equipment=("healing_potion",)),
                "that is not equipment",
            ),
            (
                make(starting_equipment=("plain_sword", "plain_sword")),
                "duplicate starting equipment",
            ),
            (
                # plain_sword and hunters_longbow are both WEAPON_MAIN items.
                make(starting_equipment=("plain_sword", "hunters_longbow")),
                "claiming the same weapon_main slot",
            ),
            (
                # Six carried accessories exceed ACCESSORY_MAX_SLOTS (5).
                make(starting_equipment=(
                    "wolf_fang_necklace", "pilgrim_medallion", "protective_ring",
                    "prism_charm", "storage_pouch", "gliding_cloak",
                )),
                "more than 5 starting accessories",
            ),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_starting_equipment({"x": preset})
        # A well-formed declaration passes: subset, distinct singleton slots,
        # accessories within the bound.
        _validate_preset_starting_equipment(
            {"x": make(starting_equipment=(
                "plain_sword", "leather_armor", "wolf_fang_necklace",
                "pilgrim_medallion", "protective_ring", "prism_charm",
                "storage_pouch",
            ))}
        )
        # Every shipped card (empty defaults included) validates clean.
        _validate_preset_starting_equipment(PLAYER_PRESET_REGISTRY)

    def test_skill_lists_returns_the_storage_shape_in_declared_order(self):
        preset = PLAYER_PRESET_REGISTRY["yuna_darknight"]
        self.assertEqual(
            preset.skill_lists(),
            {
                "active": list(preset.active_skills),
                "passive": list(preset.passive_skills),
            },
        )
        self.assertEqual(preset.skill_lists()["active"], ["divine_sexual_arts"])

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_kit_validation_rejects_unknown_kind_mismatch_and_divine_gate(self):
        from world.lore.player_presets import _validate_preset_skill_kits

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (make(active_skills=("not_a_skill",)), "unknown skill"),
            (make(active_skills=("body_enhancement_basic",)), "classifies it as"),
            (make(active_skills=("dual_wield_style",)), "classifies it as"),
            (make(passive_skills=("light_sword_style",)), "classifies it as"),
            (make(passive_skills=("divine_sexual_mastery",)), "divine-arts"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_skill_kits({"x": preset})
        _validate_preset_skill_kits({"x": make(race="elf", subrace="fionnen", passive_skills=("divine_sexual_mastery",))})

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_proficiency_validation_rejects_unknown_duplicate_bad_value(self):
        from world.lore.player_presets import _validate_preset_skill_proficiency

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            # (declared entries, expected message fragment)
            ((("not_a_skill", 1.0),), "unknown skill 'not_a_skill'"),
            (
                (("fire_ball", 1.0), ("fire_ball", 2.0)),
                "duplicate proficiency for 'fire_ball'",
            ),
            ((("fire_ball", -1.0),), "non-numeric or negative proficiency for 'fire_ball'"),
            ((("fire_ball", "50"),), "non-numeric or negative proficiency for 'fire_ball'"),
            # bool is an int subclass; a declared boolean must be rejected as
            # non-numeric, not silently read as 1/0 (tasks 1.2).
            ((("fire_ball", True),), "non-numeric or negative proficiency for 'fire_ball'"),
            ((("fire_ball", float("nan")),), "non-numeric or negative proficiency for 'fire_ball'"),
            ((("fire_ball", float("inf")),), "non-numeric or negative proficiency for 'fire_ball'"),
            (("fire_ball",), "malformed skill_proficiency entry"),
        )
        for entries, message in cases:
            preset = make(skill_proficiency=entries)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_skill_proficiency({"x": preset})
        # A well-formed declaration (including zero) passes, and the shipped
        # registry validates clean at load.
        _validate_preset_skill_proficiency(
            {"x": make(skill_proficiency=(("fire_ball", 0), ("fire_arrow", 150.5)))}
        )
        _validate_preset_skill_proficiency(PLAYER_PRESET_REGISTRY)

    def test_identity_validation_rejects_unknown_and_incompatible_subraces(self):
        from world.lore.player_presets import _validate_preset_identities

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        for preset, message in (
            (make(subrace="not_a_subrace"), "unknown subrace"),
            (make(subrace="foxkin"), "belonging to race"),
            (make(race="not_a_race"), "unknown race"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_identities({"x": preset})
        _validate_preset_identities({"x": make()})

    def test_catalog_ships_human_and_beastfolk_affinity_from_lore(self):
        self.assertEqual(
            PLAYER_PRESET_REGISTRY["violet_altoria"].affinity_elements,
            ("fire", "wind"),
        )
        self.assertEqual(
            PLAYER_PRESET_REGISTRY["foxkin_scout"].affinity_elements,
            ("wind",),
        )
        for key in ("human_wanderer", "lidzia_rosenthal"):
            self.assertEqual(PLAYER_PRESET_REGISTRY[key].affinity_elements, ())

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_elf_presets_must_declare_an_empty_affinity_set(self):
        for key in ("elf_guardian", "yuka_darknight", "yuna_darknight", "elosia_shadowmoon"):
            with self.subTest(preset=key):
                self.assertEqual(PLAYER_PRESET_REGISTRY[key].race, "elf")
                self.assertEqual(
                    PLAYER_PRESET_REGISTRY[key].affinity_elements, ()
                )

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_affinity_validation_rejects_unknown_duplicate_and_elf_non_empty(self):
        from world.lore.player_presets import _validate_preset_affinity_elements

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (make(affinity_elements=("luck",)), "unknown affinity element"),
            (make(affinity_elements=("fire", "fire")), "duplicate affinity element"),
            (make(race="elf", subrace="fionnen", affinity_elements=("light",)), "elf preset"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_affinity_elements({"x": preset})
        _validate_preset_affinity_elements({"x": make(affinity_elements=("fire", "wind"))})
        _validate_preset_affinity_elements(
            {"x": make(race="elf", subrace="fionnen")}
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_sex_validation_rejects_values_outside_the_vocabulary(self):
        from world.lore.player_presets import _validate_preset_sex

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        for preset, message in (
            (make(sex="neuter"), "unknown sex"),
            (make(sex="Female"), "unknown sex"),
            (make(sex=""), "unknown sex"),
            (make(sex=None), "unknown sex"),
        ):
            with self.subTest(message=message, sex=preset.sex), self.assertRaisesRegex(
                ValueError, message
            ):
                _validate_preset_sex({"x": preset})
        _validate_preset_sex({"x": make(sex="other")})

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_constructing_a_preset_without_sex_raises_type_error(self):
        # ``sex`` is keyword-only and required (KW_ONLY from the field-parity
        # fields onward), so a card that omits it fails at construction
        # instead of silently inheriting DEFAULT_SEX.
        with self.assertRaisesRegex(TypeError, "sex"):
            PlayerPreset(
                "x", "x", 18, 18, "human", "human_commoner", (), "e"
            )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_every_shipped_preset_declares_a_concrete_sex(self):
        from world.lore.sex import SEX_VALUES

        self.assertEqual(len(PLAYER_PRESET_REGISTRY), 8)
        for key, preset in PLAYER_PRESET_REGISTRY.items():
            with self.subTest(preset=key):
                self.assertIn(preset.sex, SEX_VALUES)
                self.assertEqual(preset.sex, "female")

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_persona_validation_rejects_malformed_structures(self):
        from world.lore.player_presets import (
            PresetAppearance,
            PresetIdentity,
            PresetPersona,
            _validate_preset_personas,
        )

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        for preset, message in (
            (make(persona=PresetPersona(personality=1)), r"persona\.personality"),
            (make(persona=PresetPersona(background=None)), r"persona\.background"),
            (
                make(persona=PresetPersona(identity=PresetIdentity(public=7))),
                r"persona\.identity\.public",
            ),
            (make(persona=PresetPersona(identity="self")), "not a PresetIdentity"),
            (
                make(persona=PresetPersona(appearance=PresetAppearance(height=1.5))),
                r"persona\.appearance\.height",
            ),
            (make(persona=PresetPersona(appearance={"height": "160cm"})), "not a PresetAppearance"),
            (make(persona=PresetPersona(social_connection=("solo",))), "pair of strings"),
            (make(persona=PresetPersona(social_connection=(("a", "b", "c"),))), "pair of strings"),
            (make(persona=PresetPersona(social_connection=(("a", 1),))), "pair of strings"),
            (make(persona=PresetPersona(social_connection=(["a", "b"],))), "pair of strings"),
            (
                make(persona=PresetPersona(
                    social_connection=(("甲", "舊識"), ("甲", "宿敵")),
                )),
                "duplicate social_connection",
            ),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                ValueError, message
            ):
                _validate_preset_personas({"x": preset})
        # Empty values are always legal so a card can be authored incrementally.
        _validate_preset_personas({"x": make()})
        _validate_preset_personas({"x": make(persona=PresetPersona(
            identity=PresetIdentity(public="公會註冊冒險者", hidden="流亡王女"),
            personality="沉穩", life_story="邊境", habit="練劍",
            appearance=PresetAppearance(height="160cm"),
            social_connection=(("悠奈", "舊識"),),
            background="背景",
        ))})

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_shipped_presets_hold_background_inside_the_persona(self):
        for key, preset in PLAYER_PRESET_REGISTRY.items():
            with self.subTest(preset=key):
                self.assertFalse(hasattr(preset, "background"))
                self.assertTrue(preset.persona.background.strip())

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_to_record_expands_the_authored_persona_exactly(self):
        from world.lore.player_presets import (
            PresetAppearance,
            PresetIdentity,
            PresetPersona,
        )

        # An all-empty persona is the six-key import-card record with empty
        # values and no background key.
        self.assertEqual(
            PresetPersona().to_record(),
            {
                "identity": {}, "personality": "", "life_story": "",
                "habit": "", "appearance": {}, "social_connection": {},
            },
        )
        self.assertEqual(
            PresetPersona(
                identity=PresetIdentity(public="冒險者", hidden="王女"),
                personality="沉穩", life_story="邊境", habit="練劍",
                appearance=PresetAppearance(height="160cm", attire="旅裝"),
                social_connection=(("悠奈", "舊識"),),
                background="背景",
            ).to_record(),
            {
                "identity": {"public": "冒險者", "hidden": "王女"},
                "personality": "沉穩", "life_story": "邊境", "habit": "練劍",
                "appearance": {"height": "160cm", "attire": "旅裝"},
                "social_connection": {"悠奈": "舊識"},
                "background": "背景",
            },
        )
        # Empty sub-entries are dropped; a hidden-only identity keeps its layer.
        partial = PresetPersona(
            identity=PresetIdentity(hidden="間諜"),
            appearance=PresetAppearance(attire="斗篷"),
        ).to_record()
        self.assertEqual(partial["identity"], {"hidden": "間諜"})
        self.assertEqual(partial["appearance"], {"attire": "斗篷"})
        self.assertNotIn("background", partial)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_disguised_stats_validation_rejects_bad_keys_values_and_duplicates(self):
        from world.lore.player_presets import _validate_preset_disguised_stats

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        for preset, message in (
            (make(disguised_stats=((5, 60),)), "key that is not text"),
            (make(disguised_stats=(("atk_phys", "60"),)), "non-integer disguise"),
            (make(disguised_stats=(("atk_phys", 60.0),)), "non-integer disguise"),
            (make(disguised_stats=(("atk_phys", True),)), "non-integer disguise"),
            (make(disguised_stats=("atk_phys",)), "malformed disguised_stats"),
            (
                make(disguised_stats=(("atk_phys", 60), ("atk_phys", 70))),
                "duplicate disguised_stats",
            ),
        ):
            with self.subTest(preset=preset.disguised_stats), self.assertRaisesRegex(
                ValueError, message
            ):
                _validate_preset_disguised_stats({"x": preset})
        # Any string axis is legal (no whitelist): the schema constrains the
        # field only to integer values, and the layer is display-only.
        _validate_preset_disguised_stats(
            {"x": make(disguised_stats=(("atk_phys", 60), ("legendary_axis", -5)))}
        )
        _validate_preset_disguised_stats({"x": make()})
        _validate_preset_disguised_stats(PLAYER_PRESET_REGISTRY)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_sexual_baseline_validation_rejects_bad_levels_and_body_parts(self):
        from world.lore.player_presets import (
            PresetSexualBaseline,
            _validate_preset_sexual_baselines,
        )

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        def baseline(**overrides):
            values = dict(
                arousal="微興奮", virgin=False,
                sensitivity=(("私處", "極高"), ("軀體", "普通")),
            )
            values.update(overrides)
            return PresetSexualBaseline(**values)

        for preset, message in (
            (make(sexual_baseline=baseline(arousal="狂暴")), "arousal"),
            # Required arousal may never be empty: to_record() always emits
            # it, so an empty level would reach the pleasure-band lookup and
            # crash the handler instead of failing at load.
            (make(sexual_baseline=baseline(arousal="")), "arousal"),
            (make(sexual_baseline=baseline(wetness="潮濕")), "wetness"),
            (make(sexual_baseline=baseline(shame="羞恥")), "shame"),
            (make(sexual_baseline=baseline(exposure="爆表")), "exposure"),
            (make(sexual_baseline=baseline(climax_phase="已結束")), "climax_phase"),
            (make(sexual_baseline=baseline(virgin=1)), "not a boolean"),
            (
                make(sexual_baseline=baseline(sensitivity=(("尾巴", "高"),))),
                "unknown body part",
            ),
            (
                make(
                    sexual_baseline=baseline(
                        sensitivity=(("私處", "極高"), ("私處", "普通"))
                    )
                ),
                "duplicate sensitivity",
            ),
            (
                make(sexual_baseline=baseline(sensitivity=(("私處", "失控"),))),
                "outside its vocabulary",
            ),
            (
                make(sexual_baseline=baseline(sensitivity=("私處",))),
                "pair of strings",
            ),
            (make(sexual_baseline="微興奮"), "not a PresetSexualBaseline"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                ValueError, message
            ):
                _validate_preset_sexual_baselines({"x": preset})
        # None and a fully/partially authored baseline pass; empty optional
        # levels are legal because to_record() omits them.
        _validate_preset_sexual_baselines({"x": make()})
        _validate_preset_sexual_baselines({"x": make(sexual_baseline=baseline())})
        _validate_preset_sexual_baselines(
            {"x": make(sexual_baseline=baseline(wetness="微濕", climax_phase="接近"))}
        )
        _validate_preset_sexual_baselines(PLAYER_PRESET_REGISTRY)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_sexual_baseline_to_record_omits_every_empty_optional(self):
        from world.lore.player_presets import PresetSexualBaseline

        # Required keys always present; empty optionals omitted so
        # SexualState's lowest-level defaulting applies to them.
        self.assertEqual(
            PresetSexualBaseline(
                arousal="微興奮", virgin=True, sensitivity=(("耳朵", "高"),)
            ).to_record(),
            {"arousal": "微興奮", "virgin": True, "sensitivity": {"耳朵": "高"}},
        )
        self.assertEqual(
            PresetSexualBaseline(
                arousal="極限", virgin=False, sensitivity=(),
                wetness="泛濫", shame="成癮", exposure="極高", climax_phase="餘韻",
            ).to_record(),
            {
                "arousal": "極限", "virgin": False, "sensitivity": {},
                "wetness": "泛濫", "shame": "成癮", "exposure": "極高",
                "climax_phase": "餘韻",
            },
        )


class StartingCompanionDeclarationTests(unittest.TestCase):
    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_the_twins_declare_each_other_symmetrically_at_95(self):
        yuna = PLAYER_PRESET_REGISTRY["yuna_darknight"]
        yuka = PLAYER_PRESET_REGISTRY["yuka_darknight"]
        self.assertEqual(
            yuna.starting_companions,
            (StartingCompanion("yuka_darknight", 95, "雙胞胎妹妹"),),
        )
        self.assertEqual(
            yuka.starting_companions,
            (StartingCompanion("yuna_darknight", 95, "雙胞胎姊姊"),),
        )
        for declaration in (*yuna.starting_companions, *yuka.starting_companions):
            partner = PLAYER_PRESET_REGISTRY[declaration.preset_key]
            # The partner's own card answers every mechanical question.
            self.assertIsInstance(partner, PlayerPreset)
            self.assertTrue(declaration.relationship)

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_every_other_preset_declares_no_companions(self):
        for key, preset in PLAYER_PRESET_REGISTRY.items():
            if key in ("yuna_darknight", "yuka_darknight"):
                continue
            with self.subTest(preset=key):
                self.assertEqual(preset.starting_companions, ())

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_companion_validation_rejects_unregistered_self_and_duplicate(self):
        from world.lore.player_presets import _validate_preset_starting_companions

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e",
                sex="female",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (
                make(starting_companions=(StartingCompanion("not_a_preset", 95, "夥伴"),)),
                "not registered",
            ),
            (
                make(starting_companions=(StartingCompanion("x", 95, "夥伴"),)),
                "its own companion",
            ),
            (
                make(starting_companions=(
                    StartingCompanion("human_wanderer", 95, "夥伴"),
                    StartingCompanion("human_wanderer", 40, "舊識"),
                )),
                "more than once",
            ),
            (make(starting_companions=("human_wanderer",)), "not a StartingCompanion"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_starting_companions(
                    {
                        "x": preset,
                        "human_wanderer": PLAYER_PRESET_REGISTRY["human_wanderer"],
                    }
                )
        # The empty default and a well-formed cross-reference both pass, and
        # the shipped registry validates clean at load.
        _validate_preset_starting_companions({"x": make()})
        _validate_preset_starting_companions(PLAYER_PRESET_REGISTRY)

