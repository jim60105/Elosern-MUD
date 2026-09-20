"""Data-contract test: skill registry content contract
Slice of ``test_skill_registry``: OutOfCombatAvailabilityPolicyTests.
"""
from tools.spec_traceability import covers_requirement
import ast
from dataclasses import fields
import pathlib
import unittest
from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import (
    DamageEffect,
    HealEffect,
    RevealDisguiseEffect,
    SelfHealEffect,
    SexualMasteryEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.rules.progression import proficiency_cap
from ..test_spell_catalogs import _CATALOG_EFFECTS

from ._support import (
    USABLE_OUT_OF_COMBAT_FALSE_KEYS,
)

class OutOfCombatAvailabilityPolicyTests(unittest.TestCase):
    """The deliberate-value contract for ``usable_out_of_combat``."""

    @classmethod
    def setUpClass(cls):
        import world.rules.disengage  # noqa: F401  (registers flee)

        # The inventory covers the sexual-act catalog too; registering it is
        # a declared prerequisite of the assertion, not an import-order
        # side effect.
        import world.skills.sexual_acts  # noqa: F401

    @covers_requirement(
        "skill-registry::the-set-of-skills-declaring-usable-out-of-combat-false-is-a-frozen-inventory"
    )
    def test_false_inventory_equals_the_frozen_set_naming_undecided_keys(self):
        computed = {
            key for key, skill in SKILL_REGISTRY.items()
            if not skill.usable_out_of_combat
        }
        missing = sorted(USABLE_OUT_OF_COMBAT_FALSE_KEYS - computed)
        extra = sorted(computed - USABLE_OUT_OF_COMBAT_FALSE_KEYS)
        self.assertEqual(
            (missing, extra),
            ([], []),
            "missing (deliberately-False keys that now declare True): "
            f"{missing}; undecided (keys defaulting to False that no "
            f"inventory records): {extra}",
        )

    @covers_requirement(
        "skill-registry::the-set-of-skills-declaring-usable-out-of-combat-false-is-a-frozen-inventory"
    )
    def test_an_injected_skill_that_omits_the_decision_fails_and_is_named(self):
        from world.skills.registry import _skill

        # The author path for a new seed row: omitting the kwarg leaves the
        # helper's False default — exactly the undecided state the frozen
        # inventory must surface.
        undecided = _skill(
            "_test_undecided_skill",
            "測試未決定",
            "注入未宣告 usable_out_of_combat 的定義。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            category=SkillCategory.UTILITY,
        )
        self.assertFalse(undecided.usable_out_of_combat)
        try:
            SKILL_REGISTRY[undecided.key] = undecided
            computed = {
                key for key, skill in SKILL_REGISTRY.items()
                if not skill.usable_out_of_combat
            }
            extra = sorted(computed - USABLE_OUT_OF_COMBAT_FALSE_KEYS)
            self.assertEqual(
                extra,
                [undecided.key],
                "the frozen-inventory diff must name the undecided key",
            )
        finally:
            SKILL_REGISTRY.pop(undecided.key, None)

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_damage_carrying_skills_all_declare_true(self):
        offenders = sorted(
            key
            for key, skill in SKILL_REGISTRY.items()
            if any(
                isinstance(effect, DamageEffect) for effect in skill.parsed_effects
            )
            and not skill.usable_out_of_combat
        )
        self.assertEqual(
            offenders,
            [],
            "DamageEffect-carrying entries must be selectable outside combat",
        )

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_flee_declares_false_at_its_own_construction_site(self):
        self.assertFalse(SKILL_REGISTRY["flee"].usable_out_of_combat)

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_every_production_construction_site_supplies_the_kwarg(self):
        """Every SkillDef/_skill/_spell call that produces a registry row
        passes ``usable_out_of_combat`` as an argument (the helper defaults
        stay False so an omission can never pass unnoticed)."""
        # Package split: one directory deeper than the flat module.
        root = pathlib.Path(__file__).resolve().parents[3]
        sources = {
            "skills/registry/builders.py": {"SkillDef", "_skill", "_spell"},
            "skills/sexual_acts/_builder.py": {"SkillDef"},
            "skills/sexual_acts/divine.py": {"SkillDef"},
            "rules/disengage.py": {"SkillDef"},
        }
        # The registry package's data slices construct rows ONLY through the
        # builders above (no bare SkillDef/_skill/_spell calls), which the
        # per-data-module scan below re-proves for every shipped row.
        data_sources = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "skills" / "registry").glob("data_*.py")
        )
        for relative, call_names in (
            *sources.items(),
            *((relative, {"SkillDef", "_skill", "_spell"})
              for relative in data_sources),
        ):
            tree = ast.parse((root / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else None
                if name not in call_names:
                    continue
                with self.subTest(site=relative, call=name, line=node.lineno):
                    self.assertIn(
                        "usable_out_of_combat",
                        {kw.arg for kw in node.keywords if kw.arg},
                        f"{relative}:{node.lineno} omits the deliberate value",
                    )

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_no_production_module_mutates_the_flag_after_construction(self):
        """No production code assigns ``usable_out_of_combat`` on an already
        built SkillDef (``dataclasses.replace`` copies are construction, not
        mutation; tests are exempt — this scan covers production sources)."""
        # Package split: one directory deeper than the flat module.
        root = pathlib.Path(__file__).resolve().parents[3]
        offenders = []
        for package in ("world", "commands", "typeclasses", "web"):
            for path in sorted((root / package).rglob("*.py")):
                if "tests" in path.parts or "test_" in path.name:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        targets = node.targets
                    elif isinstance(node, ast.AnnAssign):
                        targets = [node.target]
                    elif isinstance(node, ast.AugAssign):
                        targets = [node.target]
                    else:
                        continue
                    for target in targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and target.attr == "usable_out_of_combat"
                        ):
                            offenders.append(
                                f"{path.relative_to(root)}:{node.lineno}"
                            )
        self.assertEqual(offenders, [])
