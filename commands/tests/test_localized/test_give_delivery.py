"""Slice of ``test_localized``: LocalizedGiveDeliveryTests.
"""
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from django.test import override_settings
from evennia import default_cmds
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from commands.default_cmdsets import AccountCmdSet, CharacterCmdSet
from commands.localized import (
    CmdDrop,
    CmdGet,
    CmdGive,
    CmdGoto,
    CmdHelp,
    CmdHome,
    CmdIC,
    CmdLook,
    CmdMap,
    CmdNick,
    CmdOOC,
    CmdOOCLook,
    CmdOption,
    CmdPage,
    CmdPassword,
    CmdPose,
    CmdQuell,
    CmdQuit,
    CmdSay,
    CmdSessions,
    CmdSetDesc,
    CmdStyle,
    CmdWhisper,
    CmdWho,
    CmdColorTest,
    LOCALIZED_DEFAULT_KEYS,
)
from typeclasses.rooms import InstanceRoom
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    deliver,
    quest,
    register,
)
from world.rules.combat_session import engage
from world.rules.quest_delivery import active_deliveries_for_recipient
from world.rules.tests._combat_session_helpers import _monster
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import make_item, synthetic_registries

from ._support import (
    _BLADE,
    _FLASK,
    _POTION,
)


class LocalizedGiveDeliveryTests(
    QuestRegistryIsolation, BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest
):
    """The general give advances DELIVER objectives through the shared seam.

    The give keeps its raw-transfer contract: no quest-scoped refusal and no
    combat gate; only the committed-transfer observer decides progress.
    """

    def setUp(self):
        # The monster fixture and race baselines build against the catalogs.
        scope = synthetic_registries("races", "static_tiers", "subraces", "items")
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.room1.key = "測試房間"
        self.room1.save()
        self.holder = create_object(PlayerCharacter, key="持有人", location=self.room1)
        self.holder.race = "t_duskmari"
        self.holder.apply_race_baseline()
        self.recipient = create_object(NPC, key="灰婆婆", location=self.room1)
        self.recipient.race = "t_duskmari"
        self.recipient.apply_race_baseline()
        self.bystander = create_object(NPC, key="旁觀者", location=self.room1)
        self.bystander.race = "t_duskmari"
        self.bystander.apply_race_baseline()

        self.definition = register(
            quest(
                "give_delivery_quest",
                stages=(QuestStage(0, deliver(_POTION, quantity=2)),),
            )
        )
        self.record = accept(self.holder, self.definition.key)
        bind_stage_runtime(
            self.holder,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    def _give(self, args):
        return self.call(CmdGive(), args, caller=self.holder)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_giving_the_objective_key_to_the_bound_recipient_advances(self):
        self.holder.db.inventory = [_POTION]

        output = self._give(f"{_POTION} = 灰婆婆")

        self.assertIn(f"你把{_POTION}交給了", output)
        self.assertEqual(self.holder.db.inventory, [])
        self.assertEqual(self.recipient.db.inventory, [_POTION])
        self.assertEqual(read_records(self.holder)[0].stage_progress, 1)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_a_numbered_partial_give_leaves_the_stage_with_the_remainder(self):
        self.holder.db.inventory = [_POTION, _POTION]

        output = self._give(f"1 個 {_POTION} = 灰婆婆")

        self.assertIn(f"你把{_POTION}交給了", output)
        self.assertEqual(read_records(self.holder)[0].stage_progress, 1)
        self.assertEqual(self.holder.db.inventory, [_POTION])
        # The exploration affordance keeps advertising the remaining quantity.
        views = active_deliveries_for_recipient(self.holder, self.recipient)
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0].remaining, 1)
        self.assertTrue(views[0].deliverable)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_a_numbered_completing_give_completes_the_stage(self):
        self.holder.db.inventory = [_POTION, _POTION]

        output = self._give(f"2 個 {_POTION} = 灰婆婆")

        self.assertIn(f"你把2 個 {_POTION}交給了", output)
        advanced = read_records(self.holder)[0]
        self.assertEqual(advanced.stage_progress, 2)
        self.assertEqual(advanced.state, QuestState.COMPLETED)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_giving_a_materialized_object_advances(self):
        self.holder.db.inventory = [_POTION]
        create_object(
            "typeclasses.objects.Object",
            key=_POTION,
            attributes=[("registry_key", _POTION)],
            location=self.holder,
        )

        output = self._give(f"{_POTION} = 灰婆婆")

        self.assertIn(f"你把{_POTION}交給了", output)
        self.assertEqual(self.holder.db.inventory, [])
        self.assertEqual(self.recipient.db.inventory, [_POTION])
        self.assertEqual(read_records(self.holder)[0].stage_progress, 1)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_one_give_advances_each_distinct_registry_key_once(self):
        mana_definition = register(
            quest(
                "give_delivery_quest_two",
                stages=(QuestStage(0, deliver(_FLASK, quantity=1)),),
            )
        )
        mana_record = accept(self.holder, mana_definition.key)
        bind_stage_runtime(
            self.holder,
            mana_record.quest_id,
            objective_targets=(self.recipient,),
        )
        self.holder.db.inventory = [_POTION, _FLASK]
        create_object(
            "typeclasses.objects.Object",
            key="藥水",
            attributes=[("registry_key", _POTION)],
            location=self.holder,
        )
        create_object(
            "typeclasses.objects.Object",
            key="藥水",
            attributes=[("registry_key", _FLASK)],
            location=self.holder,
        )

        output = self._give("2 個 藥水 = 灰婆婆")

        self.assertIn("交給了", output)
        progress = {
            entry.quest_id: entry.stage_progress for entry in read_records(self.holder)
        }
        self.assertEqual(progress, {self.record.quest_id: 1, mana_record.quest_id: 1})

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_giving_to_an_unbound_recipient_advances_nothing(self):
        self.holder.db.inventory = [_POTION]

        output = self._give(f"{_POTION} = 旁觀者")

        self.assertIn(f"你把{_POTION}交給了", output)
        self.assertEqual(self.bystander.db.inventory, [_POTION])
        self.assertEqual(read_records(self.holder)[0].stage_progress, 0)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_a_mid_combat_give_advances_the_delivery(self):
        self.holder.db.inventory = [_POTION]
        monster = _monster("give goblin")
        monster.location = self.room1
        engage(self.holder, monster)

        output = self._give(f"{_POTION} = 灰婆婆")

        self.assertIn(f"你把{_POTION}交給了", output)
        self.assertEqual(read_records(self.holder)[0].stage_progress, 1)

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_a_failed_advance_rolls_the_whole_key_give_back(self):
        instance_room = create_object(InstanceRoom, key="give pin room")
        receiver_quest = register(
            quest(
                "give_receiver_acquire",
                stages=(QuestStage(0, acquire(_POTION, quantity=1)),),
            )
        )
        receiver_record = accept(self.recipient, receiver_quest.key)
        bind_stage_runtime(self.recipient, receiver_record.quest_id, room=instance_room)
        pinned_reason = f"quest:{self.recipient.pk}:{receiver_record.quest_id}:stage:0"
        self.assertEqual(instance_room.db.pin_reasons, [pinned_reason])

        self.holder.db.inventory = [_POTION]
        # Populate the recipient's contents cache so the rollback must evict
        # the mirror materialized inside the aborted transaction.
        list(self.recipient.contents)

        with patch(
            "world.rules.npc_intents.advance_deliveries_for_transfer",
            side_effect=RuntimeError("injected advance failure"),
        ) as injected, patch("commands.localized.general.log_warn") as mock_warn:
            output = self._give(f"{_POTION} = 灰婆婆")

        self.assertIn("物品交接失敗，什麼都沒有發生。", output)
        mock_warn.assert_called_once_with(
            "give_transfer_failed",
            exc=injected.side_effect,
            context={
                "char": str(self.holder.pk),
                "target": str(self.recipient.pk),
                "branch": "canonical_key",
                "item": _POTION,
            },
        )
        self.assertEqual(self.holder.db.inventory, [_POTION])
        # The recipient's inventory attribute was unset before the give; the
        # rollback restores that exact pre-state.
        self.assertIsNone(self.recipient.db.inventory)
        self.assertEqual(read_records(self.holder)[0].stage_progress, 0)
        receiver_after = next(
            entry
            for entry in read_records(self.recipient)
            if entry.quest_id == receiver_record.quest_id
        )
        self.assertEqual(receiver_after.stage_progress, 0)
        self.assertEqual(instance_room.db.pin_reasons, [pinned_reason])
        self.assertEqual(
            [o for o in self.recipient.contents if o.db.registry_key == _POTION],
            [],
        )

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_a_failed_advance_rolls_the_whole_object_give_back(self):
        self.holder.db.inventory = [_POTION]
        create_object(
            "typeclasses.objects.Object",
            key=_POTION,
            attributes=[("registry_key", _POTION)],
            location=self.holder,
        )
        held = [o for o in self.holder.contents if o.db.registry_key == _POTION]
        self.assertEqual(len(held), 1)

        with patch(
            "world.rules.npc_intents.advance_deliveries_for_transfer",
            side_effect=RuntimeError("injected advance failure"),
        ) as injected, patch("commands.localized.general.log_warn") as mock_warn:
            output = self._give(f"{_POTION} = 灰婆婆")

        self.assertIn("物品交接失敗，什麼都沒有發生。", output)
        mock_warn.assert_called_once_with(
            "give_transfer_failed",
            exc=injected.side_effect,
            context={
                "char": str(self.holder.pk),
                "target": str(self.recipient.pk),
                "branch": "materialized",
                "item": _POTION,
            },
        )
        self.assertEqual(self.holder.db.inventory, [_POTION])
        self.assertIsNone(self.recipient.db.inventory)
        self.assertEqual(read_records(self.holder)[0].stage_progress, 0)
        self.assertEqual(
            [o for o in self.holder.contents if o.db.registry_key == _POTION],
            held,
        )
        self.assertEqual(
            [o for o in self.recipient.contents if o.db.registry_key == _POTION],
            [],
        )

    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_giving_an_equipped_item_keeps_its_refusal(self):
        self.holder.db.inventory = [_BLADE]
        self.holder.db.equipment = {
            "weapon_main": _BLADE,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }

        output = self._give(f"{_BLADE} = 灰婆婆")

        self.assertIn("你無法給予已裝備的物品。", output)
        self.assertEqual(self.holder.db.inventory, [_BLADE])
