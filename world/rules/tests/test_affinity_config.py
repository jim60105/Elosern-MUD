"""Affinity rulebook ladder tests (affinity-system 2.x).

One test per stage rule ID plus the constants and resolution contracts. Rule
IDs are loaded from ``rulebook/affinity.yaml``; a mechanical check pins the
one-to-one naming correspondence.
"""

from tools.spec_traceability import covers_requirement

import inspect
import tempfile
from pathlib import Path
from unittest import TestCase

from world.quests.catalog import register_catalog
from world.rules.affinity_config import (
    AffinityConfigError,
    load_config,
)


def _register_quests() -> None:
    """Register the shipped quest catalog so cap_breaks quest keys resolve."""
    register_catalog()


class AffinityStageBoundaryTests(TestCase):
    """One test per canonical boundary value (spec scenario)."""

    def setUp(self):
        _register_quests()
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
    def setUp(self):
        _register_quests()

    def _load_deviant(self, content: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "affinity.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(AffinityConfigError):
                load_config(path=path)

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

    def test_missing_friendly_fire_penalty_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(base.replace("friendly_fire_penalty_per_hit: 1\n", ""))

    def test_non_positive_friendly_fire_penalty_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(
            base.replace(
                "friendly_fire_penalty_per_hit: 1",
                "friendly_fire_penalty_per_hit: 0",
            )
        )
        self._load_deviant(
            base.replace(
                "friendly_fire_penalty_per_hit: 1",
                "friendly_fire_penalty_per_hit: -1",
            )
        )

    def test_non_integer_friendly_fire_penalty_is_rejected(self):
        base = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._load_deviant(
            base.replace(
                "friendly_fire_penalty_per_hit: 1",
                "friendly_fire_penalty_per_hit: many",
            )
        )

    def _cap_breaks_base(self) -> str:
        return (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")

    def _replace_cap_breaks(self, content: str) -> str:
        """Replace the shipped cap_breaks block with a custom one."""
        marker = "cap_breaks:\n"
        start = content.index(marker) + len(marker)
        end = content.index("stages:\n", start)
        return content[:start] + content[start:end].replace(
            content[start:end], "  - { npc_key: 'altoria_guild_master', "
            "quest_key: 'introductory_hunt', new_cap: 150 }\n"
        )

    @covers_requirement("affinity-cap-break::the-cap-breaks-rulebook-table-drives-milestone-cap-raises-at-quest-turn-in")
    def test_cap_break_unknown_quest_key_is_rejected(self):
        base = self._cap_breaks_base()
        deviant = base.replace(
            'quest_key: "introductory_hunt"', 'quest_key: "no_such_quest"'
        )
        self._load_deviant(deviant)

    def test_cap_break_missing_quest_key_is_rejected(self):
        base = self._cap_breaks_base()
        self._load_deviant(
            base.replace('    quest_key: "introductory_hunt"\n', "")
        )

    def test_cap_break_neither_selector_is_rejected(self):
        base = self._cap_breaks_base()
        deviant = base.replace(
            'npc_key: "altoria_guild_master"\n', 'role: ""\n'
        )
        self._load_deviant(deviant)

    def test_cap_break_both_selectors_are_rejected(self):
        base = self._cap_breaks_base()
        deviant = base.replace(
            'npc_key: "altoria_guild_master"\n',
            'npc_key: "altoria_guild_master"\n    role: "guard"\n',
        )
        self._load_deviant(deviant)

    def test_cap_break_malformed_second_selector_is_still_rejected(self):
        base = self._cap_breaks_base()
        deviant = base.replace(
            'npc_key: "altoria_guild_master"\n',
            'npc_key: 123\n    role: "guard"\n',
        )
        self._load_deviant(deviant)

    def test_cap_break_npc_key_and_role_selectors_are_distinct(self):
        base = self._cap_breaks_base()
        entries = (
            "  - npc_key: 'altoria_guild_master'\n"
            "    quest_key: 'introductory_hunt'\n"
            "    new_cap: 150\n"
            "  - role: 'guard'\n"
            "    quest_key: 'introductory_hunt'\n"
            "    new_cap: 200\n"
        )
        start = base.index("cap_breaks:\n") + len("cap_breaks:\n")
        end = base.index("stages:\n", start)
        deviant = base[:start] + entries + base[end:]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "affinity.yaml"
            path.write_text(deviant, encoding="utf-8")
            config = load_config(path=path)
        self.assertEqual(
            [(e.selector_kind, e.selector, e.new_cap) for e in config.cap_breaks],
            [
                ("npc_key", "altoria_guild_master", 150),
                ("role", "guard", 200),
            ],
        )

    def test_cap_break_new_cap_at_or_below_natural_cap_is_rejected(self):
        base = self._cap_breaks_base()
        for value in ("99", "50"):
            with self.subTest(value=value):
                self._load_deviant(
                    base.replace("new_cap: 150", f"new_cap: {value}")
                )

    def test_cap_break_duplicate_quest_and_selector_is_rejected(self):
        base = self._cap_breaks_base()
        extra = (
            "  - npc_key: 'altoria_guild_master'\n"
            "    quest_key: 'introductory_hunt'\n"
            "    new_cap: 200\n"
        )
        start = base.index("cap_breaks:\n") + len("cap_breaks:\n")
        deviant = base[:start] + extra + base[start:]
        self._load_deviant(deviant)

    def test_cap_break_non_integer_new_cap_is_rejected(self):
        base = self._cap_breaks_base()
        self._load_deviant(base.replace("new_cap: 150", "new_cap: many"))


class AffinityConfigConstantsTests(TestCase):
    def setUp(self):
        _register_quests()

    def test_constants_come_from_yaml(self):
        config = load_config()
        self.assertEqual(config.invite_threshold, 70)
        self.assertEqual(config.daily_interaction_cap, 5)
        self.assertEqual(config.quest_completion_gain, 2)
        self.assertEqual(config.friendly_fire_penalty_per_hit, 1)
        self.assertEqual(
            config.cap_break_for("introductory_hunt")[0].new_cap, 150
        )

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
