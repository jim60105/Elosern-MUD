"""NPC typeclass tests: adult-identity helper and the title identity surface.

The title cases (npc-title-identity-core) pin the immutable-by-structure
attribute, the opt-in ``full_identity`` display flag, and the deliberate
absence of any title write API on the typeclass or the command surface.
"""

import inspect

from tools.spec_traceability import covers_requirement

from evennia import default_cmds
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from commands.character_creation import CharacterCreationCmdSet
from commands.default_cmdsets import AccountCmdSet, CharacterCmdSet
from commands.localized import ProjectXYZGridCmdSet
from commands.title import CmdTitle
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC, ensure_npc_adult_identity
from world.rules.npc_identity import validate_npc_title


class EnsureNpcAdultIdentityTests(EvenniaTestCase):
    def _fresh_npc(self):
        return create_object(NPC, key="identity-npc")

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_missing_identity_gets_the_adult_baseline(self):
        npc = self._fresh_npc()
        self.assertIsNone(npc.attributes.get("age"))
        self.assertIsNone(npc.attributes.get("apparent_age"))
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 18)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_existing_canonical_ages_are_preserved(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        npc.attributes.add("apparent_age", 28)
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 28)

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_partial_identity_fills_only_the_missing_field(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

        reverse = self._fresh_npc()
        reverse.attributes.add("apparent_age", 28)
        ensure_npc_adult_identity(reverse)
        self.assertEqual(int(reverse.attributes.get("apparent_age")), 28)
        self.assertEqual(int(reverse.attributes.get("age")), 18)


class NPCTitleDisplayTests(EvenniaTestCase):
    """The immutable-by-structure attribute and the opt-in display flag."""

    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="塞提斯")

    @covers_requirement('npc-identity-titles::the-npc-title-is-a-creation-time-attribute-with-no-runtime-write-surface')
    def test_new_npc_title_reads_empty_without_materializing_a_row(self):
        self.assertEqual(self.npc.npc_title, "")
        self.assertIsNone(self.npc.attributes.get("npc_title", return_obj=True))

    @covers_requirement('npc-identity-titles::full-identity-appears-only-on-opt-in-text-display-surfaces')
    def test_display_name_without_the_flag_stays_byte_identical_plain_name(self):
        self.npc.npc_title = validate_npc_title("南門守衛")
        plain = self.npc.get_display_name(self.npc)
        self.assertEqual(plain, "塞提斯")
        self.assertEqual(self.npc.get_display_name(self.npc, full_identity=False), plain)

    @covers_requirement('npc-identity-titles::full-identity-appears-only-on-opt-in-text-display-surfaces')
    def test_full_identity_flag_composes_name_and_title(self):
        self.npc.npc_title = validate_npc_title("南門守衛")
        self.assertEqual(
            self.npc.get_display_name(self.npc, full_identity=True), "塞提斯　南門守衛"
        )

    @covers_requirement('npc-identity-titles::full-identity-appears-only-on-opt-in-text-display-surfaces')
    def test_flag_is_inert_for_player_and_monster(self):
        entities = (
            create_object(PlayerCharacter, key="冒險者甲"),
            create_object(Monster, key="哥布林甲"),
        )
        for entity in entities:
            with self.subTest(entity=type(entity).__name__):
                self.assertEqual(
                    entity.get_display_name(entity, full_identity=True), entity.key
                )


class NPCTitleWriteSurfaceAbsenceTests(EvenniaTestCase):
    """No title-specific write surface exists on the typeclass or commands.

    The guarantee's scope (spec: no runtime write surface): absence of any
    title setter/helper/command this capability introduces. Evennia's generic
    attribute access (``entity.db.npc_title = ...``) is framework
    infrastructure outside the claim — malformed-state tests deliberately
    seed through it. Mirrors the title-system fixed-title delete-surface pin.
    """

    @covers_requirement('npc-identity-titles::the-npc-title-is-a-creation-time-attribute-with-no-runtime-write-surface')
    def test_npc_interface_exposes_no_title_mutating_callable(self):
        offenders = {
            name
            for name, member in inspect.getmembers(NPC, predicate=inspect.isfunction)
            if "title" in name.lower()
        }
        self.assertEqual(offenders, set())
        forbidden_write_verbs = (
            "set", "update", "assign", "change", "edit", "rename", "grant",
            "revoke", "clear", "remove", "delete", "add", "write", "mutate",
        )
        verb_offenders = {
            name
            for name, member in inspect.getmembers(NPC, predicate=inspect.isfunction)
            for verb in forbidden_write_verbs
            if verb in name.lower() and "title" in name.lower()
        }
        self.assertEqual(verb_offenders, set())

    @covers_requirement('npc-identity-titles::the-npc-title-is-a-creation-time-attribute-with-no-runtime-write-surface')
    def test_registered_command_surface_has_no_npc_title_command(self):
        merged = {
            command.key: command
            for cmdset in (CharacterCmdSet(), AccountCmdSet())
            for command in cmdset.commands
        }
        default_classes = {
            type(command)
            for cmdset in (
                default_cmds.CharacterCmdSet(),
                default_cmds.AccountCmdSet(),
            )
            for command in cmdset.commands
        }
        mounted = {
            key: command
            for key, command in merged.items()
            if type(command) not in default_classes
        }
        for cmdset in (ProjectXYZGridCmdSet(), CharacterCreationCmdSet()):
            mounted.update({command.key: command for command in cmdset.commands})
        self.assertTrue(mounted, "the mounted command scan found no project commands")
        title_tokens = ("title", "稱號", "npc_title")
        title_related = []
        for command in mounted.values():
            raw = command.aliases
            names = {command.key} | ({raw} if isinstance(raw, str) else set(raw))
            if any(token in name.lower() for name in names for token in title_tokens):
                title_related.append(command)
        # The only title commands in the game are the player title system's
        # own surface (title-system), which this capability leaves unchanged
        # and which can never touch an NPC title; no NPC-title command exists.
        self.assertTrue(
            all(isinstance(command, CmdTitle) for command in title_related),
            f"unexpected NPC-title command: {sorted({c.key for c in title_related if not isinstance(c, CmdTitle)})}",
        )
        for command in title_related:
            self.assertNotIn("npc", command.key.lower())


if __name__ == "__main__":
    import unittest

    unittest.main()
