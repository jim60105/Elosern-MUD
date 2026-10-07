"""Synthetic tests of the registry reference model (gm-portal-s4-world-data §3).

Small fake registries exercise ``ref``/``ref_many`` metadata, nullable single
references, nested dataclasses and collections, frozenset ordering, the
``DanglingReference`` shape, declaration validation (absent target registry,
inverse collisions versus repeated instances of one declaration) and the
process cache. No shipped registry is read here.
"""

from __future__ import annotations

import dataclasses
import unittest
from dataclasses import dataclass, field
from types import MappingProxyType
from unittest import mock

from tools.spec_traceability import covers_requirement
from world.lore import registry_index
from world.lore.registry_index import (
    DanglingReference,
    RegistrySpec,
    build_reference_index,
    check_references,
    declaration_errors,
    entry_references,
)
from world.lore.registry_refs import RefSpec, ref, ref_many, ref_spec_of


@dataclass(frozen=True)
class Den:
    key: str
    label: str


@dataclass(frozen=True)
class Step:
    index: int
    den_key: str | None = field(default=None, metadata=ref("t_dens", inverse="steps", nullable=True))


@dataclass(frozen=True)
class Beast:
    key: str
    home_key: str = field(metadata=ref("t_dens", inverse="residents"))
    haunt_keys: tuple[str, ...] = field(default=(), metadata=ref_many("t_dens", inverse="haunters"))
    lair_keys: frozenset[str] = field(default=frozenset(), metadata=ref_many("t_dens", inverse="lairs"))
    steps: tuple[Step, ...] = ()
    notes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Rival:
    key: str
    # Reuses the inverse name ``residents`` from a different declaration.
    den_key: str = field(metadata=ref("t_dens", inverse="residents"))


@dataclass(frozen=True)
class Stray:
    key: str
    target: str = field(metadata=ref("t_absent", inverse="strays"))


@dataclass(frozen=True)
class Burrow:
    key: str
    # Never filled by any fixture entry: only the type hints reveal it.
    step: Step | None = None


def _spec(name: str, rows: dict) -> RegistrySpec:
    view = MappingProxyType(rows)
    return RegistrySpec(name, name, "世界", lambda: view, f"fixtures/{name}.py")


DENS = {
    "t_cave": Den("t_cave", "洞窟"),
    "t_glade": Den("t_glade", "林間空地"),
}
BEASTS = {
    "t_wolf": Beast(
        "t_wolf",
        home_key="t_cave",
        haunt_keys=("t_glade", "t_cave"),
        lair_keys=frozenset({"t_glade", "t_cave"}),
        steps=(Step(0), Step(1, den_key="t_glade")),
        notes={"inner": (Step(2, den_key="t_cave"),)},
    ),
    "t_bear": Beast("t_bear", home_key="t_cave"),
}


def _index(*extra: RegistrySpec) -> tuple[RegistrySpec, ...]:
    return (_spec("t_dens", DENS), _spec("t_beasts", BEASTS), *extra)


class RefMetadataTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::declarative-reference-traversal")
    def test_ref_and_ref_many_produce_read_only_field_metadata(self):
        single = ref("t_dens", inverse="residents")
        many = ref_many("t_dens", inverse="haunters")
        nullable = ref("t_dens", inverse="steps", nullable=True)
        self.assertEqual(ref_spec_of(dataclasses.fields(Beast)[1]), RefSpec("t_dens", "residents"))
        self.assertEqual(single["registry_ref"], RefSpec("t_dens", "residents"))
        self.assertEqual(many["registry_ref"], RefSpec("t_dens", "haunters", many=True))
        self.assertTrue(nullable["registry_ref"].nullable)
        with self.assertRaises(TypeError):
            single["registry_ref"] = None  # type: ignore[index]

    @covers_requirement("authored-registry-references::declarative-reference-traversal")
    def test_declarations_change_no_type_default_or_value(self):
        fields = {item.name: item for item in dataclasses.fields(Beast)}
        self.assertIs(fields["home_key"].default, dataclasses.MISSING)
        self.assertEqual(fields["haunt_keys"].default, ())
        self.assertEqual(fields["home_key"].type, "str")
        beast = Beast("t_fox", home_key="t_glade")
        self.assertEqual(beast.home_key, "t_glade")
        self.assertEqual(beast.haunt_keys, ())
        with self.assertRaises(TypeError):
            Beast("t_fox")  # the declared single reference stays required

    def test_undeclared_field_has_no_spec(self):
        self.assertIsNone(ref_spec_of(dataclasses.fields(Den)[0]))


class ReferenceTraversalTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::declarative-reference-traversal")
    def test_single_many_nullable_nested_and_frozenset_paths(self):
        found, declared = entry_references(BEASTS["t_wolf"])
        paths = [(path, spec.inverse, key) for path, spec, key in found]
        self.assertEqual(
            paths,
            [
                ("home_key", "residents", "t_cave"),
                ("haunt_keys[0]", "haunters", "t_glade"),
                ("haunt_keys[1]", "haunters", "t_cave"),
                # frozenset members are walked in sorted order
                ("lair_keys[0]", "lairs", "t_cave"),
                ("lair_keys[1]", "lairs", "t_glade"),
                # Step(0) has a nullable None: no edge
                ("steps[1].den_key", "steps", "t_glade"),
                ("notes.inner[0].den_key", "steps", "t_cave"),
            ],
        )
        self.assertEqual(
            {(item.owner.rsplit(".", 1)[-1], item.field) for item in declared},
            {("Beast", "home_key"), ("Beast", "haunt_keys"), ("Beast", "lair_keys"), ("Step", "den_key")},
        )

    @covers_requirement("authored-registry-references::declarative-reference-traversal")
    def test_traversal_preserves_every_input_value(self):
        before = dataclasses.asdict(BEASTS["t_wolf"])
        entry_references(BEASTS["t_wolf"])
        self.assertEqual(dataclasses.asdict(BEASTS["t_wolf"]), before)

    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_forward_and_inverse_maps_agree(self):
        index = build_reference_index(_index())
        forward = index.forward[("t_beasts", "t_wolf")]
        self.assertEqual(len(forward), 7)
        cave = index.inverse[("t_dens", "t_cave")]
        self.assertEqual(sorted(cave), ["haunters", "lairs", "residents", "steps"])
        self.assertEqual(
            sorted((ref.key, ref.field_path) for ref in cave["residents"]),
            [("t_bear", "home_key"), ("t_wolf", "home_key")],
        )
        for references in index.forward.values():
            for reference in references:
                group = index.inverse[(reference.target_registry, reference.target_key)][reference.inverse]
                self.assertIn(reference, group)
        self.assertNotIn(("t_beasts", "t_bear"), index.inverse)


class IntegrityTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_missing_target_keys_are_reported_with_five_fields(self):
        beasts = {"t_ghost": Beast("t_ghost", home_key="t_nowhere", steps=(Step(0, den_key="t_void"),))}
        dangling = check_references((_spec("t_dens", DENS), _spec("t_beasts", beasts)))
        self.assertEqual(
            dangling,
            [
                DanglingReference("t_beasts", "t_ghost", "home_key", "t_dens", "t_nowhere"),
                DanglingReference("t_beasts", "t_ghost", "steps[0].den_key", "t_dens", "t_void"),
            ],
        )
        self.assertEqual(
            [item.name for item in dataclasses.fields(DanglingReference)],
            ["registry", "key", "field_path", "target_registry", "missing_key"],
        )

    def test_shipped_style_index_is_clean(self):
        self.assertEqual(check_references(_index()), [])
        # Two beasts reuse each declaration; repeated instances never collide.
        self.assertEqual(declaration_errors(_index()), [])

    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_declarations_without_instances_are_found_through_type_hints(self):
        index = build_reference_index((_spec("t_dens", DENS), _spec("t_burrows", {"t_hole": Burrow("t_hole")})))
        self.assertEqual(index.forward, {})
        self.assertEqual(
            {(item.owner.rsplit(".", 1)[-1], item.field, item.inverse) for item in index.declarations},
            {("Step", "den_key", "steps")},
        )

    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_absent_target_registry_and_inverse_collision_are_rejected(self):
        index = _index(
            _spec("t_rivals", {"t_lynx": Rival("t_lynx", den_key="t_cave")}),
            _spec("t_strays", {"t_cat": Stray("t_cat", target="t_cave")}),
        )
        errors = declaration_errors(index)
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any("unindexed registry 't_absent'" in error for error in errors))
        self.assertTrue(any("reuses inverse 'residents'" in error for error in errors))
        dangling = check_references(index)
        self.assertEqual(
            dangling,
            [DanglingReference("t_strays", "t_cat", "target", "t_absent", "t_cave")],
        )


class CacheTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_index_is_built_once_per_index_tuple(self):
        index = _index()
        registry_index._cached.cache_clear()
        with mock.patch.object(registry_index, "_build", wraps=registry_index._build) as build:
            first = build_reference_index(index)
            second = build_reference_index(index)
            other = build_reference_index(_index(_spec("t_more", {})))
        self.assertIs(first, second)
        self.assertIsNot(first, other)
        self.assertEqual(build.call_count, 2)
        registry_index._cached.cache_clear()

    def test_default_index_reads_the_module_tuple(self):
        index = _index()
        with mock.patch.object(registry_index, "REGISTRY_INDEX", index):
            self.assertIs(build_reference_index(), build_reference_index(index))
        registry_index._cached.cache_clear()


if __name__ == "__main__":
    unittest.main()
