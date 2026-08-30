"""Frozen combat-session view model tests (tasks 1.4)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.combat_session import engage
from world.rules.combat_view import (
    CATEGORY_LABELS,
    CombatViewError,
    ROOT_ACTIONS,
    SECONDARY_ACTIONS,
    SkillCategory,
    SkillDescriptorView,
    build_combat_view,
    group_skill_views,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.registry import SKILL_REGISTRY
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY


def _descriptor(key: str) -> SkillDescriptorView:
    """Build one minimal frozen skill descriptor from the registry metadata."""
    skill = SKILL_REGISTRY[key]
    return SkillDescriptorView(
        key=key,
        label=skill.label,
        description=skill.description,
        cost=dict(skill.cost),
        target_spec=skill.target_spec.value,
        element=skill.element.key if skill.element is not None else None,
        category=skill.category.value,
        group=skill.group,
        enabled=True,
        reason_code=None,
        reason_message=None,
        valid_target_ids=(),
        shorthands=(),
        freeform_scales=(),
    )


def _skills(*keys: str) -> tuple[SkillDescriptorView, ...]:
    return tuple(_descriptor(key) for key in keys)


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


class CombatViewTests(BattlefieldIsolation, EvenniaTestCase):
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
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
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
        self.player.traits.magic_power.base = 15
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == "firestorm")
        self.assertFalse(fire.enabled)
        self.assertEqual(fire.reason_code, "unknown_skill")

        # The same actor at magic level 30 passes the gate: the descriptor
        # stays enabled, proving the assertion is about the tier gate alone.
        self.player.traits.magic_power.base = 30
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


class GroupSkillViewsTests(unittest.TestCase):
    """Pure ``group_skill_views()`` grouping and ordering tests (task 5.1)."""

    def _categories(self, *keys: str):
        return group_skill_views(_skills(*keys))

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_category_order_follows_enum_declaration_not_ownership(self):
        # The movement skill is granted before the elemental one, but the
        # enum declares elemental_magic before movement.
        groups = self._categories("flash_step", "fire_ball")
        self.assertEqual(
            [category.category for category in groups],
            ["elemental_magic", "movement"],
        )
        self.assertEqual(
            [category.label for category in groups],
            [CATEGORY_LABELS[SkillCategory.ELEMENTAL_MAGIC],
             CATEGORY_LABELS[SkillCategory.MOVEMENT]],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_elemental_sub_groups_follow_registry_order(self):
        # shadow_bolt (dark) precedes fire_ball in ownership order, but
        # ELEMENT_REGISTRY declares fire before dark, so the fire sub-group
        # must come first.
        groups = self._categories("shadow_bolt", "fire_ball")
        elemental = next(
            category for category in groups if category.category == "elemental_magic"
        )
        self.assertEqual(
            [sub_group.group for sub_group in elemental.groups],
            ["fire", "dark"],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_category_with_zero_owned_skills_is_omitted(self):
        groups = self._categories("fire_ball")
        self.assertNotIn(
            "sexual_act", [category.category for category in groups]
        )
        self.assertNotIn(
            "innate_gift", [category.category for category in groups]
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_no_group_category_emits_one_null_keyed_sub_group(self):
        groups = self._categories("dual_blade_mastery")
        martial = next(
            category for category in groups if category.category == "martial_arts"
        )
        self.assertEqual(len(martial.groups), 1)
        self.assertIsNone(martial.groups[0].group)
        self.assertIsNone(martial.groups[0].label)
        self.assertEqual(
            [skill.key for skill in martial.groups[0].skills],
            ["dual_blade_mastery"],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_owned_keys_order_is_preserved_within_each_sub_group(self):
        groups = self._categories("fire_ball", "firestorm", "shadow_bolt")
        elemental = next(
            category for category in groups if category.category == "elemental_magic"
        )
        fire = next(
            sub_group for sub_group in elemental.groups if sub_group.group == "fire"
        )
        self.assertEqual(
            [skill.key for skill in fire.skills],
            ["fire_ball", "firestorm"],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_sexual_act_sub_groups_follow_first_seen_order(self):
        # divine_sexual_arts (神之秘法) is granted before the 精通 masteries,
        # so 神之秘法 must lead even though 精通 precedes it alphabetically.
        groups = self._categories(
            "divine_sexual_arts", "divine_sexual_mastery", "reincarnation_boon_yuna"
        )
        sexual = next(
            category for category in groups if category.category == "sexual_act"
        )
        self.assertEqual(
            [sub_group.label for sub_group in sexual.groups],
            ["神之秘法", "精通"],
        )

    def test_sexual_act_null_group_skill_is_not_dropped(self):
        # A sexual_act skill without a group still gets presented in its own
        # null-keyed sub-group instead of being silently omitted.
        bare = _descriptor("divine_sexual_arts")
        descriptor = SkillDescriptorView(
            key=bare.key,
            label=bare.label,
            description=bare.description,
            cost=bare.cost,
            target_spec=bare.target_spec,
            element=bare.element,
            category=bare.category,
            group=None,
            enabled=True,
            reason_code=None,
            reason_message=None,
            valid_target_ids=(),
            shorthands=(),
            freeform_scales=(),
        )
        groups = group_skill_views((descriptor,))
        sexual = next(
            category for category in groups if category.category == "sexual_act"
        )
        self.assertEqual(len(sexual.groups), 1)
        self.assertIsNone(sexual.groups[0].group)
        self.assertIsNone(sexual.groups[0].label)
        self.assertEqual(
            [skill.key for skill in sexual.groups[0].skills],
            ["divine_sexual_arts"],
        )

    def test_empty_skills_yield_no_categories(self):
        self.assertEqual(group_skill_views(()), ())


if __name__ == "__main__":
    unittest.main()
