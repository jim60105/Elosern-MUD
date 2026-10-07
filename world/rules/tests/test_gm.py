"""S6 inventory, literal traits, wallet and world-wide clock acceptance."""
from unittest import mock
from server.console.tests._support import ConsoleOwnerTest
from world.rules import gm, equipment
from world.rules.clock import AdvanceSource, MAX_ADVANCE_SECONDS, read_world_clock
from world.rules.surfaces import snapshot_traits


class RulesConsoleTests(ConsoleOwnerTest):
    def test_acquire_auto_reward_chain_pins_and_every_surface_survive_late_mirror_failure(self):
        from evennia.utils.create import create_object
        from world.tests.synthetic_data import make_quest
        from world.quests.definitions import QuestStage, register_quest_definition
        from world.quests.tests._fixtures import acquire, register_auto_issuance
        from world.quests.runtime import accept_quest
        from world.quests.binding import bind_stage_runtime
        from world.rules.guild_offers import QuestReward, ItemQuantity
        from world.rules.surfaces import attribute_snapshot
        definitions = (
            make_quest('t_gm_direct',stages=(QuestStage(0,acquire('t_huskapple')),)),
            make_quest('t_gm_chain',stages=(QuestStage(0,acquire('t_ember_spray')),)),
        )
        rooms=[]
        for index,definition in enumerate(definitions):
            register_quest_definition(definition)
            reward=QuestReward(copper=7,items=(ItemQuantity('t_ember_spray',1),) if index==0 else (),merit=0)
            issuer=register_auto_issuance(definition.key,reward)
            record=accept_quest(self.player,definition.key,issuer)
            room=create_object('typeclasses.rooms.InstanceRoom',key=f't_gm_pin_{index}')
            bind_stage_runtime(self.player,record.quest_id,room=room)
            rooms.append(room)
        before={key:attribute_snapshot(self.player,key) for key in ('inventory','equipment','buffs','wallet','guild_reward_claims','quest_log')}
        traits=snapshot_traits(self.player)
        pins=[attribute_snapshot(room,'pin_reasons') for room in rooms]
        original=equipment.materialize_registry_object
        def late(actor,key):
            original(actor,key)
            self.assertEqual(actor.db.wallet,14)
            self.assertEqual(len(actor.db.guild_reward_claims),2)
            self.assertTrue(all(not room.db.pin_reasons for room in rooms))
            raise RuntimeError('after automatic reward chain')
        with mock.patch.object(equipment,'materialize_registry_object',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.give_item(self.target,'t_huskapple',1)
        for key,value in before.items():
            self.assertEqual(attribute_snapshot(self.player,key),value)
        self.assertEqual(snapshot_traits(self.player),traits)
        self.assertEqual([attribute_snapshot(room,'pin_reasons') for room in rooms],pins)
        self.assertEqual(list(self.player.contents),[])

    def test_grant_take_repeated_materialized_mixed_and_key_only(self):
        gm.give_item(self.target,'t_huskapple',3)
        self.assertEqual(list(self.player.db.inventory), ['t_huskapple']*3)
        self.assertEqual(len(self.player.contents),3)
        gm.take_item(self.target,'t_huskapple',1)
        self.assertEqual(len(self.player.contents),2)
        self.assertEqual(len(self.player.db.inventory),2)
        for obj in list(self.player.contents):
            obj.delete()
        gm.take_item(self.target,'t_huskapple',1)
        self.assertEqual(list(self.player.db.inventory),['t_huskapple'])
        self.assertEqual(list(self.player.contents),[])

    def test_inventory_validation_before_any_change(self):
        for verb in (gm.give_item,gm.take_item):
            for quantity in (True,0,-1,1.5,'2'):
                self.assert_refusal('invalid_argument',lambda:verb(self.target,'t_huskapple',quantity))
            self.assert_refusal('registry_key_not_found',lambda:verb(self.target,'t_missing',1))
            self.assert_refusal('target_kind_mismatch',lambda:verb(f'#{self.monster.pk}','t_huskapple',1))
        self.assert_refusal('invalid_argument',lambda:gm.take_item(self.target,'t_huskapple',1))
        self.assertEqual(list(self.player.db.inventory),[])

    def test_equipped_last_copy_is_unequipped_but_ordinary_removal_stays_rejected(self):
        gm.give_item(self.target,'t_thorn_knife',2)
        self.assertEqual(equipment.toggle_equipment(self.player,'t_thorn_knife').outcome,'success')
        gm.take_item(self.target,'t_thorn_knife',1)
        self.assertIsNone(equipment.equipped_removal_conflict(self.player,()))
        self.assertIsNotNone(equipment.equipped_removal_conflict(self.player,('t_thorn_knife',)))
        with self.assertRaises(ValueError):
            equipment.plan_inventory_delta(self.player,removals=('t_thorn_knife',))
        gm.take_item(self.target,'t_thorn_knife',1)
        self.assertTrue(all(not value for value in self.player.db.equipment.values()))
        self.assertEqual(list(self.player.db.inventory),[])
        self.assertEqual(list(self.player.contents),[])

    def test_give_late_materialization_failure_restores_mirrors_and_cache(self):
        original = equipment.materialize_registry_object
        def late(entity,key):
            original(entity,key)
            raise RuntimeError('after mirror')
        with mock.patch.object(equipment,'materialize_registry_object',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.give_item(self.target,'t_huskapple',2)
        self.assertEqual(list(self.player.db.inventory),[])
        self.assertEqual(list(self.player.contents),[])

    def test_take_multiple_mirror_delete_failure_restores_all(self):
        gm.give_item(self.target,'t_huskapple',3)
        mirrors = list(self.player.contents)
        original = mirrors[1].delete
        def late():
            original()
            raise RuntimeError('after delete')
        with mock.patch.object(mirrors[1],'delete',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.take_item(self.target,'t_huskapple',3)
        self.assertEqual(len(self.player.contents),3)
        self.assertEqual(list(self.player.db.inventory),['t_huskapple']*3)

    def test_wallet_and_literal_trait_and_gauge_normal_invalid_and_rollback(self):
        gm.set_wallet(self.target,27)
        self.assertEqual(self.player.db.wallet,27)
        before = snapshot_traits(self.player)
        lower, upper = gm._base_band(self.player,'hp')
        value = lower + 1 if upper > lower else lower
        self.player.db.disguised_stats = {'hp':999}
        gm.set_trait_base(self.target,'hp',value)
        self.assertEqual(self.player.traits.hp.base,value)
        self.assertEqual(self.player.db.disguised_stats['hp'],999)
        gm.set_gauge(self.target,'hp',0)
        self.assertEqual(self.player.traits.hp.current,0)
        for invalid in (-1,True,0.5,'4'):
            self.assert_refusal('invalid_argument',lambda:gm.set_wallet(self.target,invalid))
            self.assert_refusal('invalid_argument',lambda:gm.set_gauge(self.target,'hp',invalid))
        self.assert_refusal('invalid_argument',lambda:gm.set_trait_base(self.target,'hp',upper+1))
        self.assert_refusal('registry_key_not_found',lambda:gm.set_gauge(self.target,'missing',0))
        self.assert_refusal('registry_key_not_found',lambda:gm.set_trait_base(self.target,'missing',0))
        original = self.player.attributes.add
        def late(key,value,**kwargs):
            original(key,value,**kwargs)
            if key == 'wallet' and value == 55:
                raise RuntimeError('late wallet')
        with mock.patch.object(self.player.attributes,'add',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.set_wallet(self.target,55)
        self.assertEqual(self.player.db.wallet,27)
        traits = snapshot_traits(self.player)
        with mock.patch.object(equipment,'sync_equipment_gauge_limits',side_effect=RuntimeError('late trait')):
            with self.assertRaises(RuntimeError):
                gm.set_trait_base(self.target,'hp',lower)
        self.assertEqual(snapshot_traits(self.player),traits)
        gauge=self.player.traits.hp
        descriptor=type(gauge).current
        def late_current(trait,value):
            descriptor.fset(trait,value)
            raise RuntimeError('after gauge write')
        with mock.patch.object(type(gauge),'current',property(descriptor.fget,late_current)):
            with self.assertRaises(RuntimeError):
                gm.set_gauge(self.target,'hp',1)
        self.assertEqual(snapshot_traits(self.player),traits)

    def test_clock_source_scope_bounds_and_real_settlement_rollback(self):
        from world.rules import clock
        before = read_world_clock().tick
        original = clock._run_stages
        seen = []
        def stages(driver,seconds,source,entities):
            seen.append((source,{entity.pk for entity in entities}))
            return original(driver,seconds,source,entities)
        with mock.patch.object(clock,'_run_stages',side_effect=stages):
            gm.advance_clock(0)
            gm.advance_clock(2)
        self.assertEqual(read_world_clock().tick,before+2)
        self.assertEqual(seen[-1][0],AdvanceSource.GM)
        self.assertTrue({self.player.pk,self.monster.pk,self.npc.pk} <= seen[-1][1])
        gm.advance_clock(MAX_ADVANCE_SECONDS)
        settled_tick=before+2+MAX_ADVANCE_SECONDS
        self.assertEqual(read_world_clock().tick,settled_tick)
        for seconds in (-1,True,1.5,'3',MAX_ADVANCE_SECONDS+1):
            self.assert_refusal('invalid_argument',lambda:gm.advance_clock(seconds))
        attrs = snapshot_traits(self.player)
        def fail(driver,seconds,source,entities):
            self.player.traits.hp.current=0
            raise RuntimeError('later stage')
        with mock.patch.object(clock,'_run_stages',side_effect=fail):
            with self.assertRaises(RuntimeError):
                gm.advance_clock(3)
        self.assertEqual(read_world_clock().tick,settled_tick)
        self.assertEqual(snapshot_traits(self.player),attrs)
