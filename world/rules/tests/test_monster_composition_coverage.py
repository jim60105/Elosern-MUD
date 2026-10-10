"""Data-contract test: authored-kit composition grouping and representative wiring contract

The composition signature of one variant is the ordered declaration of its kit
as the engine reads it: per effect occurrence, the effect family, the declared
audience and the occurrence index its hit dependency references. Variants that
deliver the same shape therefore group together under a key that names no
species, an addition that reuses a shape joins the existing group instead of
demanding its own battery, and each group's stable-key-ordered representative
has to be committed as real consumer evidence by the representative smoke that
declares it.

The derivation below is pure and local to this module: it reads the authored
declarations and never resolves, constructs or rolls anything itself.
"""

import ast
import pathlib
from collections.abc import Mapping
from typing import Any

import unittest

from tools.spec_traceability import covers_requirement

from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.skills.registry import SKILL_REGISTRY
from world.tests.synthetic_data import make_monster_variant, make_skill

TESTS_ROOT = pathlib.Path(__file__).resolve().parent
REPRESENTATIVE_DECLARATION = "REPRESENTATIVE_VARIANT"


# ---------------------------------------------------------------------------
# One composition signature: the ordered kit declaration, no species identity.
# ---------------------------------------------------------------------------


def effect_family(effect: str) -> str:
    """The declared effect family of one authored effect string."""
    return effect.split(":", 1)[0]


def variant_signature(
    variant: Any,
    skills: Mapping[str, Any],
) -> tuple[tuple[Any, ...], ...] | None:
    """One variant's delivered composition signature, or None without a kit.

    Each entry is ``(slot, family, audience, hit-dependency index)`` in
    authored order. A declared skill that carries no effect keeps its own
    entry keyed by the skill key, so a broken declaration is still grouped
    rather than silently vanishing.
    """
    entries: list[tuple[Any, ...]] = []
    for slot, keys in (
        ("active", variant.active_skill_keys),
        ("passive", variant.passive_skill_keys),
    ):
        for skill_key in keys:
            skill = skills.get(skill_key)
            effects = tuple(getattr(skill, "effects", ()) or ())
            policies = tuple(getattr(skill, "effect_policies", ()) or ())
            if not effects:
                entries.append((slot, skill_key, None, None))
                continue
            for index, effect in enumerate(effects):
                policy = policies[index] if index < len(policies) else None
                entries.append(
                    (
                        slot,
                        effect_family(effect),
                        str(getattr(policy, "audience", "") or ""),
                        getattr(policy, "requires_hit_from", None),
                    )
                )
    return tuple(entries) if entries else None


def composition_groups(
    variants: Mapping[str, Any],
    skills: Mapping[str, Any],
) -> dict[tuple[tuple[Any, ...], ...], tuple[str, ...]]:
    """Group every kit-delivering variant by signature, keys sorted ascending."""
    groups: dict[tuple[tuple[Any, ...], ...], list[str]] = {}
    for key, variant in variants.items():
        signature = variant_signature(variant, skills)
        if signature is None:
            continue
        groups.setdefault(signature, []).append(key)
    return {signature: tuple(sorted(keys)) for signature, keys in groups.items()}


def representatives(
    variants: Mapping[str, Any],
    skills: Mapping[str, Any],
) -> dict[tuple[tuple[Any, ...], ...], str]:
    """One stable-key-ordered representative (its group's sorted minimum)."""
    return {
        signature: keys[0]
        for signature, keys in composition_groups(variants, skills).items()
    }


# ---------------------------------------------------------------------------
# Committed evidence discovery: every test module that declares a
# representative, wherever it lives under this package's test tree.
# ---------------------------------------------------------------------------


def _module_tree(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _declared_representatives() -> dict[str, pathlib.Path]:
    """Map every declared representative variant key to its test module.

    Discovery is driven by the declaration alone - never by a filename
    pattern or a hand-written module list - so a new group whose representative
    nobody committed cannot hide behind a module name.
    """
    found: dict[str, pathlib.Path] = {}
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        if path.resolve() == pathlib.Path(__file__).resolve():
            continue
        for node in _module_tree(path).body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id != REPRESENTATIVE_DECLARATION:
                continue
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                found[node.value.value] = path
    return found


class CompositionGroupingTests(unittest.TestCase):
    """Requirement: grouping is derived from declarations, never a roster."""

    @covers_requirement(
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence"
    )
    def test_a_reused_composition_joins_its_existing_group(self):
        """Scenario: Shared reuse and Data edit, over arbitrary synthetic keys."""
        transfer = make_skill(
            "t_edge_drain",
            effects=["damage:fire:physical", "gauge_transfer:mp:drain:fixed:5"],
        )
        guard = make_skill(
            "t_edge_guard",
            effects=["damage:fire:physical", "self_buff_apply:t_edge_shell"],
        )
        skills = {transfer.key: transfer, guard.key: guard}

        def variant(key: str, skill_key: str) -> Any:
            return make_monster_variant(key, active_skill_keys=(skill_key,))

        first = {
            "t_edge_alpha": variant("t_edge_alpha", transfer.key),
            "t_edge_beta": variant("t_edge_beta", transfer.key),
            "t_edge_gamma": variant("t_edge_gamma", guard.key),
        }
        groups = composition_groups(first, skills)
        self.assertEqual(len(groups), 2)
        chosen = representatives(first, skills)
        self.assertEqual(sorted(chosen.values()), ["t_edge_alpha", "t_edge_gamma"])

        # A later declaration reusing the transfer shape joins the existing
        # group under the same signature: no new group, no new battery, and the
        # stable-key order still names the representative.
        extended = dict(first)
        extended["t_edge_alphaa"] = variant("t_edge_alphaa", transfer.key)
        self.assertEqual(composition_groups(extended, skills).keys(), groups.keys())
        self.assertEqual(representatives(extended, skills), chosen)
        self.assertEqual(
            set(representatives(extended, skills).values()) & set(MONSTER_VARIANT_REGISTRY),
            set(),
        )

    @covers_requirement(
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence"
    )
    def test_every_shipped_variant_delivers_exactly_the_grouped_composition(self):
        groups = composition_groups(MONSTER_VARIANT_REGISTRY, SKILL_REGISTRY)
        self.assertTrue(groups)
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                declares_kit = bool(
                    variant.active_skill_keys or variant.passive_skill_keys
                )
                self.assertEqual(
                    variant_signature(variant, SKILL_REGISTRY) is not None,
                    declares_kit,
                )
        for signature, keys in groups.items():
            with self.subTest(signature=signature):
                self.assertTrue(keys)
                self.assertEqual(list(keys), sorted(keys))
                self.assertEqual(
                    len(keys),
                    sum(
                        1
                        for key in keys
                        if variant_signature(MONSTER_VARIANT_REGISTRY[key], SKILL_REGISTRY)
                        == signature
                    ),
                )


class RepresentativeCoverageTests(unittest.TestCase):
    """Requirement: real consumer evidence for every discovered group."""

    @covers_requirement(
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence"
    )
    def test_every_group_has_exactly_its_representative_committed(self):
        chosen = representatives(MONSTER_VARIANT_REGISTRY, SKILL_REGISTRY)
        declared = _declared_representatives()
        self.assertTrue(chosen)

        uncovered = {
            signature: key for signature, key in chosen.items() if key not in declared
        }
        self.assertEqual(
            uncovered,
            {},
            "delivered composition groups without committed representative "
            f"evidence: {uncovered}",
        )
        stray = {
            key: path.name
            for key, path in declared.items()
            if key not in set(chosen.values())
        }
        self.assertEqual(
            stray,
            {},
            f"declared representatives that are no group's representative: {stray}",
        )

    @covers_requirement(
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence"
    )
    def test_each_representative_smoke_executes_its_declared_variant(self):
        declared = _declared_representatives()
        self.assertTrue(declared)
        for variant_key, path in sorted(declared.items()):
            with self.subTest(module=path.name):
                tree = _module_tree(path)
                calls = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "construct_species_individual"
                ]
                self.assertTrue(calls, "the smoke constructs no individual")
                for call in calls:
                    arguments = [
                        keyword.value
                        for keyword in call.keywords
                        if keyword.arg == "variant_key"
                    ] or call.args[1:2]
                    self.assertTrue(
                        any(
                            isinstance(argument, ast.Name)
                            and argument.id == REPRESENTATIVE_DECLARATION
                            for argument in arguments
                        ),
                        "construct_species_individual must take the declared "
                        "representative, not a copied variant key",
                    )
                literals = {
                    node.value
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                # The declaration itself is the one name this module is
                # allowed to carry: any *other* shipped variant key literal
                # would be a second, stale copy of the choice.
                self.assertEqual(
                    (literals - {variant_key}) & set(MONSTER_VARIANT_REGISTRY),
                    set(),
                    "a representative smoke names a shipped variant key literally",
                )
