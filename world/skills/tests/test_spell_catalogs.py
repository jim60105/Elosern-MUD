"""Data-contract test: spell catalog content contract
Elemental spell-catalog tests and their pinned catalog constants."""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.progression import PROFICIENCY_TIP_CAP, proficiency_cap
from world.skills.effects import (
    BuffApplyEffect,
    CleanseEffect,
    DamageEffect,
    HealEffect,
    MovementEffect,
    RiteBlessingEffect,
    RiteShelterEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    parse_effect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillEligibility,
    SkillKind,
    TargetSpec,
    declared_prerequisites,
    prerequisite_consumers,
)


class ElementalSpellsBuilderTests(unittest.TestCase):
    def test_elemental_spells_builder_rejects_unknown_element(self):
        from world.skills.registry import _elemental_spells

        with self.assertRaises(ValueError):
            _elemental_spells(
                "bogus",
                ("x", "X", "說明", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
            )


class ClosedVocabularyParseTests(unittest.TestCase):
    """Positive parses of the parser's closed production vocabularies.

    The accepted values of these branches ARE shipped grammar (no synthetic
    substitute exists), so their assertions live in this registered content
    contract rather than in the synthetic data-independent behavior tests.
    """

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_movement_flash_step_parses_as_the_closed_mode(self):
        self.assertEqual(
            parse_effect("movement:flash_step"),
            MovementEffect(mode="flash_step"),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_self_heal_bare_prefix_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("self_heal"), SelfHealEffect())

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_blessing_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("rite_blessing:martial_blessing"),
            RiteBlessingEffect(buff_key="martial_blessing"),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_blessing_malformed_payloads_raise(self):
        for effect in ("rite_blessing", "rite_blessing:", "rite_blessing:a:b"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_shelter_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("rite_shelter"),
            RiteShelterEffect(),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_shelter_rejects_payload(self):
        for effect in ("rite_shelter:", "rite_shelter:today", "rite_shelter:sanctuary"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)


def _is_unrestricted(skill) -> bool:
    """Whether the row is open to every actor kind, race, subrace and species."""
    return skill.eligibility == SkillEligibility()


def _is_mastery_row(skill) -> bool:
    """The mastery family as authored: a PASSIVE of the elemental-magic category."""
    return (
        skill.kind is SkillKind.PASSIVE
        and skill.category is SkillCategory.ELEMENTAL_MAGIC
    )


def _mastery_rows() -> dict[str, object]:
    """Every elemental-mastery row of the live catalog, by key."""
    return {
        key: skill
        for key, skill in SKILL_REGISTRY.items()
        if _is_mastery_row(skill)
    }


def _ordinary_universe(skill) -> set[str]:
    """One mastery's ordinary ACTIVE elemental catalog: element, group, unrestricted.

    Derived from the registry's own classification, never from a copied
    roster, so a re-authored node joins or leaves the universe by content
    alone. Element-tagged martial skills (another category) and
    identity-restricted monster rows are outside it by construction.
    """
    return {
        key
        for key, row in SKILL_REGISTRY.items()
        if row.kind is SkillKind.ACTIVE
        and row.category is SkillCategory.ELEMENTAL_MAGIC
        and row.element is not None
        and skill.element is not None
        and row.element.key == skill.element.key
        and row.group == skill.group
        and _is_unrestricted(row)
    }


def _ordinary_terminals(universe: set[str]) -> set[str]:
    """Universe members no OTHER universe member consumes."""
    consumed = {
        edge.skill_key
        for key in universe
        for edge in SKILL_REGISTRY[key].prerequisites
        if edge.skill_key in universe
    }
    return universe - consumed


def _ordinary_cap(skill_key: str) -> int:
    """The derived tip cap of one row with every mastery consumer excluded.

    The mastery consumers are subtracted so the comparison cannot become
    circular: it answers "what would this row's cap be without the masteries",
    which is the pre-mastery derived cap the contract preserves.
    """
    ordinary = [
        level
        for consumer, level in prerequisite_consumers(skill_key)
        if consumer not in SKILL_REGISTRY
        or not _is_mastery_row(SKILL_REGISTRY[consumer])
    ]
    return max(ordinary) if ordinary else PROFICIENCY_TIP_CAP


class LineageGraphContractTests(unittest.TestCase):
    """Generic registry-graph relationships over the live skill catalog.

    Mechanism, never authored topology: every relationship below is derived
    from the registry itself, so a re-authored node, edge or threshold stays a
    content decision while a dangling reference, a non-positive threshold, a
    reversed or missing reverse-cache entry or a cyclic graph is still
    detected. No assertion approves a node roster, a display label or a
    balance magnitude.
    """

    @covers_requirement(
        "skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed"
    )
    def test_every_declared_edge_references_a_registered_row_at_a_positive_level(self):
        for key, skill in SKILL_REGISTRY.items():
            with self.subTest(skill=key):
                self.assertEqual(
                    declared_prerequisites(key), tuple(skill.prerequisites)
                )
                for edge in skill.prerequisites:
                    self.assertIn(edge.skill_key, SKILL_REGISTRY)
                    self.assertIs(type(edge.min_proficiency), int)
                    self.assertGreaterEqual(edge.min_proficiency, 1)

    @covers_requirement(
        "skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed"
    )
    def test_reverse_cache_matches_the_declared_edges_exactly(self):
        expected: dict[str, list[tuple[str, int]]] = {}
        for key, skill in SKILL_REGISTRY.items():
            for edge in skill.prerequisites:
                expected.setdefault(edge.skill_key, []).append(
                    (key, edge.min_proficiency)
                )
        for prereq_key, edges in expected.items():
            with self.subTest(prerequisite=prereq_key):
                self.assertEqual(
                    prerequisite_consumers(prereq_key),
                    tuple(sorted(edges, key=lambda edge: (edge[1], edge[0]))),
                )
        for key in SKILL_REGISTRY:
            if key in expected:
                continue
            with self.subTest(canopy=key):
                self.assertEqual(prerequisite_consumers(key), ())

    @covers_requirement(
        "skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed"
    )
    def test_prerequisite_graph_is_acyclic_and_drains_completely(self):
        indegree = {
            key: len(skill.prerequisites)
            for key, skill in SKILL_REGISTRY.items()
        }
        queue = [key for key, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for consumer_key, _ in prerequisite_consumers(current):
                indegree[consumer_key] -= 1
                if indegree[consumer_key] == 0:
                    queue.append(consumer_key)
        leftover = sorted(key for key, degree in indegree.items() if degree > 0)
        self.assertEqual(visited, len(SKILL_REGISTRY), leftover)


class ElementalMasteryCoverageContractTests(unittest.TestCase):
    """Whole-tree mastery coverage as a generic registry relationship.

    The assertions derive each element's ordinary terminals instead of naming
    them, so re-authoring a branch stays a content decision while an omitted
    terminal, a foreign prerequisite, a restricted prerequisite or a mastery
    edge that would raise an ordinary cap is still caught.
    """

    @covers_requirement(
        "element-mastery::elemental-mastery-prerequisites-cover-every-ordinary-branch"
    )
    def test_each_mastery_declares_exactly_its_elements_ordinary_terminals(self):
        masteries = _mastery_rows()
        self.assertTrue(masteries)
        for key, mastery in masteries.items():
            universe = _ordinary_universe(mastery)
            terminals = _ordinary_terminals(universe)
            with self.subTest(mastery=key):
                self.assertTrue(universe)
                self.assertTrue(terminals)
                self.assertEqual(
                    {edge.skill_key for edge in mastery.prerequisites},
                    terminals,
                )

    @covers_requirement(
        "element-mastery::elemental-mastery-prerequisites-cover-every-ordinary-branch"
    )
    def test_restricted_and_unrelated_rows_are_never_mastery_prerequisites(self):
        for key, mastery in _mastery_rows().items():
            element_key = mastery.element.key
            restricted = {
                row_key
                for row_key, row in SKILL_REGISTRY.items()
                if row.element is not None
                and row.element.key == element_key
                and not _is_unrestricted(row)
            }
            with self.subTest(mastery=key):
                self.assertFalse(
                    {edge.skill_key for edge in mastery.prerequisites} & restricted
                )
                for edge in mastery.prerequisites:
                    row = SKILL_REGISTRY[edge.skill_key]
                    self.assertIs(row.kind, SkillKind.ACTIVE)
                    self.assertIs(row.category, SkillCategory.ELEMENTAL_MAGIC)
                    self.assertIsNotNone(row.element)
                    self.assertEqual(row.element.key, element_key)
                    self.assertEqual(row.group, mastery.group)
                    self.assertTrue(_is_unrestricted(row))

    @covers_requirement(
        "element-mastery::elemental-mastery-prerequisites-cover-every-ordinary-branch"
    )
    def test_mastery_edges_leave_every_ordinary_terminal_cap_unchanged(self):
        for key, mastery in _mastery_rows().items():
            for edge in mastery.prerequisites:
                with self.subTest(mastery=key, terminal=edge.skill_key):
                    baseline = _ordinary_cap(edge.skill_key)
                    self.assertLessEqual(edge.min_proficiency, baseline)
                    self.assertEqual(proficiency_cap(edge.skill_key), baseline)

    @covers_requirement(
        "element-mastery::elemental-mastery-prerequisites-cover-every-ordinary-branch"
    )
    def test_independent_passives_are_never_prerequisites(self):
        independent = {
            key
            for key, skill in SKILL_REGISTRY.items()
            if skill.kind is SkillKind.PASSIVE
            and skill.category is SkillCategory.ENHANCEMENT
        }
        self.assertTrue(independent)
        for key in independent:
            with self.subTest(passive=key):
                self.assertEqual(prerequisite_consumers(key), ())
