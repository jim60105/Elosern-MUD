"""Tests for the typed official content reference and its provenance rules.

Pure ``unittest.TestCase`` wherever it can be: the resolver performs no I/O,
reads exactly two entity attributes, and consults the live lore registries, so
the grammar, boundary, inference-trap, diagnostic, and monster contracts here
run without a database or a catalog snapshot. Synthetic registries are injected
through the module's own registry bindings (string-named ``patch.object``,
never a literal catalog symbol — the test-data gate) and the diagnostic dedupe
seam is the module-private reported-key set. Exactly one test imports the
catalog module, to pin that the resolver answers from the registries alone.

Deferred annotations: the new ``official-content-provenance`` requirement ids
exist only in this change's delta spec, and ``tools.spec_traceability`` indexes
main specs only, so this module carries no ``covers_requirement`` annotation
yet. The archive step adds them in the commit that syncs the spec into
``openspec/specs/`` — the ``official-artwork-catalog`` precedent.
"""

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from world.art import official_refs
from world.art.gallery_fallback import (
    NPC_TIER_PROVENANCE_ATTRIBUTE as FALLBACK_TIER_ATTRIBUTE,
    PRESET_PROVENANCE_ATTRIBUTE as FALLBACK_PRESET_ATTRIBUTE,
)
from world.art.official_refs import (
    MAX_UNRESOLVED_DIAGNOSTICS,
    NPC_PROFILE_PROVENANCE_ATTRIBUTE,
    OFFICIAL_CONTENT_KINDS,
    OFFICIAL_KIND_MONSTER,
    OFFICIAL_KIND_NPC,
    OFFICIAL_KIND_PRESET,
    PRESET_PROVENANCE_ATTRIBUTE,
    UNRESOLVED_REFERENCE_EVENT,
    OfficialContentReference,
    OfficialContentReferenceError,
    official_content_reference,
    official_content_reference_for_entity,
    official_content_reference_for_preset,
    registered_content_key,
)
from world.art.subjects import is_valid_subject_key

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "world" / "art" / "official_refs.py"

# The production module roots the zero-producer scan walks, derived from the
# filesystem so a hand-maintained file list can never rot.
PRODUCTION_ROOTS = ("commands", "server", "typeclasses", "world", "web/webclient")

# The exact direct project-import boundary the leaf module is allowed: the
# shared stable-key predicate, the two immutable lore registries, and the
# observability facade. Nothing else — no catalog module, no rules layer, no
# typeclass, no transport.
EXPECTED_PROJECT_IMPORTS = frozenset(
    {
        "world.art.subjects",
        "world.lore.npc_profiles",
        "world.lore.player_presets",
        "world.observability",
    }
)

# One-hop dependency sources the back-import check parses: everything the leaf
# module's direct dependencies are made of.
DEPENDENCY_SOURCES = (
    "world/art/subjects.py",
    "world/lore/npc_profiles",
    "world/lore/player_presets",
    "world/observability",
)

# Synthetic content keys. Never a shipped catalog key: the registries are
# injected with these, so every resolution here is synthetic.
_SYNTH_PRESET = "t_synth_preset"
_SYNTH_PROFILE = "t_synth_profile"
_SYNTH_TIER = "t_synth_tier"


class _RecordingEntity:
    """A stand-in entity recording exactly which attribute names were read."""

    def __init__(self, **attributes):
        self.pk = 7
        self.key = ""
        self.display_name = ""
        self._values = dict(attributes)
        self.read_keys: list[str] = []

    @property
    def attributes(self):
        return SimpleNamespace(get=self._read)

    def _read(self, key, **_kwargs):
        self.read_keys.append(key)
        return self._values.get(key)


def _production_module_paths():
    """Every non-test Python module under the production roots."""
    for root in PRODUCTION_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if "__pycache__" in relative:
                continue
            if "/tests/" in f"/{relative}" or path.name.startswith("test_"):
                continue
            yield path


def _imported_module_names(tree: ast.Module) -> set[str]:
    """Every module name a parsed module imports (absolute form)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def _unresolved_events(logged) -> list:
    """The bounded unresolved-reference events among a patched warn's calls."""
    return [
        call
        for call in logged.call_args_list
        if call.args and call.args[0] == UNRESOLVED_REFERENCE_EVENT
    ]


def _monster_reference_constructions(tree: ast.Module) -> list[str]:
    """Every monster-kind ``OfficialContentReference`` construction in a module.

    The zero-producer scan's whole body: a construction is a monster reference
    when any argument — positional or keyword — is the vocabulary's monster
    kind literal or the ``OFFICIAL_KIND_MONSTER`` name a future producer would
    reach for. Returned as ``(kind token, line)`` pairs for the report.
    """
    monster_kind = OFFICIAL_CONTENT_KINDS[0]
    monster_tokens = {"OFFICIAL_KIND_MONSTER"}
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name != "OfficialContentReference":
            continue
        arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
        for argument in arguments:
            if isinstance(argument, ast.Constant) and argument.value == monster_kind:
                found.append(f"literal:{argument.lineno}")
            elif isinstance(argument, (ast.Name, ast.Attribute)):
                token = getattr(argument, "id", None) or getattr(argument, "attr", None)
                if token in monster_tokens:
                    found.append(f"{token}:{argument.lineno}")
    return found


class ReferenceTypeTests(unittest.TestCase):
    """The frozen type: closed kind vocabulary, shared key grammar."""

    def test_the_vocabulary_is_exactly_the_three_kinds_in_layout_order(self):
        self.assertEqual(
            OFFICIAL_CONTENT_KINDS,
            (OFFICIAL_KIND_MONSTER, OFFICIAL_KIND_PRESET, OFFICIAL_KIND_NPC),
        )

    def test_a_reference_accepts_every_closed_kind_with_a_contract_key(self):
        for kind in OFFICIAL_CONTENT_KINDS:
            with self.subTest(kind=kind):
                reference = OfficialContentReference(kind, _SYNTH_PRESET)
                self.assertEqual(reference.kind, kind)
                self.assertEqual(reference.key, _SYNTH_PRESET)
                self.assertEqual(reference.identity(), f"{kind}/{_SYNTH_PRESET}")

    def test_a_reference_rejects_an_unknown_kind(self):
        with self.assertRaises(OfficialContentReferenceError):
            OfficialContentReference("t_not_a_kind", _SYNTH_PRESET)

    def test_a_reference_rejects_a_key_outside_the_shared_contract(self):
        over_long = "x" * 65
        over_bytes = "\U0001d54f" * 51  # 51 code points, 204 UTF-8 bytes
        for key in (
            "",
            None,
            7,
            "a/b",
            "a:b",
            "a|b",
            "a{b",
            "a}b",
            "a\x00b",
            over_long,
            over_bytes,
        ):
            with self.subTest(key=repr(key)):
                self.assertFalse(is_valid_subject_key(key))
                with self.assertRaises(OfficialContentReferenceError):
                    OfficialContentReference(OFFICIAL_KIND_PRESET, key)

    def test_a_reference_is_frozen(self):
        reference = OfficialContentReference(OFFICIAL_KIND_PRESET, _SYNTH_PRESET)
        with self.assertRaises(FrozenInstanceError):
            reference.key = _SYNTH_PROFILE

    def test_the_provenance_attribute_names_stay_separate(self):
        self.assertEqual(PRESET_PROVENANCE_ATTRIBUTE, FALLBACK_PRESET_ATTRIBUTE)
        self.assertNotEqual(NPC_PROFILE_PROVENANCE_ATTRIBUTE, FALLBACK_TIER_ATTRIBUTE)


class LeafBoundaryTests(unittest.TestCase):
    """The gallery_kinds discipline: a bounded, cycle-free import surface."""

    def test_the_module_imports_only_its_declared_boundary(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported = _imported_module_names(tree)
        project = {
            name
            for name in imported
            if name.split(".")[0] in ("world", "typeclasses", "commands", "server", "web")
        }
        self.assertEqual(project, EXPECTED_PROJECT_IMPORTS)
        self.assertEqual(
            [name for name in imported if name == "world.rules" or name.startswith("world.rules.")],
            [],
        )
        self.assertEqual(
            [name for name in imported if name == "typeclasses" or name.startswith("typeclasses.")],
            [],
        )

    def test_no_dependency_imports_the_module_back(self):
        # One-hop cycle guard: a cycle needs one of these modules (or a sibling
        # inside its package) to import the leaf back.
        for source in DEPENDENCY_SOURCES:
            base = REPO_ROOT / source
            paths = [base] if base.is_file() else sorted(base.rglob("*.py"))
            self.assertTrue(paths, f"dependency source {source!r} is missing")
            for path in paths:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                with self.subTest(module=path.relative_to(REPO_ROOT).as_posix()):
                    self.assertNotIn(
                        "world.art.official_refs", _imported_module_names(tree)
                    )


class ProvenanceResolutionTests(unittest.TestCase):
    """Provenance-derived resolution, inference traps, bounded diagnostics."""

    def setUp(self):
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    def test_a_registered_preset_key_resolves_from_provenance(self):
        entity = _RecordingEntity(**{PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})
        with patch.object(
            official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}
        ):
            reference = official_content_reference_for_entity(entity)
        self.assertEqual(
            reference, OfficialContentReference(OFFICIAL_KIND_PRESET, _SYNTH_PRESET)
        )
        # Nothing else changed on the entity: resolution is a pure read.
        self.assertEqual(entity._values, {PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})

    def test_a_registered_profile_key_resolves_as_an_npc_reference(self):
        entity = _RecordingEntity(**{NPC_PROFILE_PROVENANCE_ATTRIBUTE: _SYNTH_PROFILE})
        with patch.object(
            official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}
        ):
            reference = official_content_reference_for_entity(entity)
        self.assertEqual(
            reference, OfficialContentReference(OFFICIAL_KIND_NPC, _SYNTH_PROFILE)
        )

    def test_the_resolver_reads_exactly_the_two_provenance_attribute_names(self):
        preset_only = _RecordingEntity(**{PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})
        profile_only = _RecordingEntity(
            **{
                NPC_PROFILE_PROVENANCE_ATTRIBUTE: _SYNTH_PROFILE,
                "npc_tier_key": _SYNTH_TIER,
                "creation_preset_name": _SYNTH_PRESET,
            }
        )
        with (
            patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}),
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}),
        ):
            official_content_reference_for_entity(preset_only)
            official_content_reference_for_entity(profile_only)
        self.assertEqual(preset_only.read_keys, [PRESET_PROVENANCE_ATTRIBUTE])
        self.assertEqual(
            profile_only.read_keys,
            [PRESET_PROVENANCE_ATTRIBUTE, NPC_PROFILE_PROVENANCE_ATTRIBUTE],
        )

    def test_a_display_name_never_becomes_a_key(self):
        # The entity's display text equals a registered key, but it carries no
        # authored provenance: nothing resolves and nothing is logged.
        entity = _RecordingEntity()
        entity.key = _SYNTH_PRESET
        entity.display_name = _SYNTH_PROFILE
        with (
            patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}),
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            self.assertIsNone(official_content_reference_for_entity(entity))
        self.assertEqual(_unresolved_events(logged), [])

    def test_a_numeric_tier_never_selects_a_reference(self):
        entity = _RecordingEntity(npc_tier_key=_SYNTH_TIER)
        entity.display_name = _SYNTH_TIER
        with (
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_TIER: object()}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            self.assertIsNone(official_content_reference_for_entity(entity))
        self.assertNotIn("npc_tier_key", entity.read_keys)
        self.assertEqual(_unresolved_events(logged), [])

    def test_an_unregistered_key_resolves_nothing_and_logs_once(self):
        entity = _RecordingEntity(**{NPC_PROFILE_PROVENANCE_ATTRIBUTE: _SYNTH_PROFILE})
        with (
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            self.assertIsNone(official_content_reference_for_entity(entity))
            self.assertIsNone(official_content_reference_for_entity(entity))
        events = _unresolved_events(logged)
        self.assertEqual(len(events), 1)
        context = events[0].kwargs["context"]
        self.assertEqual(context["kind"], OFFICIAL_KIND_NPC)
        self.assertEqual(context["key"], _SYNTH_PROFILE)
        self.assertEqual(context["reason"], "unregistered_key")
        self.assertEqual(context["entity"], "7")

    def test_a_malformed_key_resolves_nothing_and_logs_once(self):
        for label, declared in {
            "forbidden_character": "t_synth/../escape",
            "non_text": 12,
        }.items():
            with self.subTest(case=label):
                official_refs._reported_unresolved.clear()
                entity = _RecordingEntity(**{NPC_PROFILE_PROVENANCE_ATTRIBUTE: declared})
                with (
                    patch.object(official_refs, "NPC_PROFILE_REGISTRY", {}),
                    patch.object(official_refs, "log_warn") as logged,
                ):
                    self.assertIsNone(official_content_reference_for_entity(entity))
                events = _unresolved_events(logged)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs["context"]["reason"], "malformed_key")

    def test_the_diagnostic_ceiling_bounds_distinct_keys(self):
        with (
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            for index in range(MAX_UNRESOLVED_DIAGNOSTICS + 2):
                entity = _RecordingEntity(
                    **{NPC_PROFILE_PROVENANCE_ATTRIBUTE: f"t_synth_bad_{index}"}
                )
                self.assertIsNone(official_content_reference_for_entity(entity))
        self.assertEqual(len(_unresolved_events(logged)), MAX_UNRESOLVED_DIAGNOSTICS)

    def test_two_entities_share_the_reference_value_without_shared_state(self):
        first = _RecordingEntity(**{PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})
        second = _RecordingEntity(**{PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})
        second.pk = 8
        with patch.object(
            official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}
        ):
            one = official_content_reference_for_entity(first)
            two = official_content_reference_for_entity(second)
        self.assertEqual(one, two)
        self.assertIsNot(one, two)
        self.assertEqual(first._values, second._values)

    def test_an_entity_without_a_named_portrait_subject_gets_no_reference(self):
        # Requirement: a runtime identity is a hash input only. An entity with
        # no provenance resolves nothing even though its identity text names
        # registered content, and no attribute is written to obtain that.
        entity = _RecordingEntity()
        entity.key = _SYNTH_PROFILE
        with patch.object(official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}):
            self.assertIsNone(official_content_reference_for_entity(entity))
        self.assertEqual(
            entity.read_keys,
            [PRESET_PROVENANCE_ATTRIBUTE, NPC_PROFILE_PROVENANCE_ATTRIBUTE],
        )
        self.assertEqual(entity._values, {})


class AuthoredChannelTests(unittest.TestCase):
    """The preset-preview / authored-channel entry point."""

    def setUp(self):
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    def test_the_preview_entry_point_resolves_the_same_reference_silently(self):
        entity = _RecordingEntity(**{PRESET_PROVENANCE_ATTRIBUTE: _SYNTH_PRESET})
        with (
            patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            from_entity = official_content_reference_for_entity(entity)
            from_preview = official_content_reference_for_preset(_SYNTH_PRESET)
        self.assertEqual(from_preview, from_entity)
        self.assertIsNotNone(from_preview)
        self.assertEqual(_unresolved_events(logged), [])

    def test_the_preview_entry_point_degrades_silently(self):
        for key in (_SYNTH_PRESET, "t_synth/../escape", None, 12):
            with self.subTest(key=repr(key)):
                official_refs._reported_unresolved.clear()
                with (
                    patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {}),
                    patch.object(official_refs, "log_warn") as logged,
                ):
                    self.assertIsNone(official_content_reference_for_preset(key))
                self.assertEqual(_unresolved_events(logged), [])

    def test_a_registered_key_resolves_without_any_catalog_snapshot(self):
        # The resolver answers from the live registry; whether the mounted
        # catalog holds images is the presentation layer's concern, so a
        # registered key must resolve against an empty snapshot too.
        from world.art import official

        self.addCleanup(official.reset_catalog)
        official.reset_catalog()
        self.assertEqual(len(official.current_catalog()), 0)
        with patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}):
            self.assertEqual(
                official_content_reference_for_preset(_SYNTH_PRESET),
                OfficialContentReference(OFFICIAL_KIND_PRESET, _SYNTH_PRESET),
            )


class MonsterBoundaryTests(unittest.TestCase):
    """Zero producers, no tier substitution, and the species-provider seam."""

    def setUp(self):
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    def test_the_monster_kind_has_no_registry_membership(self):
        self.assertFalse(registered_content_key(OFFICIAL_KIND_MONSTER, _SYNTH_TIER))
        self.assertIsNone(official_content_reference(OFFICIAL_KIND_MONSTER, _SYNTH_TIER))

    def test_a_tier_bearing_monster_resolves_no_reference(self):
        entity = _RecordingEntity(npc_tier_key=_SYNTH_TIER)
        entity.key = _SYNTH_TIER
        entity.display_name = _SYNTH_TIER
        with (
            patch.object(official_refs, "NPC_PROFILE_REGISTRY", {_SYNTH_TIER: object()}),
            patch.object(official_refs, "PLAYER_PRESET_REGISTRY", {_SYNTH_TIER: object()}),
            patch.object(official_refs, "log_warn") as logged,
        ):
            self.assertIsNone(official_content_reference_for_entity(entity))
        # No tier-to-species or name-to-species mapping ran, and no diagnostic
        # was emitted for an entity that declared no provenance.
        self.assertEqual(_unresolved_events(logged), [])

    def test_an_injected_species_provider_answers_only_the_entities_own_reference(self):
        def provider(entity):
            species = getattr(entity, "species_key", None)
            if not isinstance(species, str) or not species:
                return None
            return OfficialContentReference(OFFICIAL_KIND_MONSTER, species)

        wolf = SimpleNamespace(pk=1, species_key="t_synth_wolf", attributes=None)
        boar = SimpleNamespace(pk=2, species_key="t_synth_boar", attributes=None)
        with patch.object(official_refs, "_species_content_reference", provider):
            wolf_reference = official_content_reference_for_entity(wolf)
            boar_reference = official_content_reference_for_entity(boar)
        self.assertEqual(
            wolf_reference, OfficialContentReference(OFFICIAL_KIND_MONSTER, "t_synth_wolf")
        )
        self.assertEqual(
            boar_reference, OfficialContentReference(OFFICIAL_KIND_MONSTER, "t_synth_boar")
        )
        self.assertNotEqual(wolf_reference, boar_reference)

    def test_the_default_species_seam_has_no_producer(self):
        entity = _RecordingEntity(species_key="t_synth_wolf")
        self.assertIsNone(official_content_reference_for_entity(entity))

    def test_no_production_module_constructs_a_monster_reference(self):
        violations: list[str] = []
        scanned = 0
        for path in _production_module_paths():
            scanned += 1
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(REPO_ROOT).as_posix()
            violations.extend(
                f"{relative}:{found}"
                for found in _monster_reference_constructions(tree)
            )
        self.assertGreater(scanned, 50)
        self.assertEqual(
            violations, [], f"production module constructs a monster reference: {violations}"
        )

    def test_the_scan_detects_a_planted_monster_reference(self):
        # The scanner's own control: a scan that matches nothing must not pass
        # as a scan that found nothing. The planted sources exercise both
        # argument forms (positional and keyword) and both monster-kind
        # spellings (the literal and the vocabulary constant).
        monster_constant = "OFFICIAL_KIND_MONSTER"
        planted = (
            f"x = OfficialContentReference({monster_constant}, 't_synth')\n"
            f"y = OfficialContentReference(kind={monster_constant}, key='t_synth')\n"
            f"z = OfficialContentReference(kind={OFFICIAL_CONTENT_KINDS[0]!r}, key='t_synth')\n"
        )
        found = _monster_reference_constructions(ast.parse(planted))
        self.assertEqual(len(found), 3)
        # A preset-kind construction with a variable kind is not a monster one.
        clean = "x = OfficialContentReference(kind, key)\ny = len(another_call())\n"
        self.assertEqual(_monster_reference_constructions(ast.parse(clean)), [])


if __name__ == "__main__":
    unittest.main()
