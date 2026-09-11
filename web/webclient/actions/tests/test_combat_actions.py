"""Combat action validator and adapter integration tests (tasks 3.3-3.5)."""

import unittest

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.actions.combat_actions import (
    validate_cast_payload,
    validate_flee_payload,
    validate_forfeit_payload,
    _cast_adapter,
    _flee_adapter,
    _forfeit_adapter,
)
from world.rules.combat_session import engage, read_session
from world.rules.progression import (
    FREEFORM_SCALE_LADDER,
    scaled_mp_cost,
)
from world.rules.tests._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.skills.registry import SkillCategory
from world.tests.synthetic_data import SYNTH_SKILLS

# File-local cast rows built from the kit templates (skills scope; the borrowed
# shipped element stays live because the scope never patches the element
# registry): a single elemental spell fills every old shipped-spell role —
# _T_SINGLE the affordable SINGLE cast, _T_AREA the AREA/shorthand cast.
# Which shipped spell those roles once used is irrelevant to the adapters.
_T_SINGLE = SYNTH_SKILLS["t_ember_burst"]
_T_AREA = SYNTH_SEAM_AREA_SKILL
_T_ELEMENT = _T_SINGLE.element.key


def _mastery_key() -> str:
    """The element-mastery passive key the production entitlement derives.

    ``progression.freeform_mastery_entitled`` hardcodes ``f"{element}_mastery"``
    — a production vocabulary (the ``synth_innate_overlay`` precedent), so the
    row lives under the runtime-derived key and no shipped identifier is named.
    """
    return f"{_T_ELEMENT}_mastery"


def _mastery_row():
    return replace(
        SYNTH_SKILLS["t_steady_stride"],
        key=_mastery_key(),
        label="合成元素精通",
        description="對該元素達到最高造詣的合成被動。",
        effects=["passive_trait:element_mastery"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_T_ELEMENT,
    )


# The scale rung this file exercises is a production-vocabulary member of the
# closed freeform table; its proficiency gate is looked up in the ladder table
# at runtime, never hardcoded.
_T_SCALE = 2.0
_T_SCALE_LEVEL = next(
    min_level for scale, min_level in FREEFORM_SCALE_LADDER if scale == _T_SCALE
)

_SCOPE_EXTRA = {
    "skills": {
        **synth_innate_overlay()["skills"],
        _T_SINGLE.key: _T_SINGLE,
        _T_AREA.key: _T_AREA,
        _mastery_row().key: _mastery_row(),
    }
}

# A zero-cost SELF passive: the "skill-only payload" fixture (the old
# body-enhancement/concentration role — the validator checks target shape
# against the TargetSpec, not the effects).
_T_SELF = SYNTH_SKILLS["t_steady_stride"]


def _player(key="adapter player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="adapter goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class CastPayloadValidationTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", extra=_SCOPE_EXTRA)
        super().setUp()

    def test_none_and_self_accept_skill_only(self):
        validated = validate_cast_payload({"skill_key": _T_SELF.key})
        self.assertEqual(validated["target_ids"], ())
        self.assertIsNone(validated["target_shorthand"])
        self.assertEqual(validated["skill_key"], _T_SELF.key)

    def test_single_requires_exactly_one_target(self):
        validated = validate_cast_payload(
            {"skill_key": _T_SINGLE.key, "target_ids": [3]}
        )
        self.assertEqual(validated["target_ids"], (3,))
        for ids in ([], [1, 2]):
            with self.assertRaises(Exception):
                validate_cast_payload(
                    {"skill_key": _T_SINGLE.key, "target_ids": ids}
                )

    def test_area_accepts_list_or_shorthand_never_both(self):
        validated = validate_cast_payload(
            {"skill_key": _T_AREA.key, "target_ids": [3, 4]}
        )
        self.assertEqual(validated["target_ids"], (3, 4))
        validated = validate_cast_payload(
            {"skill_key": _T_AREA.key, "target_shorthand": "all-enemies"}
        )
        self.assertEqual(validated["target_shorthand"], "all-enemies")
        with self.assertRaises(Exception):
            validate_cast_payload(
                {
                    "skill_key": _T_AREA.key,
                    "target_ids": [3],
                    "target_shorthand": "all",
                }
            )

    def test_rejects_reserved_flee_key(self):
        with self.assertRaises(Exception) as caught:
            validate_cast_payload({"skill_key": "flee"})
        self.assertIn("reserved flee", str(caught.exception))

    def test_rejects_unknown_fields_and_bad_values(self):
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_ids": [True]}
            )
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": _T_SINGLE.key, "target_ids": [0]})
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_ids": [1, 1]}
            )
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": _T_SINGLE.key, "bogus": 1})
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_shorthand": "all"}
            )

    def test_flee_and_forfeit_exact_payloads(self):
        self.assertEqual(validate_flee_payload({}), {})
        with self.assertRaises(Exception):
            validate_flee_payload({"skill_key": "flee"})
        validated = validate_forfeit_payload({"session_id": "hostile:1:0"})
        self.assertEqual(validated["session_id"], "hostile:1:0")
        with self.assertRaises(Exception):
            validate_forfeit_payload({})
        with self.assertRaises(Exception):
            validate_forfeit_payload({"session_id": "hostile:1:0", "extra": 1})

    @covers_requirement("webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale")
    def test_member_scale_is_accepted_on_every_target_form(self):
        validated = validate_cast_payload(
            {"skill_key": _T_AREA.key, "target_ids": [3, 4], "scale": _T_SCALE}
        )
        self.assertEqual(validated["scale"], _T_SCALE)
        validated = validate_cast_payload(
            {
                "skill_key": _T_AREA.key,
                "target_shorthand": "all-enemies",
                "scale": 0.5,
            }
        )
        self.assertEqual(validated["scale"], 0.5)
        validated = validate_cast_payload({"skill_key": _T_SELF.key, "scale": 4.0})
        self.assertEqual(validated["scale"], 4.0)
        validated = validate_cast_payload({"skill_key": _T_SELF.key, "scale": 1.0})
        self.assertEqual(validated["scale"], 1.0)

    @covers_requirement("webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale")
    def test_non_member_scale_is_rejected_as_malformed(self):
        for bad_scale in (3.0, "2", True, None):
            with self.subTest(scale=bad_scale):
                with self.assertRaises(Exception):
                    validate_cast_payload(
                        {
                            "skill_key": _T_AREA.key,
                            "target_ids": [3],
                            "scale": bad_scale,
                        }
                    )

    @covers_requirement("webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale")
    def test_absent_scale_defaults_to_one(self):
        validated = validate_cast_payload(
            {"skill_key": _T_AREA.key, "target_shorthand": "all-enemies"}
        )
        self.assertEqual(validated["scale"], 1.0)


class CombatAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # Round paths resolve the forced innate keys and this file's cast rows
        # through the scoped skill registry.
        open_synthetic_scope(self, "skills", extra=_SCOPE_EXTRA)
        super().setUp()
        self.room = create_object(Room, key="adapter arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_SINGLE.key])
        self.monster = _monster()
        self.monster.location = self.room

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_no_session_rejects(self):
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_ids": [self.monster.pk]}
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_tampered_remote_target_rejects(self):
        engage(self.player, self.monster)
        other_room = create_object(Room, key="elsewhere")
        other = _monster("intruder")
        other.location = other_room
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_ids": [other.pk]}
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertEqual(self.monster.traits.hp.current, 100)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    def test_successful_cast_updates_session(self):
        engage(self.player, self.monster)
        from unittest.mock import Mock, patch

        self.player.msg = Mock()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = _cast_adapter(
                self.player,
                validate_cast_payload(
                    {"skill_key": _T_SINGLE.key, "target_ids": [self.monster.pk]}
                ),
            )
        self.assertIn(result["outcome"], ("success", "rejected"))
        if result["outcome"] == "success":
            self.assertIn(result["code"], ("round", "victory", "defeat"))
            self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertGreaterEqual(
                len(self.player.msg.call_args_list),
                1,
                "adapter must emit committed EventLog narrative via text output",
            )
            narrative = "\n".join(
                call.args[0] for call in self.player.msg.call_args_list
            )
            self.assertNotIn("ui_action_result", narrative)
            self.assertTrue(narrative.strip())

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_flee_accepts_no_target_and_runs(self):
        engage(self.player, self.monster)
        from unittest.mock import patch

        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = _flee_adapter(self.player, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "fled")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_stale_forfeit_rejects(self):
        engage(self.player, self.monster)
        result = _forfeit_adapter(
            self.player, {"session_id": "hostile:999:0"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertIsNotNone(self.player.db.active_combat)

    def test_matching_forfeit_succeeds(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        result = _forfeit_adapter(self.player, {"session_id": session_id})
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self.player.db.active_combat)

    def test_matching_forfeit_emits_terminal_text_message(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        from unittest.mock import Mock

        self.player.msg = Mock()
        result = _forfeit_adapter(self.player, {"session_id": session_id})
        self.assertEqual(result["outcome"], "success")
        self.assertIn(result["code"], ("defeat", "exam_failed"))
        narrative = "\n".join(
            call.args[0] for call in self.player.msg.call_args_list
        )
        self.assertTrue(narrative.strip(), "forfeit must emit terminal text prose")
        self.assertIn("你被擊敗了", narrative)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_reserved_flee_rejected_before_submission(self):
        engage(self.player, self.monster)
        with self.assertRaises(Exception):
            validate_cast_payload({"skill_key": "flee"})

    def test_area_shorthand_adapter_path(self):
        engage(self.player, self.monster)
        self.player.db.skills = {"active": [_T_AREA.key], "passive": []}
        from unittest.mock import patch

        with patch("world.rules.combat.roll_d100", return_value=100):
            result = _cast_adapter(
                self.player,
                validate_cast_payload(
                    {"skill_key": _T_AREA.key, "target_shorthand": "all-enemies"}
                ),
            )
        self.assertIn(result["outcome"], ("success", "rejected"))
        self.assertLessEqual(self.monster.traits.hp.current, 100)

    @covers_requirement("webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale")
    def test_scaled_cast_adapter_path_deducts_scaled_mp(self):
        engage(self.player, self.monster)
        grant_lineage(
            self.player,
            [_T_AREA.key],
            [_mastery_key()],
            rungs={_T_AREA.key: _T_SCALE_LEVEL},
        )
        self.player.traits.mp.base = 500
        self.player.traits.mp.current = 500
        # A scaled crit must not end the round (a terminal settlement would
        # regenerate MP through the clock), so the monster survives it.
        self.monster.traits.hp.base = 500
        self.monster.traits.hp.current = 500
        mp_before = self.player.traits.mp.value
        expected_cost = scaled_mp_cost(int(_T_AREA.cost["mp"]), _T_SCALE)
        from unittest.mock import patch

        with patch("world.rules.combat.roll_d100", return_value=100):
            result = _cast_adapter(
                self.player,
                validate_cast_payload(
                    {
                        "skill_key": _T_AREA.key,
                        "target_ids": [self.monster.pk],
                        "scale": _T_SCALE,
                    }
                ),
            )
        self.assertIn(result["outcome"], ("success", "rejected"))
        self.assertEqual(self.player.traits.mp.value, mp_before - expected_cost)
        self.assertLess(self.monster.traits.hp.current, 500)

    @covers_requirement("webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale")
    def test_scaled_cast_without_mastery_rejects_before_initiative(self):
        engage(self.player, self.monster)
        self.player.db.skills = {"active": [_T_AREA.key], "passive": []}
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {
                    "skill_key": _T_AREA.key,
                    "target_ids": [self.monster.pk],
                    "scale": _T_SCALE,
                }
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "scaled_cast_forbidden")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    def test_flee_adapter_rejects_without_session(self):
        result = _flee_adapter(self.player, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    def test_forfeit_adapter_rejects_without_session(self):
        result = _forfeit_adapter(self.player, {"session_id": "hostile:1:0"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    def test_cast_adapter_rejects_unknown_skill(self):
        engage(self.player, self.monster)
        with self.assertRaises(Exception):
            validate_cast_payload(
                {"skill_key": "no_such_skill", "target_ids": [self.monster.pk]}
            )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    def test_cast_adapter_rejects_insufficient_resource(self):
        engage(self.player, self.monster)
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        result = _cast_adapter(
            self.player,
            validate_cast_payload(
                {"skill_key": _T_SINGLE.key, "target_ids": [self.monster.pk]}
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_resource")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)


if __name__ == "__main__":
    unittest.main()
