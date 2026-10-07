"""The handoff encloses a real owner rollback, not merely mocked dispatch."""
from types import SimpleNamespace
from unittest import mock
from server.console import execution
from server.console.errors import ConsoleError
from server.console.snapshot_policy import SnapshotPolicy
from server.console.tests._support import ConsoleOwnerTest
from world.rules import equipment, gm
from world.rules.clock import AdvanceSource, read_world_clock
from tools.spec_traceability import covers_requirement


class OwnerHandoffTests(ConsoleOwnerTest):
    @covers_requirement('gm-developer-console::gameplay-thread-serialized-console-execution')
    def test_player_inventory_and_time_commit_only_before_or_after_owner_compensation(self):
        calls=[]
        def player_change(key):
            equipment.apply_inventory_plan(equipment.plan_inventory_delta(self.player,additions=(key,)))
            read_world_clock().advance(1,AdvanceSource.COMMAND,(self.player,))
        def runner(call):
            if not calls:
                player_change('t_iron_fang')
            calls.append(call)
            result=call()
            if not result.needs_save:
                self.assertNotIn('t_huskapple',self.player.db.inventory)
                player_change('t_ember_spray')
            return result
        def saver(kind,label):
            self.assertFalse(execution.in_handoff())
            return SimpleNamespace(id='t_undo',clock={'tick':read_world_clock().tick})
        policy=SnapshotPolicy(runner=runner,saver=saver)
        initial=read_world_clock().tick
        original=equipment.materialize_registry_object
        def late(actor,key):
            self.assertTrue(execution.in_handoff())
            self.assertEqual(list(actor.db.inventory),['t_iron_fang','t_huskapple'])
            original(actor,key)
            raise RuntimeError('late real owner mutation')
        with mock.patch.object(equipment,'materialize_registry_object',side_effect=late),mock.patch('server.console.snapshot_policy.log_error'):
            with self.assertRaises(ConsoleError) as caught:
                policy.execute(lambda:gm.give_item(self.target,'t_huskapple',1),action='give_item',account='synthetic',target=self.target)
        self.assertEqual(caught.exception.code,'internal_error')
        self.assertEqual(caught.exception.snapshot,{'taken':True,'save_id':'t_undo'})
        self.assertEqual(list(self.player.db.inventory),['t_iron_fang','t_ember_spray'])
        self.assertEqual(list(self.player.contents),[])
        self.assertEqual(read_world_clock().tick,initial+2)
        self.assertEqual(policy.baseline_tick,initial+1)
        self.assertTrue(policy.status()['will_snapshot'])
        self.assertEqual(len(calls),2)
