"""Name-corpus registry checks (npc-namegen-lore-registry).

Pure ``unittest.TestCase`` covers the frozen registry shape, array-by-array
coverage against the vendored JSON, the import-time invariant fail-fast paths
through the injectable builder, and the 「名・姓」 composition. The
``EvenniaTestCase`` class pins the ``sync_all`` mirror of the new
``name_packs`` category.
"""

import json
from pathlib import Path
import types
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTestCase

from world.lore.names import (
    _CORPUS_ROOT,
    _GIVEN_POOLS,
    _PACK_KEYS,
    NAME_PACK_BY_RACE,
    NAME_PACK_REGISTRY,
    NAME_SEPARATOR,
    FrozenDict,
    NameCorpusError,
    NamePack,
    NamePart,
    _build_registry,
    compose_display_name,
)
from world.lore.races import RACE_REGISTRY
from world.lore.sync import _ALL_REGISTRIES, _db_safe, sync_all

from dataclasses import asdict


def _load_source_corpus() -> tuple[dict, dict]:
    packs = {
        key: json.loads((_CORPUS_ROOT / "data" / "packs" / f"{key}.json").read_text(encoding="utf-8"))
        for key in _PACK_KEYS
    }
    translit = json.loads(
        (_CORPUS_ROOT / "data" / "translit" / "fantasy.json").read_text(encoding="utf-8")
    )
    return packs, translit


def _minimal_payloads(
    *, surname_zh: str = "姓", given_zh: str = "名"
) -> tuple[dict, dict]:
    """Five valid single-part packs with an injectable translit table."""

    payloads = {
        key: {
            "surnames": [{"s": "Surn", "meaning": "源"}],
            "given": {pool_key: [{"g": f"Giv{pool_key}"}] for pool_key in _GIVEN_POOLS},
            "rules": {"naming": {"note": "命名慣例"}},
        }
        for key in _PACK_KEYS
    }
    translit = {"Surn": surname_zh}
    for pool_key in _GIVEN_POOLS:
        translit[f"Giv{pool_key}"] = given_zh
    return payloads, translit


class NamePackRegistryTests(unittest.TestCase):
    @covers_requirement("namegen-corpus-registry::name-pack-registry-freezes-the-vendored-corpus-at-import-time")
    def test_registry_is_a_frozen_mapping_of_the_five_vendored_packs(self):
        self.assertIsInstance(NAME_PACK_REGISTRY, types.MappingProxyType)
        self.assertEqual(set(NAME_PACK_REGISTRY), set(_PACK_KEYS))
        for pack in NAME_PACK_REGISTRY.values():
            self.assertIsInstance(pack, NamePack)
            self.assertTrue(pack.surnames, pack.key)
            self.assertEqual(set(pack.given), set(_GIVEN_POOLS))
            self.assertIsInstance(pack.given, FrozenDict)  # concrete dict for asdict deepcopy
            self.assertTrue(pack.naming_note_zh, pack.key)
            for pool in pack.given.values():
                self.assertTrue(pool, pack.key)

    @covers_requirement("namegen-corpus-registry::name-pack-registry-freezes-the-vendored-corpus-at-import-time")
    def test_registry_rejects_mutation_below_the_top_level(self):
        given = NAME_PACK_REGISTRY["fantasy-human"].given
        with self.assertRaises(TypeError):
            given["m"] = ()
        with self.assertRaises(TypeError):
            given.clear()
        with self.assertRaises(TypeError):
            given.pop("f")
        with self.assertRaises(TypeError):
            given.setdefault("u", ())
        # The mirror path must still rebuild the type through deepcopy.
        from copy import deepcopy

        mirrored = _db_safe(asdict(NAME_PACK_REGISTRY["fantasy-human"]))
        # asdict deepcopy rebuilds via __reduce__, then _db_safe normalizes
        # back to plain dicts for storage.
        self.assertIsInstance(mirrored["given"], dict)
        self.assertNotIsInstance(mirrored["given"], FrozenDict)
        self.assertEqual(
            mirrored["given"],
            {pool_key: tuple(asdict(part) for part in pool) for pool_key, pool in given.items()},
        )
        cloned = deepcopy(given)
        self.assertIsInstance(cloned, FrozenDict)
        self.assertIsNot(cloned, given)

    @covers_requirement("namegen-corpus-registry::name-pack-registry-freezes-the-vendored-corpus-at-import-time")
    def test_registry_content_matches_the_vendored_corpus_array_by_array(self):
        packs, translit = _load_source_corpus()
        total = 0
        for key, pack in NAME_PACK_REGISTRY.items():
            source = packs[key]
            expected_surnames = tuple(
                NamePart(text=raw["s"], zh=translit[raw["s"]], meaning_zh=raw.get("meaning") or "")
                for raw in source["surnames"]
            )
            self.assertEqual(pack.surnames, expected_surnames, key)
            total += len(expected_surnames)
            for pool_key in _GIVEN_POOLS:
                expected_pool = tuple(
                    NamePart(
                        text=raw["g"],
                        zh=translit[raw["g"]],
                        meaning_zh=raw.get("meaning") or "",
                    )
                    for raw in source["given"][pool_key]
                )
                self.assertEqual(pack.given[pool_key], expected_pool, f"{key}:{pool_key}")
                total += len(expected_pool)
        # Current vendored snapshot total; a manual re-sync updates this with
        # the corpus, same as the spec's stated count.
        self.assertEqual(total, 1274)

    @covers_requirement("namegen-corpus-registry::name-pack-registry-freezes-the-vendored-corpus-at-import-time")
    def test_every_part_has_a_chinese_rendering_without_raw_text_leakage(self):
        _packs, translit = _load_source_corpus()
        for pack in NAME_PACK_REGISTRY.values():
            parts = [*pack.surnames, *(p for pool in pack.given.values() for p in pool)]
            for part in parts:
                self.assertTrue(part.zh, f"{pack.key}:{part.text}")
                self.assertEqual(part.zh, translit[part.text], part.text)
                self.assertFalse(
                    any(char.isascii() and char.isalpha() for char in part.zh),
                    f"{part.text} fell back to the untranslated original",
                )
                self.assertIsInstance(part.meaning_zh, str)

    @covers_requirement("namegen-corpus-registry::race-binding-maps-the-three-playable-races-and-leaves-the-spare-packs-unbound")
    def test_race_binding_maps_three_races_and_leaves_spares_unbound(self):
        self.assertIsInstance(NAME_PACK_BY_RACE, types.MappingProxyType)
        self.assertEqual(
            dict(NAME_PACK_BY_RACE),
            {"human": "fantasy-human", "elf": "fantasy-elf", "beastfolk": "fantasy-orc"},
        )
        for race_key, pack_key in NAME_PACK_BY_RACE.items():
            self.assertIn(race_key, RACE_REGISTRY)
            self.assertEqual(NAME_PACK_REGISTRY[pack_key].race_key, race_key)
        for spare in ("fantasy-dwarf", "fantasy-halfling"):
            self.assertIsNone(NAME_PACK_REGISTRY[spare].race_key, spare)
            self.assertNotIn(spare, NAME_PACK_BY_RACE.values())

    @covers_requirement("namegen-corpus-registry::name-pack-registry-is-mirrored-into-lorerecord-scripts-idempotently")
    def test_name_packs_category_is_wired_into_the_sync_mirror(self):
        self.assertIs(_ALL_REGISTRIES["name_packs"], NAME_PACK_REGISTRY)


class NameCorpusInvariantTests(unittest.TestCase):
    @covers_requirement("namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")
    def test_translit_gap_raises_and_names_the_missing_words(self):
        payloads, translit = _minimal_payloads()
        del translit["Givm"]
        translit.pop("Surn")
        with self.assertRaises(NameCorpusError) as caught:
            _build_registry(payloads, translit, _race_bindings_stub())
        message = str(caught.exception)
        self.assertIn("Givm", message)
        self.assertIn("Surn", message)

    @covers_requirement("namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")
    def test_missing_or_extra_pack_raises(self):
        payloads, translit = _minimal_payloads()
        payloads.pop("fantasy-orc")
        with self.assertRaises(NameCorpusError):
            _build_registry(payloads, translit, _race_bindings_stub())

    @covers_requirement("namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")
    def test_empty_pool_or_surnames_raises(self):
        for mutate, fragment in (
            (lambda p: p["fantasy-elf"]["given"]["f"].clear(), "pool"),
            (lambda p: p["fantasy-elf"]["surnames"].clear(), "surnames"),
        ):
            payloads, translit = _minimal_payloads()
            mutate(payloads)
            with self.subTest(mutate=fragment):
                with self.assertRaises(NameCorpusError):
                    _build_registry(payloads, translit, _race_bindings_stub())

    @covers_requirement("namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")
    def test_unknown_race_key_or_unregistered_pack_binding_raises(self):
        payloads, translit = _minimal_payloads()
        with self.assertRaises(NameCorpusError):
            _build_registry(payloads, translit, {"dragonborn": "fantasy-human"})
        with self.assertRaises(NameCorpusError):
            _build_registry(payloads, translit, {"human": "fantasy-goblin"})

    @covers_requirement("namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")
    def test_overlong_composed_name_raises_through_the_builder(self):
        payloads, translit = _minimal_payloads(given_zh="名" * 64)
        with self.assertRaises(NameCorpusError):
            _build_registry(payloads, translit, _race_bindings_stub())

    @covers_requirement(
        "namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time",
        "namegen-corpus-registry::display-names-compose-from-chinese-renderings-with-the-middle-dot-separator",
    )
    def test_real_corpus_longest_composition_passes_the_validator(self):
        from world.rules.character_creation import _validate_name

        longest = max(
            (
                compose_display_name(given, surname)
                for pack in NAME_PACK_REGISTRY.values()
                for given in pack.given["m"] + pack.given["f"] + pack.given["u"]
                for surname in pack.surnames
            ),
            key=len,
        )
        self.assertEqual(_validate_name(longest), longest)


def _race_bindings_stub() -> dict[str, str]:
    from world.lore.names import _RACE_BINDINGS

    return dict(_RACE_BINDINGS)


class DisplayCompositionTests(unittest.TestCase):
    @covers_requirement("namegen-corpus-registry::display-names-compose-from-chinese-renderings-with-the-middle-dot-separator")
    def test_separator_is_the_katakana_middle_dot(self):
        self.assertEqual(NAME_SEPARATOR, "・")
        self.assertEqual(ord(NAME_SEPARATOR), 0x30FB)

    @covers_requirement("namegen-corpus-registry::display-names-compose-from-chinese-renderings-with-the-middle-dot-separator")
    def test_composition_is_given_separator_surname(self):
        given = NamePart(text="Gaspar", zh="加斯帕", meaning_zh="")
        surname = NamePart(text="Snow", zh="斯諾", meaning_zh="")
        self.assertEqual(compose_display_name(given, surname), "加斯帕・斯諾")

    @covers_requirement("namegen-corpus-registry::display-names-compose-from-chinese-renderings-with-the-middle-dot-separator")
    def test_composed_names_never_contain_raw_corpus_text(self):
        pack = NAME_PACK_REGISTRY["fantasy-human"]
        given_parts = pack.given["m"] + pack.given["f"] + pack.given["u"]
        raw_texts = {part.text for part in given_parts} | {p.text for p in pack.surnames}
        for given in given_parts[::7]:
            for surname in pack.surnames[::5]:
                composed = compose_display_name(given, surname)
                self.assertEqual(composed, f"{given.zh}{NAME_SEPARATOR}{surname.zh}")
                for text in raw_texts:
                    if text.isascii():
                        self.assertNotIn(text, composed)


class NamePackMirrorTests(EvenniaTestCase):
    @covers_requirement("namegen-corpus-registry::name-pack-registry-is-mirrored-into-lorerecord-scripts-idempotently")
    def test_sync_all_mirrors_the_five_name_packs_idempotently(self):
        sync_all()
        first = {}
        for key, pack in NAME_PACK_REGISTRY.items():
            records = search_script(f"lore:name_packs:{key}")
            self.assertEqual(len(records), 1, key)
            self.assertEqual(records[0].db.category, "name_packs")
            self.assertEqual(records[0].db.fields, _db_safe(asdict(pack)), key)
            first[key] = records[0].id

        sync_all()
        for key, pack in NAME_PACK_REGISTRY.items():
            records = search_script(f"lore:name_packs:{key}")
            self.assertEqual(len(records), 1, key)
            self.assertEqual(records[0].id, first[key], key)
            self.assertEqual(records[0].db.fields, _db_safe(asdict(pack)), key)
