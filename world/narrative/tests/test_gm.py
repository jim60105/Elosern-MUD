"""S6 append-only memory revisions, ownership and atomic generation acceptance."""
from unittest import mock
from server.console.tests._support import ConsoleOwnerTest
from world.narrative import gm, memory
from world.narrative.models import MemoryRecord, MemoryRevision
from tools.spec_traceability import covers_requirement


class MemoryConsoleTests(ConsoleOwnerTest):
    def record(self,owner=None):
        return memory.record_memory(owner_id=str((owner or self.npc).pk),content={'summary':'synthetic memory'},tick=0,category='observation',knowledge_scope='witnessed')[0]

    @covers_requirement('gm-developer-console::append-only-memory-interventions')
    def test_retraction_supersession_preserve_original_and_update_generation(self):
        old,new=self.record(),self.record()
        owner=str(self.npc.pk)
        generation=memory.get_owner_generation(owner)
        target=f'#{self.npc.pk}'
        gm.retract_memory(target,old.pk)
        old.refresh_from_db()
        self.assertEqual(old.effective_availability,'inactive')
        self.assertEqual(memory.get_owner_generation(owner),generation+1)
        gm.supersede_memory(target,old.pk,new.pk)
        old.refresh_from_db(); new.refresh_from_db()
        self.assertEqual(old.effective_availability,'superseded')
        self.assertEqual(old.revisions.order_by('-revision_number').first().supersedes_record_id,str(new.pk))
        self.assertEqual(old.content,{'summary':'synthetic memory'})
        self.assertEqual(old.tick,0)
        self.assertEqual(old.knowledge_scope,'witnessed')
        self.assertEqual(memory.get_owner_generation(owner),generation+3)

    @covers_requirement('gm-developer-console::append-only-memory-interventions')
    def test_rejected_owner_self_missing_and_malformed_ids(self):
        old,new=self.record(),self.record(self.player)
        target=f'#{self.npc.pk}'
        self.assert_refusal('invalid_argument',lambda:gm.supersede_memory(target,old.pk,old.pk))
        self.assert_refusal('target_kind_mismatch',lambda:gm.supersede_memory(target,old.pk,new.pk))
        self.assert_refusal('target_kind_mismatch',lambda:gm.retract_memory(self.target,old.pk))
        self.assert_refusal('target_not_found',lambda:gm.retract_memory(target,99999999))
        for value in (True,-1,'1',1.5):
            self.assert_refusal('invalid_argument',lambda:gm.retract_memory(target,value))
            self.assert_refusal('invalid_argument',lambda:gm.supersede_memory(target,old.pk,value))
        self.assert_refusal('target_not_found',lambda:gm.supersede_memory(target,old.pk,99999999))
        old.refresh_from_db()
        self.assertEqual(old.effective_availability,'active')

    @covers_requirement('gm-developer-console::append-only-memory-interventions')
    def test_second_revision_failure_and_late_retract_roll_back_all_rows(self):
        old,new=self.record(),self.record()
        target=f'#{self.npc.pk}'
        count=MemoryRevision.objects.count()
        generation=memory.get_owner_generation(str(self.npc.pk))
        original=memory.revise_memory
        def late(**kwargs):
            result=original(**kwargs)
            if kwargs['record'].pk==new.pk:
                raise RuntimeError('second revision')
            return result
        with mock.patch.object(memory,'revise_memory',side_effect=late):
            with self.assertRaises(RuntimeError):
                gm.supersede_memory(target,old.pk,new.pk)
        self.assertEqual(MemoryRevision.objects.count(),count)
        self.assertEqual(memory.get_owner_generation(str(self.npc.pk)),generation)
        self.assertEqual(MemoryRecord.objects.get(pk=old.pk).effective_availability,'active')
        def fail(**kwargs):
            original(**kwargs)
            raise RuntimeError('after retract')
        with mock.patch.object(memory,'revise_memory',side_effect=fail):
            with self.assertRaises(RuntimeError):
                gm.retract_memory(target,old.pk)
        self.assertEqual(MemoryRevision.objects.count(),count)
        self.assertEqual(memory.get_owner_generation(str(self.npc.pk)),generation)
