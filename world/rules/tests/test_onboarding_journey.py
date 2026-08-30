"""Arrival/guard integration and full-journey onboarding tests (tasks 5.4/6.1).

These ``EvenniaTest`` cases walk the deterministic journey end to end: create ->
activate -> relocate -> arrival scene -> ``look`` -> guard guidance -> guild
registration -> quest acceptance -> wilderness hunt -> turn-in -> ``onboarded``.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.character_creation import CmdCharacter
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from evennia.utils.test_resources import EvenniaCommandTestMixin
from world.maps.bootstrap import (
    GUILD_HALL_EXTERIOR_XYZ,
    GUILD_HALL_TAG,
    SOUTH_GATE_XYZ,
    sync_grid,
    sync_service_interiors,
)
from world.quests.catalog import INTRODUCTORY_HUNT
from world.quests.runtime import QuestState, fulfill_record, read_records
from world.quests.transitions import apply_quest_log_replacement
from world.rules.character_creation import (
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.guild import register_adventurer, turn_in_quest
from world.rules.onboarding import (
    advance_beat,
    guard_adult_identity,
    maybe_play_arrival,
    observe_room_entry,
    relocate_to_starting_location,
    sync_guard_npc,
)
from world.rules.surfaces import read_counter_trait


def _grid(xyz):
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    return XYZRoom.objects.filter_xyz(xyz=xyz).first()


class OnboardingJourneyMixin:
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog
        from world.rules.guild_config import (
            get_catalog,
            register_catalog_offers,
        )

        # Snapshot the process-global registries this setup populates so a
        # parallel worker never sees another journey test's catalog entries
        # (world.quests tests assert empty registries).
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._journey_quest_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._journey_offer_items = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        register_catalog_offers(get_catalog())
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        sync_guard_npc()
        self.gate = _grid(SOUTH_GATE_XYZ)
        self.guild_exterior = _grid(GUILD_HALL_EXTERIOR_XYZ)
        self.hall = create_object(Room, key="altoria_hall")
        self.staff = create_object(NPC, key="staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        self.player = create_object(PlayerCharacter, key="journey-player")
        self.account.at_post_create_character(self.player)
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.gate

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._journey_quest_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._journey_offer_items)
        super().tearDown()

    def _activate(self):
        activate_player_character(
            self.account,
            self.player,
            CharacterCreationRequest(mode="preset", preset_key="human_wanderer"),
        )
        relocate_to_starting_location(self.player)

    def _complete_intro_hunt(self) -> str:
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.quests.runtime import accept_quest

        accept_record = accept_quest(self.player, INTRODUCTORY_HUNT.key)
        completed = fulfill_record(
            accept_record,
            QUEST_DEFINITION_REGISTRY[INTRODUCTORY_HUNT.key],
        )
        records = read_records(self.player)
        apply_quest_log_replacement(
            self.player,
            [completed if r.quest_id == accept_record.quest_id else r for r in records],
        )
        return completed.quest_id


class ArrivalGuardIntegrationTests(OnboardingJourneyMixin, EvenniaTest):
    @covers_requirement("onboarding-guide::new-players-arrive-at-the-capital-s-south-gate")
    def test_activation_arrives_at_south_gate_with_welcome(self):
        self.player.location = self.room1
        messages = []
        self.player.msg = lambda text, **kwargs: messages.append(str(text))
        self._activate()
        self.assertIs(self.player.location, self.gate)
        self.assertTrue(any("踏上了伊洛瑟恩大陸" in message for message in messages))

    def test_arrival_does_not_depend_on_the_guard(self):
        with patch("world.rules.onboarding._south_gate", return_value=self.gate):
            self.player.location = self.room1
            messages = []
            self.player.msg = lambda text, **kwargs: messages.append(str(text))
            self._activate()
        self.assertIs(self.player.location, self.gate)

    @covers_requirement("onboarding-guide::the-arrival-scene-plays-as-the-first-guided-beat")
    def test_arrival_scene_then_look_then_guidance(self):
        messages = []
        self.player.msg = lambda text, **kwargs: messages.append(str(text))
        self._activate()
        self.assertTrue(maybe_play_arrival(self.player))
        joined = "".join(messages)
        self.assertIn("南門", joined)
        self.assertEqual(self.player.onboarding_beat, "look")
        guidance = advance_beat(self.player)
        self.assertIsNotNone(guidance)
        self.assertIn("先向北走到南大道", guidance)
        self.assertIn("冒險者公會外", guidance)
        self.assertTrue(self.player.first_arrival_seen)

    @covers_requirement("onboarding-guide::the-arrival-scene-plays-as-the-first-guided-beat")
    def test_reconnect_replays_incomplete_arrival(self):
        messages = []
        self.player.msg = lambda text, **kwargs: messages.append(str(text))
        self._activate()
        maybe_play_arrival(self.player)
        self.assertFalse(self.player.first_arrival_seen)
        replay = []
        self.player.msg = lambda text, **kwargs: replay.append(str(text))
        self.assertTrue(maybe_play_arrival(self.player))
        self.assertTrue(replay)

    @covers_requirement("onboarding-guide::the-arrival-scene-plays-as-the-first-guided-beat")
    def test_completed_arrival_never_replays(self):
        self._activate()
        maybe_play_arrival(self.player)
        advance_beat(self.player)
        self.assertFalse(maybe_play_arrival(self.player))

    def test_look_elsewhere_does_not_advance(self):
        self._activate()
        maybe_play_arrival(self.player)
        self.player.location = self.guild_exterior
        self.assertIsNone(advance_beat(self.player))
        self.assertFalse(self.player.first_arrival_seen)

    @covers_requirement("onboarding-guide::the-south-gate-guard-offers-scripted-guidance")
    def test_guard_sync_produces_an_adult_guard(self):
        sync_guard_npc()
        from evennia.utils.search import search_object_by_tag

        guards = search_object_by_tag("onboarding_guard")
        self.assertEqual(len(guards), 1)
        age, apparent_age = guard_adult_identity(guards[0])
        self.assertGreaterEqual(age, 18)
        self.assertGreaterEqual(apparent_age, 18)

    @covers_requirement("onboarding-guide::guidance-hands-off-at-the-guild-exterior")
    def test_reaching_guild_exterior_ends_guidance(self):
        self._activate()
        maybe_play_arrival(self.player)
        self.player.onboarding_beat = "guidance"
        self.player.location = self.guild_exterior
        observe_room_entry(self.player)
        from world.rules.onboarding import snapshot_for

        self.assertEqual(snapshot_for(self.player).guide_progress.state, "completed")
        self.assertFalse(self.player.onboarded)

    @covers_requirement("onboarding-guide::guidance-hands-off-at-the-guild-exterior")
    def test_guild_exterior_before_look_ends_arrival_and_never_replays(self):
        self._activate()
        maybe_play_arrival(self.player)
        self.assertFalse(self.player.first_arrival_seen)
        self.player.location = self.guild_exterior
        observe_room_entry(self.player)
        self.assertTrue(self.player.first_arrival_seen)
        self.player.location = self.gate
        self.assertFalse(maybe_play_arrival(self.player))

    @covers_requirement("onboarding-guide::onboarding-state-is-written-only-by-the-deterministic-service")
    def test_corridor_deviation_marks_guide_skipped(self):
        self._activate()
        maybe_play_arrival(self.player)
        self.player.location = self.room1
        observe_room_entry(self.player)
        from world.rules.onboarding import snapshot_for

        self.assertEqual(snapshot_for(self.player).guide_progress.state, "skipped")
        self.assertFalse(self.player.onboarded)


class TalkCommandTests(EvenniaCommandTestMixin, OnboardingJourneyMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        sync_guard_npc()
        from evennia.utils.search import search_object_by_tag

        self.guard = search_object_by_tag("onboarding_guard")[0]

    @covers_requirement("onboarding-guide::talk-behaves-predictably-for-any-npc")
    def test_talk_known_keyword_answers_authored_response(self):
        from commands.talk import CmdsTalk

        output = self.call(CmdsTalk(), f"{self.guard.key} 公會", caller=self.player)
        self.assertIn("冒險者公會", output)

    @covers_requirement("onboarding-guide::talk-behaves-predictably-for-any-npc")
    def test_talk_unknown_keyword_gives_no_understanding(self):
        from commands.talk import CmdsTalk

        output = self.call(CmdsTalk(), f"{self.guard.key} 謎語", caller=self.player)
        self.assertIn("明白", output)

    def test_talk_componentless_npc_gives_no_response(self):
        from commands.talk import CmdsTalk

        plain = create_object(NPC, key="plain", location=self.player.location)
        output = self.call(CmdsTalk(), "plain", caller=self.player)
        self.assertIn("沒有理會", output)

    def test_talk_no_keyword_on_componentless_npc_during_guidance(self):
        from commands.talk import CmdsTalk
        from world.rules.onboarding import maybe_play_arrival

        self._activate()
        maybe_play_arrival(self.player)
        plain = create_object(NPC, key="plain", location=self.player.location)
        output = self.call(CmdsTalk(), "plain", caller=self.player)
        self.assertIn("沒有理會", output)

    def test_talk_resolution_errors_are_distinct(self):
        from commands.talk import CmdsTalk

        missing = self.call(CmdsTalk(), "ghost", caller=self.player)
        self.assertIn("不是", missing)


class TurnInAtomicityTests(OnboardingJourneyMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self._activate()
        self.player.guide_progress = {"state": "active", "seen_keywords": []}
        self.player.onboarding_beat = "guidance"
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    def _turn_in(self, quest_id):
        self.player.location = self.hall
        return turn_in_quest(self.player, self.staff, quest_id)

    @covers_requirement("onboarding-guide::onboarding-state-is-written-only-by-the-deterministic-service")
    def test_first_hunt_turn_in_completes_onboarding(self):
        quest_id = self._complete_intro_hunt()
        result = self._turn_in(quest_id)
        self.assertTrue(result["onboarding_completed"])
        self.assertTrue(self.player.onboarded)

    def test_double_turn_in_does_not_repeat_closing_line(self):
        quest_id = self._complete_intro_hunt()
        first = self._turn_in(quest_id)
        self.assertTrue(first["onboarding_completed"])
        self.assertTrue(self.player.onboarded)
        from world.rules.guild import RewardClaimError

        with self.assertRaises(RewardClaimError):
            self._turn_in(quest_id)
        self.assertTrue(self.player.onboarded)

    @covers_requirement("onboarding-guide::onboarding-state-is-written-only-by-the-deterministic-service")
    def test_turn_in_settlement_failure_rolls_back_onboarding(self):
        quest_id = self._complete_intro_hunt()
        snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.quest_log),
            list(self.player.db.guild_reward_claims or []),
            self.player.onboarded,
        )

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                self._turn_in(quest_id)
        self.assertEqual(
            (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                read_counter_trait(self.player, "guild_merit"),
                list(self.player.db.quest_log),
                list(self.player.db.guild_reward_claims or []),
                self.player.onboarded,
            ),
            snapshot,
        )
        self.assertFalse(self.player.onboarded)


class HelpEntryTests(OnboardingJourneyMixin, EvenniaTest):
    @covers_requirement("onboarding-guide::a-help-entry-explains-onboarding-afterwards")
    def test_help_exposes_the_onboarding_entry(self):
        from world.help_entries import HELP_ENTRY_DICTS

        entries = {entry["key"]: entry for entry in HELP_ENTRY_DICTS}
        self.assertIn("新手引導", entries)
        text = entries["新手引導"]["text"]
        self.assertIn("南門", text)
        self.assertIn("守衛", text)
        self.assertIn("冒險者公會", text)

    @covers_requirement("onboarding-guide::a-help-entry-explains-onboarding-afterwards")
    def test_help_entry_states_the_two_step_route(self):
        from world.help_entries import HELP_ENTRY_DICTS

        entries = {entry["key"]: entry for entry in HELP_ENTRY_DICTS}
        text = entries["新手引導"]["text"]
        self.assertIn("先向北走到南大道", text)
        self.assertIn("再向東抵達冒險者公會外", text)
        self.assertNotIn("中央廣場", text)


class FullJourneyTests(OnboardingJourneyMixin, EvenniaTest):
    @covers_requirement(
        "onboarding-guide::new-players-arrive-at-the-capital-s-south-gate",
        "onboarding-guide::the-arrival-scene-plays-as-the-first-guided-beat",
        "onboarding-guide::the-south-gate-guard-offers-scripted-guidance",
        "onboarding-guide::onboarding-state-is-written-only-by-the-deterministic-service",
    )
    def test_full_first_day_journey_completes_onboarding(self):
        self._activate()
        messages = []
        self.player.msg = lambda text, **kwargs: messages.append(str(text))
        self.assertTrue(maybe_play_arrival(self.player))
        guidance = advance_beat(self.player)
        self.assertIsNotNone(guidance)
        self.player.location = self.guild_exterior
        observe_room_entry(self.player)
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        quest_id = self._complete_intro_hunt()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertTrue(self.player.onboarded)
        self.assertFalse(maybe_play_arrival(self.player))
        from world.rules.onboarding import current_guide_prompt

        self.assertIsNone(current_guide_prompt(self.player))


if __name__ == "__main__":
    import unittest

    unittest.main()
