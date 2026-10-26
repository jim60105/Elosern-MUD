"""Data-contract test: shipped dialogue source inventory and profile service distinction

Covers:
- Complete 25-table static inventory resolution.
- Canonical profile/service distinction (e.g. guild_staff -> altoria_guild_master).
- Greeting and topic identity stability.
- Unknown/missing context behavior.
- GeneratedDialogueIdentity handling on provider interface.
- Legacy DialogueDefinition adaptation.
"""

from types import SimpleNamespace
import unittest

from tools.spec_traceability import covers_requirement
from world.lore.dialogue import DIALOGUE_SNAPSHOT, canonical_dialogue_bindings
from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    make_generated_host_key,
    make_static_host_key,
)
from world.lore.dialogue.shape import AuthoredDialogue, DialogueDefinition, KeywordResponse
from world.rules.dialogue_sources import (
    ResolvedDialogueSource,
    canonical_dialogue_bindings,
    resolve_dialogue_source,
    to_authored_dialogue,
)


class DialogueSourcesTests(unittest.TestCase):
    """Tests for ResolvedDialogueSource and resolve_dialogue_source."""

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed",
        "authored-dialogue-selection::scene-selection-is-independent-of-content-provider",
        "authored-dialogue-content::lower-hospitality-content-has-exclusive-profile-key-yaml-ownership",
        "authored-dialogue-content::lower-civic-content-has-exclusive-profile-key-yaml-ownership",
    )
    def test_complete_inventory_of_25_tables(self):
        bindings = canonical_dialogue_bindings()
        self.assertEqual(len(bindings), 25)
        self.assertEqual(len(DIALOGUE_SNAPSHOT), 25)

        for diag_key, prof_key in bindings.items():
            with self.subTest(dialogue_key=diag_key):
                ctx = SimpleNamespace(
                    source_identity=StaticDialogueIdentity(prof_key, diag_key),
                    host_key=make_static_host_key(prof_key),
                )
                source = resolve_dialogue_source(ctx)
                self.assertIsNotNone(source)
                self.assertIsInstance(source, ResolvedDialogueSource)
                self.assertEqual(source.host_key, f"s:{prof_key}")
                self.assertEqual(source.identity.profile_key, prof_key)
                self.assertEqual(source.identity.dialogue_key, diag_key)
                self.assertTrue(source.dialogue.greeting)
                self.assertEqual(len(source.dialogue.topics), 4)

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed",
        "authored-dialogue-content::guild-content-has-exclusive-profile-key-yaml-ownership",
    )
    def test_guild_staff_profile_service_distinction(self):
        bindings = canonical_dialogue_bindings()
        self.assertEqual(bindings["guild_staff"], "altoria_guild_master")

        ctx = SimpleNamespace(
            source_identity=StaticDialogueIdentity("altoria_guild_master", "guild_staff"),
            host_key=make_static_host_key("altoria_guild_master"),
        )
        source = resolve_dialogue_source(ctx)
        self.assertIsNotNone(source)
        self.assertEqual(source.host_key, "s:altoria_guild_master")
        self.assertEqual(source.identity.profile_key, "altoria_guild_master")
        self.assertEqual(source.identity.dialogue_key, "guild_staff")
        topic_ids = [t.topic_id for t in source.dialogue.topics]
        self.assertEqual(
            topic_ids,
            [
                "guild_staff.topic_01",
                "guild_staff.topic_02",
                "guild_staff.topic_03",
                "guild_staff.topic_04",
            ],
        )

    @covers_requirement("scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed")
    def test_unknown_or_missing_source_returns_none(self):
        self.assertIsNone(resolve_dialogue_source(None))
        self.assertIsNone(resolve_dialogue_source(SimpleNamespace(source_identity=None)))

        ctx = SimpleNamespace(
            source_identity=StaticDialogueIdentity("unknown_prof", "nonexistent_key"),
            host_key="s:unknown_prof",
        )
        self.assertIsNone(resolve_dialogue_source(ctx))

    @covers_requirement(
        "scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed",
        "authored-dialogue-selection::scene-selection-is-independent-of-content-provider",
    )
    def test_generated_identity_returns_none_until_generated_packages(self):
        ctx = SimpleNamespace(
            source_identity=GeneratedDialogueIdentity("pkg1", "role1", "phase1"),
            host_key=make_generated_host_key("pkg1", "role1"),
        )
        self.assertIsNone(resolve_dialogue_source(ctx))

    @covers_requirement("scripted-dialogue::dialogue-tables-are-immutable-keyed-and-registry-backed")
    def test_to_authored_dialogue_adapts_legacy_definition(self):
        legacy = DialogueDefinition(
            greeting="Hello traveler.",
            responses=(
                KeywordResponse("rumors", "I heard something interesting."),
                KeywordResponse("goods", "Take a look at my wares."),
            ),
        )
        authored = to_authored_dialogue(legacy, "t_test_host")
        self.assertIsInstance(authored, AuthoredDialogue)
        self.assertEqual(authored.greeting, "Hello traveler.")
        self.assertEqual(len(authored.topics), 2)
        self.assertEqual(authored.topics[0].topic_id, "t_test_host.topic_01")
        self.assertEqual(authored.topics[0].keyword, "rumors")
        self.assertEqual(authored.topics[0].fallback.lines[0].text, "rumors")
        self.assertEqual(authored.topics[0].fallback.lines[1].text, "I heard something interesting.")

        # Responses backward-compat property
        self.assertEqual(len(authored.responses), 2)
        self.assertEqual(authored.responses[0].keyword, "rumors")
        self.assertEqual(authored.responses[0].response, "I heard something interesting.")
