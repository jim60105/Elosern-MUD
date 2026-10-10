"""Data-contract test: keyed bestiary documentation relationship contract

The current bestiary sections carry a bounded, machine-readable index: species
key, parent species key, default variant key, every owned variant with its
kit-backed executable status, and the public registry fields the section
documents. This module checks the shipped document against the live registries
both ways, proves that a wording-only prose edit still passes, proves that
historical appendix text can never satisfy current coverage, and drives every
named relationship fault - missing, duplicate, orphaned, mis-parented,
field-incomplete, private-field and status-mismatched - through the same pure
parser and checker with synthetic rows.

No expected sentence, substring or roster table appears here: the prose half of
the publication stays editable, and the checker's own limits (it judges
structure, never semantic accuracy) are stated rather than faked.
"""

import pathlib
import unittest

import yaml

from tools.spec_traceability import covers_requirement

from world.lore.bestiary_documentation import (
    CURRENT_END_MARKER,
    DELIVERED,
    NARRATIVE,
    check_bestiary_documentation,
    parse_bestiary_document,
)
from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
)
from world.tests.synthetic_data import make_monster_species, make_monster_variant

BESTIARY = pathlib.Path(__file__).resolve().parents[3] / "docs" / "lore" / "bestiary.md"
REQUIREMENT = (
    "monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships"
)
DEFAULT_FIELDS = [
    "display_name_zh",
    "published_description_zh",
    "published_ecology_zh",
    "description_zh",
]


def _status(variant) -> str:
    return DELIVERED if (variant.active_skill_keys or variant.passive_skill_keys) else NARRATIVE


def _synthetic_rows():
    """One synthetic species with an ordinary variant and one delivering variant."""
    species = make_monster_species(
        "t_doc_species",
        default_variant_key="t_doc_ordinary",
        published_description_zh="合成文件描述。",
        published_appearance_zh="合成文件外觀。",
        published_ecology_zh="合成文件生態。",
    )
    variants = {
        "t_doc_ordinary": make_monster_variant(
            "t_doc_ordinary",
            species_key="t_doc_species",
            description_zh="合成普通型敘述。",
            ordinary_variant=True,
        ),
        "t_doc_stronger": make_monster_variant(
            "t_doc_stronger",
            species_key="t_doc_species",
            description_zh="合成強勢型敘述。",
            active_skill_keys=("t_doc_skill",),
            ordinary_variant=False,
        ),
    }
    return {"t_doc_species": species}, variants


def _section(species_key: str, block: dict, *, prose: str = "合成敘述段落。") -> str:
    rendered = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
    return f"### {species_key}\n\n```bestiary\n{rendered}```\n\n{prose}\n"


class LiveBestiaryDocumentationTests(unittest.TestCase):
    """Requirement: the shipped publication matches the shipped registries."""

    @covers_requirement(REQUIREMENT)
    def test_the_current_documentation_covers_every_shipped_key_both_ways(self):
        problems = check_bestiary_documentation(
            MONSTER_SPECIES_REGISTRY,
            MONSTER_VARIANT_REGISTRY,
            parse_bestiary_document(BESTIARY.read_text(encoding="utf-8")),
        )
        self.assertEqual(problems, ())

    @covers_requirement(REQUIREMENT)
    def test_a_wording_only_edit_of_a_valid_section_still_passes(self):
        text = BESTIARY.read_text(encoding="utf-8")
        marker = text.index(CURRENT_END_MARKER)
        current, historical = text[:marker], text[marker:]
        # Reword every published sentence and append a fresh paragraph without
        # touching a single key, status or field name.
        reworded = current.replace("。", "。改寫") + "\n新增的敘述段落。\n" + historical
        self.assertNotEqual(reworded, text)
        problems = check_bestiary_documentation(
            MONSTER_SPECIES_REGISTRY,
            MONSTER_VARIANT_REGISTRY,
            parse_bestiary_document(reworded),
        )
        self.assertEqual(problems, ())

    @covers_requirement(REQUIREMENT)
    def test_historical_entries_never_satisfy_current_coverage(self):
        text = BESTIARY.read_text(encoding="utf-8")
        marker = text.index(CURRENT_END_MARKER)
        # Move the whole boundary in front of the sections: the same, complete
        # blocks are now historical appendix text and cover nothing.
        demoted = CURRENT_END_MARKER + "\n\n" + text
        problems = check_bestiary_documentation(
            MONSTER_SPECIES_REGISTRY,
            MONSTER_VARIANT_REGISTRY,
            parse_bestiary_document(demoted),
        )
        for key in MONSTER_SPECIES_REGISTRY:
            self.assertIn(f"{key}: shipped species is not documented by any current section", problems)
        self.assertTrue(
            any("historical section carries current-coverage metadata" in problem for problem in problems)
        )


class BestiaryRelationshipFaultTests(unittest.TestCase):
    """Requirement: every named fault is rejected, naming key and relationship."""

    def setUp(self):
        self.species, self.variants = _synthetic_rows()
        self.row = next(iter(self.species.values()))
        self.valid = _section(self.row.key, self._block())

    def _block(self, **overrides) -> dict:
        owned = [self.variants[key] for key in sorted(self.variants)]
        block = {
            "species": self.row.key,
            "parent-species": self.row.key,
            "default-variant": self.row.default_variant_key,
            "variants": [
                {"key": variant.key, "status": _status(variant)} for variant in owned
            ],
            "public-fields": list(DEFAULT_FIELDS),
            "status": DELIVERED,
        }
        block.update(overrides)
        return block

    def _problems(self, text: str) -> tuple[str, ...]:
        return check_bestiary_documentation(
            self.species, self.variants, parse_bestiary_document(text)
        )

    def test_the_valid_synthetic_section_passes(self):
        self.assertEqual(self._problems(self.valid), ())

    def test_missing_species_and_missing_variant_are_named(self):
        other = make_monster_species("t_doc_absent", default_variant_key="t_doc_absent_variant")
        problems = check_bestiary_documentation(
            {**self.species, "t_doc_absent": other},
            self.variants,
            parse_bestiary_document(self.valid),
        )
        self.assertIn(
            "t_doc_absent: shipped species is not documented by any current section",
            problems,
        )

        block = self._block(
            variants=[{"key": "t_doc_ordinary", "status": NARRATIVE}]
        )
        problems = self._problems(_section(self.row.key, block))
        self.assertIn(
            "t_doc_stronger: owned by t_doc_species but missing from its section",
            problems,
        )

    def test_duplicate_documentation_is_named(self):
        problems = self._problems(self.valid + "\n" + self.valid)
        self.assertIn("t_doc_species: documented by more than one section", problems)

        block = self._block(
            variants=[
                {"key": "t_doc_ordinary", "status": NARRATIVE},
                {"key": "t_doc_ordinary", "status": NARRATIVE},
                {"key": "t_doc_stronger", "status": DELIVERED},
            ]
        )
        problems = self._problems(_section(self.row.key, block))
        self.assertIn("t_doc_ordinary: documented twice (also under t_doc_species)", problems)

    def test_orphan_and_wrong_parent_are_named(self):
        problems = self._problems(_section("t_doc_unknown", self._block(species="t_doc_unknown")))
        self.assertIn("t_doc_unknown: documented species is not in the registry", problems)

        problems = self._problems(_section(self.row.key, self._block(**{"parent-species": "t_doc_other"})))
        self.assertIn(
            "t_doc_species: parent-species 't_doc_other' is not the owning species",
            problems,
        )

        block = self._block(
            variants=[
                {"key": "t_doc_ordinary", "status": NARRATIVE},
                {"key": "t_doc_stronger", "status": DELIVERED},
                {"key": "t_doc_foreign", "status": NARRATIVE},
            ]
        )
        problems = self._problems(_section(self.row.key, block))
        self.assertIn(
            "t_doc_foreign: documented under t_doc_species but not owned by it", problems
        )

    def test_missing_field_private_reference_and_status_mismatch_are_named(self):
        problems = self._problems(
            _section(self.row.key, self._block(**{"public-fields": ["display_name_zh"]}))
        )
        self.assertIn(
            "t_doc_species: public field 'published_description_zh' is not documented",
            problems,
        )
        self.assertIn(
            "t_doc_species: public field 'published_ecology_zh' is not documented",
            problems,
        )

        problems = self._problems(
            _section(
                self.row.key,
                self._block(**{"public-fields": [*DEFAULT_FIELDS, "author_hidden_truth_zh"]}),
            )
        )
        self.assertIn(
            "t_doc_species: 'author_hidden_truth_zh' is not a published registry field",
            problems,
        )

        block = self._block(
            variants=[
                {"key": "t_doc_ordinary", "status": NARRATIVE},
                {"key": "t_doc_stronger", "status": NARRATIVE},
            ]
        )
        problems = self._problems(_section(self.row.key, block))
        self.assertIn(
            "t_doc_stronger: status 'narrative' contradicts its declared kit", problems
        )

        problems = self._problems(_section(self.row.key, self._block(status=NARRATIVE)))
        self.assertIn("t_doc_species: status 'narrative' contradicts its declared kits", problems)

    def test_default_variant_ordinary_ownership_is_enforced(self):
        block = self._block(**{"default-variant": "t_doc_stronger"})
        problems = self._problems(_section(self.row.key, block))
        self.assertIn(
            "t_doc_species: default variant 't_doc_stronger' is not the registry default",
            problems,
        )

        block = self._block(**{"default-variant": "t_doc_absent"})
        problems = self._problems(_section(self.row.key, block))
        self.assertIn(
            "t_doc_species: default variant 't_doc_absent' is not documented as an owned variant",
            problems,
        )

        # An ordinary-looking default that the registry classifies otherwise is
        # an invented documentation-only variant.
        stronger_default = make_monster_variant(
            "t_doc_stronger",
            species_key="t_doc_species",
            description_zh="合成強勢型敘述。",
            active_skill_keys=("t_doc_skill",),
            ordinary_variant=False,
        )
        weaker_species = make_monster_species(
            "t_doc_species",
            default_variant_key="t_doc_stronger",
            published_description_zh="合成文件描述。",
            published_appearance_zh="合成文件外觀。",
            published_ecology_zh="合成文件生態。",
        )
        block = self._block(**{"default-variant": "t_doc_stronger"})
        problems = check_bestiary_documentation(
            {"t_doc_species": weaker_species},
            {**self.variants, "t_doc_stronger": stronger_default},
            parse_bestiary_document(_section(self.row.key, block)),
        )
        self.assertIn(
            "t_doc_species: default variant 't_doc_stronger' is not an ordinary variant",
            problems,
        )

    def test_unkeyed_section_extra_block_and_empty_body_are_named(self):
        problems = self._problems("### 合成無索引小節\n\n只有敘述，沒有索引區塊。\n")
        self.assertIn(
            "合成無索引小節: current section carries no parseable 'bestiary' metadata block",
            problems,
        )

        extra = self.valid + "\n```bestiary\nspecies: t_doc_species\n```\n"
        problems = self._problems(extra)
        self.assertTrue(
            any("carries more than one 'bestiary' metadata block" in problem for problem in problems)
        )

        empty_body = self.valid.replace("合成敘述段落。", "")
        problems = self._problems(empty_body)
        self.assertIn("t_doc_species: current section carries no prose body", problems)
