"""The gallery prompt-field catalog, fragments, and composition (pure).

Covers the closed catalog validation (declared-order normalization, typed
rejections, empty selection), the registry-owned equipment presentation
fragment (slot order, sorted accessories, tolerant empties, write-free
reads), the bounded free text, selection-aware description composition
(byte-for-byte unselected-appearance regression, determinism, exclusions),
the broken-library fallback's total data-read refusal, and the module's
import discipline.
"""

import ast
import unittest
from unittest.mock import Mock

from world.prompts.tests.fixtures import REPO_ROOT, PromptFixture

from world.art import subjects
from world.art.gallery_prompt import (
    CUSTOM_PROMPT_MAX,
    EQUIPMENT_FIELDS,
    GALLERY_PROMPT_FIELDS,
    GalleryPromptError,
    equipment_fragment,
    validate_custom_prompt,
    validate_fields,
)
from world.art.subjects import (
    ArtSubjectError,
    character_description,
    description_for,
    monster_description,
    monster_subject_for,
    scene_description,
    scene_subject_for,
)
from world.lore.items import ITEM_REGISTRY

from tools.spec_traceability import covers_requirement


_APPEARANCE_TEXT = {"feature": "a silver ear piercing", "height": "tall"}


def _entity(persona=None, equipment=None):
    """A DB-free stand-in character with fixed identity and stored state."""
    entity = Mock()
    entity.db.display_name = "艾琳"
    entity.db.race = "beastfolk"
    entity.db.subrace = "catkin"
    entity.db.persona = persona
    entity.db.equipment = equipment
    entity.key = "艾琳"
    return entity


class FieldCatalogTests(unittest.TestCase):
    """The closed catalog and its typed, side-effect-free validation."""

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_catalog_is_closed_and_declared_in_order(self):
        self.assertEqual(
            GALLERY_PROMPT_FIELDS,
            ("appearance", "weapon_main", "weapon_off", "armor", "accessories"),
        )
        self.assertEqual(EQUIPMENT_FIELDS, GALLERY_PROMPT_FIELDS[1:])

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_selection_normalizes_to_declared_order(self):
        self.assertEqual(
            validate_fields(("armor", "appearance", "accessories")),
            ("appearance", "armor", "accessories"),
        )
        self.assertEqual(
            validate_fields(["weapon_off", "weapon_main"]),
            ("weapon_main", "weapon_off"),
        )
        self.assertEqual(validate_fields(()), ())
        self.assertEqual(validate_fields([]), ())

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_unknown_duplicate_nonstring_and_bad_containers_are_rejected(self):
        for bad in (
            ["nope"],                     # unknown id
            ["appearance", "appearance"],  # duplicate id
            [""],                          # empty id
            ["appearance", 7],             # non-string id
            ["appearance", None],          # non-string id
            "appearance",                  # bare string, not a selection
            b"armor",                      # byte blob
            {"appearance": True},          # mapping
            None,                          # no selection object
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(GalleryPromptError):
                    validate_fields(bad)

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_kind_without_field_support_rejects_any_selection(self):
        # The catalog applies ONLY to kinds declaring field support (change
        # gallery-monster-generation): a monster-kind selection is a typed
        # rejection naming the undeclared capability, never a silent drop —
        # while the empty selection stays legal for every gallery kind.
        monster_value = subjects.ArtSubjectKind.MONSTER.value
        character_value = subjects.ArtSubjectKind.CHARACTER.value
        with self.assertRaises(GalleryPromptError) as caught:
            validate_fields(["appearance"], kind=monster_value)
        self.assertIn(monster_value, str(caught.exception))
        self.assertIn("field selection", str(caught.exception))
        # Any catalog field is rejected for the kind, not just one.
        for field in GALLERY_PROMPT_FIELDS:
            with self.subTest(field=field):
                with self.assertRaises(GalleryPromptError):
                    validate_fields([field], kind=monster_value)
        # Empty stays legal for BOTH vocabularies; a declaring kind is
        # unaffected by the scope.
        self.assertEqual(validate_fields((), kind=monster_value), ())
        self.assertEqual(validate_fields([], kind=monster_value), ())
        self.assertEqual(
            validate_fields(("armor", "appearance"), kind=character_value),
            ("appearance", "armor"),
        )
        # A syntactically bad selection for the no-support kind still fails
        # with the catalog-level typed error (never silently accepted).
        with self.assertRaises(GalleryPromptError):
            validate_fields(["nope"], kind=monster_value)


class CustomPromptBoundTests(unittest.TestCase):
    """The bounded, sanitized, single-line free text."""

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_accepted_text_is_normalized_to_one_line_verbatim(self):
        self.assertEqual(
            validate_custom_prompt("  月下持杖，  藍袍拖地 "),
            "月下持杖， 藍袍拖地",
        )
        self.assertEqual(validate_custom_prompt("x" * CUSTOM_PROMPT_MAX), "x" * CUSTOM_PROMPT_MAX)

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_empty_and_whitespace_only_are_legal_noops(self):
        self.assertEqual(validate_custom_prompt(""), "")
        self.assertEqual(validate_custom_prompt("   "), "")

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_over_long_non_text_and_control_bearing_text_is_rejected(self):
        for bad in (
            "x" * (CUSTOM_PROMPT_MAX + 1),
            17,
            None,
            "a\u0001b",
            "a\nb",
            "a\rb",
            "a\u2028b",  # line separator
            "a\u2029b",  # paragraph separator
            "a\ufeffb",  # zero-width no-break (format character)
        ):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(GalleryPromptError):
                    validate_custom_prompt(bad)


class EquipmentFragmentTests(unittest.TestCase):
    """Registry-owned visual text, slot order, tolerant reads, zero writes."""

    def _gear(self, **slots):
        return {
            "weapon_main": slots.get("weapon_main"),
            "weapon_off": slots.get("weapon_off"),
            "armor": slots.get("armor"),
            "accessories": slots.get("accessories", []),
        }

    @covers_requirement(
        "art-gallery-prompt-fields::equipment-fields-contribute-registry-owned-visual-text-and-nothing-else"
    )
    def test_selected_slots_contribute_presentation_text_in_declared_order(self):
        sword = ITEM_REGISTRY["plain_sword"].presentation.summary_zh
        robe = ITEM_REGISTRY["mage_robe"].presentation.summary_zh
        entity = _entity(equipment=self._gear(weapon_main="plain_sword", armor="mage_robe"))
        fragment = equipment_fragment(entity, ("weapon_main", "armor"))
        self.assertEqual(fragment, "\n" + sword + "\n" + robe)
        # Selecting only armor says nothing about the sword.
        self.assertEqual(equipment_fragment(entity, ("armor",)), "\n" + robe)

    @covers_requirement(
        "art-gallery-prompt-fields::equipment-fields-contribute-registry-owned-visual-text-and-nothing-else"
    )
    def test_accessories_contribute_in_sorted_key_order(self):
        hairpin = ITEM_REGISTRY["silver_hairpin"].presentation.summary_zh
        necklace = ITEM_REGISTRY["wolf_fang_necklace"].presentation.summary_zh
        entity = _entity(
            equipment=self._gear(accessories=["wolf_fang_necklace", "silver_hairpin"])
        )
        self.assertEqual(
            equipment_fragment(entity, ("accessories",)), "\n" + hairpin + "\n" + necklace
        )

    @covers_requirement(
        "art-gallery-prompt-fields::equipment-fields-contribute-registry-owned-visual-text-and-nothing-else"
    )
    def test_empty_unregistered_and_malformed_contribute_nothing_without_raising(self):
        for equipment in (
            None,                                    # missing storage
            "not-a-mapping",                         # malformed storage
            {},                                      # empty mapping
            self._gear(weapon_main="not_a_real_key"),  # unregistered key
            self._gear(accessories=["silver_hairpin", 42]),  # malformed accessory list
            {"weapon_main": 5},                      # malformed slot type
        ):
            with self.subTest(equipment=equipment):
                entity = _entity(equipment=equipment)
                for fields in (EQUIPMENT_FIELDS, ("weapon_main", "accessories")):
                    self.assertEqual(equipment_fragment(entity, fields), "")

    @covers_requirement(
        "art-gallery-prompt-fields::equipment-fields-contribute-registry-owned-visual-text-and-nothing-else"
    )
    def test_composing_never_writes_equipment_state(self):
        stored = self._gear(weapon_main="plain_sword", armor="leather_armor")

        class _WriteTrap:
            """Reads resolve; any equipment write fails the test."""

            display_name = "艾琳"
            race = "beastfolk"
            subrace = "catkin"
            persona = None

            @property
            def equipment(self):
                return stored

            @equipment.setter
            def equipment(self, value):
                raise AssertionError("fragment composition must never write equipment")

        entity = Mock()
        entity.db = _WriteTrap()
        entity.key = "艾琳"
        text = character_description(entity, 30, fields=EQUIPMENT_FIELDS)
        self.assertIn(ITEM_REGISTRY["plain_sword"].presentation.summary_zh, text)
        self.assertEqual(stored["weapon_main"], "plain_sword")


class CompositionTests(PromptFixture):
    """Selection-aware character_description over the shipped template."""

    _BASE = "A 貓人族 character named 艾琳 ({age}) in the approved visual style."

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_unselected_appearance_reproduces_the_pre_appearance_description(self):
        self.load()
        persona = {
            "appearance": _APPEARANCE_TEXT,
            "personality": "guarded",
            "identity": {"hidden": "流放的王室信使"},
        }
        for fields in ((), ("weapon_main",), ("armor", "accessories")):
            with self.subTest(fields=fields):
                self.assertEqual(
                    character_description(_entity(persona), 24, fields=fields),
                    self._BASE.format(age=24),
                )

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_selected_appearance_still_contributes_the_full_block(self):
        self.load()
        text = character_description(_entity({"appearance": _APPEARANCE_TEXT}), 24, fields=("appearance",))
        self.assertTrue(text.startswith(self._BASE.format(age=24)))
        self.assertIn("a silver ear piercing", text)
        self.assertIn("tall", text)

    @covers_requirement(
        "art-gallery-prompt-fields::equipment-fields-contribute-registry-owned-visual-text-and-nothing-else"
    )
    def test_equipment_selection_carries_only_presentation_text(self):
        self.load()
        gear = {
            "weapon_main": "plain_sword",
            "weapon_off": "iron_shield",
            "armor": "leather_armor",
            "accessories": ["silver_hairpin"],
        }
        entity = _entity(equipment=gear)
        text = character_description(entity, 24, fields=("armor", "weapon_main"))
        self.assertIn(ITEM_REGISTRY["plain_sword"].presentation.summary_zh, text)
        self.assertIn(ITEM_REGISTRY["leather_armor"].presentation.summary_zh, text)
        # Nothing from the unselected slots reaches the description.
        self.assertNotIn(ITEM_REGISTRY["iron_shield"].presentation.summary_zh, text)
        self.assertNotIn(ITEM_REGISTRY["silver_hairpin"].presentation.summary_zh, text)
        # No registry field other than the presentation summary can reach it.
        for forbidden in ("plain_sword", "leather_armor", "iron_shield", "silver_hairpin", "weapon", "rarity", "price"):
            self.assertNotIn(forbidden, text)

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_accepted_free_text_is_appended_after_every_field_contribution(self):
        self.load()
        entity = _entity(
            {"appearance": _APPEARANCE_TEXT},
            equipment={"armor": "leather_armor"},
        )
        custom = "逆光剪影，藍調色調"
        text = character_description(
            entity, 24, fields=("appearance", "armor"), custom_prompt=custom
        )
        self.assertTrue(text.endswith("\n" + custom))
        self.assertLess(text.index("外觀："), text.index(custom))
        self.assertLess(text.index(ITEM_REGISTRY["leather_armor"].presentation.summary_zh), text.index(custom))

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_empty_free_text_is_a_legal_noop(self):
        self.load()
        entity = _entity({"appearance": _APPEARANCE_TEXT})
        # What reaches the description is validated text; whitespace-only
        # input normalizes to the empty text before composition.
        for custom in ("", validate_custom_prompt("   ")):
            with self.subTest(custom=custom):
                from_custom = character_description(
                    entity, 24, fields=("appearance",), custom_prompt=custom
                )
                without = character_description(entity, 24, fields=("appearance",))
                self.assertEqual(from_custom, without)

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_same_entity_selection_and_text_are_byte_identical(self):
        self.load()
        entity = _entity(
            {"appearance": _APPEARANCE_TEXT},
            equipment={"weapon_main": "plain_sword", "accessories": ["wolf_fang_necklace", "silver_hairpin"]},
        )
        first = character_description(
            entity, 24, fields=("armor", "appearance", "accessories", "weapon_main"), custom_prompt="月夜"
        )
        second = character_description(
            entity, 24, fields=("accessories", "weapon_main", "appearance"), custom_prompt="月夜"
        )
        self.assertEqual(first, second)

    @covers_requirement(
        "art-gallery-prompt-fields::the-prompt-library-remains-the-sole-source-of-the-composed-template"
    )
    def test_section_framing_is_library_authored_not_python_authored(self):
        # Re-authoring the template's section framing changes the composed
        # description exactly the way the new framing says: the surrounding
        # text lives only in prompts/art.yaml.
        self.write_file(
            "art.yaml",
            "schema_version: 1\nprompts:\n"
            "  art.style: approved visual style\n"
            "  art.character_description: 'A {name} ({age}) [{style}]|{appearance}|{equipment}|{custom}'\n"
            "  art.monster_description: '{description} ({display_name}；例如：{examples})'\n",
        )
        self.load()
        entity = _entity(
            {"appearance": {"feature": "quiet eyes"}},
            equipment={"armor": "leather_armor"},
        )
        text = character_description(entity, 24, fields=("appearance", "armor"), custom_prompt="雨")
        armor_line = ITEM_REGISTRY["leather_armor"].presentation.summary_zh
        self.assertTrue(text.startswith("A 艾琳 (24) [approved visual style]"))
        self.assertIn(f"|\n外觀：\nfeature：quiet eyes|\n{armor_line}|\n雨", text)

    @covers_requirement(
        "art-gallery-prompt-fields::the-prompt-library-remains-the-sole-source-of-the-composed-template"
    )
    def test_broken_library_fallback_reads_no_persona_equipment_or_free_text(self):
        self.write_file(
            "art.yaml",
            "schema_version: 1\nprompts:\n"
            "  art.style: approved visual style\n"
            "  art.character_description: A {race} character named {name} ({age}) in the {style} {oops}.\n"
            "  art.monster_description: \"{description} ({display_name}；例如：{examples})\"\n",
        )
        self.load()

        class _Trap:
            """Identity fields resolve; any composition input fails the test."""

            display_name = "艾琳"
            race = "beastfolk"
            subrace = "catkin"

            @property
            def persona(self):
                raise AssertionError("the degraded fallback must read no persona")

            @property
            def equipment(self):
                raise AssertionError("the degraded fallback must read no equipment")

        entity = Mock()
        entity.db = _Trap()
        entity.key = "艾琳"
        self.assertEqual(
            character_description(
                entity, 24, fields=GALLERY_PROMPT_FIELDS, custom_prompt="任何自由文字"
            ),
            "艾琳（貓人族，24 歲）",
        )

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_a_generator_selection_composes_identically_to_the_same_tuple(self):
        # A one-shot iterable must not silently lose fields to exhaustion:
        # the public boundary normalizes once, before any membership test.
        self.load()
        entity = _entity(
            {"appearance": _APPEARANCE_TEXT},
            equipment={
                "weapon_main": "plain_sword",
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
        )
        as_tuple = character_description(
            entity, 24, fields=("weapon_main", "appearance"), custom_prompt=""
        )
        as_generator = character_description(
            entity, 24, fields=(field for field in ("weapon_main", "appearance"))
        )
        self.assertEqual(as_generator, as_tuple)
        self.assertIn(
            ITEM_REGISTRY["plain_sword"].presentation.summary_zh, as_generator
        )

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_the_direct_api_rejects_invalid_inputs_before_any_data_read(self):
        # The composition boundary validates too: no render, no persona or
        # equipment read, for a raw selection or free text the seam rejects.
        self.load()

        class _Trap:
            display_name = "艾琳"
            race = "beastfolk"
            subrace = "catkin"

            @property
            def persona(self):
                raise AssertionError("validation must precede every persona read")

            @property
            def equipment(self):
                raise AssertionError("validation must precede every equipment read")

        entity = Mock()
        entity.db = _Trap()
        entity.key = "艾琳"
        for bad_fields, bad_custom in (
            (("armor", "nope"), ""),
            (("armor", "armor"), ""),
            (("armor", 7), ""),
            (("armor",), "a\nb"),
            (("armor",), "x" * (CUSTOM_PROMPT_MAX + 1)),
        ):
            with self.subTest(fields=bad_fields, custom=bad_custom[:8]):
                with self.assertRaises(GalleryPromptError):
                    character_description(
                        entity, 24, fields=bad_fields, custom_prompt=bad_custom
                    )
                with self.assertRaises(GalleryPromptError):
                    description_for(
                        subjects.ArtSubject(subjects.ArtSubjectKind.CHARACTER, "42"),
                        entity=entity,
                        age=24,
                        fields=bad_fields,
                        custom_prompt=bad_custom,
                    )


class DescriptionDispatcherTests(PromptFixture):
    """The description_for boundary: explicit selection only for characters."""

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_character_without_an_explicit_selection_is_rejected(self):
        self.load()
        subject = subjects.ArtSubject(subjects.ArtSubjectKind.CHARACTER, "42")
        with self.assertRaises(ArtSubjectError):
            description_for(subject, entity=object(), age=30)

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_scene_and_monster_dispatch_ignore_the_selection(self):
        self.load()
        scene = scene_subject_for("forest_path")
        monster = monster_subject_for("low")
        from world.art.subjects import monster_description, scene_description

        self.assertEqual(description_for(scene), scene_description(scene))
        self.assertEqual(
            description_for(scene, fields=("armor",), custom_prompt="x"),
            scene_description(scene),
        )
        self.assertEqual(description_for(monster), monster_description(monster))
        self.assertEqual(
            description_for(monster, fields=("armor",), custom_prompt="x"),
            monster_description(monster),
        )


class GalleryPromptImportBoundaryTests(unittest.TestCase):
    """The deterministic art path's import discipline, module by module."""

    FORBIDDEN = ("world.ai", "ollama", "llm_client", "world.art.connectivity")

    @covers_requirement(
        "art-gallery-prompt-fields::the-prompt-library-remains-the-sole-source-of-the-composed-template"
    )
    def test_gallery_prompt_imports_no_generation_or_ai_surface(self):
        source = (REPO_ROOT / "world/art/gallery_prompt.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for module in imported:
            for forbidden in self.FORBIDDEN:
                self.assertNotIn(forbidden, module)

    @covers_requirement(
        "art-gallery-prompt-fields::the-prompt-library-remains-the-sole-source-of-the-composed-template"
    )
    def test_no_section_framing_text_is_defined_in_python(self):
        # The composition modules carry no CJK section labels of their own;
        # every surrounding string comes from the prompt library. (The only
        # Chinese literals allowed in these two modules are the documented
        # registry-driven fallback and the persona store's own label — the
        # latter lives in world/rules/persona.py, not here.)
        for relative in ("world/art/gallery_prompt.py",):
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            for fragment in ("外觀", "裝備", "自訂"):
                self.assertNotIn(fragment, source, relative)


if __name__ == "__main__":
    unittest.main()
