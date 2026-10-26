"""Persistence proof for assembly-written binding fields (tasks 4.1/4.2).

The binding fields are ordinary ``DBField``s (AttributeProperty-backed), so the
proof is: write them through the shared capability assembly, flush the idmapper
cache exactly like a process reload, and re-read the SAME object row from the
database to confirm the values come back and the resolver agrees with them.
"""

from tools.spec_traceability import covers_requirement

from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import Merchant, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.npc_capabilities import (
    CapabilityValidationError,
    assemble_capabilities,
    capability,
    person_bound,
    place_bound,
    validate_capabilities,
)
from world.rules.service_gate import (
    REASON_OFF_ANCHOR,
    REASON_REMOTE,
    service_available,
)

#: The kit's synthetic shop identity (never a shipped catalog token).
_PROBE_SHOP_KEY = "t_mossgate_stall"
#: One probe dialogue table, registered in the live table for this module only.
_PROBE_DIALOGUE_KEY = "binding_probe_dialogue"
_ANCHOR_TAG = "binding_probe_anchor"
_SQUARE_TAG = "binding_probe_square"


def _patch_dialogue_table():
    from world.rules import dialogue

    table = dict(dialogue.DIALOGUE_TABLE)
    table[_PROBE_DIALOGUE_KEY] = next(iter(dialogue.DIALOGUE_TABLE.values()))
    return patch.object(dialogue, "DIALOGUE_TABLE", MappingProxyType(table))


class ServiceBindingPersistenceTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        dialogue_patcher = _patch_dialogue_table()
        dialogue_patcher.start()
        self.addCleanup(dialogue_patcher.stop)
        self.anchor = create_object(Room, key="binding anchor", tags=[_ANCHOR_TAG])
        self.square = create_object(Room, key="binding square", tags=[_SQUARE_TAG])

    def _resolver(self, tag):
        return {
            _ANCHOR_TAG: [self.anchor],
            _SQUARE_TAG: [self.square],
        }.get(tag, [])

    def _plan(self, tag=_ANCHOR_TAG, **kwargs):
        return validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound(tag),
                    service_id="s",
                    shop_key=kwargs.get("shop_key", _PROBE_SHOP_KEY),
                )
            ],
            room_resolver=self._resolver,
        )

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_binding_and_anchor_survive_a_save_reload_round_trip(self):
        npc = create_object(NPC, key="binding merchant", location=self.anchor)
        assemble_capabilities(npc, self._plan())
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
        npc = create_object(NPC, key="binding courier", location=self.square)
        plan = validate_capabilities(
            [
                capability(
                    "scripted_dialogue",
                    binding=person_bound(),
                    dialogue_key=_PROBE_DIALOGUE_KEY,
                )
            ]
        )
        assemble_capabilities(npc, plan)
        component = npc.components.get(ScriptedDialogue.get_component_slot())
        self.assertEqual(component.service_binding, "person")
        self.assertIsNone(component.anchor_room_id)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_place_plan_without_a_resolved_anchor_never_creates_components(self):
        npc = create_object(NPC, key="unanchored merchant", location=self.square)
        unresolved = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound(_ANCHOR_TAG),
                    service_id="s",
                    shop_key=_PROBE_SHOP_KEY,
                )
            ]
        )
        with self.assertRaises(CapabilityValidationError):
            assemble_capabilities(npc, unresolved)
        self.assertFalse(npc.components.has(Merchant.name))

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_reassembly_converges_bindings_without_touching_identity(self):
        npc = create_object(NPC, key="converged merchant", location=self.anchor)
        assemble_capabilities(npc, self._plan())
        before = npc.components.get(Merchant.get_component_slot())
        before_id = (before.service_id, before.shop_key)
        # Re-running assembly (the sync's per-sync convergence) keeps the slot
        # and identity intact while re-writing the authored binding fields.
        assemble_capabilities(npc, self._plan(_SQUARE_TAG))
        after = npc.components.get(Merchant.get_component_slot())
        self.assertEqual((after.service_id, after.shop_key), before_id)
        self.assertEqual(after.anchor_room_id, self.square.pk)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_reassembly_converges_only_the_authored_configuration_allowlist(self):
        # Authored configuration converges on a live component; the commerce
        # lifecycle's own state (stock, restock day) is never written by
        # assembly, so a shop edit cannot reset progress.
        npc = create_object(NPC, key="configured merchant", location=self.anchor)
        assemble_capabilities(npc, self._plan())
        component = npc.components.get(Merchant.get_component_slot())
        component.merchant_stock = {"t_probe_goods": 2}
        component.last_restock_day = 9
        assemble_capabilities(npc, self._plan(shop_key="t_other_stall"))
        after = npc.components.get(Merchant.get_component_slot())
        self.assertEqual(after.shop_key, "t_other_stall")
        self.assertEqual(dict(after.merchant_stock), {"t_probe_goods": 2})
        self.assertEqual(after.last_restock_day, 9)
