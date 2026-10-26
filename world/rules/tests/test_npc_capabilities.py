"""The direct NPC capability core: schema, validation, room resolution, assembly.

Pure boundary tests for ``world/rules/npc_capabilities.py`` — the single owner
every producer shares. Component vocabulary symmetry is checked against the
real classes; room resolution and assembly use real Evennia objects because the
anchor is a persisted dbref and the component holder is the typeclass one.
"""

import unittest
from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses import components as component_classes
from typeclasses.components import Merchant, QuestIssuer, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.npc_capabilities import (
    BINDING_KINDS,
    COMPONENT_TYPES,
    OPTIONAL_KWARGS,
    REQUIRED_BINDING,
    REQUIRED_KWARGS,
    RUNTIME_FIELDS,
    Binding,
    CapabilityDeclaration,
    CapabilityPlan,
    CapabilityValidationError,
    PlannedCapability,
    assemble_capabilities,
    capability,
    component_attribute_keys,
    component_field_names,
    managed_type_keys,
    person_bound,
    place_bound,
    validate_capabilities,
)

_DECLARATIONS_REQUIREMENT = (
    "npc-capability-declarations::npc-capabilities-are-direct-unique-declarations"
)
_BINDING_REQUIREMENT = (
    "npc-capability-declarations::each-bound-capability-authors-its-own-binding-and-unique-room"
)

_DIALOGUE_KEY = "assembly_probe_dialogue"


def _patch_dialogue_table():
    """Register one probe dialogue key without touching shipped content."""
    from world.rules import dialogue

    table = dict(dialogue.DIALOGUE_TABLE)
    table[_DIALOGUE_KEY] = next(iter(dialogue.DIALOGUE_TABLE.values()))
    return patch.object(dialogue, "DIALOGUE_TABLE", MappingProxyType(table))


def _merchant(**overrides):
    kwargs = {"service_id": "probe_service", "shop_key": "probe_shop"}
    kwargs.update(overrides)
    return capability("merchant", binding=place_bound("probe_anchor"), **kwargs)


def _issuer(**overrides):
    kwargs = {"service_id": "probe_service"}
    kwargs.update(overrides)
    return capability("quest_issuer", binding=person_bound(), **kwargs)


class VocabularyContractTests(unittest.TestCase):
    def test_vocabulary_keys_are_the_class_declared_names(self):
        from evennia.contrib.base_systems.components import Component

        declared = {
            value.name: value
            for value in vars(component_classes).values()
            if isinstance(value, type)
            and issubclass(value, Component)
            and value is not Component
        }
        self.assertEqual(COMPONENT_TYPES, declared)

    def test_every_required_and_optional_kwarg_is_an_authored_class_field(self):
        for type_key in COMPONENT_TYPES:
            allowed = component_field_names(type_key)
            self.assertLessEqual(REQUIRED_KWARGS[type_key], allowed)
            self.assertLessEqual(OPTIONAL_KWARGS.get(type_key, frozenset()), allowed)
            self.assertFalse(REQUIRED_KWARGS[type_key] & RUNTIME_FIELDS)
            self.assertFalse(
                OPTIONAL_KWARGS.get(type_key, frozenset()) & RUNTIME_FIELDS
            )

    def test_runtime_owned_fields_are_never_accepted_as_authored_kwargs(self):
        for type_key in COMPONENT_TYPES:
            allowed = component_field_names(type_key)
            self.assertFalse(allowed & RUNTIME_FIELDS, type_key)
            for field in allowed:
                self.assertIn(field, COMPONENT_TYPES[type_key]._fields)

    def test_managed_slots_are_the_vocabulary_and_attributes_are_class_backed(self):
        self.assertEqual(managed_type_keys(), frozenset(COMPONENT_TYPES))
        for type_key, component_class in COMPONENT_TYPES.items():
            slot = component_class.get_component_slot()
            self.assertEqual(
                component_attribute_keys(type_key),
                tuple(f"{slot}::{name}" for name in component_class._fields),
            )

    def test_service_types_are_exactly_the_binding_required_ones(self):
        self.assertEqual(
            REQUIRED_BINDING,
            frozenset(
                {
                    "merchant",
                    "guild_staff",
                    "guild_exam_reception",
                    "quest_issuer",
                    "church_host",
                }
            ),
        )

    def test_binding_kinds_are_the_closed_pair(self):
        self.assertEqual(BINDING_KINDS, frozenset({"person", "place"}))


class DeclarationTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        patcher = _patch_dialogue_table()
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_authored_kwargs_are_read_only(self):
        declaration = _merchant()
        with self.assertRaises(TypeError):
            declaration.kwargs["shop_key"] = "other"  # type: ignore[index]

    def test_an_empty_declaration_set_is_a_valid_empty_plan(self):
        self.assertEqual(validate_capabilities(None).components, ())
        self.assertEqual(validate_capabilities([]).type_keys(), frozenset())

    @covers_requirement(_DECLARATIONS_REQUIREMENT)
    def test_unknown_type_is_rejected_by_name(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities([{"type": "blacksmith", "kwargs": {}}])
        self.assertIn("blacksmith", caught.exception.issues[0])
        self.assertIn("vocabulary", caught.exception.issues[0])

    @covers_requirement(_DECLARATIONS_REQUIREMENT)
    def test_duplicate_type_is_rejected(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities([_merchant(), _merchant(service_id="second")])
        self.assertTrue(
            any("more than once" in issue for issue in caught.exception.issues)
        )

    @covers_requirement(_DECLARATIONS_REQUIREMENT)
    def test_unknown_kwarg_and_runtime_field_are_rejected_separately(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities(
                [
                    capability(
                        "merchant",
                        binding=person_bound(),
                        service_id="probe_service",
                        shop_key="probe_shop",
                        branch_key="not_a_merchant_field",
                    )
                ]
            )
        self.assertTrue(
            any("branch_key" in issue for issue in caught.exception.issues)
        )

        with self.assertRaises(CapabilityValidationError) as runtime:
            validate_capabilities(
                [
                    capability(
                        "merchant",
                        binding=person_bound(),
                        service_id="probe_service",
                        shop_key="probe_shop",
                        merchant_stock={"probe_item": 1},
                    )
                ]
            )
        self.assertTrue(
            any("runtime-owned field" in issue for issue in runtime.exception.issues)
        )

    def test_required_kwargs_are_named_when_absent_or_blank(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities(
                [capability("merchant", binding=person_bound(), service_id="probe")]
            )
        self.assertTrue(
            any("shop_key" in issue for issue in caught.exception.issues)
        )
        with self.assertRaises(CapabilityValidationError) as blank:
            validate_capabilities(
                [
                    capability(
                        "merchant",
                        binding=person_bound(),
                        service_id="",
                        shop_key="probe_shop",
                    )
                ]
            )
        self.assertTrue(
            any("service_id" in issue for issue in blank.exception.issues)
        )

    def test_issuer_key_stays_optional_and_the_plan_keeps_its_absence(self):
        plan = validate_capabilities([_issuer()])
        self.assertNotIn("issuer_key", plan.kwargs_for("quest_issuer"))
        with_key = validate_capabilities([_issuer(issuer_key="probe_key")])
        self.assertEqual(with_key.kwargs_for("quest_issuer")["issuer_key"], "probe_key")

    def test_a_dialogue_service_id_is_ordinary_optional_config(self):
        plan = validate_capabilities(
            [
                capability(
                    "scripted_dialogue",
                    binding=person_bound(),
                    dialogue_key=_DIALOGUE_KEY,
                    service_id="probe_service",
                )
            ]
        )
        self.assertEqual(
            plan.kwargs_for("scripted_dialogue")["service_id"], "probe_service"
        )

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_narrative_dialogue_needs_no_binding(self):
        plan = validate_capabilities(
            [capability("scripted_dialogue", dialogue_key=_DIALOGUE_KEY)]
        )
        planned = plan.component("scripted_dialogue")
        self.assertIsNotNone(planned)
        self.assertIsNone(planned.binding)
        self.assertIsNone(planned.anchor_room)

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_a_service_without_binding_is_rejected(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities(
                [
                    capability(
                        "merchant",
                        service_id="probe_service",
                        shop_key="probe_shop",
                    )
                ]
            )
        self.assertTrue(
            any("must declare its" in issue for issue in caught.exception.issues)
        )

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_person_with_an_anchor_and_place_without_one_are_rejected(self):
        with self.assertRaises(CapabilityValidationError) as anchored:
            validate_capabilities(
                [
                    capability(
                        "quest_issuer",
                        binding=Binding("person", "probe_anchor"),
                        service_id="probe_service",
                    )
                ]
            )
        self.assertTrue(
            any("invalid combination" in issue for issue in anchored.exception.issues)
        )
        with self.assertRaises(CapabilityValidationError) as unanchored:
            validate_capabilities(
                [
                    capability(
                        "merchant",
                        binding=Binding("place"),
                        service_id="probe_service",
                        shop_key="probe_shop",
                    )
                ]
            )
        self.assertTrue(
            any("anchor_room tag is required" in issue for issue in unanchored.exception.issues)
        )

    def test_unknown_binding_kind_and_field_are_rejected(self):
        with self.assertRaises(CapabilityValidationError) as caught:
            validate_capabilities(
                [
                    {
                        "type": "quest_issuer",
                        "kwargs": {"service_id": "probe_service"},
                        "binding": {"kind": "portable"},
                    }
                ]
            )
        self.assertTrue(any("portable" in issue for issue in caught.exception.issues))

        with self.assertRaises(CapabilityValidationError) as extra:
            validate_capabilities(
                [
                    {
                        "type": "quest_issuer",
                        "kwargs": {"service_id": "probe_service"},
                        "binding": {"kind": "person", "anchor_room": "probe_anchor"},
                    }
                ]
            )
        self.assertTrue(
            any("invalid combination" in issue for issue in extra.exception.issues)
        )


class RoomResolutionTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        patcher = _patch_dialogue_table()
        patcher.start()
        self.addCleanup(patcher.stop)
        self.anchor = create_object(Room, key="probe anchor room")
        self.other = create_object(Room, key="probe other room")

    def _resolver(self, tag):
        if tag == "probe_anchor":
            return [self.anchor]
        if tag == "ambiguous":
            return [self.anchor, self.other]
        if tag == "squatter":
            return [create_object(NPC, key="probe squatter")]
        return []

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_a_place_binding_resolves_exactly_one_room(self):
        plan = validate_capabilities([_merchant()], room_resolver=self._resolver)
        planned = plan.component("merchant")
        self.assertIs(planned.anchor_room, self.anchor)

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_missing_ambiguous_and_non_room_anchors_are_rejected(self):
        for tag, fragment in (
            ("absent", "resolves to no room"),
            ("ambiguous", "the anchor must be unique"),
            ("squatter", "non-Room object"),
        ):
            with self.subTest(tag=tag):
                with self.assertRaises(CapabilityValidationError) as caught:
                    validate_capabilities(
                        [capability(
                            "merchant",
                            binding=place_bound(tag),
                            service_id="probe_service",
                            shop_key="probe_shop",
                        )],
                        room_resolver=self._resolver,
                    )
                self.assertTrue(
                    any(fragment in issue for issue in caught.exception.issues),
                    caught.exception.issues,
                )

    def test_without_a_resolver_the_anchor_stays_unresolved(self):
        plan = validate_capabilities([_merchant()])
        self.assertIsNone(plan.component("merchant").anchor_room)


class AssemblyTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        patcher = _patch_dialogue_table()
        patcher.start()
        self.addCleanup(patcher.stop)
        self.anchor = create_object(Room, key="assembly anchor room", tags=["asm"])
        self.npc = create_object(NPC, key="assembly probe npc", location=self.anchor)

    def _resolver(self, tag):
        return [self.anchor] if tag == "asm" else []

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_place_and_person_capabilities_assemble_on_one_host(self):
        plan = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound("asm"),
                    service_id="probe_service",
                    shop_key="probe_shop",
                ),
                capability(
                    "quest_issuer",
                    binding=person_bound(),
                    service_id="probe_service",
                    issuer_key="probe_commission",
                ),
            ],
            room_resolver=self._resolver,
        )
        attached = assemble_capabilities(self.npc, plan)
        self.assertEqual(sorted(attached), ["merchant", "quest_issuer"])
        merchant = self.npc.components.get(Merchant.get_component_slot())
        issuer = self.npc.components.get(QuestIssuer.get_component_slot())
        self.assertEqual(merchant.service_binding, "place")
        self.assertEqual(merchant.anchor_room_id, self.anchor.pk)
        self.assertEqual(issuer.service_binding, "person")
        self.assertIsNone(issuer.anchor_room_id)

    def test_reassembly_converges_configuration_and_keeps_the_slot(self):
        plan = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound("asm"),
                    service_id="probe_service",
                    shop_key="probe_shop",
                )
            ],
            room_resolver=self._resolver,
        )
        assemble_capabilities(self.npc, plan)
        merchant = self.npc.components.get(Merchant.get_component_slot())
        merchant.merchant_stock = {"probe_item": 3}
        changed = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound("asm"),
                    service_id="probe_service_2",
                    shop_key="probe_shop_2",
                )
            ],
            room_resolver=self._resolver,
        )
        self.assertEqual(assemble_capabilities(self.npc, changed), [])
        converged = self.npc.components.get(Merchant.get_component_slot())
        self.assertEqual(converged.shop_key, "probe_shop_2")
        self.assertEqual(converged.service_id, "probe_service_2")
        # Subsystem-owned runtime state is never the assembly's to rewrite.
        self.assertEqual(converged.merchant_stock, {"probe_item": 3})

    @covers_requirement(_BINDING_REQUIREMENT)
    def test_assembly_refuses_an_unresolved_place_anchor(self):
        plan = validate_capabilities([_merchant()])
        with self.assertRaises(CapabilityValidationError) as caught:
            assemble_capabilities(self.npc, plan)
        self.assertTrue(
            any("never resolved" in issue for issue in caught.exception.issues)
        )
        self.assertFalse(self.npc.components.has(Merchant.name))

    def test_assembly_refuses_an_incomplete_plan(self):
        plan = CapabilityPlan(
            (
                PlannedCapability(
                    type="merchant",
                    kwargs={"service_id": "probe_service"},
                    binding=person_bound(),
                ),
            )
        )
        with self.assertRaises(CapabilityValidationError) as caught:
            assemble_capabilities(self.npc, plan)
        self.assertTrue(
            any("missing authored kwargs" in issue for issue in caught.exception.issues)
        )

    def test_assembly_requires_a_validated_plan(self):
        with self.assertRaises(TypeError):
            assemble_capabilities(self.npc, ())

    def test_reconcile_removes_undeclared_managed_slots_only(self):
        plan = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound("asm"),
                    service_id="probe_service",
                    shop_key="probe_shop",
                ),
                capability("scripted_dialogue", dialogue_key=_DIALOGUE_KEY),
            ],
            room_resolver=self._resolver,
        )
        assemble_capabilities(self.npc, plan)
        self.assertTrue(self.npc.components.has(ScriptedDialogue.name))
        narrowed = validate_capabilities(
            [
                capability(
                    "merchant",
                    binding=place_bound("asm"),
                    service_id="probe_service",
                    shop_key="probe_shop",
                )
            ],
            room_resolver=self._resolver,
        )
        assemble_capabilities(self.npc, narrowed, reconcile=True)
        self.assertFalse(self.npc.components.has(ScriptedDialogue.name))
        self.assertTrue(self.npc.components.has(Merchant.name))
        # The person is never a capability: reconcile leaves the entity alone.
        self.assertEqual(self.npc.key, "assembly probe npc")


if __name__ == "__main__":
    unittest.main()
