"""Data-contract test: static permitted-reference catalog mirrors canonical registries

``world.rules.dialogue_references.static_dialogue_references()`` is the single
composition of the authored-dialogue permission catalog. This module pins that
it carries exactly the canonical registry keys and labels, that a profile is
only referenceable under one unambiguous authored public name, that the
daypart family comes from the clock rulebook, and that the composition is
import-order safe for both entry points (``world.lore.dialogue`` and
``world.rules.dialogue_references``) in fresh processes -- an in-process test
would hide that ordering defect behind earlier imports.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import textwrap
import unittest
from unittest.mock import patch

import yaml

from world.lore.guild_adventurers import ADVENTURER_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY, place_is_hostless
from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY
from world.rules.dialogue_references import (
    CLOCK_RULEBOOK_PATH,
    DAYPART_LABELS,
    static_dialogue_references,
)
from world.skills.registry import SKILL_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[3]
LABEL_MAX_CODE_POINTS = 128


class StaticDialogueReferencesTests(unittest.TestCase):
    """The catalog is exactly the canonical registries' key/label projection."""

    def setUp(self) -> None:
        self.references = static_dialogue_references()

    def test_registry_families_match_their_canonical_sources(self):
        expected = {
            "race": (RACE_REGISTRY, "display_name_zh"),
            "social_identity": (SOCIAL_IDENTITY_REGISTRY, "display_name_zh"),
            "item": (ITEM_REGISTRY, "display_name_zh"),
            "skill": (SKILL_REGISTRY, "label"),
            "preset": (PLAYER_PRESET_REGISTRY, "display_name"),
        }
        for family, (registry, field) in expected.items():
            with self.subTest(family=family):
                self.assertEqual(
                    self.references.keys_for(family), frozenset(registry.keys())
                )
                for key, row in registry.items():
                    self.assertEqual(
                        self.references.label(family, key),
                        getattr(row, field),
                        f"{family} label for {key!r}",
                    )

    def test_profile_family_only_carries_uniquely_named_profiles(self):
        canonical_names: dict[str, set[str]] = {}
        for place in PLACE_REGISTRY.values():
            if place_is_hostless(place) or not place.host_profile_key:
                continue
            canonical_names.setdefault(place.host_profile_key, set()).add(
                place.host_name
            )
        for row in ADVENTURER_REGISTRY.values():
            canonical_names.setdefault(row.profile_key, set()).add(row.name)

        profile_table = self.references.tables["profile"]
        self.assertTrue(profile_table, "the shipped profile family is empty")
        self.assertEqual(set(profile_table), frozenset(NPC_PROFILE_REGISTRY))
        for profile_key, label in profile_table.items():
            with self.subTest(profile=profile_key):
                self.assertEqual(canonical_names.get(profile_key), {label})

    def test_ambiguous_and_unlabelled_profiles_are_excluded(self):
        keys = sorted(NPC_PROFILE_REGISTRY)
        self.assertGreaterEqual(len(keys), 2, "need two profiles for the controls")
        ambiguous, unlabelled = keys[0], keys[1]
        with patch(
            "world.rules.dialogue_references._profile_names",
            return_value={
                ambiguous: {"合成甲名", "合成乙名"},
                unlabelled: set(),
            },
        ):
            table = static_dialogue_references().tables["profile"]
        self.assertNotIn(ambiguous, table)
        self.assertNotIn(unlabelled, table)

    def test_daypart_family_comes_from_the_clock_rulebook(self):
        document = yaml.safe_load(CLOCK_RULEBOOK_PATH.read_text(encoding="utf-8"))
        dayparts = document["dayparts"]
        self.assertEqual(self.references.keys_for("daypart"), frozenset(dayparts))
        for key in dayparts:
            with self.subTest(daypart=key):
                self.assertEqual(self.references.label("daypart", key), DAYPART_LABELS[key])

    def test_every_label_is_a_bounded_single_line_string(self):
        for family in (
            "race",
            "social_identity",
            "item",
            "skill",
            "preset",
            "profile",
            "daypart",
        ):
            table = self.references.tables[family]
            self.assertTrue(table, f"the shipped {family} family is empty")
            for key, label in table.items():
                with self.subTest(family=family, key=key):
                    self.assertIsInstance(label, str)
                    self.assertTrue(label.strip())
                    self.assertLessEqual(len(label), LABEL_MAX_CODE_POINTS)
                    self.assertNotIn("\n", label)

    def test_progression_families_stay_empty_until_their_slice(self):
        for family in ("guild_rank", "quest", "affinity_stage"):
            with self.subTest(family=family):
                self.assertFalse(self.references.keys_for(family))

    def test_catalog_is_immutable_and_rebuilt_from_live_registries(self):
        with self.assertRaises(TypeError):
            self.references.tables["race"]["t_probe"] = "合成"
        with patch(
            "world.lore.races.RACE_REGISTRY",
            {"t_live_probe": SimpleNamespace(display_name_zh="合成種族")},
        ):
            rebuilt = static_dialogue_references()
        self.assertEqual(rebuilt.keys_for("race"), frozenset({"t_live_probe"}))

    def test_fresh_processes_load_in_either_import_order(self):
        script = textwrap.dedent(
            """
            import json
            {first}
            {second}
            from world.lore.dialogue import DIALOGUE_SNAPSHOT
            from world.rules.dialogue_references import static_dialogue_references
            print(json.dumps({{
                "tables": sorted(DIALOGUE_SNAPSHOT),
                "races": sorted(static_dialogue_references().keys_for("race")),
            }}))
            """
        )
        orders = (
            (
                "import world.rules.dialogue_references as _references\n"
                "_references.static_dialogue_references()",
                "import world.lore.dialogue as _dialogue",
            ),
            (
                "import world.lore.dialogue as _dialogue",
                "import world.rules.dialogue_references as _references\n"
                "_references.static_dialogue_references()",
            ),
        )
        outputs = []
        for first, second in orders:
            completed = subprocess.run(
                [sys.executable, "-c", script.format(first=first, second=second)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(
                completed.returncode,
                0,
                f"import order failed:\n{completed.stderr}",
            )
            outputs.append(json.loads(completed.stdout.strip().splitlines()[-1]))
        self.assertEqual(outputs[0], outputs[1])
        self.assertTrue(outputs[0]["tables"], "no dialogue table loaded")
        self.assertTrue(outputs[0]["races"], "no race reference loaded")


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
