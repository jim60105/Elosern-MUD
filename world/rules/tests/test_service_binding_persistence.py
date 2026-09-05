"""Persistence proof for assembly-written binding fields (tasks 4.1/4.2).

The binding fields are ordinary ``DBField``s (AttributeProperty-backed), so the
proof is: write them through the shared assembly, flush the idmapper cache
exactly like a process reload, and re-read the SAME object row from the
database to confirm the values come back and the resolver agrees with them.
"""

from tools.spec_traceability import covers_requirement

from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import profession_config
from world.rules.profession_config import Profession, ProfessionComponent
from world.rules.profession_assembly import (
    ProfessionAssemblyError,
    assemble_profession_components,
)
from world.rules.service_gate import (
    REASON_OFF_ANCHOR,
    REASON_REMOTE,
    service_available,
)


MERCHANT_PROBE = Profession(
    key="merchant",
    components=(ProfessionComponent("merchant", "place"),),
    schedule_template=None,
    default_tier=None,
)
PROBE_TABLE = MappingProxyType({"merchant": MERCHANT_PROBE})


class ServiceBindingPersistenceTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch.object(profession_config, "TABLE", PROBE_TABLE)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.anchor = create_object(Room, key="binding anchor")
        self.square = create_object(Room, key="binding square")

    def _assemble(self, npc, room):
        assemble_profession_components(
            npc,
            MERCHANT_PROBE,
            {"merchant": {"service_id": "s", "shop_key": "altoria_general_store"}},
            anchor_room=room,
        )

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_binding_and_anchor_survive_a_save_reload_round_trip(self):
        npc = create_object(NPC, key="binding merchant", location=self.anchor)
        self._assemble(npc, self.anchor)
        component = npc.components.get(Merchant.get_component_slot())
        self.assertEqual(component.service_binding, "place")
        self.assertEqual(component.anchor_room_id, self.anchor.pk)

        # Simulated reload: drop every cached instance, then re-read the row.
        flush_cache()
        reloaded = NPC.objects.get(id=npc.id)
        reread = reloaded.components.get(Merchant.get_component_slot())
        self.assertEqual(reread.service_binding, "place")
        self.assertEqual(reread.anchor_room_id, self.anchor.pk)

        # The resolver reaches its verdicts from the reloaded data alone.
        actor = create_object(NPC, key="binding actor", location=self.anchor)
        self.assertTrue(service_available(actor, reloaded, reread).allowed)
        actor.location = self.square
        reloaded.location = self.square
        self.assertEqual(
            service_available(actor, reloaded, reread).reason, REASON_OFF_ANCHOR
        )
        actor.location = self.anchor
        self.assertEqual(
            service_available(actor, reloaded, reread).reason, REASON_REMOTE
        )

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_person_bound_components_persist_no_anchor(self):
        person_probe = Profession(
            key="courier",
            components=(ProfessionComponent("scripted_dialogue", "person"),),
            schedule_template=None,
            default_tier=None,
        )
        npc = create_object(NPC, key="binding courier", location=self.square)
        assemble_profession_components(
            npc,
            person_probe,
            {"scripted_dialogue": {"dialogue_key": "d"}},
            # No anchor_room: person-bound plans never need one.
        )
        component = npc.components.get("scripted_dialogue")
        self.assertEqual(component.service_binding, "person")
        self.assertIsNone(component.anchor_room_id)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_place_plan_without_an_anchor_room_never_creates_components(self):
        npc = create_object(NPC, key="unanchored merchant", location=self.square)
        with self.assertRaises(ProfessionAssemblyError):
            assemble_profession_components(
                npc,
                MERCHANT_PROBE,
                {"merchant": {"service_id": "s", "shop_key": "altoria_general_store"}},
            )
        self.assertFalse(npc.components.has(Merchant.name))

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_reassembly_converges_bindings_without_touching_identity(self):
        npc = create_object(NPC, key="converged merchant", location=self.anchor)
        self._assemble(npc, self.anchor)
        before = npc.components.get(Merchant.get_component_slot())
        before_id = (before.service_id, before.shop_key)
        # Re-running assembly (the sync's per-sync convergence) keeps the slot
        # and identity intact while re-writing the authored binding fields.
        self._assemble(npc, self.square)
        after = npc.components.get(Merchant.get_component_slot())
        self.assertEqual((after.service_id, after.shop_key), before_id)
        self.assertEqual(after.anchor_room_id, self.square.pk)
