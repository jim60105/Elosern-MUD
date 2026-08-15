from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.lore import sex


class SexVocabularyTests(TestCase):
    @covers_requirement("entity-sex-vocabulary::world-lore-sex-py-defines-the-canonical-sex-vocabulary-and-its-default")
    def test_sex_values_match_the_canonical_vocabulary_in_order(self):
        self.assertEqual(sex.SEX_VALUES, ("female", "male", "other"))
        self.assertEqual(sex.DEFAULT_SEX, "other")
        self.assertIn(sex.DEFAULT_SEX, sex.SEX_VALUES)

    @covers_requirement("entity-sex-vocabulary::world-lore-sex-py-defines-the-canonical-sex-vocabulary-and-its-default")
    def test_sex_module_has_no_rules_or_imports_dependency(self):
        source = sex.__loader__.get_source(sex.__name__)
        self.assertNotIn("world.rules", source)
        self.assertNotIn("world.imports", source)

    @covers_requirement("entity-sex-vocabulary::the-module-documents-itself-as-the-single-canonical-source-for-this-vocabulary")
    def test_module_docstring_names_its_consumers(self):
        self.assertIn("CHARACTER_SCHEMA_V1", sex.__doc__)
        self.assertIn("LivingEntity.sex", sex.__doc__)
