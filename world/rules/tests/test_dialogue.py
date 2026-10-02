"""Tests for the scripted dialogue runtime (scripted-dialogue D3/D4).

These EvenniaTest cases exercise ``world.rules.dialogue`` component resolution,
keyword lookup, greetings, and the deterministic scripted-talk affinity writer.
The guild-master dialogue is exercised through the sync-attached
``ScriptedDialogue`` host and the ``talk`` command.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    NO_UNDERSTANDING_LINE,
    dialogue_key_for,
    dialogue_response,
    greeting_for,
    is_dialogue_host,
    misunderstood_line_for,
    offline_greeting_for,
    opens_dialogue,
    resolve_dialogue_component,
    run_scripted_talk,
)
from world.rules.player_messages import dialogue_open_fallback_line
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    live_dialogue_table,
    synthetic_branch_key,
)
from world.tests.synthetic_data import SYNTH_DIALOGUE

# The staff component carries an opaque synthetic branch identity; the
# turnin path never resolves it against any registry, so the kit branch key
# stands in for the former shipped branch token.
SYNTH_BRANCH = synthetic_branch_key()

# The kit-authored dialogue row key (test-data-independence: the predicate is
# exercised against the synthetic table, never shipped prose).
SYNTH_DIALOGUE_KEY = next(iter(SYNTH_DIALOGUE))


def _staff_answer(keyword):
    """The guild_staff table's authored answer to ``keyword``, read live.

    Tests compare the host's answers with its own authored table and never
    pin the prose, so rewording a line breaks nothing.
    """
    definition = live_dialogue_table()[GUILD_STAFF_DIALOGUE_KEY]
    return next(
        entry.response for entry in definition.responses if entry.keyword == keyword
    )


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

    def _affinity_host(self) -> NPC:
        """A scripted host whose every known keyword carries the +1 talk gain."""
        host = create_object(NPC, key="talk-host")
        host.components.add(ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY))
        return host

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
        self.assertEqual(response, _staff_answer("公會"))

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
        self.assertEqual(greeting, live_dialogue_table()[GUILD_STAFF_DIALOGUE_KEY].greeting)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_missing_greeting_falls_back_to_none(self):
        host = self._scripted_host(dialogue_key="no_such_table")
        self.assertIsNone(greeting_for(host))

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_scripted_host_without_greeting_answers_talk_without_state_change(self):
        from commands.talk import CmdsTalk
        from typeclasses.characters import PlayerCharacter

        # A host whose dialogue_key resolves to no definition exercises the
        # no-keyword fallback branch of the talk command.
        host = create_object(NPC, key="greetingless", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key="no_such_table")
        )
        player = create_object(PlayerCharacter, key="greetingless-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.location = self.room1
        output = self.call(CmdsTalk(), host.key, caller=player)
        self.assertIn("沒有理會", output)

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
        host = self._scripted_host()
        relations_before = host.db.relations_data
        dialogue_response(host, player, "公會")
        greeting_for(host)
        self.assertEqual(host.db.relations_data, relations_before)

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
        player.location = room
        host = self._scripted_host()
        host.location = room
        host.components.add(
            GuildStaff.create(host, service_id="staff", branch_key=SYNTH_BRANCH)
        )
        response = dialogue_response(host, player, GUILD_STAFF_TURNIN_KEYWORD)
        self.assertEqual(response, _staff_answer(GUILD_STAFF_TURNIN_KEYWORD))
        self.assertNotIn("可以交回", response)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_turnin_keyword_on_non_guild_host_is_an_unknown_keyword(self):
        host = self._scripted_host(dialogue_key="no_such_table")
        response = dialogue_response(host, self.player, GUILD_STAFF_TURNIN_KEYWORD)
        self.assertEqual(response, NO_UNDERSTANDING_LINE)

    @covers_requirement(
        "scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
    )
    def test_known_keyword_writes_affinity_and_unknown_writes_nothing(self):
        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="talk-host-talker")
        player.race = "human"
        player.apply_race_baseline()
        host = self._affinity_host()
        result = run_scripted_talk(host, player, "公會")
        self.assertIn("冒險者公會", result.response)
        self.assertFalse(result.budget_capped)
        self.assertEqual(host.relations.affinity_for(player), 1)
        unknown = run_scripted_talk(host, player, "謎語")
        self.assertIn("明白", unknown.response)
        self.assertEqual(host.relations.affinity_for(player), 1)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_failed_talk_write_restores_the_relations_surface(self):
        from unittest.mock import patch

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="guard-talker")
        player.race = "human"
        player.apply_race_baseline()
        host = self._affinity_host()
        relations_before = host.db.relations_data

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                run_scripted_talk(host, player, "公會")
        self.assertEqual(host.db.relations_data, relations_before)

    @covers_requirement("affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_budget_capped_talk_presents_the_non_numeric_hint(self):
        from commands.talk import CmdsTalk
        from typeclasses.characters import PlayerCharacter

        host = self._affinity_host()
        host.location = self.room1
        player = create_object(PlayerCharacter, key="capped-talker")
        player.race = "human"
        player.apply_race_baseline()
        player.location = self.room1
        for _ in range(5):
            self.call(CmdsTalk(), f"{host.key} 公會", caller=player)
        from world.rules.affinity import AFFINITY_DAILY_CAP_HINT

        output = self.call(CmdsTalk(), f"{host.key} 公會", caller=player)
        self.assertIn(AFFINITY_DAILY_CAP_HINT, output)
        self.assertEqual(host.relations.affinity_for(player), 5)

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    @covers_requirement("scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed")
    def test_guild_staff_definition_stays_in_character(self):
        # The branch master explains the counter in the world's own terms and
        # names no command (npc-persona-content-altoria-guild D5): no backticked
        # token and no `guild <verb>` anywhere in the greeting or answers.
        definition = live_dialogue_table()[GUILD_STAFF_DIALOGUE_KEY]
        combined = definition.greeting + "".join(
            entry.response for entry in definition.responses
        )
        self.assertNotIn("`", combined)
        self.assertNotRegex(combined, r"guild\s+[a-z]")
        self.assertNotRegex(
            combined,
            r"(?<![A-Za-z])(register|list|accept|log|show|turnin|abandon|merit)(?![A-Za-z])",
        )
        self.assertIn(
            GUILD_STAFF_TURNIN_KEYWORD,
            [entry.keyword for entry in definition.responses],
        )


class OpensDialoguePredicateTests(EvenniaTest):
    """The conversable-host gate and the fixed opening line (avg-stage §8.1).

    One predicate decides who can open a conversation: the ``explore.talk_open``
    adapter commits through it and the exploration panel renders its 交談 row
    from it, so the affordance and the action agree.
    """

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "dialogue")
        self.player = create_object(NPC, key="gate-probe")

    def _scripted_host(self, dialogue_key: str = SYNTH_DIALOGUE_KEY) -> NPC:
        host = create_object(NPC, key="synthetic-host")
        host.components.add(ScriptedDialogue.create(host, dialogue_key=dialogue_key))
        return host

    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_a_scripted_host_with_a_table_row_opens_dialogue(self):
        host = self._scripted_host()
        self.assertTrue(is_dialogue_host(host))
        self.assertTrue(opens_dialogue(host))

    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_an_llmnpc_without_a_component_opens_dialogue(self):
        bard = create_object(LLMNPC, key="synthetic-bard")
        self.assertFalse(is_dialogue_host(bard))
        self.assertTrue(opens_dialogue(bard))

    def test_a_component_host_without_a_table_row_does_not_open_dialogue(self):
        host = self._scripted_host(dialogue_key="t_synth_absent_table")
        self.assertTrue(is_dialogue_host(host))
        self.assertFalse(opens_dialogue(host))

    def test_a_plain_npc_does_not_open_dialogue(self):
        plain = create_object(NPC, key="plain-probe")
        self.assertFalse(opens_dialogue(plain))

    def test_the_fallback_line_names_the_host(self):
        self.assertEqual(dialogue_open_fallback_line("甲"), "甲看向你，等你開口。")


class GuildStaffSyncDialogueTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(NPC, key="placeholder")
        from evennia.utils.create import create_object as co
        from typeclasses.rooms import Room
        from world.maps.bootstrap import sync_grid, sync_service_interiors

        self.hall_room = co(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        from world.quests.catalog import register_catalog
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._quest_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        from world.rules.guild_config import load_catalog_into_cache

        load_catalog_into_cache()
        from evennia.utils.search import search_object_by_tag
        from world.rules.guild_economy import sync_service_content

        sync_service_content()
        # The roster is identity-agnostic: after syncing the shipped catalog
        # roster, the guild host is exactly the one NPC carrying the
        # scripted-dialogue component whose key the roster authored — no
        # authored display name is ever named here.
        self.guild_master = next(
            npc
            for npc in NPC.objects.all()
            if npc.components.has(ScriptedDialogue.get_component_slot())
            and npc.components.get(ScriptedDialogue.get_component_slot()).dialogue_key
            == GUILD_STAFF_DIALOGUE_KEY
        )

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
        self.assertIn(_staff_answer("公會"), output)

    @covers_requirement("guild-registration::guild-service-hosts-teach-their-service-commands-through-scripted-dialogue")
    def test_no_keyword_talk_presents_the_greeting(self):
        from commands.talk import CmdsTalk

        self.guild_master.location = self.hall_room
        self.char1.location = self.hall_room
        output = self.call(CmdsTalk(), self.guild_master.key, caller=self.char1)
        self.assertIn(live_dialogue_table()[GUILD_STAFF_DIALOGUE_KEY].greeting, output)

    def _player_state(self):
        return {
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


class DialogueVoiceRoutingTests(EvenniaCommandTestMixin, EvenniaTest):
    """Voice routing and offline greeting resolution tests (design D3)."""

    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="語音測試NPC", location=self.room1)
        self.char1.location = self.room1

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_profiled_host_misunderstands_in_its_own_voice(self):
        from unittest.mock import patch
        from world.lore.npc_card import NpcCard, NpcCardIdentity
        from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

        profile = NpcProfile(
            key="t_voice_test_01",
            card=NpcCard(
                identity=NpcCardIdentity(public="公會接待", hidden=""),
                appearance="外觀",
                personality="性格",
                speech_style="語氣",
                life_story="經歷",
                habit="習慣",
                social_connection="",
            ),
            age=30,
            apparent_age=30,
            voice=NpcVoiceLines(
                greeting="你好呀，旅行者！",
                misunderstood="哎呀，這我不清楚呢。",
            ),
        )
        self.npc.db.npc_persona_meta = {
            "format": 1,
            "generation": 1,
            "persona_version": 1,
            "provenance": {"kind": "profile", "profile": "t_voice_test_01"},
        }
        with patch("world.lore.npc_profiles.NPC_PROFILE_REGISTRY", {"t_voice_test_01": profile}):
            line = misunderstood_line_for(self.npc)
            self.assertEqual(line, "哎呀，這我不清楚呢。")

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_unprofiled_host_uses_shared_misunderstanding_line(self):
        self.assertEqual(misunderstood_line_for(self.npc), NO_UNDERSTANDING_LINE)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_dangling_profile_reference_emits_error_and_returns_shared_line(self):
        from unittest.mock import patch
        self.npc.db.npc_persona_meta = {
            "format": 1,
            "generation": 1,
            "persona_version": 1,
            "provenance": {"kind": "profile", "profile": "dangling_profile_key"},
        }
        with patch("world.rules.dialogue.log_error") as mock_log_error:
            line = misunderstood_line_for(self.npc)
            self.assertEqual(line, NO_UNDERSTANDING_LINE)
            mock_log_error.assert_called_once_with(
                "npc_voice_profile_missing",
                context={"npc": str(self.npc.pk), "profile": "dangling_profile_key"},
            )

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_offline_greeting_field_wins_over_table_and_profile(self):
        from unittest.mock import patch
        from world.lore.npc_card import NpcCard, NpcCardIdentity
        from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

        profile = NpcProfile(
            key="t_voice_test_02",
            card=NpcCard(
                identity=NpcCardIdentity(public="守衛", hidden=""),
                appearance="外觀",
                personality="性格",
                speech_style="語氣",
                life_story="經歷",
                habit="習慣",
                social_connection="",
            ),
            age=30,
            apparent_age=30,
            voice=NpcVoiceLines(greeting="Profile問候語"),
        )
        self.npc.db.npc_persona_meta = {
            "format": 1,
            "generation": 1,
            "persona_version": 1,
            "provenance": {"kind": "profile", "profile": "t_voice_test_02"},
        }
        self.npc.components.add(ScriptedDialogue.create(self.npc, dialogue_key=GUILD_STAFF_DIALOGUE_KEY))
        self.npc.db.npc_offline_greeting = "自訂覆寫問候語！"

        with patch("world.lore.npc_profiles.NPC_PROFILE_REGISTRY", {"t_voice_test_02": profile}):
            greeting = offline_greeting_for(self.npc)
            self.assertEqual(greeting, "自訂覆寫問候語！")

            # Clear field -> falls back to table greeting
            self.npc.db.npc_offline_greeting = ""
            table_greeting = offline_greeting_for(self.npc)
            self.assertEqual(table_greeting, greeting_for(self.npc))

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_profile_greeting_when_no_table_and_field_empty(self):
        from unittest.mock import patch
        from world.lore.npc_card import NpcCard, NpcCardIdentity
        from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

        profile = NpcProfile(
            key="t_voice_test_03",
            card=NpcCard(
                identity=NpcCardIdentity(public="測試者", hidden=""),
                appearance="外觀",
                personality="性格",
                speech_style="語氣",
                life_story="經歷",
                habit="習慣",
                social_connection="",
            ),
            age=30,
            apparent_age=30,
            voice=NpcVoiceLines(greeting="來自Profile的問候。"),
        )
        self.npc.db.npc_persona_meta = {
            "format": 1,
            "generation": 1,
            "persona_version": 1,
            "provenance": {"kind": "profile", "profile": "t_voice_test_03"},
        }
        with patch("world.lore.npc_profiles.NPC_PROFILE_REGISTRY", {"t_voice_test_03": profile}):
            self.assertEqual(offline_greeting_for(self.npc), "來自Profile的問候。")

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_talk_command_no_keyword_speaks_offline_greeting_field_even_without_dialogue_component(self):
        from commands.talk import CmdsTalk

        # NPC without ScriptedDialogue component
        plain_npc = create_object(NPC, key="普通NPC", location=self.room1)
        plain_npc.db.npc_offline_greeting = "你好，我是普通路人。"
        output = self.call(CmdsTalk(), plain_npc.key, caller=self.char1)
        self.assertIn("你好，我是普通路人。", output)

        # Plain NPC without offline greeting field gives no response
        plain_npc.db.npc_offline_greeting = ""
        output = self.call(CmdsTalk(), plain_npc.key, caller=self.char1)
        self.assertIn("對方沒有理會你", output)


class DialogueTableImmutabilityTests(unittest.TestCase):
    """The authored table is frozen at the lore assembly, not just the view.

    The scripted-dialogue registry contract makes the table read-only at
    runtime (place-attendant-profession): DIALOGUE_ROWS itself is a
    MappingProxyType, so no consumer can grow or replace the rows that
    DIALOGUE_TABLE and the service-host validators read through it.
    """

    def test_a_write_through_the_lore_mapping_is_blocked(self):
        from world.lore.dialogue import DIALOGUE_ROWS
        # The shared binding-safe accessor reaches the live view without the
        # test ever naming the shipped catalog symbol; the view itself is what
        # gets pinned immutably.
        table = live_dialogue_table()

        with self.assertRaises(TypeError):
            DIALOGUE_ROWS["t_frozen_probe"] = DIALOGUE_ROWS[GUILD_STAFF_DIALOGUE_KEY]
        with self.assertRaises(TypeError):
            table["t_frozen_probe"] = table[GUILD_STAFF_DIALOGUE_KEY]
        # The blocked write left the table untouched.
        self.assertNotIn("t_frozen_probe", table)


if __name__ == "__main__":
    import unittest

    unittest.main()
