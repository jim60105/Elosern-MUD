from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.lore import sexual_vocab


class SexualVocabularyTests(TestCase):
    @covers_requirement("sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-sexual-state-vocabularies-sexualstate-is-built-from")
    def test_all_vocabularies_match_the_design_in_order(self):
        self.assertEqual(sexual_vocab.AROUSAL_LEVELS, ("平靜", "微興奮", "中等", "高度", "極限"))
        self.assertEqual(sexual_vocab.WETNESS_LEVELS, ("乾燥", "微濕", "濕潤", "大量", "泛濫"))
        self.assertEqual(sexual_vocab.SHAME_LEVELS, ("無", "輕微", "中等", "強烈", "成癮"))
        self.assertEqual(sexual_vocab.EXPOSURE_LEVELS, ("極低", "低", "中等", "高", "極高"))
        self.assertEqual(sexual_vocab.CLIMAX_PHASE_LEVELS, ("未達", "接近", "進行中", "餘韻"))
        self.assertEqual(sexual_vocab.SENSITIVITY_LEVELS, ("普通", "高", "極高", "敏感異常"))

    @covers_requirement("sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-sexual-state-vocabularies-sexualstate-is-built-from")
    def test_body_parts_matches_the_documented_set_in_exact_order(self):
        self.assertEqual(
            sexual_vocab.BODY_PARTS,
            ("口唇", "頸項", "耳朵", "乳房", "腰腹", "臀部", "大腿", "足部", "私處", "後庭"),
        )
        self.assertEqual(len(sexual_vocab.BODY_PARTS), 10)

    @covers_requirement("sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-sexual-state-vocabularies-sexualstate-is-built-from")
    def test_generic_body_part_is_the_monster_sentinel(self):
        self.assertEqual(sexual_vocab.GENERIC_BODY_PART, "軀體")

    @covers_requirement("sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-sexual-state-vocabularies-sexualstate-is-built-from")
    def test_generic_body_part_is_not_a_member_of_body_parts(self):
        self.assertNotIn(sexual_vocab.GENERIC_BODY_PART, sexual_vocab.BODY_PARTS)

    def test_vocabulary_module_has_no_rules_or_imports_dependency(self):
        source = sexual_vocab.__loader__.get_source(sexual_vocab.__name__)
        self.assertNotIn("world.rules", source)
        self.assertNotIn("world.imports", source)

    @covers_requirement("sexual-vocabulary::the-module-documents-itself-as-the-single-canonical-source-for-every-vocabulary-it-defines")
    def test_module_docstring_documents_the_expanded_vocabulary_scope(self):
        docstring = sexual_vocab.__doc__
        self.assertIn("single source", docstring)
        self.assertIn("import-contract", docstring)
        self.assertIn("CHARACTER_SCHEMA_V1", docstring)
        self.assertIn("Trait", docstring)
        self.assertIn("design doc", docstring)
        self.assertIn("BODY_PARTS", docstring)
        self.assertIn("GENERIC_BODY_PART", docstring)
        self.assertIn("no current consumer", docstring)
        self.assertIn("sexual-act-registry", docstring)
        self.assertIn("sexual-act-effects", docstring)