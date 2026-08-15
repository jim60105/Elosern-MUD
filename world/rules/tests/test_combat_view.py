"""Frozen combat-session view model tests (tasks 1.4)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.combat_session import engage
from world.rules.combat_view import (
    CombatViewError,
    ROOT_ACTIONS,
    SECONDARY_ACTIONS,
    build_combat_view,
)
from .combat_fixtures import BattlefieldIsolation


def _player(key="view player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="view goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class CombatViewTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="view arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.monster = _monster()
        self.monster.location = self.room

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_view_preserves_persisted_participant_order_and_tokens(self):
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        self.assertFalse(view.recovery)
        self.assertEqual(view.session.mode, "hostile")
        self.assertEqual(view.session.round, 0)
        self.assertEqual(view.session.state, "ready")
        self.assertIsNone(view.session.reason)
        self.assertEqual(
            [(p.token, p.team, p.identity) for p in view.participants],
            [("a1", "party", self.player.pk), ("e1", "foes", self.monster.pk)],
        )
        self.assertEqual(view.root_actions, ROOT_ACTIONS)
        self.assertEqual(view.secondary_actions, SECONDARY_ACTIONS)
        for participant in view.participants:
            self.assertEqual(
                participant.portrait_ref, str(participant.identity)
            )
            self.assertGreater(participant.identity, 0)
            self.assertEqual(participant.state, "active")
            self.assertEqual(participant.hp_maximum, 100)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_skills_follow_handler_order_and_exclude_passives(self):
        self.player.db.skills = {
            "active": ["wind_blade", "fire_ball"],
            "passive": ["defense_instinct"],
        }
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        keys = [skill.key for skill in view.skills]
        self.assertEqual(
            keys,
            [
                "wind_blade",
                "fire_ball",
                "flee",
                "basic_attack",
            ],
        )
        self.assertNotIn("defense_instinct", keys)
        wind = next(skill for skill in view.skills if skill.key == "wind_blade")
        self.assertEqual(wind.target_spec, "area")
        # With free targeting every approved shorthand expands to valid
        # candidates, so all three are exposed as conveniences.
        self.assertEqual(wind.shorthands, ("all-enemies", "all-allies", "all"))
        self.assertTrue(wind.enabled)
        # With ANY scope every relation passes the faction check, so the
        # actor itself is also a valid explicit target for the area skill.
        self.assertEqual(wind.valid_target_ids, (self.player.pk, self.monster.pk))
        fire = next(skill for skill in view.skills if skill.key == "fire_ball")
        self.assertEqual(fire.cost, {"mp": 14})
        self.assertEqual(fire.element, "fire")

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_freeform_scales_only_for_a_masters_eligible_spells(self):
        self.player.db.skills = {
            "active": ["wind_blade", "gale_step"],
            "passive": [],
        }
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == "wind_blade")
        self.assertEqual(wind.freeform_scales, ())
        gale = next(skill for skill in view.skills if skill.key == "gale_step")
        self.assertEqual(gale.freeform_scales, ())

        self.player.db.skills = {
            "active": ["wind_blade", "gale_step"],
            "passive": ["wind_mastery"],
        }
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == "wind_blade")
        self.assertEqual(
            wind.freeform_scales,
            (
                (0.25, "1/4", 4),
                (0.5, "1/2", 7),
                (1.0, "1", 14),
                (2.0, "2", 28),
                (4.0, "4", 56),
            ),
        )
        gale = next(skill for skill in view.skills if skill.key == "gale_step")
        self.assertEqual(gale.freeform_scales, ())

        # Wind mastery never advertises scales for another element's spells.
        self.player.db.skills = {
            "active": ["light_arrow"],
            "passive": ["wind_mastery"],
        }
        view = build_combat_view(self.player)
        light = next(skill for skill in view.skills if skill.key == "light_arrow")
        self.assertEqual(light.freeform_scales, ())

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_disabled_skill_keeps_stable_reason(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == "fire_ball")
        self.assertFalse(fire.enabled)
        self.assertEqual(fire.reason_code, "insufficient_resource")
        self.assertTrue(fire.reason_message.strip())
        self.assertTrue(fire.label.strip())
        self.assertTrue(fire.description.strip())

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_tier_blocked_spell_descriptor_is_disabled(self):
        self.player.db.skills = {
            "active": ["firestorm"],
            "passive": [],
        }
        self.player.traits.mp.base = 50
        self.player.traits.mp.current = 50
        engage(self.player, self.monster)

        # magic level 15 with no affinities and no mastery: floor(15 * 1.0)
        # == 15 is below the 術師 threshold (16), so the descriptor is
        # disabled with the unknown-skill reason code.
        self.player.traits.magic_level.base = 15
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == "firestorm")
        self.assertFalse(fire.enabled)
        self.assertEqual(fire.reason_code, "unknown_skill")

        # The same actor at magic level 30 passes the gate: the descriptor
        # stays enabled, proving the assertion is about the tier gate alone.
        self.player.traits.magic_level.base = 30
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == "firestorm")
        self.assertTrue(fire.enabled)

    @covers_requirement("webclient-combat-menu::menu-target-shorthands-are-convenience-ui")
    def test_any_skill_offers_companion_as_explicit_target_alongside_shorthands(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="view companion", location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        self.player.db.skills = {
            "active": ["wind_blade", "fire_ball"],
            "passive": [],
        }
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == "wind_blade")
        self.assertTrue(wind.enabled)
        # The menu's all-enemies shorthand remains a convenience, while the
        # freely-targetable skill also lists the ally companion as an explicit
        # target — the shorthand neither widens nor narrows the scope.
        self.assertEqual(wind.shorthands, ("all-enemies", "all-allies", "all"))
        self.assertIn(self.monster.pk, wind.valid_target_ids)
        self.assertIn(companion.pk, wind.valid_target_ids)
        fire = next(skill for skill in view.skills if skill.key == "fire_ball")
        self.assertIn(companion.pk, fire.valid_target_ids)

    @covers_requirement("webclient-combat-menu::combat-context-actions-are-an-exact-read-only-panel")
    def test_view_is_read_only(self):
        engage(self.player, self.monster)
        before = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
            "mp": self.player.traits.mp.current,
        }
        view = build_combat_view(self.player)
        self.assertTrue(view.participants)
        after = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
            "mp": self.player.traits.mp.current,
        }
        self.assertEqual(before, after)

    def test_no_session_raises_view_error(self):
        with self.assertRaises(CombatViewError):
            build_combat_view(self.player)

    def test_unreconstructable_participant_yields_recovery_view(self):
        engage(self.player, self.monster)
        self.monster.delete()
        view = build_combat_view(self.player)
        self.assertTrue(view.recovery)
        self.assertEqual(view.session.state, "recovery")
        self.assertIsNotNone(view.session.reason)
        self.assertEqual(view.root_actions, ())
        self.assertEqual(view.secondary_actions, ("forfeit",))
        self.assertEqual(view.participants, ())
        self.assertEqual(view.skills, ())

    def test_participant_states_fled_knocked_out_and_defeated(self):
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        engage(self.player, self.monster)
        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [self.monster.pk],
            }
        )
        _persist(self.player, record)
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "fled")

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [],
                "knocked_out_ids": [self.monster.pk],
            }
        )
        _persist(self.player, record)
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "knocked_out")

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [],
                "knocked_out_ids": [],
            }
        )
        _persist(self.player, record)
        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "defeated")

    def test_hp_maximum_falls_back_when_trait_max_missing(self):
        engage(self.player, self.monster)
        from unittest.mock import patch

        with patch.object(type(self.monster.traits.hp), "max", None, create=True):
            view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertGreaterEqual(monster_view.hp_maximum, 1)


if __name__ == "__main__":
    unittest.main()
