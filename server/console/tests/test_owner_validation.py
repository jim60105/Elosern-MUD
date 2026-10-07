"""All object-bound verbs reject malformed, missing and incompatible identities."""
from server.console.tests._support import ConsoleOwnerTest
from server.console import registry
from tools.spec_traceability import covers_requirement


class OwnerIdentityTests(ConsoleOwnerTest):
    @covers_requirement('gm-developer-console::complete-validated-domain-verb-batch')
    def test_every_object_bound_verb_has_existence_kind_and_shape_validation(self):
        npc=f'#{self.npc.pk}'
        room=f'#{self.room1.pk}'
        cases={
            'give_item':({'key':'t_huskapple','quantity':1},npc),
            'take_item':({'key':'t_huskapple','quantity':1},npc),
            'set_wallet':({'copper':1},npc),
            'set_trait_base':({'trait':'hp','value':1},npc),
            'set_gauge':({'gauge':'hp','value':1},npc),
            'teleport':({'room':room},npc),
            'delete_entity':({},self.target),
            'set_quest_state':({'quest_id':'t_identity','state':'failed'},npc),
            'set_quest_stage':({'quest_id':'t_identity','stage':0},npc),
            'issue_quest':({'definition_key':'t_ember_cull','issuer_key':'npc:t_grey_lantern'},npc),
            'retract_memory':({'memory_id':1},self.target),
            'supersede_memory':({'memory_id':1,'replacement_id':2},self.target),
        }
        for name,(arguments,wrong_kind) in cases.items():
            with self.subTest(verb=name,case='absent'):
                self.assert_refusal('target_not_found',lambda:registry.dispatch(name,{**arguments,'target':'#99999999'}))
            with self.subTest(verb=name,case='kind'):
                self.assert_refusal('target_kind_mismatch',lambda:registry.dispatch(name,{**arguments,'target':wrong_kind}))
            for target in (None,True,1,'1','#0','#-1','#1.5',{},[]):
                with self.subTest(verb=name,target=target):
                    self.assert_refusal('invalid_argument',lambda:registry.dispatch(name,{**arguments,'target':target}))
        for target,code in [(self.target,'target_kind_mismatch'),('#99999999','target_not_found'),(True,'invalid_argument')]:
            self.assert_refusal(code,lambda:registry.dispatch('spawn_monster',{'species':'t_whisper_quail','variant':'t_whisper_quail_ordinary','room':target}))
