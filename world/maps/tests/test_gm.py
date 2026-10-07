"""S6 map lifecycle consequences and persistent/live atomicity acceptance."""
from unittest import mock
from evennia.objects.models import ObjectDB
from server.console.tests._support import ConsoleOwnerTest
from world.maps import gm
from world.rules.clock import read_world_clock
from world.rules import skip_safety


class MapConsoleTests(ConsoleOwnerTest):
    def setUp(self):
        super().setUp()
        self.registrations=dict(skip_safety._BATTLEFIELDS)

    def test_teleport_party_instance_arrival_and_all_live_consequence_rollback(self):
        from evennia.utils.create import create_object
        from world.rules.party import join_party
        from world.rules.surfaces import attribute_snapshot
        join_party(self.npc,self.player)
        destination=create_object('typeclasses.rooms.InstanceRoom',key='t_console_destination')
        destination.db.pin_reasons=['t_manual_pin']
        tick=read_world_clock().tick
        gm.teleport(self.target,f'#{destination.pk}')
        self.assertIs(self.npc.location,destination)
        self.assertTrue(destination.interacted)
        self.assertEqual(list(destination.pin_reasons),['t_manual_pin'])
        self.assertEqual(read_world_clock().tick,tick)
        before={key:attribute_snapshot(self.player,key) for key in ('party','map_knowledge','quest_log','home')}
        with mock.patch('world.rules.city_gates.reanchor_home_on_gate_arrival',side_effect=RuntimeError('after companion arrival')):
            with self.assertRaises(RuntimeError):
                gm.teleport(self.target,f'#{self.room2.pk}')
        self.assertIs(self.player.location,destination)
        self.assertIs(self.npc.location,destination)
        for key,value in before.items():
            self.assertEqual(attribute_snapshot(self.player,key),value)
        self.assertIn(self.npc,destination.contents)
        self.assertNotIn(self.npc,self.room2.contents)
        self.assertEqual(list(destination.pin_reasons),['t_manual_pin'])
        self.assertEqual(read_world_clock().tick,tick)

    def tearDown(self):
        skip_safety._BATTLEFIELDS.clear()
        skip_safety._BATTLEFIELDS.update(self.registrations)
        super().tearDown()

    def test_teleport_dialogue_and_no_cost_with_late_rollback(self):
        self.player.db.dialogue_session={'npc_id':self.npc.pk,'line':'Synthetic line','updated_tick':0}
        tick=read_world_clock().tick
        gm.teleport(self.target,f'#{self.room2.pk}')
        self.assertIs(self.player.location,self.room2)
        self.assertIsNone(self.player.db.dialogue_session)
        self.assertEqual(read_world_clock().tick,tick)
        with mock.patch('world.rules.city_gates.reanchor_home_on_gate_arrival',side_effect=RuntimeError('late')):
            with self.assertRaises(RuntimeError):
                gm.teleport(self.target,f'#{self.room1.pk}')
        self.assertIs(self.player.location,self.room2)
        self.assertIn(self.player,self.room2.contents)
        self.assertNotIn(self.player,self.room1.contents)
        self.assertEqual(read_world_clock().tick,tick)

    def test_teleport_validation(self):
        self.assert_refusal('target_kind_mismatch',lambda:gm.teleport(f'#{self.npc.pk}',f'#{self.room2.pk}'))
        self.assert_refusal('target_kind_mismatch',lambda:gm.teleport(self.target,self.target))
        self.assert_refusal('target_not_found',lambda:gm.teleport(self.target,'#99999999'))
        self.assert_refusal('invalid_argument',lambda:gm.teleport(self.target,True))
        self.assertIs(self.player.location,self.room1)

    def test_spawn_authoritative_identity_and_placement_rollback(self):
        result=gm.spawn_monster('t_whisper_quail','t_whisper_quail_ordinary',f'#{self.room2.pk}')
        entity=ObjectDB.objects.get(pk=int(result['target'][1:]))
        self.assertEqual(entity.species_key,'t_whisper_quail')
        self.assertEqual(entity.variant_key,'t_whisper_quail_ordinary')
        self.assertIs(entity.location,self.room2)
        stronger=gm.spawn_monster('t_whisper_quail','t_whisper_quail_stronger',f'#{self.room1.pk}')
        strong_entity=ObjectDB.objects.get(pk=int(stronger['target'][1:]))
        from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS
        profile=SYNTH_MONSTER_VARIANTS['t_whisper_quail_stronger'].combat_profile
        for trait in ('hp','mp','sp','atk_phys','agility','defense','magic_power'):
            self.assertEqual(strong_entity.traits.get(trait).base,getattr(profile,trait))
        before=ObjectDB.objects.count()
        from typeclasses.monsters import Monster
        original=Monster.move_to
        def late(monster,*args,**kwargs):
            original(monster,*args,**kwargs)
            raise RuntimeError('after placement')
        with mock.patch.object(Monster,'move_to',late):
            with self.assertRaises(RuntimeError):
                gm.spawn_monster('t_whisper_quail','t_whisper_quail_ordinary',f'#{self.room2.pk}')
        self.assertEqual(ObjectDB.objects.count(),before)
        self.assertEqual(len([obj for obj in self.room2.contents if isinstance(obj, Monster) and obj.species_key=='t_whisper_quail']),1)
        self.assert_refusal('registry_key_not_found',lambda:gm.spawn_monster('t_missing','t_whisper_quail_ordinary',f'#{self.room2.pk}'))
        self.assert_refusal('target_kind_mismatch',lambda:gm.spawn_monster('t_whisper_quail','t_whisper_quail_ordinary',self.target))
        self.assert_refusal('registry_key_not_found',lambda:gm.spawn_monster('t_whisper_quail','t_missing',f'#{self.room2.pk}'))
        for value in (None,True,3,[],{}):
            self.assert_refusal('invalid_argument',lambda:gm.spawn_monster(value,'t_whisper_quail_ordinary',f'#{self.room2.pk}'))
            self.assert_refusal('invalid_argument',lambda:gm.spawn_monster('t_whisper_quail',value,f'#{self.room2.pk}'))
        from world.tests.synthetic_data import synthetic_registries, make_monster_variant, SYNTH_MONSTER_VARIANTS
        self.enterContext(synthetic_registries('monster_variants',extra={'monster_variants':{**SYNTH_MONSTER_VARIANTS,'t_other_variant':make_monster_variant('t_other_variant',species_key='t_other_species')}}))
        self.assert_refusal('invalid_argument',lambda:gm.spawn_monster('t_whisper_quail','t_other_variant',f'#{self.room2.pk}'))

    def test_delete_real_hooks_cleanup_and_late_failure_rebinds_live_roster(self):
        from world.rules.combat_session.lifecycle import engage
        engage(self.player,self.monster)
        field=skip_safety._BATTLEFIELDS[str(self.player.pk)]
        monster_pk=self.monster.pk
        registrations=dict(skip_safety._BATTLEFIELDS)
        before=dict(self.player.db.active_combat)
        context=self.player.ndb.action_context
        from world.rules.surfaces import attribute_snapshot
        buffs=attribute_snapshot(self.player,'buffs')
        original=self.monster.delete
        def late():
            original()
            raise RuntimeError('after actual delete')
        with mock.patch.object(self.monster,'delete',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.delete_entity(f'#{monster_pk}')
        self.assertTrue(ObjectDB.objects.filter(pk=monster_pk).exists())
        self.assertEqual(dict(self.player.db.active_combat),before)
        self.assertIs(self.player.ndb.action_context,context)
        self.assertEqual(attribute_snapshot(self.player,'buffs'),buffs)
        self.assertEqual(skip_safety._BATTLEFIELDS,registrations)
        restored=ObjectDB.objects.get(pk=monster_pk)
        self.assertIn(restored,field.roster.values())
        self.assertIsNotNone(restored.pk)
        with mock.patch.object(restored,'at_object_delete',wraps=restored.at_object_delete) as hook:
            result=gm.delete_entity(f'#{monster_pk}')
        hook.assert_called_once()
        self.assertTrue(result['deleted'])
        self.assertFalse(ObjectDB.objects.filter(pk=monster_pk).exists())
        self.assertIsNone(self.player.db.active_combat)
        self.assertNotIn(str(monster_pk),skip_safety._BATTLEFIELDS)
        self.assert_refusal('target_kind_mismatch',lambda:gm.delete_entity(self.target))
        self.assert_refusal('target_not_found',lambda:gm.delete_entity(f'#{monster_pk}'))

    def test_delete_compensation_survives_a_stale_registration(self):
        """An unrelated stale registration cannot abort the compensation."""
        from evennia.utils.create import create_object
        from world.rules.combat import Battlefield
        from world.rules.combat_session.lifecycle import engage

        # A participant deleted before its battlefield settled leaves the landed
        # registration in place with a revoked instance in its roster (the state
        # unregister_participants' dbref guard anticipates).
        ghost=create_object('typeclasses.monsters.Monster',key='t_console_ghost',location=self.room1)
        ally=create_object('typeclasses.monsters.Monster',key='t_console_ally',location=self.room1)
        stale=Battlefield(teams={'enemies':frozenset({str(ghost.key)}),'allies':frozenset({str(ally.key)})},roster={str(ghost.key):ghost,str(ally.key):ally})
        skip_safety.register_active_battlefield(stale)
        ghost.delete()
        self.assertIsNone(ghost.pk)
        self.assertIn(str(ghost.key),stale.roster)
        engage(self.player,self.monster)
        field=skip_safety._BATTLEFIELDS[str(self.player.pk)]
        monster_pk=self.monster.pk
        registrations=dict(skip_safety._BATTLEFIELDS)
        before=dict(self.player.db.active_combat)
        original=self.monster.delete
        def late():
            original()
            raise RuntimeError('after actual delete')
        with mock.patch.object(self.monster,'delete',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.delete_entity(f'#{monster_pk}')
        self.assertTrue(ObjectDB.objects.filter(pk=monster_pk).exists())
        self.assertEqual(skip_safety._BATTLEFIELDS,registrations)
        self.assertEqual(dict(self.player.db.active_combat),before)
        self.assertIn(str(self.monster.key),field.roster)
        self.assertNotIn(str(ghost.key),stale.roster)
        self.assertIn(str(ally.key),stale.roster)
