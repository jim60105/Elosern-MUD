"""S6 frozen-record repair, issuance, binding release and rollback acceptance."""
from unittest import mock
from evennia.utils.create import create_object
from server.console.tests._support import ConsoleOwnerTest
from world.quests import gm, runtime, transitions
from world.quests.binding import bind_stage_runtime
from world.tests.synthetic_data import SYNTH_COMMISSIONER_KEY
from world.quests.tests._fixtures import RegistryIsolationMixin


class QuestConsoleTests(RegistryIsolationMixin, ConsoleOwnerTest):
    def test_generated_definition_restores_without_store_creation_and_rebinds_stage_pins(self):
        from world.tests.synthetic_data import make_quest, synthetic_registries
        from world.quests.compile import CompiledQuest, IssuanceDescriptor, StageSpawnRequirement, register_generated_quest, SCENE_REQUIREMENT_REGISTRY
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestStage, QuestObjective, ObjectiveKind, DestinationKind, RoomLocator, QuestType
        from world.rules.guild_offers import QuestReward
        from world.rules.quest_issuance import Settlement, QUEST_ISSUANCE_REGISTRY
        from world.quests.generated_quest_store import read_payloads
        self.enterContext(synthetic_registries('archetypes'))
        from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
        locator=RoomLocator(DestinationKind.BOUND_INSTANCE)
        definition=make_quest('t_gm_generated',quest_type=QuestType.EXPLORE,stages=(
            QuestStage(0,QuestObjective(ObjectiveKind.REACH,destination=locator)),
            QuestStage(1,QuestObjective(ObjectiveKind.REACH,destination=locator)),
        ))
        archetype=next(iter(SCENE_ARCHETYPE_REGISTRY))
        compiled=CompiledQuest(definition,QuestReward(copper=2,items=(),merit=0),IssuanceDescriptor(SYNTH_COMMISSIONER_KEY,Settlement.AUTO),tuple(StageSpawnRequirement(index,ObjectiveKind.REACH,locator,archetype,None,'合成測試場景。',()) for index in (0,1)))
        register_generated_quest(compiled)
        payloads=read_payloads()
        identity=gm.issue_quest(self.target,definition.key,SYNTH_COMMISSIONER_KEY)['quest_id']
        QUEST_DEFINITION_REGISTRY.pop(definition.key)
        QUEST_ISSUANCE_REGISTRY.pop((definition.key,SYNTH_COMMISSIONER_KEY))
        SCENE_REQUIREMENT_REGISTRY.pop(definition.key)
        gm.set_quest_stage(self.target,identity,0)
        record=runtime.read_records(self.player)[0]
        from evennia.objects.models import ObjectDB
        previous=ObjectDB.objects.get(pk=record.stage_room_id)
        self.assertTrue(previous.db.pin_reasons)
        gm.set_quest_stage(self.target,identity,1)
        current=runtime.read_records(self.player)[0]
        self.assertNotEqual(current.stage_room_id,previous.pk)
        self.assertEqual(list(previous.db.pin_reasons),[])
        new=ObjectDB.objects.get(pk=current.stage_room_id)
        self.assertTrue(new.db.pin_reasons)
        before=list(self.player.db.quest_log)
        pins=list(new.db.pin_reasons)
        from world.quests import scene_builder
        original=scene_builder.materialize_stage
        def late(*args,**kwargs):
            original(*args,**kwargs)
            raise RuntimeError('after new binding')
        with mock.patch.object(scene_builder,'materialize_stage',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.set_quest_stage(self.target,identity,0)
        self.assertEqual(list(self.player.db.quest_log),before)
        self.assertEqual(list(new.db.pin_reasons),pins)
        self.assertEqual(read_payloads(),payloads)

    def issue(self):
        return gm.issue_quest(self.target,'t_ember_cull',SYNTH_COMMISSIONER_KEY)['quest_id']

    def test_issue_initialized_repair_and_reward_idempotence(self):
        identity=self.issue()
        record=runtime.find_record(runtime.read_records(self.player),identity)
        self.assertEqual(record.stage_progress,0)
        self.assertEqual(record.state,runtime.QuestState.IN_PROGRESS)
        gm.set_quest_state(self.target,identity,'completed')
        self.assertEqual(runtime.read_records(self.player)[0].state,runtime.QuestState.COMPLETED)
        wallet=self.player.db.wallet
        claims=list(self.player.db.guild_reward_claims or [])
        gm.set_quest_state(self.target,identity,'in_progress')
        gm.set_quest_state(self.target,identity,'completed')
        self.assertEqual(self.player.db.wallet,wallet)
        self.assertEqual(list(self.player.db.guild_reward_claims or []),claims)
        gm.set_quest_stage(self.target,identity,0)
        self.assertEqual(runtime.read_records(self.player)[0].state,runtime.QuestState.IN_PROGRESS)

    def test_invalid_state_stage_issuer_definition_kind_and_identity(self):
        identity=self.issue()
        before=list(self.player.db.quest_log)
        for value in (True,1,'missing'):
            self.assert_refusal('invalid_argument',lambda:gm.set_quest_state(self.target,identity,value))
        for value in (True,-1,1,1.5,'0'):
            self.assert_refusal('invalid_argument',lambda:gm.set_quest_stage(self.target,identity,value))
        self.assert_refusal('target_not_found',lambda:gm.set_quest_state(self.target,'absent','failed'))
        self.assert_refusal('registry_key_not_found',lambda:gm.issue_quest(self.target,'t_missing',SYNTH_COMMISSIONER_KEY))
        self.assert_refusal('invalid_argument',lambda:gm.issue_quest(self.target,'t_tarn_messenger','malformed'))
        self.assert_refusal('target_kind_mismatch',lambda:gm.issue_quest(f'#{self.npc.pk}','t_tarn_messenger',SYNTH_COMMISSIONER_KEY))
        self.assertEqual(list(self.player.db.quest_log),before)

    def test_obsolete_pin_release_and_replacement_failure_rollback(self):
        identity=self.issue()
        room=create_object('typeclasses.rooms.InstanceRoom',key='t_console_instance')
        bind_stage_runtime(self.player,identity,room=room,objective_targets=(self.monster,))
        before=list(self.player.db.quest_log)
        pins=list(room.db.pin_reasons)
        original=transitions._apply_pin_operations
        def fail(operations):
            original(operations)
            raise RuntimeError('after pins')
        for operation in (lambda:gm.set_quest_state(self.target,identity,'failed'),lambda:gm.set_quest_stage(self.target,identity,0)):
            with mock.patch.object(transitions,'_apply_pin_operations',side_effect=fail):
                with self.assertRaises(RuntimeError):
                    operation()
            self.assertEqual(list(self.player.db.quest_log),before)
            self.assertEqual(list(room.db.pin_reasons),pins)
        gm.set_quest_state(self.target,identity,'failed')
        self.assertEqual(list(room.db.pin_reasons),[])
        self.assertIsNone(runtime.read_records(self.player)[0].stage_room_id)

    def test_issuance_late_failure_leaves_no_record(self):
        original=runtime.apply_quest_log_replacement
        def late(*args,**kwargs):
            original(*args,**kwargs)
            raise RuntimeError('after issuance')
        with mock.patch.object(runtime,'apply_quest_log_replacement',side_effect=late):
            with self.assertRaises(RuntimeError):
                self.issue()
        self.assertEqual(list(self.player.db.quest_log),[])
