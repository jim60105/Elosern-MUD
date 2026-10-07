"""Protected S6 API, fixed dispatch, truthful saves and post-commit projection."""
import json
from types import SimpleNamespace
from unittest import mock
from django.conf import settings
from server.console import registry, snapshot_policy
from server.console.errors import ConsoleError
from server.console.tests._support import ConsoleOwnerTest
from web.gm.tests._support import GmTestCase
from tools.spec_traceability import covers_requirement


class ConsoleApiTests(ConsoleOwnerTest,GmTestCase):
    def setUp(self):
        super().setUp()
        self.saves=[]
        def save(kind,label):
            self.saves.append((kind,label))
            return SimpleNamespace(id='synthetic-save',clock={'tick':self.clock.tick})
        self.policy=snapshot_policy.SnapshotPolicy(runner=lambda call:call(),saver=save)
        patcher=mock.patch.object(snapshot_policy,'policy',self.policy)
        patcher.start(); self.addCleanup(patcher.stop)
        self.client=self.client_for('developer')

    def post(self,path,body,client=None,**headers):
        return (client or self.client).post(path,data=json.dumps(body),content_type='application/json',**headers)

    def result(self,response,status=200):
        self.assertEqual(response.status_code,status,response.content)
        return json.loads(response.content)

    @covers_requirement(
        'gm-portal-access-api::protected-gm-namespace',
        'gm-portal-access-api::consistent-json-transport',
        'gm-developer-console::protected-deterministic-console-boundary',
        'gm-runtime-state::runtime-api-routes-and-bounded-lists',
    )
    def test_access_and_csrf_apply_to_all_fixed_verbs_raw_and_status(self):
        routes=[f'/gm/api/console/{verb}' for verb in registry.VERBS]+[f'/gm/api/state/object/{self.player.pk}/raw']
        for kind,status,code in [('anonymous',401,'unauthenticated'),('player',403,'forbidden')]:
            client=self.client_for(kind)
            for path in routes:
                self.assert_error_envelope(self.post(path,{},client),status,code)
            self.assert_error_envelope(client.get('/gm/api/console/status'),status,code)
        csrf=self.client_for('developer',enforce_csrf_checks=True)
        token=csrf.get('/gm/').cookies[settings.CSRF_COOKIE_NAME].value
        for path in routes:
            for headers in ({},{'HTTP_X_CSRFTOKEN':'x'*len(token)}):
                self.assert_error_envelope(self.post(path,{},csrf,**headers),403,'csrf_failed')
            accepted=self.post(path,{},csrf,HTTP_X_CSRFTOKEN=token)
            self.assertEqual(accepted.status_code,400,accepted.content)
        self.assertEqual(self.saves,[])
        for kind in ('developer','superuser'):
            privileged=self.client_for(kind)
            self.assert_ok_envelope(privileged.get('/gm/api/console/status'))
            for path in routes:
                self.assertEqual(self.post(path,{},privileged).status_code,400)
        body=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':5},csrf,HTTP_X_CSRFTOKEN=token))
        self.assertTrue(body['ok'])
        self.assertEqual(self.player.db.wallet,5)

    @covers_requirement('gm-developer-console::shared-console-transport-results-and-errors')
    def test_status_is_noncreating_and_read_only_and_registry_is_closed(self):
        data=self.assert_ok_envelope(self.client.get('/gm/api/console/status'))
        self.assertEqual(data['tick'],self.clock.tick)
        self.assertIsNone(data['baseline_tick'])
        self.assertTrue(data['will_snapshot'])
        self.assertEqual(self.saves,[])
        self.assert_error_envelope(self.post('/gm/api/console/status',{}),405,'method_not_allowed')
        for path in ('/gm/api/console/python','/gm/api/console/eval','/gm/api/console/reset_xp'):
            body=self.result(self.post(path,{}),404)
            self.assertEqual(body['error']['code'],'unknown_verb')
            self.assertEqual(body['snapshot'],{'taken':False,'save_id':None})
        for verb in registry.VERBS:
            self.assert_error_envelope(self.client.get(f'/gm/api/console/{verb}'),405,'method_not_allowed')
        self.assertEqual(self.saves,[])

    @covers_requirement('gm-developer-console::shared-console-transport-results-and-errors')
    def test_missing_clock_status_and_write_are_noncreating(self):
        from evennia.scripts.models import ScriptDB
        from evennia.typeclasses.models import Attribute
        ScriptDB.objects.filter(db_key='world_clock').delete()
        before=(ScriptDB.objects.count(),Attribute.objects.count())
        status=self.assert_ok_envelope(self.client.get('/gm/api/console/status'))
        self.assertIsNone(status['tick'])
        self.assertTrue(status['will_snapshot'])
        refusal=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':1}),404)
        self.assertEqual(refusal['error']['code'],'target_not_found')
        self.assertEqual(before,(ScriptDB.objects.count(),Attribute.objects.count()))
        self.assertEqual(self.saves,[])
        self.assertIsNone(self.policy.baseline_tick)
        self.assertEqual(self.player.db.wallet,0)

    @covers_requirement('gm-developer-console::shared-console-transport-results-and-errors')
    def test_real_authoritative_wallet_raw_clock_deletion_and_domain_refusal(self):
        wallet=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':9}))['data']
        self.assertEqual(wallet['snapshot'],{'taken':True,'save_id':'synthetic-save'})
        self.assertEqual(wallet['target'],self.target)
        self.assertEqual(self.player.db.wallet,9)
        self.assertEqual(wallet['state'],self.assert_ok_envelope(self.client.get(f'/gm/api/state/characters/{self.player.pk}')))
        raw=self.result(self.post(f'/gm/api/state/object/{self.player.pk}/raw',{'operations':[{'op':'set_attr','key':'repair','category':'a','value':False}]}))['data']
        self.assertFalse(raw['snapshot']['taken'])
        self.assertFalse(self.player.attributes.get('repair',category='a'))
        clock=self.result(self.post('/gm/api/console/advance_clock',{'seconds':2}))['data']
        from world.rules.clock import read_world_clock
        self.assertEqual(clock['state']['clock']['tick'],read_world_clock().tick)
        self.assertFalse(clock['snapshot']['taken'])
        refused=self.result(self.post('/gm/api/console/give_item',{'target':self.target,'key':'missing','quantity':1}),404)
        self.assertFalse(refused['snapshot']['taken'])
        self.assertEqual(refused['error']['code'],'registry_key_not_found')
        deleted=self.result(self.post('/gm/api/console/delete_entity',{'target':f'#{self.monster.pk}'}))['data']
        self.assertTrue(deleted['state']['deleted'])
        self.assertIn('room',deleted['state'])
        self.assertEqual(len(self.saves),1)

    @covers_requirement('gm-developer-console::shared-console-transport-results-and-errors')
    def test_spawn_quest_memory_and_instance_room_project_real_committed_readers(self):
        from evennia.utils.create import create_object
        from world.tests.synthetic_data import SYNTH_COMMISSIONER_KEY
        from world.narrative import memory
        room=create_object('typeclasses.rooms.InstanceRoom',key='t_api_instance')
        room_id=f'#{room.pk}'
        rooms=self.assert_ok_envelope(self.client.get('/gm/api/state/rooms'))['items']
        self.assertIn(str(room.pk),{row['id'] for row in rooms})
        spawned=self.result(self.post('/gm/api/console/spawn_monster',{'room':room_id,'species':'t_whisper_quail','variant':'t_whisper_quail_ordinary'}))['data']
        spawned_id=spawned['target'][1:]
        self.assertEqual(spawned['state']['monster'],self.assert_ok_envelope(self.client.get(f'/gm/api/state/monsters/{spawned_id}')))
        self.assertEqual(spawned['state']['room'],room_id)
        issued=self.result(self.post('/gm/api/console/issue_quest',{'target':self.target,'definition_key':'t_ember_cull','issuer_key':SYNTH_COMMISSIONER_KEY}))['data']
        self.assertEqual(issued['state'],self.assert_ok_envelope(self.client.get(f'/gm/api/state/quests?owner=%23{self.player.pk}')))
        repaired=self.result(self.post('/gm/api/console/set_quest_state',{'target':self.target,'quest_id':issued['quest_id'],'state':'failed'}))['data']
        self.assertEqual(repaired['state'],self.assert_ok_envelope(self.client.get(f'/gm/api/state/quests?owner=%23{self.player.pk}')))
        old=memory.record_memory(owner_id=str(self.npc.pk),content={'summary':'synthetic'},tick=0,category='observation',knowledge_scope='witnessed')[0]
        retracted=self.result(self.post('/gm/api/console/retract_memory',{'target':f'#{self.npc.pk}','memory_id':old.pk}))['data']
        self.assertEqual(retracted['state']['generation'],memory.get_owner_generation(str(self.npc.pk)))
        self.assertEqual(retracted['state']['memory'],self.assert_ok_envelope(self.client.get(f'/gm/api/state/memories/{old.pk}?owner=%23{self.npc.pk}')))

    @covers_requirement(
        'gm-developer-console::shared-console-transport-results-and-errors',
        'gm-runtime-state::runtime-api-routes-and-bounded-lists',
    )
    def test_seven_domain_codes_internal_failure_and_allow_contract(self):
        cases=[
            ('no_such_verb',{},'unknown_verb',404),
            ('set_wallet',{'target':self.target,'copper':-1},'invalid_argument',400),
            ('give_item',{'target':self.target,'key':'t_missing','quantity':1},'registry_key_not_found',404),
            ('set_wallet',{'target':'#99999999','copper':1},'target_not_found',404),
            ('set_wallet',{'target':f'#{self.npc.pk}','copper':1},'target_kind_mismatch',400),
        ]
        for verb,args,code,status in cases:
            body=self.result(self.post(f'/gm/api/console/{verb}',args),status)
            self.assertEqual(body['error']['code'],code)
            self.assertRegex(body['error']['message'],r'[一-鿿]')
            self.assertIn('snapshot',body)
        raw_path=f'/gm/api/state/object/{self.player.pk}/raw'
        raw=self.result(self.post(raw_path,{'operations':[{'op':'set_typeclass'}]}),400)
        self.assertEqual(raw['error']['code'],'raw_edit_invalid')
        before=self.player.db.wallet
        with mock.patch('world.rules.gm.set_wallet',side_effect=RuntimeError('unexpected')),mock.patch('server.console.snapshot_policy.log_error') as log:
            unexpected=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':2}),500)
        self.assertEqual(unexpected['error']['code'],'internal_error')
        self.assertEqual(self.player.db.wallet,before)
        self.assertEqual(log.call_args.args[0],'gm_action')
        for path,allow in [('/gm/api/console/status','GET'),('/gm/api/console/set_wallet','POST'),(raw_path,'GET, HEAD, POST')]:
            self.assertEqual(self.client.put(path)['Allow'],allow)
        self.assert_error_envelope(self.client.get('/gm/api/state/object/99999999/raw'),404,'object_not_found')

    @covers_requirement(
        'gm-developer-console::shared-console-transport-results-and-errors',
        'gm-developer-console::complete-validated-domain-verb-batch',
    )
    def test_invalid_payloads_have_no_write_and_failed_save_blocks_owner(self):
        for body in ([1],{}, {'target':self.target,'copper':True}, {'target':self.target,'copper':1,'code':'danger'}):
            response=self.post('/gm/api/console/set_wallet',body)
            self.assertEqual(response.status_code,400,response.content)
        before=self.player.db.wallet
        self.policy.baseline_tick=None
        self.policy.saver=mock.Mock(side_effect=RuntimeError('save failed'))
        with mock.patch('world.rules.gm.set_wallet') as writer:
            failure=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':1}),500)
        writer.assert_not_called()
        self.assertEqual(failure['error']['code'],'snapshot_failed')
        self.assertEqual(failure['snapshot'],{'taken':False,'save_id':None})
        self.assertEqual(self.player.db.wallet,before)
        self.assertIsNone(self.policy.baseline_tick)

    @covers_requirement(
        'gm-developer-console::shared-console-transport-results-and-errors',
        'gm-developer-console::tick-conditioned-recoverable-intervention',
    )
    def test_manual_and_console_busy_statuses_leave_state_and_baseline_unchanged(self):
        self.policy.baseline_tick=7
        self.policy._lock.acquire()
        try:
            self.assert_error_envelope(self.post('/gm/api/saves/',{'label':'busy'}),409,'save_in_progress')
            refusal=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':3}),500)
            self.assertEqual(refusal['error']['code'],'snapshot_failed')
            self.assertIn('正在進行',refusal['error']['message'])
            self.assertEqual(refusal['snapshot'],{'taken':False,'save_id':None})
            self.assertEqual(self.policy.baseline_tick,7)
            self.assertEqual(self.player.db.wallet,0)
            self.assertEqual(self.saves,[])
        finally:
            self.policy._lock.release()

    @covers_requirement('gm-developer-console::shared-console-transport-results-and-errors')
    def test_snapshot_retained_on_domain_failure_and_projection_failure_not_refusal(self):
        refused=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':-1}),400)
        self.assertTrue(refused['snapshot']['taken'])
        self.assertEqual(len(self.saves),1)
        with mock.patch('web.gm.console_api._project',side_effect=RuntimeError('projection')),mock.patch('web.gm.console_api.log_error') as log:
            committed=self.result(self.post('/gm/api/console/set_wallet',{'target':self.target,'copper':77}))
        self.assertTrue(committed['ok'])
        self.assertEqual(self.player.db.wallet,77)
        self.assertEqual(committed['data']['state']['error']['code'],'state_projection_failed')
        self.assertEqual(log.call_args.args[0],'gm_projection_failed')

    @covers_requirement('gm-developer-console::console-operational-evidence-and-operator-guidance')
    def test_success_and_refusal_logs_redact_argument_contents_and_keep_save_identity(self):
        secret='password secret session-token'
        with mock.patch('server.console.snapshot_policy.log_info') as log:
            self.result(self.post(f'/gm/api/state/object/{self.player.pk}/raw',{'operations':[{'op':'set_attr','key':'notes','value':secret}]}))
        event=log.call_args
        self.assertEqual(event.args[0],'gm_action')
        self.assertEqual(event.kwargs['context']['save'],'synthetic-save')
        self.assertNotIn(secret,str(event))
        self.assertLessEqual(len(event.kwargs['context']['arguments']),200)
