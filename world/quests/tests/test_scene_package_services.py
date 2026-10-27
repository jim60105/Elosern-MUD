"""Generated service-bound dialogue: trusted plans, validation, and projection.

A generated phase may advertise the same explicit service associations as a
static source, but only for a topic it bound an ``offer_commission`` effect to.
The role then declares the person-bound ``scripted_dialogue`` capability whose
dialogue/service identity is the trusted scoped one. The validated plan travels
through activation into the shared assembler, and the derived projection exposes
the opening as navigation only: accepting the commission still needs the
player's separate explicit activation.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests.encounters import publish_scene_package
from world.quests.compile.compiler import compile_blueprint_core
from world.quests.scene_package import ScenePackageError, validate_scene_package
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.runtime import read_records
from world.quests.tests._fixtures import RegistryIsolationMixin, register_catalog_once
from world.quests.tests._scene_package_fixtures import (
    LONG_PROSE,
    dialogue as _dialogue,
    issuer_capabilities,
    package as _package,
    phase as _phase,
    topic as _topic,
    topic_scene as _topic_scene,
)
from world.quests.tests._scene_package_fixtures import _anchor_key
from world.rules.npc_services import project_npc_services

SERVICE_KEY = "commission_dialogue"
SERVICE_LABEL = "洽談委託"
OFFER_KEYWORD = "接受委託"


def _scripted_capability(**kwargs):
    return {
        "type": "scripted_dialogue",
        "kwargs": dict(kwargs),
        "binding": {"kind": "person"},
    }


def _service_payload(
    definition_key, *, service_topic="offer", services=True, roles=None
):
    """One complete package whose mother role may advertise a service."""
    payload = _package()
    mother = _dialogue("mother")
    offer = _topic(
        "offer",
        OFFER_KEYWORD,
        LONG_PROSE,
        requires={
            "kind": "quest_is",
            "definition_key": definition_key,
            "state": "not_accepted",
        },
        refusal=_topic_scene("offer_refusal", LONG_PROSE),
    )
    informational = _topic("information", "線索", LONG_PROSE)
    searching = mother["phases"][0]
    searching["topics"] = [informational, offer]
    searching["topic_effects"] = [
        {
            "topic_id": "offer",
            "verb": "offer_commission",
            "reference": definition_key,
        }
    ]
    if services:
        searching["services"] = [
            {"key": SERVICE_KEY, "topic_id": service_topic, "label": SERVICE_LABEL}
        ]
    payload["dialogue"] = [mother, _dialogue("daughter")]
    base_roles = _package()["roles"]
    payload["roles"] = list(roles) if roles is not None else [
        {
            **base_roles[0],
            "capabilities": issuer_capabilities("story_mother")
            + [_scripted_capability()],
        },
        base_roles[1],
    ]
    return payload


class GeneratedServicePackageTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog_once()
        base = _package()
        self.definition_key = compile_blueprint_core(base["quest"]).definition.key
        self.payload = _service_payload(self.definition_key)

    def _payload(self, **overrides):
        return _service_payload(self.definition_key, **overrides)

    def test_a_service_bound_generated_phase_compiles(self):
        definition = validate_scene_package(self.payload)
        phase = definition.role_dialogue("mother").phases[0]
        (service,) = phase.services
        self.assertEqual(service.key, SERVICE_KEY)
        self.assertEqual(service.label, SERVICE_LABEL)
        (topic,) = [item for item in phase.topics if item.keyword == OFFER_KEYWORD]
        self.assertEqual(service.topic_id, topic.topic_id)
        capability_types = {
            item.type for item in definition.role("mother").capabilities
        }
        self.assertEqual(capability_types, {"quest_issuer", "scripted_dialogue"})

    def test_an_informational_topic_is_never_a_service(self):
        payload = self._payload(service_topic="information")
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_dangling_and_cross_phase_topics_reject_before_publication(self):
        for topic_id in ("missing", "daughter_offer", "g:foreign-phase"):
            with self.subTest(topic_id=topic_id):
                with self.assertRaises(ScenePackageError):
                    validate_scene_package(self._payload(service_topic=topic_id))

    def test_every_phase_validates_its_own_service_effect(self):
        from copy import deepcopy

        payload = self._payload()
        later = deepcopy(payload["dialogue"][0]["phases"][0])
        later["phase_id"] = "later"
        later["topic_effects"] = []
        payload["dialogue"][0]["phases"].append(later)
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_services_without_the_dialogue_capability_reject(self):
        payload = self._payload()
        payload["roles"][0]["capabilities"] = issuer_capabilities("story_mother")
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_the_dialogue_capability_without_services_rejects(self):
        payload = self._payload(services=False)
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_a_non_trusted_dialogue_identity_rejects(self):
        payload = self._payload()
        payload["roles"][0]["capabilities"][1]["kwargs"]["dialogue_key"] = "t_other"
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_a_non_trusted_service_identity_rejects(self):
        payload = self._payload()
        payload["roles"][0]["capabilities"][1]["kwargs"]["service_id"] = "t_other"
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    def test_a_non_person_binding_rejects(self):
        payload = self._payload()
        payload["roles"][0]["capabilities"][1]["binding"] = {"kind": "place"}
        with self.assertRaises(ScenePackageError):
            validate_scene_package(payload)

    @covers_requirement(
        "npc-contextual-services::explicit-dialogue-services-retain-source-and-execution-authority"
    )
    def test_a_narrative_only_role_stays_unbound(self):
        definition = validate_scene_package(self.payload)
        self.assertEqual(definition.role("daughter").capabilities, ())
        self.assertFalse(
            any(
                phase.services
                for phase in definition.role_dialogue("daughter").phases
            )
        )


class GeneratedServiceActivationTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog_once()
        self.player = create_object(PlayerCharacter, key="訪客")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.player.move_to(self.room, quiet=True)
        definition_key = compile_blueprint_core(_package()["quest"]).definition.key
        payload = _service_payload(definition_key)
        payload["encounters"].append({
            **payload["encounters"][1], "scene_id": "return_market",
        })
        self.published = publish_scene_package(payload, owner="tester")
        activate_scene_encounter(
            self.player, self.published.package_id, "market", room=self.room, tick=5
        )

    def _mother(self):
        from world.quests import scene_store
        from evennia.objects.models import ObjectDB

        binding = scene_store.get_role_binding(self.published.package_id, "mother")
        return ObjectDB.objects.filter(id=binding.npc_id).first()

    def test_activation_projects_the_commission_service(self):
        from world.rules.dialogue_sources import dialogue_source_for_host

        mother = self._mother()
        services = project_npc_services(self.player, self.player, mother)
        entry = next(
            item for item in services.entries if item.key == f"dialogue.{SERVICE_KEY}"
        )
        self.assertTrue(entry.enabled)
        self.assertEqual(entry.label, SERVICE_LABEL)
        self.assertEqual(entry.route.kind, "dialogue")
        self.assertEqual(entry.route.npc_id, int(mother.pk))
        source = dialogue_source_for_host(mother)
        offer = next(
            topic for topic in source.dialogue.topics if topic.keyword == OFFER_KEYWORD
        )
        self.assertEqual(entry.route.topic_id, offer.topic_id)
        # Opening the route is navigation only: no quest record was created.
        self.assertEqual(read_records(self.player), [])

    def test_the_projected_topic_is_the_phases_bound_topic(self):
        from world.rules.dialogue_sources import dialogue_source_for_host

        mother = self._mother()
        source = dialogue_source_for_host(mother)
        offer = next(
            topic for topic in source.dialogue.topics if topic.keyword == OFFER_KEYWORD
        )
        (service,) = source.dialogue.services
        self.assertEqual(service.topic_id, offer.topic_id)

    @covers_requirement(
        "npc-contextual-services::explicit-dialogue-services-retain-source-and-execution-authority"
    )
    def test_opening_and_explicit_activation_have_separate_effect_authority(self):
        from web.webclient.actions.exploration_actions import _talk_open_adapter
        from world.rules.dialogue import live_dialogue_session, select_authored_topic

        mother = self._mother()
        entry = project_npc_services(self.player, self.player, mother).entries[0]
        result = _talk_open_adapter(self.player, {"npc_id": mother.pk})
        self.assertEqual(result["outcome"], "success")
        session = live_dialogue_session(self.player)
        self.assertEqual(session.completion_receipts, ())
        self.assertEqual(session.selection_receipts, ())
        self.assertEqual(read_records(self.player), [])
        select_authored_topic(
            self.player, mother, entry.route.topic_id,
            selection_id="explicit-offer", expected_context_id=session.context_id,
        )
        self.assertTrue(read_records(self.player))

    @covers_requirement(
        "npc-contextual-services::selections-always-revalidate-the-exact-provider"
    )
    def test_departed_service_host_is_never_replaced_by_a_bystander(self):
        from web.webclient.actions.exploration_actions import _talk_open_adapter
        from typeclasses.npcs import NPC

        mother = self._mother()
        create_object(NPC, key="bystander", location=self.room)
        mother.location = None
        result = _talk_open_adapter(self.player, {"npc_id": mother.pk})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(read_records(self.player), [])

    @covers_requirement(
        "npc-contextual-services::explicit-dialogue-services-retain-source-and-execution-authority"
    )
    def test_reactivation_rejects_conflicting_dialogue_binding_without_rewriting(self):
        from typeclasses.components import ScriptedDialogue

        mother = self._mother()
        component = mother.components.get(ScriptedDialogue.get_component_slot())
        for binding, anchor in (("place", self.room.pk), ("person", self.room.pk), (None, None)):
            with self.subTest(binding=binding, anchor=anchor):
                component.service_binding = binding
                component.anchor_room_id = anchor
                result = activate_scene_encounter(
                    self.player, self.published.package_id, "return_market",
                    room=self.room, tick=6,
                )
                self.assertFalse(result.activated)
                self.assertEqual(result.reason, "role_config_conflict")
                self.assertEqual(component.service_binding, binding)
                self.assertEqual(component.anchor_room_id, anchor)
                self.assertEqual(read_records(self.player), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
