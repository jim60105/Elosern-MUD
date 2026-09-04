"""NPC identity validator and composer tests (npc-title-identity-core).

Covers the single-validator contract (strip-normalize, reject-on-stripped-form,
the 32-code-point bound, and the whitespace/control/markup rejections), the
composer's 「姓名　稱號」 rendering with its plain-name degradations (untitled,
non-NPC, malformed stored state), and the pure-read invariant: reading a title
never materializes a storage row. Validator cases are pure
``unittest.TestCase``; entity cases need ``EvenniaTest``.
"""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from world.rules.npc_identity import (
    MAX_NPC_NAME_CODE_POINTS,
    MAX_NPC_TITLE_CODE_POINTS,
    NPCNameError,
    NPCTitleError,
    npc_display_name,
    npc_title_value,
    validate_npc_name,
    validate_npc_title,
)

_FULL_WIDTH_SPACE = "\u3000"


class RaisingTitleNPC(NPC):
    """An NPC whose persisted title accessor explodes on every read."""

    @property
    def npc_title(self) -> str:
        raise RuntimeError("corrupt persisted attribute read")


class BreakingStr:
    """A key-like object whose __str__ raises."""

    def __str__(self) -> str:
        raise RuntimeError("corrupt key __str__")


class ValidateNPCTitleTests(unittest.TestCase):
    """The single validator every authored title write path validates against."""

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_legal_title_round_trips_stripped(self):
        self.assertEqual(validate_npc_title(" 南門守衛 "), "南門守衛")
        self.assertEqual(
            validate_npc_title(f"{_FULL_WIDTH_SPACE}雜貨店老闆{_FULL_WIDTH_SPACE}"),
            "雜貨店老闆",
        )

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_boundary_lengths_are_decided_exactly(self):
        at_bound = "守" * MAX_NPC_TITLE_CODE_POINTS
        self.assertEqual(validate_npc_title(at_bound), at_bound)
        with self.assertRaises(NPCTitleError):
            validate_npc_title(at_bound + "守")

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_internal_whitespace_and_separator_are_rejected(self):
        for value in ("南門 守衛", f"南門{_FULL_WIDTH_SPACE}守衛", "南門\t守衛"):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_control_and_nonprintable_characters_are_rejected(self):
        for value in ("南門\x00守衛", "南門\x1b守衛", "南門\u200b守衛"):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_markup_delimiter_is_rejected(self):
        with self.assertRaises(NPCTitleError):
            validate_npc_title("|r南門守衛|n")

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_non_text_values_are_rejected(self):
        for value in (None, 42, True, False, 3.5, ["南門守衛"], {"t": "南門守衛"}):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_empty_and_whitespace_only_values_are_rejected(self):
        for value in ("", "   ", _FULL_WIDTH_SPACE, " \t\u3000 "):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_rejection_messages_are_stable_english_identifiers(self):
        cases = {
            123: "npc title must be text",
            "  ": "npc title must be non-empty after stripping",
            "守" * (MAX_NPC_TITLE_CODE_POINTS + 1): "npc title must be at most",
            "南 門": "npc title must not contain whitespace",
            "南\x00門": "npc title contains a control character",
            "南|門": "npc title contains an Evennia markup delimiter",
        }
        for value, expected in cases.items():
            with self.subTest(value=repr(value)):
                with self.assertRaises(NPCTitleError) as caught:
                    validate_npc_title(value)
                self.assertIn(expected, str(caught.exception))
                self.assertTrue(
                    all(ord(char) < 128 for char in str(caught.exception))
                )


class ValidateNPCNameTests(unittest.TestCase):
    """The shared authored-name rule (npc-title-authored-identities).

    Traceability annotations are attached after the change's delta syncs
    (tasks 6.2 fixes the canonical requirement IDs); behavior is pinned here.
    """

    def test_legal_name_round_trips_stripped(self):
        self.assertEqual(validate_npc_name(" 黑鬍 "), "黑鬍")
        self.assertEqual(
            validate_npc_name(f"{_FULL_WIDTH_SPACE}雷加·鐵拳{_FULL_WIDTH_SPACE}"),
            "雷加·鐵拳",
        )

    def test_interior_ordinary_whitespace_is_allowed(self):
        # The single deliberate divergence from the title rule: multi-word
        # names are legal entity keys and must validate untouched.
        self.assertEqual(validate_npc_name("Jorn Urial"), "Jorn Urial")

    def test_boundary_lengths_are_decided_exactly(self):
        at_bound = "守" * MAX_NPC_NAME_CODE_POINTS
        self.assertEqual(validate_npc_name(at_bound), at_bound)
        with self.assertRaises(NPCNameError):
            validate_npc_name(at_bound + "守")

    def test_full_width_separator_is_rejected(self):
        with self.assertRaises(NPCNameError):
            validate_npc_name(f"南門{_FULL_WIDTH_SPACE}守衛")

    def test_control_and_nonprintable_characters_are_rejected(self):
        for value in ("雷加\x00拳", "雷加\x1b拳", "雷加\u200b拳"):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_markup_delimiter_is_rejected(self):
        with self.assertRaises(NPCNameError):
            validate_npc_name("|r雷加|n")

    def test_non_text_values_are_rejected(self):
        for value in (None, 42, True, False, 3.5, ["雷加"], {"n": "雷加"}):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_empty_and_whitespace_only_values_are_rejected(self):
        for value in ("", "   ", _FULL_WIDTH_SPACE, " \t\u3000 "):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_rejection_messages_are_stable_english_identifiers(self):
        cases = {
            123: "npc name must be text",
            "  ": "npc name must be non-empty after stripping",
            "守" * (MAX_NPC_NAME_CODE_POINTS + 1): "npc name must be at most",
            f"南{_FULL_WIDTH_SPACE}門": "npc name contains the identity separator",
            "雷\x00加": "npc name contains a control character",
            "雷|加": "npc name contains an Evennia markup delimiter",
        }
        for value, expected in cases.items():
            with self.subTest(value=repr(value)):
                with self.assertRaises(NPCNameError) as caught:
                    validate_npc_name(value)
                self.assertIn(expected, str(caught.exception))
                self.assertTrue(
                    all(ord(char) < 128 for char in str(caught.exception))
                )


class NPCTitleComposerTests(EvenniaTest):
    """The single deterministic composer and the pure-read invariant."""


    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="塞提斯")

    def _assert_no_title_row(self, entity):
        # autocreate=False keeps an absent title unmaterialized: a read must
        # never persist a storage row (the composer is a pure read).
        self.assertIsNone(entity.attributes.get("npc_title", return_obj=True))

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_titled_npc_composes_with_full_width_separator(self):
        self.npc.npc_title = "南門守衛"
        self.assertEqual(npc_display_name(self.npc), "塞提斯　南門守衛")
        self.assertNotIn("  ", npc_display_name(self.npc))
        self.assertEqual(
            [ord(char) for char in npc_display_name(self.npc) if char == _FULL_WIDTH_SPACE],
            [0x3000],
        )

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_untitled_npc_degrades_to_plain_name(self):
        self._assert_no_title_row(self.npc)
        self.assertEqual(npc_title_value(self.npc), "")
        self.assertEqual(npc_display_name(self.npc), "塞提斯")
        self._assert_no_title_row(self.npc)

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_player_and_monster_never_compose(self):
        player = create_object(PlayerCharacter, key="冒險者")
        for entity in (player, create_object(Monster, key="哥布林")):
            with self.subTest(entity=type(entity).__name__):
                self.assertEqual(npc_title_value(entity), "")
                self.assertEqual(npc_display_name(entity), entity.key)

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_player_and_monster_carrying_a_stray_title_row_never_compose(self):
        monster = create_object(Monster, key="哥布林")
        monster.db.npc_title = "深林領主"
        self.assertEqual(npc_title_value(monster), "")
        self.assertEqual(npc_display_name(monster), "哥布林")
        player = create_object(PlayerCharacter, key="冒險者二")
        player.db.npc_title = "深林領主"
        self.assertEqual(npc_title_value(player), "")
        self.assertEqual(npc_display_name(player), "冒險者二")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_malformed_stored_state_degrades_without_raising(self):
        for stored in (123, None, True, ["南門守衛"], "   ", _FULL_WIDTH_SPACE):
            with self.subTest(stored=repr(stored)):
                self.npc.db.npc_title = stored
                self.assertEqual(npc_title_value(self.npc), "")
                self.assertEqual(npc_display_name(self.npc), "塞提斯")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_corrupt_stored_strings_degrade_instead_of_rendering(self):
        # A stored string failing the validator's content rules could never
        # come from an authored path; rendering it would emit Evennia markup
        # or a separator-ambiguous identity, so the composer hides it.
        for stored in (
            "|r南門守衛|n",  # display markup
            "南|r門",
            f"南門{_FULL_WIDTH_SPACE}守衛",  # internal separator
            "南門 守衛",  # internal space
            "南門\x00守衛",  # control characters
            "南門\x1b守衛",
        ):
            with self.subTest(stored=repr(stored)):
                self.npc.db.npc_title = stored
                self.assertEqual(npc_title_value(self.npc), "")
                self.assertEqual(npc_display_name(self.npc), "塞提斯")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_overlong_stored_title_is_content_legal_and_still_composes(self):
        # Length is deliberately NOT part of the render filter: the overlong
        # row is the documented degraded state the display bounds truncate,
        # distinct from content corruption, which degrades to the plain name.
        self.npc.db.npc_title = "壞" * 200
        self.assertEqual(npc_title_value(self.npc), "壞" * 200)
        self.assertEqual(
            npc_display_name(self.npc), f"塞提斯{_FULL_WIDTH_SPACE}{'壞' * 200}"
        )

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_a_raising_title_accessor_degrades_to_the_plain_name(self):
        broken = create_object(RaisingTitleNPC, key="炸裂")
        self.assertEqual(npc_title_value(broken), "")
        self.assertEqual(npc_display_name(broken), "炸裂")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_an_unreadable_key_degrades_instead_of_composing_ambiguity(self):
        # No key attribute, a raising key accessor, and a key whose __str__
        # raises all yield "" — never 「　稱號」-style leading-separator junk.
        self.assertEqual(npc_display_name(object()), "")

        class _RaisingKey:
            @property
            def key(self):
                raise RuntimeError("corrupt key accessor")

        self.assertEqual(npc_display_name(_RaisingKey()), "")

        class _Holder:
            key = "placeholder"

        holder = _Holder()
        holder.key = BreakingStr()
        self.assertEqual(npc_display_name(holder), "")
        titled = create_object(NPC, key="無名")
        titled.db.npc_title = "南門守衛"
        titled.key = ""
        self.assertEqual(npc_display_name(titled), "")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_stored_title_is_read_back_stripped(self):
        # Only authored paths write through validate_npc_title, but a value
        # that arrives with surrounding whitespace still composes cleanly.
        self.npc.db.npc_title = " 南門守衛 "
        self.assertEqual(npc_display_name(self.npc), "塞提斯　南門守衛")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_llmnpc_subclass_composes(self):
        llm_npc = create_object(LLMNPC, key="米拉")
        llm_npc.npc_title = "酒館女合夥人"
        self.assertEqual(npc_display_name(llm_npc), "米拉　酒館女合夥人")

    @covers_requirement('npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity', 'npc-identity-titles::the-webclient-exploration-panel-renders-the-npc-full-identity-on-entity-and-interact-rows')
    def test_boundary_composition_stays_under_panel_bound(self):
        npc = create_object(NPC, key="長" * 64)
        npc.npc_title = "守" * MAX_NPC_TITLE_CODE_POINTS
        composed = npc_display_name(npc)
        self.assertEqual(len(composed), 64 + 1 + MAX_NPC_TITLE_CODE_POINTS)
        self.assertLessEqual(len(composed), 128)
