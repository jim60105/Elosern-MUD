"""Ordered raw repair, reference decoding and durable/live rollback acceptance."""
from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.create import create_object
from server.console.raw import apply_raw
from server.console.errors import ConsoleError


class RawTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.target = f'#{self.obj1.pk}'

    def test_ordered_categories_refs_tags_and_null_location(self):
        apply_raw(self.target, [
            {'op':'set_attr','key':'repair','category':'a','value': {'nested':[{'$ref':f'#{self.room1.pk}', 'key':'ignored', 'typeclass':'ignored'}, True, 3, None]}},
            {'op':'set_attr','key':'repair','category':'b','value':2},
            {'op':'del_attr','key':'repair','category':'b'},
            {'op':'add_tag','key':'marker','category':'a'},
            {'op':'add_tag','key':'marker','category':'b'},
            {'op':'remove_tag','key':'marker','category':'b'},
            {'op':'set_location','value':{'$ref':f'#{self.room2.pk}'}},
            {'op':'set_location','value':None},
        ])
        self.assertIs(self.obj1.attributes.get('repair', category='a')['nested'][0], self.room1)
        self.assertFalse(self.obj1.attributes.has('repair', category='b'))
        self.assertTrue(self.obj1.tags.has('marker', category='a'))
        self.assertFalse(self.obj1.tags.has('marker', category='b'))
        self.assertIsNone(self.obj1.location)

    def test_late_failure_restores_same_instance_and_rows(self):
        self.obj1.db.repair = 1
        self.obj1.tags.add('original', category='a')
        source = self.obj1.location
        with mock.patch.object(self.obj1.tags, 'add', side_effect=RuntimeError('late')):
            with self.assertRaises(RuntimeError):
                apply_raw(self.target, [{'op':'set_attr','key':'repair','value':2}, {'op':'remove_tag','key':'original','category':'a'}, {'op':'set_location','value':{'$ref':f'#{self.room2.pk}'}}, {'op':'add_tag','key':'later','category':None}])
        self.assertEqual(self.obj1.db.repair, 1)
        self.assertIs(self.obj1.location, source)
        self.assertIn(self.obj1, source.contents)
        self.assertNotIn(self.obj1, self.room2.contents)
        self.assertTrue(self.obj1.tags.has('original', category='a'))

    def test_forbidden_display_fields_models_execution_and_shapes(self):
        invalid=[
            {'op':'set_components','value':[]},{'op':'set_created','value':0},
            {'op':'set_model','model':'world.narrative.MemoryRecord','value':{}},
            {'op':'exec','code':'pass'},{'op':None},
            {'op':'del_attr','key':''},{'op':'set_attr','key':'x','value':1,'extra':True},
            {'op':'set_location','value':{'$ref':f'#{self.room1.pk}','extra':True}},
            {'op':'set_attr','key':'x','value':{'$ref':True}},
        ]
        for operation in invalid:
            with self.subTest(operation=operation),self.assertRaises(ConsoleError) as caught:
                apply_raw(self.target,[operation])
            self.assertEqual(caught.exception.code,'raw_edit_invalid')
        for operations in (None,{},'set_attr',[None],['set_attr']):
            with self.subTest(operations=operations),self.assertRaises(ConsoleError):
                apply_raw(self.target,operations)

    def test_invalid_complete_batch_never_writes(self):
        invalid = [ {'op':'set_typeclass','value':'anything'}, {'op':'set_attr','key':'x','value':{'$unserializable':'object'}}, {'op':'set_attr','key':'x','value':{'$ref':'#99999999'}}, {'op':'set_attr','key':'x','value':{'$ref':'bad'}}, {'op':'set_attr','key':'x','value':float('inf')}, {'op':'set_attr','key':'x','value':[float('nan')]}, {'op':'add_tag','key':'x'}, {'op':'set_location','value':3}, {'op':'set_attr','key':'x','category':4,'value':1} ]
        for operation in invalid:
            with self.subTest(operation=operation), self.assertRaises(ConsoleError) as caught:
                apply_raw(self.target, [{'op':'set_attr','key':'before','value':True}, operation])
            self.assertEqual(caught.exception.code, 'raw_edit_invalid')
            self.assertFalse(self.obj1.attributes.has('before'))

    def test_raw_location_has_no_movement_settlement(self):
        with mock.patch.object(self.obj1, 'move_to') as move:
            apply_raw(self.target, [{'op':'set_location','value':{'$ref':f'#{self.room2.pk}'}}])
        move.assert_not_called()
        self.assertIs(self.obj1.location, self.room2)

    def test_mounted_gameplay_handlers_rebind_on_success_and_failure(self):
        entity = create_object('typeclasses.entities.LivingEntity', key='t_raw_living', location=self.room1)
        entity.traits.add('hp', trait_type='gauge', base=20, min=0)
        mounted = entity.traits
        state = dict(entity.attributes.get('traits', category='traits'))
        state = {key: dict(value) for key,value in state.items()}
        state['hp']['base'] = 30
        apply_raw(f'#{entity.pk}', [{'op':'set_attr','key':'traits','category':'traits','value':state}])
        self.assertEqual(mounted.hp.base,30)
        with mock.patch.object(entity.tags, 'add', side_effect=RuntimeError('late')):
            with self.assertRaises(RuntimeError):
                apply_raw(f'#{entity.pk}', [{'op':'set_attr','key':'traits','category':'traits','value':{}}, {'op':'add_tag','key':'late','category':None}])
        self.assertEqual(mounted.hp.base,30)
        sexual=entity.sexual
        sexual._traits.add('t_raw_gauge',trait_type='gauge',base=10,min=0)
        storage=entity.attributes.get('sexual_traits',category='traits')
        state={'t_raw_gauge':dict(storage['t_raw_gauge'])}
        key='t_raw_gauge'
        state[key]['base']+=1
        apply_raw(f'#{entity.pk}',[{'op':'set_attr','key':'sexual_traits','category':'traits','value':state}])
        self.assertEqual(sexual._traits.get(key).base,state[key]['base'])
        with mock.patch.object(entity.tags,'add',side_effect=RuntimeError('late sexual')):
            with self.assertRaises(RuntimeError):
                apply_raw(f'#{entity.pk}',[{'op':'set_attr','key':'sexual_traits','category':'traits','value':{}},{'op':'add_tag','key':'late','category':None}])
        self.assertEqual(sexual._traits.get(key).base,state[key]['base'])
