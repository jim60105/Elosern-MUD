"""Slice of ``test_combat_session_flow``: InnateSkillTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch
from dataclasses import replace
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill
from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from ..combat_fixtures import grant_lineage


from ._support import (
    _T_CAST,
    _T_PASSIVE,
    _basic_attack_row,
    _innate_keys,
    _live_registry,
    _open_scope,
)


class InnateSkillTests(EvenniaTest):
    def setUp(self):
        _open_scope(self)
        super().setUp()

    @covers_requirement("universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data")
    def test_no_skill_entity_owns_both_innate_actions(self):
        attack_key, flee_key, innate, unlock_free = _innate_keys()
        player = _player()
        player.db.skills = None
        self.assertEqual(
            player.skills.owned_keys(),
            [
                flee_key,
                attack_key,
                *unlock_free,
            ],
        )
        self.assertIn(attack_key, innate)

    def test_full_import_list_plus_innate(self):
        attack_key, flee_key, _, unlock_free = _innate_keys()
        player = _player()
        player.db.skills = {"active": [_T_CAST], "passive": [_T_PASSIVE]}
        self.assertEqual(
            player.skills.owned_keys(),
            [
                _T_CAST,
                _T_PASSIVE,
                flee_key,
                attack_key,
                *unlock_free,
            ],
        )

    def test_monster_instance_can_fight_without_spawned_skills(self):
        attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
        monster = create_object(Monster, key="bare")
        monster.db.skills = None
        self.assertIn(attack_key, monster.skills.owned_keys())

    def test_basic_attack_is_zero_cost_single_enemy_physical(self):
        skill = _basic_attack_row()
        self.assertEqual(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.target_spec, TargetSpec.SINGLE)
        self.assertEqual(skill.cost, {})
        # D-7 (field-combat initiation): the flag governs SELECTION only, so
        # the innate attack is selectable from exploration as the field-combat
        # initiation; the damaging-action gate keeps it unable to resolve
        # without a battlefield.
        self.assertTrue(skill.usable_out_of_combat)
        self.assertTrue(any(e.startswith("damage:") for e in skill.effects))

    @covers_requirement(
        "universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data"
    )
    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_basic_attack_selectable_out_of_combat_but_damage_gated(self):
        player = _player()
        player.location = create_object(Room, key="bare room")
        mp_before = player.traits.mp.value
        hp_before = player.traits.hp.value
        request = ActionRequest(
            player,
            BASIC_ATTACK_KEY,
            [player],
            __import__(
                "world.rules.targeting", fromlist=["RoomActionContext"]
            ).RoomActionContext(player.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        # The usable_out_of_combat gate no longer rejects it (it is
        # deliberately selectable outside combat); the damaging-action gate
        # rejects instead, before any resource or damage step.
        self.assertEqual(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertEqual(player.traits.mp.value, mp_before)
        self.assertEqual(player.traits.hp.value, hp_before)
