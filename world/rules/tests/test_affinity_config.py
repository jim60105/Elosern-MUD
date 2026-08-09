"""Affinity rulebook ladder tests (affinity-system 2.x).

One test per stage rule ID plus the constants and resolution contracts. Rule
IDs are loaded from ``rulebook/affinity.yaml``; a mechanical check pins the
one-to-one naming correspondence.
"""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
from unittest import TestCase

from world.rules.affinity_config import (
    AffinityConfigError,
    load_config,
)


class AffinityStageBoundaryTests(TestCase):
    """One test per canonical boundary value (spec scenario)."""

    def setUp(self):
        self.config = load_config()

    def test_floor_0_resolves_to_acquaintance(self):
        stage = self.config.stage_for_value(0)
        self.assertEqual(stage.id, "acquaintance")
        self.assertEqual(stage.name, "初識")

    def test_floor_10_resolves_to_familiar(self):
        stage = self.config.stage_for_value(10)
        self.assertEqual(stage.id, "familiar")
        self.assertEqual(stage.name, "熟識")

    def test_floor_30_resolves_to_warm(self):
        stage = self.config.stage_for_value(30)
        self.assertEqual(stage.id, "warm")
        self.assertEqual(stage.name, "親睦")

    @covers_requirement("affinity-system::the-stage-ladder-maps-hidden-values-to-seven-traditional-chinese-stage-names")
    def test_floor_50_resolves_to_trusted(self):
        stage = self.config.stage_for_value(50)
        self.assertEqual(stage.id, "trusted")
        self.assertEqual(stage.name, "信賴")

    def test_floor_70_resolves_to_bonded(self):
        stage = self.config.stage_for_value(70)
        self.assertEqual(stage.id, "bonded")
        self.assertEqual(stage.name, "羈絆")

    def test_floor_90_resolves_to_beloved(self):
        stage = self.config.stage_for_value(90)
        self.assertEqual(stage.id, "beloved")
        self.assertEqual(stage.name, "至愛")

    def test_floor_100_resolves_to_absolute_bond(self):
        stage = self.config.stage_for_value(100)
        self.assertEqual(stage.id, "absolute_bond")
        self.assertEqual(stage.name, "絕對羈絆")

    def test_values_between_floors_use_the_lower_stage(self):
        for value, expected in ((49, "warm"), (69, "trusted"), (99, "beloved")):
            with self.subTest(value=value):
                self.assertEqual(self.config.stage_for_value(value).id, expected)

    def test_value_above_natural_cap_resolves_to_topmost_stage(self):
        stage = self.config.stage_for_value(130)
        self.assertEqual(stage.id, "absolute_bond")
        self.assertEqual(stage.name, "絕對羈絆")


class AffinityConfigValidationTests(TestCase):
    def _write_temporary(self, content: str) -> Path:
        target = Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        self._original = target.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        return target

    def tearDown(self):
        target = Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        if hasattr(self, "_original"):
            target.write_text(self._original, encoding="utf-8")
        from world.rules import affinity_config

        affinity_config._CONFIG = None

    def _load_deviant(self, content: str):
        self._write_temporary(content)
        with self.assertRaises(AffinityConfigError):
            load_config()

    @covers_requirement("affinity-system::the-stage-ladder-maps-hidden-values-to-seven-traditional-chinese-stage-names")
    def test_deviant_floor_outside_canonical_set_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(base.replace("floor: 30\n", "floor: 25\n"))

    def test_duplicated_floor_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(base.replace("floor: 10\n", "floor: 0\n"))

    def test_wrong_stage_count_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        removed = (
            "  - id: absolute_bond\n"
            "    floor: 100\n"
            "    name: 絕對羈絆\n"
            "    look_flavor: 她的一切心思都繫在你身上，眼中唯有你。\n"
        )
        self.assertIn(removed, base)
        self._load_deviant(base.replace(removed, ""))

    def test_non_positive_threshold_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(base.replace("invite_threshold: 70", "invite_threshold: 0"))

    def test_unknown_top_level_field_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(base + "\nunknown_field: 1\n")


class AffinityConfigConstantsTests(TestCase):
    def test_constants_come_from_yaml(self):
        config = load_config()
        self.assertEqual(config.invite_threshold, 70)
        self.assertEqual(config.daily_interaction_cap, 5)
        self.assertEqual(config.quest_completion_gain, 2)

    def test_every_stage_id_has_exactly_one_named_test(self):
        names = [
            name
            for name, _ in inspect.getmembers(
                AffinityStageBoundaryTests, inspect.isfunction
            )
        ]
        for stage in load_config().stages:
            self.assertEqual(
                names.count(f"test_floor_{stage.floor}_resolves_to_{stage.id}"),
                1,
                stage.id,
            )
