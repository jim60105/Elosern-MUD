"""Tests for the read-only scripted dialogue service (scripted-dialogue D3/D4).

These EvenniaTest cases exercise ``world.rules.dialogue`` component resolution,
keyword lookup, greetings, and the guard's stateful exception. The guild-master
dialogue is exercised through the sync-attached ``ScriptedDialogue`` host and
the ``talk`` command.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import GuildStaff, OnboardingGuide, ScriptedDialogue
from typeclasses.npcs import NPC
from world.onboarding.guide import GuideProgress
from world.onboarding.guide_dialogue import (
    GUARD_DIALOGUE_KEY,
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    NO_UNDERSTANDING_LINE,
)
from world.rules.dialogue import (
    dialogue_key_for,
    dialogue_response,
    greeting_for,
    is_dialogue_host,
    resolve_dialogue_component,
)
from world.rules.onboarding import run_scripted_talk, snapshot_for


class ScriptedDialogueServiceTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        # Register the quest catalog in this class's own setup: scripted talk
        # reaches the affinity rulebook load (through ``run_scripted_talk``),
        # which resolves ``introductory_hunt`` from the definition registry,
        # so this class must not depend on an earlier test to have registered
        # it.
        from world.quests.catalog import register_catalog

        register_catalog()
        self.player = create_object(NPC, key="talker")

    def _scripted_host(self, dialogue_key: str = GUILD_STAFF_DIALOGUE_KEY) -> NPC:
        host = create_object(NPC, key="scripted-host")
        host.components.add(ScriptedDialogue.create(host, dialogue_key=dialogue_key))
        return host

    def _guard(self) -> NPC:
        guard = create_object(NPC, key="guard")
        guard.components.add(OnboardingGuide.create(guard, dialogue_key=GUARD_DIALOGUE_KEY))
        return guard

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_scripted_host_is_a_dialogue_host(self):
        host = self._scripted_host()
        self.assertTrue(is_dialogue_host(host))
        self.assertEqual(dialogue_key_for(host), GUILD_STAFF_DIALOGUE_KEY)
        component = resolve_dialogue_component(host)
        self.assertIsInstance(component, ScriptedDialogue)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_scripted_host_answers_known_keyword(self):
        host = self._scripted_host()
        response = dialogue_response(host, self.player, "公會")
        self.assertIn("guild list", response)

    @covers_requirement("scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed")
    def test_unknown_keyword_yields_no_understanding(self):
        host = self._scripted_host()
        self.assertEqual(dialogue_response(host, self.player, "謎語"), NO_UNDERSTANDING_LINE)

    @covers_requirement("scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed")
    def test_missing_table_yields_no_understanding_and_no_greeting(self):
        host = self._scripted_host(dialogue_key="no_such_table")
        self.assertEqual(dialogue_response(host, self.player, "公會"), NO_UNDERSTANDING_LINE)
        self.assertIsNone(greeting_for(host))

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_no_keyword_talk_presents_the_greeting(self):
        host = self._scripted_host()
        greeting = greeting_for(host)
        self.assertIsNotNone(greeting)
        self.assertIn("guild register", greeting)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_missing_greeting_falls_back_to_none(self):
        guard = self._guard()
        self.assertIsNone(greeting_for(guard))

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_scripted_host_without_greeting_answers_talk_without_state_change(self):
        from commands.talk import CmdsTalk
        from typeclasses.characters import PlayerCharacter

        # The guard's table is the only registered definition with greeting=None;
        # a generic ScriptedDialogue host pointing at it exercises the
        # no-keyword fallback branch (not the OnboardingGuide guard branch).
        host = create_object(NPC, key="greetingless", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUARD_DIALOGUE_KEY)
        )
        player = create_object(PlayerCharacter, key="greetingless-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        player.location = self.room1
        output = self.call(CmdsTalk(), host.key, caller=player)
        self.assertIn("沒有理會", output)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ())

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_componentless_npc_is_not_a_host(self):
        plain = create_object(NPC, key="plain")
        self.assertFalse(is_dialogue_host(plain))
        self.assertIsNone(resolve_dialogue_component(plain))
        self.assertIsNone(dialogue_response(plain, self.player, "公會"))
        self.assertIsNone(greeting_for(plain))

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_scripted_dialogue_causes_no_state_change(self):
        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="guild-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        host = self._scripted_host()
        dialogue_response(host, player, "公會")
        greeting_for(host)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ())

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_guild_staff_turnin_keyword_for_unregistered_member_falls_back_to_authored_line(self):
        # The host must be the sole local staff (the sole-host rule applies to
        # every caller), so an unregistered member still resolves the listing
        # path and gets the authored register-first line, never the listing.
        from typeclasses.characters import PlayerCharacter
        from typeclasses.components import GuildStaff
        from typeclasses.rooms import Room

        room = create_object(Room, key="hall")
        player = create_object(PlayerCharacter, key="unregistered-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        player.location = room
        host = self._scripted_host()
        host.location = room
        host.components.add(
            GuildStaff.create(host, service_id="staff", branch_key="guild_branch_altoria")
        )
        response = dialogue_response(host, player, GUILD_STAFF_TURNIN_KEYWORD)
        self.assertIn("guild register", response)
        self.assertNotIn("可以交回", response)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ())

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_turnin_keyword_on_non_guild_host_is_an_unknown_keyword(self):
        guard = self._guard()
        response = dialogue_response(guard, self.player, GUILD_STAFF_TURNIN_KEYWORD)
        self.assertEqual(response, NO_UNDERSTANDING_LINE)

    @covers_requirement(
        "scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines",
        "onboarding-guide::talk-behaves-predictably-for-any-npc",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
    )
    def test_guard_known_keyword_writes_progress_and_unknown_writes_nothing(self):
        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="guard-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        guard = self._guard()
        result = run_scripted_talk(guard, player, "公會")
        self.assertIn("冒險者公會", result.response)
        self.assertFalse(result.budget_capped)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ("公會",))
        self.assertEqual(guard.relations.affinity_for(player), 1)
        unknown = run_scripted_talk(guard, player, "謎語")
        self.assertIn("明白", unknown.response)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ("公會",))
        self.assertEqual(guard.relations.affinity_for(player), 1)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_failed_guard_talk_write_restores_both_surfaces(self):
        from unittest.mock import patch

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="guard-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        guard = self._guard()
        progress_before = player.guide_progress
        relations_before = guard.db.relations_data

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                run_scripted_talk(guard, player, "公會")
        self.assertEqual(player.guide_progress, progress_before)
        self.assertEqual(guard.db.relations_data, relations_before)
        self.assertEqual(snapshot_for(player).guide_progress.seen_keywords, ())

    @covers_requirement("affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_budget_capped_talk_presents_the_non_numeric_hint(self):
        from commands.talk import CmdsTalk
        from typeclasses.characters import PlayerCharacter

        guard = self._guard()
        guard.location = self.room1
        player = create_object(PlayerCharacter, key="capped-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.guide_progress = GuideProgress.active().to_storage()
        player.location = self.room1
        for _ in range(5):
            self.call(CmdsTalk(), f"{guard.key} 公會", caller=player)
        from world.rules.affinity import AFFINITY_DAILY_CAP_HINT

        output = self.call(CmdsTalk(), f"{guard.key} 公會", caller=player)
        self.assertIn(AFFINITY_DAILY_CAP_HINT, output)
        self.assertEqual(guard.relations.affinity_for(player), 5)

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_every_taught_guild_command_resolves_to_a_registered_command(self):
        from commands.default_cmdsets import CharacterCmdSet

        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        taught = [
            "guild register",
            "guild list",
            "guild accept",
            "guild log",
            "guild show",
            "guild turnin",
            "guild abandon",
            "guild merit",
        ]
        keys = {str(command) for command in cmdset.commands}
        for command in taught:
            with self.subTest(command=command):
                self.assertIn(command, keys)

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_guild_staff_definition_teaches_the_guild_commands(self):
        from world.onboarding.guide_dialogue import DIALOGUE_TABLE

        definition = DIALOGUE_TABLE[GUILD_STAFF_DIALOGUE_KEY]
        combined = definition.greeting + "".join(
            entry.response for entry in definition.responses
        )
        for command in (
            "guild register",
            "guild list",
            "guild accept",
            "guild log",
            "guild show",
            "guild turnin",
            "guild abandon",
            "guild merit",
        ):
            self.assertIn(command, combined)


class GuildStaffSyncDialogueTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(NPC, key="placeholder")
        from evennia.utils.create import create_object as co
        from typeclasses.rooms import Room
        from world.maps.bootstrap import (
            GUILD_HALL_TAG,
            sync_grid,
            sync_service_interiors,
        )

        self.hall_room = co(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        from world.quests.catalog import register_catalog
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._quest_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        from world.rules.guild_config import CATALOG, load_catalog_into_cache

        self._previous_catalog = CATALOG
        load_catalog_into_cache()
        from evennia.utils.search import search_object_by_tag
        from world.rules.guild_economy import sync_service_content
        from world.lore.guild import GUILD_BRANCH_REGISTRY

        sync_service_content()
        # The host's key is its authored registry name (service anchor reuse,
        # npc-title-authored-identities D3).
        self.guild_master = NPC.objects.filter(
            db_key=GUILD_BRANCH_REGISTRY["guild_branch_altoria"].host_name
        ).first()

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._quest_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

    def test_sync_attaches_exactly_one_scripted_dialogue(self):
        from world.rules.guild_economy import sync_service_content

        sync_service_content()
        self.assertTrue(self.guild_master.components.has(ScriptedDialogue.name))
        self.assertEqual(
            self.guild_master.components.get(ScriptedDialogue.get_component_slot()).dialogue_key,
            GUILD_STAFF_DIALOGUE_KEY,
        )
        self.assertTrue(self.guild_master.components.has(GuildStaff.name))

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_guild_master_answers_talk_with_command_guidance(self):
        from commands.talk import CmdsTalk

        self.guild_master.location = self.hall_room
        self.char1.location = self.hall_room
        output = self.call(CmdsTalk(), f"{self.guild_master.key} 公會", caller=self.char1)
        self.assertIn("guild list", output)
        self.assertIn("guild turnin", output)

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_no_keyword_talk_presents_the_greeting(self):
        from commands.talk import CmdsTalk

        self.guild_master.location = self.hall_room
        self.char1.location = self.hall_room
        output = self.call(CmdsTalk(), self.guild_master.key, caller=self.char1)
        self.assertIn("guild register", output)

    def _player_state(self):
        return {
            "guide_progress": self.char1.guide_progress,
            "onboarded": self.char1.onboarded,
            "guild_rank": self.char1.guild_rank,
            "guild_registration": self.char1.db.guild_registration,
            "quest_log": list(self.char1.db.quest_log or []),
            "wallet": self.char1.db.wallet,
            "inventory": list(self.char1.db.inventory or []),
        }

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_guild_master_talk_never_writes_player_state(self):
        from commands.talk import CmdsTalk

        self.guild_master.location = self.hall_room
        self.char1.location = self.hall_room
        before = self._player_state()
        self.call(CmdsTalk(), f"{self.guild_master.key} 公會", caller=self.char1)
        self.call(CmdsTalk(), f"{self.guild_master.key} 謎語", caller=self.char1)
        self.call(CmdsTalk(), self.guild_master.key, caller=self.char1)
        self.assertEqual(self._player_state(), before)


if __name__ == "__main__":
    import unittest

    unittest.main()
