"""Behavior tests for the NPC profile vocabulary and registry assembly."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from evennia.scripts.models import ScriptDB
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from world.lore.npc_card import NpcCard, NpcCardError, NpcCardIdentity
from world.lore.npc_profiles import assemble_profile_registry
from world.lore.npc_profiles.shape import VOICE_LINE_LIMIT, NpcProfile, NpcVoiceLines
from world.lore.sync import sync_all


def _card_record(**overrides) -> dict:
    record = {
        "identity": {"public": "t_公開身分", "hidden": ""},
        "appearance": "t_外觀",
        "personality": "t_性格",
        "speech_style": "t_說話風格",
        "life_story": "t_人生經歷",
        "habit": "t_習慣",
        "social_connection": "",
    }
    record.update(overrides)
    return record


def _card(**overrides) -> NpcCard:
    return NpcCard.from_record(_card_record(**overrides))


class NpcVoiceLinesTests(unittest.TestCase):
    """Bounds and normalization of the prewritten voice lines."""

    @covers_requirement(
        "npc-profile-registry::authored-npc-profiles-are-immutable-keyed-lore-records"
    )
    def test_overlong_greeting_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            NpcVoiceLines(greeting="字" * (VOICE_LINE_LIMIT + 1))
        self.assertIn("greeting", str(caught.exception))

    @covers_requirement(
        "npc-profile-registry::authored-npc-profiles-are-immutable-keyed-lore-records"
    )
    def test_multi_paragraph_line_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            NpcVoiceLines(misunderstood="第一段\n第二段")
        self.assertIn("misunderstood", str(caught.exception))

    def test_multi_paragraph_line_survives_crlf_normalization(self):
        with self.assertRaises(ValueError) as caught:
            NpcVoiceLines(greeting="第一段\r第二段")
        self.assertIn("greeting", str(caught.exception))

    def test_non_string_line_raises_npc_card_error(self):
        with self.assertRaises(NpcCardError):
            NpcVoiceLines(greeting=123)

    def test_crlf_normalizes_to_lf_and_strips_outer_whitespace(self):
        voice = NpcVoiceLines(greeting="  哈囉世界\r\n  ")
        self.assertEqual(voice.greeting, "哈囉世界")

    def test_default_voice_lines_are_both_none(self):
        voice = NpcVoiceLines()
        self.assertIsNone(voice.greeting)
        self.assertIsNone(voice.misunderstood)


class NpcProfileTests(unittest.TestCase):
    """Profile key vocabulary and the card-type guard."""

    @covers_requirement(
        "npc-profile-registry::authored-npc-profiles-are-immutable-keyed-lore-records"
    )
    def test_valid_lowercase_snake_key_passes(self):
        profile = NpcProfile(key="t_valid_snake_123", card=_card())
        self.assertEqual(profile.key, "t_valid_snake_123")

    def test_uppercase_key_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            NpcProfile(key="T_bad", card=_card())
        self.assertIn("T_bad", str(caught.exception))

    def test_leading_digit_key_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            NpcProfile(key="1bad", card=_card())
        self.assertIn("1bad", str(caught.exception))

    def test_65_char_key_is_rejected(self):
        overlong = "t_" + ("a" * 63)
        self.assertEqual(len(overlong), 65)
        with self.assertRaises(ValueError) as caught:
            NpcProfile(key=overlong, card=_card())
        self.assertIn(overlong, str(caught.exception))

    def test_non_npccard_card_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            NpcProfile(key="t_sample", card={"identity": {"public": "x", "hidden": ""}})
        self.assertIn("t_sample", str(caught.exception))


class AssembleProfileRegistryTests(unittest.TestCase):
    """The pure, module-level slice assembly function (synthetic rows only)."""

    @covers_requirement(
        "npc-profile-registry::one-module-assembles-the-profile-registry-from-owned-slices"
    )
    def test_duplicate_key_across_slices_names_the_key_and_both_slices(self):
        profile = NpcProfile(key="t_dup", card=_card())
        with self.assertRaises(ValueError) as caught:
            assemble_profile_registry(
                (
                    ("t_slice_one", (profile,)),
                    ("t_slice_two", (profile,)),
                )
            )
        message = str(caught.exception)
        self.assertIn("t_dup", message)
        self.assertIn("t_slice_one", message)
        self.assertIn("t_slice_two", message)

    def test_non_npcprofile_row_is_rejected_naming_the_slice(self):
        with self.assertRaises(ValueError) as caught:
            assemble_profile_registry((("t_slice", ("not-a-profile",)),))
        self.assertIn("t_slice", str(caught.exception))

    def test_invalid_key_reaching_assembly_is_rejected(self):
        profile = NpcProfile(key="t_placeholder", card=_card())
        object.__setattr__(profile, "key", "T_Bad")
        with self.assertRaises(ValueError) as caught:
            assemble_profile_registry((("t_slice", (profile,)),))
        self.assertIn("T_Bad", str(caught.exception))

    @covers_requirement(
        "npc-profile-registry::authored-npc-profiles-are-immutable-keyed-lore-records"
    )
    def test_malformed_card_names_profile_key_slice_and_leaf(self):
        bad_card = NpcCard(
            identity=NpcCardIdentity(public="t_公開", hidden=""),
            appearance="t_外觀",
            personality="t_性格",
            speech_style="",  # missing required leaf
            life_story="t_人生經歷",
            habit="t_習慣",
            social_connection="",
        )
        profile = NpcProfile(key="t_broken", card=bad_card)
        with self.assertRaises(ValueError) as caught:
            assemble_profile_registry((("t_slice", (profile,)),))
        message = str(caught.exception)
        self.assertIn("t_broken", message)
        self.assertIn("t_slice", message)
        self.assertIn("speech_style", message)

    def test_valid_rows_assemble_into_a_plain_dict(self):
        profile = NpcProfile(key="t_ok", card=_card())
        registry = assemble_profile_registry((("t_slice", (profile,)),))
        self.assertEqual(registry, {"t_ok": profile})


class ImportBoundaryTests(unittest.TestCase):
    @covers_requirement(
        "npc-profile-registry::one-module-assembles-the-profile-registry-from-owned-slices"
    )
    def test_package_imports_no_rules_evennia_or_django(self):
        """ast-parse every package source; none may import world.rules/evennia/django."""
        forbidden = ("world.rules", "evennia", "django")
        package_dir = Path(__file__).resolve().parent.parent / "npc_profiles"
        for path in sorted(package_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module] if node.module else []
                else:
                    continue
                for name in names:
                    for prefix in forbidden:
                        self.assertFalse(
                            name == prefix or name.startswith(f"{prefix}."),
                            f"{path.name} leaks forbidden dependency: {name}",
                        )


class NpcProfileSyncTests(EvenniaTestCase):
    """Profiles carry hidden identities and are never mirrored into lore Scripts."""

    @covers_requirement(
        "npc-profile-registry::one-module-assembles-the-profile-registry-from-owned-slices"
    )
    def test_sync_all_creates_no_npc_profile_scripts(self):
        sync_all()
        self.assertEqual(
            ScriptDB.objects.filter(db_key__startswith="lore:npc_profiles:").count(), 0
        )
