"""Behavior tests for the race-bounded sex seam (``world.rules.identity``).

Pure-function arms run on ``unittest.TestCase``; the entity-write arm uses
``EvenniaTestCase`` because it persists an ``AttributeProperty``. The elf case
is a borrowed kit race profile under the production key, so the tests resolve
through the same scoped registry the production rule reads.
"""

import ast
from dataclasses import replace
from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.npcs import NPC
from world.lore.sex import DEFAULT_SEX, SEX_VALUES
from world.rules.identity import (
    IdentityError,
    ensure_entity_sex,
    permitted_sexes,
    resolve_sex,
)
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries


def _elf_row():
    """The kit race row borrowed under the production key, female-only."""
    return replace(SYNTH_RACES["t_duskmari"], key="elf", allowed_sexes=("female",))


class ResolveSexTests(unittest.TestCase):
    """The pure rule: an omitted sex normalizes, a forbidden member is refused."""

    @covers_requirement(
        "living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other"
    )
    def test_an_omitted_sex_resolves_to_the_race_permitted_default(self):
        with synthetic_registries("races", extra={"races": {"elf": _elf_row()}}):
            # The sole-member race cannot keep the vocabulary default.
            self.assertEqual(permitted_sexes("elf"), ("female",))
            self.assertEqual(resolve_sex("elf", None), "female")
            # A full-vocabulary race keeps DEFAULT_SEX.
            self.assertEqual(permitted_sexes("t_duskmari"), SEX_VALUES)
            self.assertEqual(resolve_sex("t_duskmari", None), DEFAULT_SEX)
            # An unresolvable race normalizes instead of crashing.
            self.assertEqual(permitted_sexes("t_absent_race"), SEX_VALUES)
            self.assertEqual(permitted_sexes(None), SEX_VALUES)
            self.assertEqual(resolve_sex("t_absent_race", None), DEFAULT_SEX)

    @covers_requirement(
        "living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other"
    )
    def test_a_forbidden_member_is_refused_and_a_permitted_one_is_kept(self):
        with synthetic_registries("races", extra={"races": {"elf": _elf_row()}}):
            for forbidden in SEX_VALUES:
                if forbidden in ("female",):
                    continue
                with self.subTest(forbidden=forbidden):
                    with self.assertRaisesRegex(
                        IdentityError, "is not available for race 'elf'"
                    ):
                        resolve_sex("elf", forbidden)
            self.assertEqual(resolve_sex("elf", "female"), "female")
            # A full-vocabulary race keeps every declared member.
            self.assertEqual(resolve_sex("t_duskmari", "male"), "male")

    @covers_requirement(
        "living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other"
    )
    def test_a_non_member_keeps_the_vocabulary_message(self):
        with synthetic_registries("races", extra={"races": {"elf": _elf_row()}}):
            for value in ("", "Female", "horse", 5, []):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(IdentityError, "sex must be one of"):
                        resolve_sex("elf", value)


class EntitySexSeamTests(EvenniaTestCase):
    """``ensure_entity_sex`` is the only production writer of an entity's sex."""

    @covers_requirement(
        "living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other"
    )
    def test_ensure_entity_sex_writes_the_resolved_value(self):
        with synthetic_registries("races", extra={"races": {"elf": _elf_row()}}):
            elf = create_object(NPC, key="seam elf")
            elf.race = "elf"
            self.assertEqual(ensure_entity_sex(elf), "female")
            self.assertEqual(elf.sex, "female")

            human = create_object(NPC, key="seam human")
            human.race = "t_duskmari"
            self.assertEqual(ensure_entity_sex(human, "male"), "male")
            self.assertEqual(human.sex, "male")
            # An omitted sex on a full-vocabulary race keeps the default.
            self.assertEqual(ensure_entity_sex(human), DEFAULT_SEX)
            self.assertEqual(human.sex, DEFAULT_SEX)


def _assigned_sex_offenders(root: Path) -> list[str]:
    """Production modules (outside test packages) that assign ``<expr>.sex``."""
    seam = root / "world" / "rules" / "identity.py"
    offenders: list[str] = []
    for base in (root / "world", root / "typeclasses"):
        for path in sorted(base.rglob("*.py")):
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            if path == seam:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    targets = node.targets
                elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                    targets = [node.target]
                else:
                    continue
                for target in targets:
                    for child in ast.walk(target):
                        if isinstance(child, ast.Attribute) and child.attr == "sex":
                            offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    return offenders


class SeamOwnershipTests(unittest.TestCase):
    """No production module outside the seam assigns an entity's ``sex``."""

    @covers_requirement(
        "living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other"
    )
    def test_no_production_module_outside_the_seam_assigns_sex(self):
        root = Path(__file__).resolve().parents[3]
        self.assertEqual(_assigned_sex_offenders(root), [])


if __name__ == "__main__":
    unittest.main()
