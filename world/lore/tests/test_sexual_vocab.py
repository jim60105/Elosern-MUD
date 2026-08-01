from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.lore import sexual_vocab


class SexualVocabularyTests(TestCase):
    @covers_requirement("sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-six-ordered-level-name-vocabularies-from-design-doc-s6-4")
    def test_all_vocabularies_match_the_design_in_order(self):
        self.assertEqual(sexual_vocab.AROUSAL_LEVELS, ("平靜", "微興奮", "中等", "高度", "極限"))
        self.assertEqual(sexual_vocab.WETNESS_LEVELS, ("乾燥", "微濕", "濕潤", "大量", "泛濫"))
        self.assertEqual(sexual_vocab.SHAME_LEVELS, ("無", "輕微", "中等", "強烈", "成癮"))
        self.assertEqual(sexual_vocab.EXPOSURE_LEVELS, ("極低", "低", "中等", "高", "極高"))
        self.assertEqual(sexual_vocab.CLIMAX_PHASE_LEVELS, ("未達", "接近", "進行中", "餘韻"))
        self.assertEqual(sexual_vocab.SENSITIVITY_LEVELS, ("普通", "高", "極高", "敏感異常"))

    def test_vocabulary_module_has_no_rules_or_imports_dependency(self):
        source = sexual_vocab.__loader__.get_source(sexual_vocab.__name__)
        self.assertNotIn("world.rules", source)
        self.assertNotIn("world.imports", source)
