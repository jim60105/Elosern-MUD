"""Behavior tests for the terrain-marker ground hazard primitive and lifecycle."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.monsters import Monster
from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    load_buff_definitions,
    remove_ground_markers,
    tick_buffs,
)
from world.rules.combat_session import (
    engage,
    is_in_active_session,
    read_session,
    submit_player_action,
)
from world.rules.party import join_party
from world.rules.target_facts import matches_target_predicate
from world.rules.tests._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import grant_lineage
from world.tests.synthetic_data import SYNTH_SKILLS

_T_CAST = SYNTH_SKILLS["t_ember_burst"].key

_SYNTH_GROUND_MARKER = BuffDefinition(
    key="t_ground_hazard",
    duration=30,
    tick_interval=10,
    stacking="refresh",
    modifiers={"rate": {"target": "hp", "delta": -10}},
    polarity="debuff",
    marker="ground",
)

_SYNTH_CONTROL_BUFF = BuffDefinition(
    key="t_control_buff",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
    polarity="buff",
    marker=None,
)


def _write_yaml(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    handle.write(content)
    handle.close()
    return Path(handle.name)


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = _race_key()
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    npc.traits.agility.base = agility
    join_party(npc, player)
    return npc


class TerrainMarkerDefinitionTests(unittest.TestCase):
    """Load-time validation for the marker: ground buff definition clause."""

    @covers_requirement(
        "terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact"
    )
    def test_marker_ground_loads_carrying_clause(self):
        path = _write_yaml("- key: fissure\n  marker: ground\n")
        definitions = load_buff_definitions(path)
        self.assertEqual(definitions["fissure"].marker, "ground")

    def test_marker_omitted_defaults_to_none(self):
        path = _write_yaml("- key: ordinary_buff\n")
        definitions = load_buff_definitions(path)
        self.assertIsNone(definitions["ordinary_buff"].marker)

    @covers_requirement(
        "terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact"
    )
    def test_malformed_marker_clause_fails_closed(self):
        for bad_value in ("fire", "water", "true", "false", "3", "null", "['ground']"):
            with self.subTest(bad_value=bad_value):
                path = _write_yaml(f"- key: bad_marker_row\n  marker: {bad_value}\n")
                with self.assertRaises(ValueError) as ctx:
                    load_buff_definitions(path)
                self.assertIn("bad_marker_row", str(ctx.exception))
                self.assertIn("invalid marker", str(ctx.exception))


class TerrainMarkerLifecycleTests(BattlefieldIsolation, EvenniaTestCase):
    """Behavior tests for marker ticking, standing-on-it fact, and exit extinguishment."""

    def setUp(self):
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            "monster_tiers",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.buff_patch = patch.dict(
            BUFF_DEFINITIONS,
            {
                _SYNTH_GROUND_MARKER.key: _SYNTH_GROUND_MARKER,
                _SYNTH_CONTROL_BUFF.key: _SYNTH_CONTROL_BUFF,
            },
        )
        self.buff_patch.start()
        self.addCleanup(self.buff_patch.stop)

        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        self.monster = _monster("goblin", hp=100)
        self.monster.location = self.room

    def tearDown(self):
        super().tearDown()
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)

    @covers_requirement(
        "terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact"
    )
    def test_marker_hazard_damages_holder_while_it_lasts(self):
        """A ground marker damages its holder each tick interval; standing-on-it fact holds until expiry."""
        target = self.monster
        target.traits.hp.base = 100
        target.traits.hp.current = 100
        apply_buff(target, "t_ground_hazard")

        # Holding it is the canonical standing-on-it fact
        self.assertIn("t_ground_hazard", entity_active_buffs(target))
        self.assertTrue(matches_target_predicate(target, ("buff:t_ground_hazard",)))
        self.assertFalse(matches_target_predicate(target, ("buff:t_control_buff",)))

        # Tick 10 seconds: 1 tick interval of -10 HP
        records = tick_buffs(target, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].delta, -10)
        self.assertEqual(target.traits.hp.current, 90)
        self.assertTrue(matches_target_predicate(target, ("buff:t_ground_hazard",)))

        # Tick another 10 seconds: another -10 HP
        records = tick_buffs(target, 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(target.traits.hp.current, 80)
        self.assertTrue(matches_target_predicate(target, ("buff:t_ground_hazard",)))

        # Tick 10 seconds (total 30s == duration): buff expires
        tick_buffs(target, 10)
        self.assertEqual(target.traits.hp.current, 70)
        self.assertNotIn("t_ground_hazard", entity_active_buffs(target))
        self.assertFalse(matches_target_predicate(target, ("buff:t_ground_hazard",)))

        # Further clock advances deal zero damage
        tick_buffs(target, 10)
        self.assertEqual(target.traits.hp.current, 70)

    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_pure_remove_ground_markers_removes_only_ground_markers(self):
        """remove_ground_markers removes ground-marker buffs and leaves control buffs untouched."""
        apply_buff(self.player, "t_ground_hazard")
        apply_buff(self.player, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertIn("t_control_buff", entity_active_buffs(self.player))
        hp_before = self.player.traits.hp.current

        removed = remove_ground_markers(self.player)
        self.assertEqual(removed, 1)
        self.assertNotIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertIn("t_control_buff", entity_active_buffs(self.player))
        self.assertEqual(self.player.traits.hp.current, hp_before)

        # Idempotent: second call returns 0 and writes nothing
        self.assertEqual(remove_ground_markers(self.player), 0)
        self.assertEqual(self.player.traits.hp.current, hp_before)

    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_fleeing_extinguishes_marker_while_control_buff_persists(self):
        """A fleeing participant steps off the ground hazard at flee settlement; control buff persists."""
        engage(self.player, self.monster)
        apply_buff(self.player, "t_ground_hazard")
        apply_buff(self.player, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertIn("t_control_buff", entity_active_buffs(self.player))

        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, "flee", [])
        self.assertEqual(result["outcome"], "fled")

        # Ground marker was swept at flee settlement
        self.assertNotIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertFalse(matches_target_predicate(self.player, ("buff:t_ground_hazard",)))

        # Control buff persists across session boundary untouched
        self.assertIn("t_control_buff", entity_active_buffs(self.player))
        self.assertTrue(matches_target_predicate(self.player, ("buff:t_control_buff",)))

    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_knockout_extinguishes_marker_while_control_buff_persists(self):
        """A knocked out participant has ground marker extinguished at round settlement; control buff persists."""
        companion = _companion(self.player, "fellow_fighter", hp=50)
        engage(self.player, self.monster)
        apply_buff(companion, "t_ground_hazard")
        apply_buff(companion, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(companion))
        self.assertIn("t_control_buff", entity_active_buffs(companion))

        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch(
                "world.rules.combat_session.rounds._knocked_out_ids",
                return_value=(int(companion.pk),),
            ),
        ):
            submit_player_action(self.player, _T_CAST, [self.monster])

        # Companion's ground marker was swept on knockout
        self.assertNotIn("t_ground_hazard", entity_active_buffs(companion))
        self.assertFalse(matches_target_predicate(companion, ("buff:t_ground_hazard",)))

        # Control buff persists on knocked out companion
        self.assertIn("t_control_buff", entity_active_buffs(companion))
        self.assertTrue(matches_target_predicate(companion, ("buff:t_control_buff",)))

    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_session_end_sweeps_markers_only(self):
        """When a combat session ends, ground markers are swept while non-marker buffs persist."""
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)

        apply_buff(self.player, "t_ground_hazard")
        apply_buff(self.player, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertIn("t_control_buff", entity_active_buffs(self.player))

        # Win the fight: monster dies in 1 hit
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertFalse(is_in_active_session(self.player))

        # Ground marker was swept at session teardown
        self.assertNotIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertFalse(matches_target_predicate(self.player, ("buff:t_ground_hazard",)))

        # Control buff persists with its remaining duration
        self.assertIn("t_control_buff", entity_active_buffs(self.player))
        self.assertTrue(matches_target_predicate(self.player, ("buff:t_control_buff",)))

    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_active_holder_keeps_marker_across_rounds(self):
        """A combatant surviving rounds untouched keeps their ground marker across round boundaries until duration expiry."""
        self.monster.traits.hp.base = 1000
        self.monster.traits.hp.current = 1000
        engage(self.player, self.monster)

        apply_buff(self.player, "t_ground_hazard")
        self.assertIn("t_ground_hazard", entity_active_buffs(self.player))

        # Submit a round that does not end the fight
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "round")
        self.assertTrue(is_in_active_session(self.player))

        # Still-active holder's ground marker persists across the round!
        self.assertIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertTrue(matches_target_predicate(self.player, ("buff:t_ground_hazard",)))
