"""Data-contract test: guild staff authored dialogue content and office integrity

Covers:
- Authored YAML discovery and profile binding for altoria_guild_master
- Inventory of all 4 topics and stable IDs (guild_staff.topic_01 to topic_04)
- Multi-line scenes starting with actor speech and containing host response
- Absence of out-of-character (OOC) tokens, commands, backticks, or system words
- Presence of rank-qualified variant on topic_03 with GuildRankAtLeast
- Real host offline smoke test (CmdTalk/select_authored_topic) and deterministic replay
"""

from __future__ import annotations

import re
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.talk import CmdsTalk
from tools.spec_traceability import covers_requirement
from world.quests.catalog import register_catalog
from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.dialogue import DIALOGUE_SNAPSHOT, canonical_dialogue_bindings
from world.lore.dialogue.conditions import GuildRankAtLeast
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.scenes import Narration, Speech
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_context import resolve_dialogue_context
from world.rules.dialogue_sources import resolve_dialogue_source

_BANNED_OOC_SUBSTRINGS = ("指令", "系統", "選單", "按鈕", "輸入", "點擊", "介面")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


class AuthoredDialogueContentGuildContractTests(unittest.TestCase):
    """Data-contract assertions for altoria_guild_master dialogue content."""

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed"
    )
    def test_discovered_snapshot_contains_guild_staff(self):
        bindings = canonical_dialogue_bindings()
        self.assertEqual(bindings.get(GUILD_STAFF_DIALOGUE_KEY), "altoria_guild_master")
        self.assertIn(GUILD_STAFF_DIALOGUE_KEY, DIALOGUE_SNAPSHOT)
        dialogue = DIALOGUE_SNAPSHOT[GUILD_STAFF_DIALOGUE_KEY]
        self.assertIsInstance(dialogue, AuthoredDialogue)
        self.assertTrue(dialogue.greeting)

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed"
    )
    def test_guild_staff_topics_inventory_and_scene_structure(self):
        dialogue = DIALOGUE_SNAPSHOT[GUILD_STAFF_DIALOGUE_KEY]
        self.assertEqual(len(dialogue.topics), 4)
        expected_topic_ids = [
            f"guild_staff.topic_{i:02d}" for i in range(1, 5)
        ]
        actual_topic_ids = [t.topic_id for t in dialogue.topics]
        self.assertEqual(actual_topic_ids, expected_topic_ids)

        for topic in dialogue.topics:
            with self.subTest(topic=topic.topic_id):
                self.assertIsInstance(topic, AuthoredTopic)
                # Fallback scene assertions
                fallback = topic.fallback
                self.assertGreaterEqual(len(fallback.lines), 3)
                self.assertLessEqual(len(fallback.lines), 8)
                self.assertIsInstance(fallback.lines[0], Speech)
                self.assertEqual(fallback.lines[0].speaker, "actor")
                self.assertTrue(
                    any(isinstance(line, Speech) and line.speaker == "host" for line in fallback.lines)
                )

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed"
    )
    def test_topic_03_has_rank_qualified_variant(self):
        dialogue = DIALOGUE_SNAPSHOT[GUILD_STAFF_DIALOGUE_KEY]
        topic_03 = next(t for t in dialogue.topics if t.topic_id == "guild_staff.topic_03")
        self.assertEqual(len(topic_03.variants), 1)
        variant = topic_03.variants[0]
        self.assertEqual(variant.priority, 10)
        self.assertIsInstance(variant.when, GuildRankAtLeast)
        self.assertEqual(variant.when.rank_key, "E")
        self.assertIn(variant.when.rank_key, GUILD_RANK_REGISTRY)

        # Variant scene structure
        v_scene = variant.scene
        self.assertGreaterEqual(len(v_scene.lines), 3)
        self.assertLessEqual(len(v_scene.lines), 8)
        self.assertIsInstance(v_scene.lines[0], Speech)
        self.assertEqual(v_scene.lines[0].speaker, "actor")
        self.assertTrue(
            any(isinstance(line, Speech) and line.speaker == "host" for line in v_scene.lines)
        )

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed"
    )
    def test_no_ooc_or_commands_in_guild_dialogue_prose(self):
        dialogue = DIALOGUE_SNAPSHOT[GUILD_STAFF_DIALOGUE_KEY]
        all_prose_lines: list[tuple[str, str]] = [("greeting", dialogue.greeting)]

        for topic in dialogue.topics:
            for idx, line in enumerate(topic.fallback.lines):
                all_prose_lines.append((f"{topic.topic_id}.fallback[{idx}]", line.text))
            for v in topic.variants:
                for idx, line in enumerate(v.scene.lines):
                    all_prose_lines.append((f"{topic.topic_id}.variant_{v.variant_id}[{idx}]", line.text))

        for origin, text in all_prose_lines:
            with self.subTest(origin=origin):
                self.assertNotIn("`", text, f"{origin} contains backticks")
                for banned in _BANNED_OOC_SUBSTRINGS:
                    self.assertNotIn(banned, text, f"{origin} contains banned OOC word {banned!r}")
                # Single letters like 'F' or 'E' for guild rank are allowed; multi-character Latin is rejected
                latin_match = _LATIN_WORD_RE.search(text)
                self.assertIsNone(latin_match, f"{origin} contains Latin token: {latin_match.group() if latin_match else ''}")


class AuthoredDialogueContentGuildSmokeTests(EvenniaCommandTestMixin, EvenniaTest):
    """Real-host offline smoke execution driving dialogue selection through CmdTalk."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.hall = create_object(Room, key="大廳")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="葛里安‧衛登", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="altoria_guild_master")
        )
        self.staff.components.add(
            ScriptedDialogue.create(self.staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )

    def tearDown(self):
        clear_dialogue_session(self.char1)
        super().tearDown()

    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    def test_real_host_smoke_cmd_talk_and_topic_selection(self):
        # 1. Topic selection for unconditional fallback
        context = resolve_dialogue_context(self.char1, self.staff)
        source = resolve_dialogue_source(context)
        self.assertIsNotNone(source)

        delivery = select_authored_topic(
            self.char1, self.staff, "guild_staff.topic_03",
            selection_id="smoke-1",
            expected_context_id=None,
        )
        self.assertEqual(delivery.topic_id, "guild_staff.topic_03")
        self.assertEqual(delivery.scene_id, "guild_staff.topic_03_scene")
        self.assertIsInstance(delivery.lines[0], Speech)
        self.assertEqual(delivery.lines[0].speaker, "actor")

        # 2. CmdTalk invocation through command line
        output = self.call(CmdsTalk(), "葛里安‧衛登 公會")
        self.assertIn("能跟我說說這座公會的背景嗎？", output)
        self.assertIn("三國皆承認公會的公正身分", output)

        # 3. Reading session recorded
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        self.assertEqual(session.delivery.topic_id, "guild_staff.topic_03")

        # 4. Replay test (deterministic without double effect)
        replay_delivery = select_authored_topic(
            self.char1, self.staff, "guild_staff.topic_03",
            selection_id="smoke-1",
            expected_context_id=session.context_id,
        )
        self.assertEqual(replay_delivery.topic_id, "guild_staff.topic_03")
        self.assertEqual(replay_delivery.scene_id, "guild_staff.topic_03_scene")
