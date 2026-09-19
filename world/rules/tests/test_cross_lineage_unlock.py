"""Behavior tests for the cross-lineage unlock rulebook and its loader.

Gate-clean by construction (test-data-independence): every rule table, clause,
and registry row here is synthetic (``t_``-prefixed keys authored inline),
except the shipped-rulebook assertions at the bottom, which are structural
only — rule count, group count, and ``SkillDef.kind`` checks — and never name
a shipped catalog identifier. Behavior is proved with synthetic rules; the
only shipped-content assertion is that the shipped table loads cleanly.

Traceability: the seven cross-lineage-unlock requirement IDs below are bound
with ``@covers_requirement`` on the test methods whose assertions establish
each requirement. They enter the main-spec index when the change's delta
syncs into ``openspec/specs/`` (see docs/development/spec-test-traceability.md);
the canonical IDs (``normalize_requirement_name`` of the delta titles,
verified with ``tools.spec_traceability list`` format) are:

- cross-lineage-unlock::the-unlock-table-declares-rules-of-and-ed-clauses-and-ownership-grants
- cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups
- cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire
- cross-lineage-unlock::a-granted-key-is-never-a-condition-source
- cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic
- cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else
- cross-lineage-unlock::the-shipped-table-loads-without-violating-any-validation-rule

At sync/archive time, run ``python -m tools.spec_traceability list`` and add
the decorators onto the test methods below whose assertions establish each
requirement.
"""

import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement

from world.rules import cross_lineage_unlock
from world.rules.cross_lineage_unlock import (
    CrossLineageUnlockRule,
    UnlockClause,
    clause_satisfied,
    evaluate_cross_lineage_unlocks,
    grant_owned_skill,
    load_rules,
)
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    skill_proficiency_level,
)
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec


def _skill(
    key: str,
    kind: SkillKind = SkillKind.ACTIVE,
    category: SkillCategory = SkillCategory.UTILITY,
    group: str | None = None,
) -> SkillDef:
    """One minimal valid registry-shaped synthetic skill row."""
    return SkillDef(
        key=key,
        label=f"測試技能{key}",
        description=f"cross-lineage fixture {key}",
        kind=kind,
        target_spec=TargetSpec.NONE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=category,
        group=group,
    )


# --- synthetic registry and clause vocabulary ---------------------------------

# Two same-group spell rows plus a second group, an unrelated martial row, an
# ACTIVE drill, and two grantable passives. No key exists in any shipped
# catalog.
_REGISTRY = {
    "t_fire_spark": _skill(
        "t_fire_spark", category=SkillCategory.ELEMENTAL_MAGIC, group="t_fire"
    ),
    "t_fire_veil": _skill(
        "t_fire_veil", category=SkillCategory.ELEMENTAL_MAGIC, group="t_fire"
    ),
    "t_frost_bite": _skill(
        "t_frost_bite", category=SkillCategory.ELEMENTAL_MAGIC, group="t_frost"
    ),
    "t_blade_drill": _skill("t_blade_drill"),
    "t_grant_passive": _skill(
        "t_grant_passive",
        kind=SkillKind.PASSIVE,
        category=SkillCategory.ENHANCEMENT,
    ),
    "t_grant_passive_b": _skill(
        "t_grant_passive_b",
        kind=SkillKind.PASSIVE,
        category=SkillCategory.ENHANCEMENT,
    ),
    "t_mastery": _skill(
        "t_mastery",
        kind=SkillKind.PASSIVE,
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="t_fire",
    ),
}


def _cap(_key: str) -> int:
    """Every synthetic node caps at 3 for reachability validation."""
    return 3


def _rule(
    rule_id: str = "t_rule",
    grants: tuple[str, ...] = ("t_grant_passive",),
    requires: list[dict] | None = None,
) -> dict:
    """One raw YAML-shaped rule; the default clause samples the drill."""
    if requires is None:
        requires = [{"scope": {"keys": ["t_blade_drill"]}, "min_level": 1}]
    return {"id": rule_id, "grants": list(grants), "requires": requires}


def _stub(
    proficiency: dict[str, float] | None = None,
    owned: dict[str, list[str]] | None = None,
) -> SimpleNamespace:
    """A pure stub entity the evaluator and progression queries accept."""
    db_skills = dict(owned if owned is not None else {"active": [], "passive": []})
    db = SimpleNamespace(
        skill_proficiency=dict(proficiency or {}),
        skills=db_skills,
        affinity_elements=[],
    )
    entity = SimpleNamespace(race=None, pk=None, key="stub", db=db)

    def _owned_keys() -> set[str]:
        return set(entity.db.skills.get("active", [])) | set(
            entity.db.skills.get("passive", [])
        )

    entity.skills = SimpleNamespace(owned_keys=_owned_keys)
    return entity


class LoaderValidationTests(unittest.TestCase):
    """One fail-closed rejection branch per test (spec requirement 3)."""

    def _loads(self, raw_rules, registry=None):
        return load_rules(raw_rules, registry=registry or _REGISTRY, cap=_cap)

    @covers_requirement("cross-lineage-unlock::the-unlock-table-declares-rules-of-and-ed-clauses-and-ownership-grants")
    def test_duplicate_rule_ids_fail_naming_the_id(self):
        with self.assertRaises(ValueError) as caught:
            self._loads([_rule("t_dup"), _rule("t_dup")])
        self.assertIn("t_dup", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_empty_rule_id_fails_naming_the_entry(self):
        with self.assertRaises(ValueError) as caught:
            self._loads([{"id": "", "grants": ["t_grant_passive"], "requires": []}])
        self.assertIn("#0", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_non_string_rule_id_fails(self):
        with self.assertRaises(ValueError):
            self._loads([{"id": 7, "grants": [], "requires": []}])

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_non_mapping_rule_entry_fails(self):
        with self.assertRaises(ValueError) as caught:
            self._loads(["t_not_a_rule"])
        self.assertIn("#0", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_empty_grants_fails_naming_the_rule(self):
        with self.assertRaises(ValueError) as caught:
            self._loads([_rule(grants=())])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_missing_grants_fails(self):
        raw = {"id": "t_rule", "requires": [{"scope": {"keys": ["t_blade_drill"]}, "min_level": 1}]}
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_empty_requires_fails_naming_the_rule(self):
        with self.assertRaises(ValueError) as caught:
            self._loads([{"id": "t_rule", "grants": ["t_grant_passive"], "requires": []}])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_grant_naming_an_unknown_key_fails_with_key_and_rule(self):
        with self.assertRaises(ValueError) as caught:
            self._loads([_rule(grants=("t_no_such_skill",))])
        message = str(caught.exception)
        self.assertIn("t_rule", message)
        self.assertIn("t_no_such_skill", message)

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_scope_key_unknown_to_registry_fails_with_key_and_rule(self):
        raw = _rule(requires=[{"scope": {"keys": ["t_no_such_skill"]}, "min_level": 1}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        message = str(caught.exception)
        self.assertIn("t_rule", message)
        self.assertIn("t_no_such_skill", message)

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_empty_keys_scope_selects_no_nodes(self):
        raw = _rule(requires=[{"scope": {"keys": []}, "min_level": 1}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_unreachable_min_level_fails_with_threshold(self):
        # Every synthetic node caps at 3 (_cap): min_level 5 can never fire.
        raw = _rule(requires=[{"scope": {"keys": ["t_blade_drill"]}, "min_level": 5}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        message = str(caught.exception)
        self.assertIn("t_rule", message)
        self.assertIn("min_level 5", message)

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_clause_demanding_more_groups_than_can_qualify_fails(self):
        raw = _rule(
            requires=[
                {
                    "scope": {"keys": ["t_fire_spark", "t_frost_bite"]},
                    "min_level": 1,
                    "distinct_groups": 3,
                }
            ]
        )
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_explicit_keys_scope_naming_a_passive_node_fails(self):
        raw = _rule(requires=[{"scope": {"keys": ["t_mastery"]}, "min_level": 1}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        message = str(caught.exception)
        self.assertIn("t_rule", message)
        self.assertIn("t_mastery", message)

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_non_positive_min_level_and_distinct_groups_fail(self):
        for field in ("min_level", "distinct_groups"):
            for bad in (0, -1, True, 1.5, "3"):
                with self.subTest(field=field, bad=bad):
                    clause = {
                        "scope": {"keys": ["t_blade_drill"]},
                        "min_level": 1,
                    }
                    clause[field] = bad
                    with self.assertRaises(ValueError) as caught:
                        self._loads([_rule(requires=[clause])])
                    self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_scope_declaring_neither_nor_both_forms_fails(self):
        for scope in ({}, {"category": "utility", "keys": ["t_blade_drill"]}):
            with self.subTest(scope=scope):
                raw = _rule(
                    requires=[{"scope": scope, "min_level": 1}]
                )
                with self.assertRaises(ValueError) as caught:
                    self._loads([raw])
                self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_declarative_scope_over_unknown_category_fails(self):
        raw = _rule(requires=[{"scope": {"category": "t_no_category"}, "min_level": 1}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw])
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_declarative_scope_with_no_active_members_fails(self):
        # Every row in this category is PASSIVE: no node can hold proficiency.
        registry = {"t_only_passive": _skill("t_only_passive", kind=SkillKind.PASSIVE)}
        raw = _rule(requires=[{"scope": {"category": "utility"}, "min_level": 1}])
        with self.assertRaises(ValueError) as caught:
            self._loads([raw], registry=registry)
        self.assertIn("t_rule", str(caught.exception))

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_declarative_mixed_kind_category_silently_omits_passive_members(self):
        registry = {
            **_REGISTRY,
            "t_mixed_active": _skill("t_mixed_active", group="t_mixed"),
            "t_mixed_passive": _skill(
                "t_mixed_passive", kind=SkillKind.PASSIVE, group="t_mixed"
            ),
        }
        raw = _rule(
            requires=[
                {
                    "scope": {"category": "utility", "group": "t_mixed"},
                    "min_level": 1,
                }
            ]
        )
        rulebook = load_rules([raw], registry=registry, cap=_cap)
        group = rulebook.rules[0].requires[0].groups[0]
        self.assertEqual(group, ("t_mixed_active",))
        self.assertNotIn("t_mixed_passive", group)

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_declarative_scope_partitions_by_group_field(self):
        raw = _rule(
            requires=[
                {
                    "scope": {"category": "elemental_magic"},
                    "min_level": 1,
                    "distinct_groups": 2,
                }
            ]
        )
        rulebook = self._loads([raw])
        groups = rulebook.rules[0].requires[0].groups
        self.assertEqual(len(groups), 2)
        self.assertEqual({group[0] for group in groups}, {"t_fire_spark", "t_frost_bite"})

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_narrowed_declarative_scope_forms_one_group(self):
        raw = _rule(
            requires=[
                {
                    "scope": {"category": "elemental_magic", "group": "t_fire"},
                    "min_level": 1,
                    "distinct_groups": 1,
                }
            ]
        )
        rulebook = self._loads([raw])
        groups = rulebook.rules[0].requires[0].groups
        self.assertEqual(len(groups), 1)
        self.assertEqual(frozenset(groups[0]), {"t_fire_spark", "t_fire_veil"})


class NoCycleValidationTests(unittest.TestCase):
    """A granted key is never a condition source (spec requirement 4)."""

    @covers_requirement("cross-lineage-unlock::a-granted-key-is-never-a-condition-source")
    def test_grant_fed_into_another_rules_scope_fails_naming_both_rules(self):
        # Rule A grants the key rule B samples as a condition source.
        # A's own requires samples the drill only, so the overlap it creates
        # is exclusively with B's scope.
        raw_rules = [
            _rule("t_granter", grants=("t_fire_spark",)),
            _rule(
                "t_sampler",
                grants=("t_grant_passive",),
                requires=[{"scope": {"keys": ["t_fire_spark"]}, "min_level": 1}],
            ),
        ]
        with self.assertRaises(ValueError) as caught:
            load_rules(raw_rules, registry=_REGISTRY, cap=_cap)
        message = str(caught.exception)
        self.assertIn("t_granter", message)
        self.assertIn("t_sampler", message)
        self.assertIn("t_fire_spark", message)

    @covers_requirement("cross-lineage-unlock::a-granted-key-is-never-a-condition-source")
    def test_self_referential_rule_fails_naming_its_id(self):
        raw = _rule("t_selfish", grants=("t_blade_drill",))
        with self.assertRaises(ValueError) as caught:
            load_rules([raw], registry=_REGISTRY, cap=_cap)
        message = str(caught.exception)
        self.assertIn("t_selfish", message)
        self.assertIn("t_blade_drill", message)


class ReverseIndexTests(unittest.TestCase):
    """The skill_key -> rule ids index (design D4)."""

    def test_key_sampled_by_two_rules_resolves_to_both(self):
        raw_rules = [_rule("t_first"), _rule("t_second")]
        rulebook = load_rules(raw_rules, registry=_REGISTRY, cap=_cap)
        self.assertEqual(
            rulebook.reverse_index["t_blade_drill"], ("t_first", "t_second")
        )

    def test_key_sampled_by_none_resolves_to_empty(self):
        rulebook = load_rules([_rule()], registry=_REGISTRY, cap=_cap)
        self.assertEqual(rulebook.reverse_index.get("t_fire_spark", ()), ())

    def test_grants_are_not_indexed(self):
        rulebook = load_rules([_rule()], registry=_REGISTRY, cap=_cap)
        self.assertNotIn("t_grant_passive", rulebook.reverse_index)


class ClausePredicateTests(unittest.TestCase):
    """The distinct-qualifying-groups predicate (spec requirement 2)."""

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_two_same_group_nodes_fail_a_two_group_clause(self):
        clause = UnlockClause(
            min_level=5,
            distinct_groups=2,
            groups=(("t_fire_spark", "t_fire_veil"),),
            scope_desc="t_fire",
        )
        entity = _stub(
            proficiency={
                "t_fire_spark": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "t_fire_veil": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            }
        )
        self.assertFalse(clause_satisfied(entity, clause))

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_nodes_in_two_groups_satisfy_a_two_group_clause(self):
        clause = UnlockClause(
            min_level=5,
            distinct_groups=2,
            groups=(("t_fire_spark",), ("t_frost_bite",)),
            scope_desc="synthetic",
        )
        entity = _stub(
            proficiency={
                "t_fire_spark": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "t_frost_bite": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            }
        )
        self.assertTrue(clause_satisfied(entity, clause))

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_node_one_level_short_fails(self):
        clause = UnlockClause(
            min_level=5,
            distinct_groups=1,
            groups=(("t_fire_spark",),),
            scope_desc="synthetic",
        )
        entity = _stub(
            proficiency={"t_fire_spark": 4 * SKILL_PROFICIENCY_XP_PER_LEVEL}
        )
        self.assertFalse(clause_satisfied(entity, clause))

    @covers_requirement("cross-lineage-unlock::a-clause-is-satisfied-by-distinct-qualifying-groups")
    def test_one_node_at_threshold_qualifies_its_group(self):
        clause = UnlockClause(
            min_level=5,
            distinct_groups=1,
            groups=(("t_fire_spark", "t_fire_veil"),),
            scope_desc="synthetic",
        )
        entity = _stub(
            proficiency={
                "t_fire_veil": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL + 1
            }
        )
        self.assertTrue(clause_satisfied(entity, clause))


class GrantWriterTests(unittest.TestCase):
    """Ownership-only, monotonic, idempotent grants (spec requirement 5)."""

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_passive_grant_lands_in_the_passive_list(self):
        entity = _stub(owned={"active": ["t_blade_drill"], "passive": []})
        self.assertTrue(grant_owned_skill(entity, "t_grant_passive", _REGISTRY))
        self.assertEqual(entity.db.skills["active"], ["t_blade_drill"])
        self.assertEqual(entity.db.skills["passive"], ["t_grant_passive"])

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_active_grant_lands_in_the_active_list(self):
        entity = _stub(owned={"active": [], "passive": []})
        self.assertTrue(grant_owned_skill(entity, "t_fire_spark", _REGISTRY))
        self.assertEqual(entity.db.skills["active"], ["t_fire_spark"])
        self.assertEqual(entity.db.skills["passive"], [])

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_grant_is_idempotent_and_never_duplicates(self):
        entity = _stub(owned={"active": [], "passive": ["t_grant_passive"]})
        self.assertFalse(grant_owned_skill(entity, "t_grant_passive", _REGISTRY))
        self.assertEqual(entity.db.skills["passive"], ["t_grant_passive"])
        self.assertEqual(entity.db.skills, {"active": [], "passive": ["t_grant_passive"]})

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_already_owned_key_is_a_no_op_like_a_preset_grant(self):
        # A character preset may ship with the granted key (lore constraint 6):
        # the rule's re-evaluation must leave the stored entry untouched.
        entity = _stub(owned={"active": [], "passive": ["t_grant_passive"]})
        self.assertFalse(grant_owned_skill(entity, "t_grant_passive", _REGISTRY))
        self.assertEqual(entity.db.skills["passive"], ["t_grant_passive"])

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_grant_never_writes_proficiency(self):
        entity = _stub(
            proficiency={"t_blade_drill": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL},
            owned={"active": ["t_blade_drill"], "passive": []},
        )
        self.assertTrue(grant_owned_skill(entity, "t_grant_passive", _REGISTRY))
        self.assertEqual(
            entity.db.skill_proficiency,
            {"t_blade_drill": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL},
        )
        # The granted node starts unpractised: derived level 0.
        self.assertEqual(skill_proficiency_level(entity, "t_grant_passive"), 0)

    @covers_requirement("cross-lineage-unlock::the-table-fails-closed-on-any-rule-that-can-never-fire")
    def test_unknown_key_is_rejected(self):
        entity = _stub()
        with self.assertRaises(ValueError):
            grant_owned_skill(entity, "t_no_such_skill", _REGISTRY)


class EvaluatorTests(unittest.TestCase):
    """Reverse-indexed, AND-clause, monotonic evaluation (requirements 1-5)."""

    @covers_requirement(
        "cross-lineage-unlock::the-unlock-table-declares-rules-of-and-ed-clauses-and-ownership-grants",
        "cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic",
    )
    def test_satisfied_rule_grants_every_key_it_names(self):
        rulebook = load_rules(
            [{"id": "t_dual", "grants": ["t_grant_passive", "t_grant_passive_b"], "requires": [
                {"scope": {"keys": ["t_blade_drill"]}, "min_level": 1}
            ]}],
            registry=_REGISTRY,
            cap=_cap,
        )
        entity = _stub(
            proficiency={"t_blade_drill": SKILL_PROFICIENCY_XP_PER_LEVEL},
            owned={"active": ["t_blade_drill"], "passive": []},
        )
        newly = evaluate_cross_lineage_unlocks(entity, "t_blade_drill", rulebook)
        self.assertEqual(newly, ["t_grant_passive", "t_grant_passive_b"])
        self.assertEqual(
            entity.db.skills,
            {
                "active": ["t_blade_drill"],
                "passive": ["t_grant_passive", "t_grant_passive_b"],
            },
        )

    @covers_requirement("cross-lineage-unlock::the-unlock-table-declares-rules-of-and-ed-clauses-and-ownership-grants")
    def test_rule_with_one_unsatisfied_clause_grants_nothing(self):
        rulebook = load_rules(
            [{"id": "t_two_clause", "grants": ["t_grant_passive"], "requires": [
                {"scope": {"keys": ["t_blade_drill"]}, "min_level": 1},
                {"scope": {"keys": ["t_fire_spark"]}, "min_level": 3},
            ]}],
            registry=_REGISTRY,
            cap=_cap,
        )
        # First clause satisfied (level 1), second not (level 2 < 3).
        entity = _stub(
            proficiency={
                "t_blade_drill": 1 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "t_fire_spark": 2 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            },
            owned={"active": ["t_blade_drill", "t_fire_spark"], "passive": []},
        )
        newly = evaluate_cross_lineage_unlocks(entity, "t_blade_drill", rulebook)
        self.assertEqual(newly, [])
        self.assertEqual(entity.db.skills["passive"], [])

    def test_unrelated_award_evaluates_nothing(self):
        rulebook = load_rules([_rule()], registry=_REGISTRY, cap=_cap)
        entity = _stub(
            proficiency={"t_fire_spark": 1 * SKILL_PROFICIENCY_XP_PER_LEVEL},
            owned={"active": ["t_fire_spark"], "passive": []},
        )
        newly = evaluate_cross_lineage_unlocks(entity, "t_fire_spark", rulebook)
        self.assertEqual(newly, [])
        self.assertEqual(entity.db.skills["passive"], [])

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_regranting_already_owned_grants_returns_empty_and_writes_nothing(self):
        rulebook = load_rules([_rule()], registry=_REGISTRY, cap=_cap)
        entity = _stub(
            proficiency={"t_blade_drill": 1 * SKILL_PROFICIENCY_XP_PER_LEVEL},
            owned={"active": ["t_blade_drill"], "passive": ["t_grant_passive"]},
        )
        before = dict(entity.db.skills)
        newly = evaluate_cross_lineage_unlocks(entity, "t_blade_drill", rulebook)
        self.assertEqual(newly, [])
        self.assertEqual(entity.db.skills, before)

    @covers_requirement("cross-lineage-unlock::grants-convey-ownership-only-and-are-monotonic")
    def test_evaluation_never_removes_a_granted_key(self):
        # A rule that stops being satisfied revokes nothing.
        rulebook = load_rules([_rule()], registry=_REGISTRY, cap=_cap)
        entity = _stub(
            proficiency={},  # below the clause's min_level 1
            owned={"active": [], "passive": ["t_grant_passive"]},
        )
        evaluate_cross_lineage_unlocks(entity, "t_blade_drill", rulebook)
        self.assertEqual(entity.db.skills["passive"], ["t_grant_passive"])


class ShippedRulebookTests(unittest.TestCase):
    """The shipped table loads and is structural (spec requirement 7).

    Structural only: these assertions never name a shipped catalog identifier
    — no key literal, no label, no count beyond the table's own shape.
    """

    @covers_requirement("cross-lineage-unlock::the-shipped-table-loads-without-violating-any-validation-rule")
    def test_shipped_table_loads_three_unique_rules_with_clauses_and_grants(self):
        rules = cross_lineage_unlock.RULEBOOK.rules
        self.assertEqual(len(rules), 3)
        self.assertEqual(len({rule.id for rule in rules}), len(rules))
        for rule in rules:
            self.assertTrue(rule.requires)
            self.assertTrue(rule.grants)
            self.assertIsInstance(rule, CrossLineageUnlockRule)

    @covers_requirement("cross-lineage-unlock::the-shipped-table-loads-without-violating-any-validation-rule")
    def test_declarative_elemental_scope_yields_eight_groups_without_passive_nodes(self):
        elemental_rules = [
            rule
            for rule in cross_lineage_unlock.RULEBOOK.rules
            if len(rule.requires[0].groups) == 8
        ]
        self.assertEqual(len(elemental_rules), 2)
        for rule in elemental_rules:
            for group in rule.requires[0].groups:
                for key in group:
                    self.assertNotEqual(
                        cross_lineage_unlock.RULEBOOK.registry[key].kind,
                        SkillKind.PASSIVE,
                    )
                self.assertTrue(group)


if __name__ == "__main__":
    unittest.main()