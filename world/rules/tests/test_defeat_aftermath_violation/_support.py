"""Defeat-aftermath violation fixtures and bases for the `test_defeat_aftermath_violation` slices.

Module-level fixtures, helpers, and the shared isolation bases moved verbatim
from the original flat module (not a collected test module).
"""
import unittest


from dataclasses import replace as dataclass_replace


from unittest.mock import patch


from django.test import override_settings


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTestCase


import world.rules.defeat_aftermath as defeat_aftermath_module


import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module


from typeclasses.monsters import Monster


from typeclasses.npcs import NPC


from typeclasses.rooms import Room


from world.quests.catalog import register_catalog


from world.rules import clock as clock_module


from world.rules import combat_session as combat_session_module


from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    forfeit,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)


from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    load_defeat_aftermath_sections,
    register_violation_hook,
    run_violation_sequence,
)


from world.rules.clock import WorldClock


from world.rules.event_log import render_plain_text


from world.rules.party import join_party


from world.rules.state_derived_roll import derived_roll


from tools.spec_traceability import covers_requirement


from .._combat_session_helpers import BattlefieldIsolation, _player


def _aftermath_logs(result):
    """Return the defeat aftermath EventLog of one settlement result."""
    return [
        log for log in result["logs"] if log.skill_key == "defeat_aftermath"
    ]


def _aftermath_entries(result):
    """Return the aftermath's ordered EventEntry list of one settlement."""
    (log,) = _aftermath_logs(result)
    return list(log.entries)


def _kinds(entries):
    return [entry.kind for entry in entries]


class ViolationBase(BattlefieldIsolation, EvenniaTestCase):
    """Shared clock isolation, hook save/restore, and lore-keyed winners.

    The production hook body registers at import (DA4 D-V6). Every test
    saves the process-wide hook and restores exactly that value, then
    re-registers the engine, so test order can never leave the global in a
    mutated state (rubber-duck implementation review finding 5).
    """

    def setUp(self):
        super().setUp()
        # The resist contest's affinity config validates quest keys against
        # the quest definition registry (same bootstrap as the coercion suites).
        register_catalog()
        self.room = create_object(Room, key="violation arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = self._lore_monster("哥布林")
        self.monster.location = self.room
        self.clock = WorldClock()
        for target in (
            "world.rules.combat_session.settlement.get_world_clock",
            "world.rules.clock.get_world_clock",
        ):
            patcher = patch(target, return_value=self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(
            setattr,
            defeat_aftermath_violation_module,
            "_VIOLATION_HOOK",
            defeat_aftermath_violation_module._VIOLATION_HOOK,
        )
        register_violation_hook(run_violation_sequence)

    def _lore_monster(self, name, atk=10):
        """Create one tier-floor monster keyed by a lore species name."""
        monster = create_object(Monster, key=name)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 100
        monster.traits.hp.current = 100
        monster.traits.atk_phys.base = atk
        return monster

    def _companion(self, key):
        """Create one co-located companion bound to the player's party."""
        companion = create_object(NPC, key=key)
        companion.location = self.room
        companion.race = "human"
        companion.apply_race_baseline()
        join_party(companion, self.player)
        return companion

    def _equalize_scores(self, *extra):
        """Make the resist contest a pure roll gate: resisted iff roll >= 51.

        With equal blended scores on both sides the shipped contest formula
        (roll + resister_score >= 51 + actor_score) reduces to the raw roll.
        """
        for entity in (self.player, self.monster, *extra):
            entity.traits.agility.base = 10
            entity.traits.atk_phys.base = 10

    def _arouse(self, pleasure):
        """Raise the winner's pleasure to simulate mid-fight accumulation."""
        self.monster.sexual.pleasure.base = pleasure

    def _defeat(self):
        """Drive one hostile defeat settlement through ``forfeit``."""
        engage(self.player, self.monster)
        return self._settle()

    def _settle(self):
        """Lose and forfeit the already-engaged session."""
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        return forfeit(self.player)

    def _knock_out(self, companion):
        """Mark one companion knocked out on the durable record (and floor)."""
        companion.traits.hp.current = 1
        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(
                record,
                knocked_out_ids=(*record.knocked_out_ids, int(companion.pk)),
            ),
        )

    def _flee(self, companion):
        """Mark one companion fled on the durable record."""
        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(
                record,
                fled_ids=(*record.fled_ids, int(companion.pk)),
            ),
        )

    def _patch_rolls(self, rolls):
        """Patch the engine's derivation to return ``rolls`` by attempt index."""
        return patch.object(
            defeat_aftermath_violation_module,
            "derived_roll",
            side_effect=lambda *args: rolls[args[3]],
        )

    def _patch_purpose_rolls(self, target_rolls, resist_rolls):
        """Patch the derivation purpose-aware (companion-victims D-P1).

        ``target_rolls[attempt_index]`` feeds the target-selection draws
        (purpose ``target``); ``resist_rolls[attempt_index]`` feeds the
        resist contests (purpose ``resist``).
        """

        def roll(session_id, violator_key, victim_key, attempt_index, purpose):
            if purpose == "target":
                return target_rolls[attempt_index]
            return resist_rolls[attempt_index]

        return patch.object(
            defeat_aftermath_violation_module,
            "derived_roll",
            side_effect=roll,
        )


class EventSourceIsolation:
    """Snapshot/restore the process-global clock event-source registry."""

    def isolate_event_sources(self) -> None:
        backup = dict(clock_module._EVENT_SOURCES)
        clock_module._EVENT_SOURCES.clear()
        self.addCleanup(self._restore_event_sources, backup)

    def _restore_event_sources(self, backup) -> None:
        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(backup)


