"""Slice of ``test_guild_economy_sync``: ServiceHostQuestIssuerSyncTests.
"""
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.components import QuestIssuer
from typeclasses.npcs import NPC
from world.rules.guild_config import ServiceHostRow
from world.rules.guild_config import get_catalog
from world.rules.profession_assembly import assemble_profession_components
from world.rules.profession_config import get_profession
from world.rules.quest_issuance import resolve_issuer_key
from world.rules.guild_economy import sync_service_content
import unittest
from ._support import (
    COMMISSIONER_NAME,
    COMMISSIONER_SERVICE_ID,
    GUILD_HALL_TAG,
    IMPORTED_COMMISSIONER_SERVICE_ID,
    ServiceContentIsolation,
)


class ServiceHostQuestIssuerSyncTests(ServiceContentIsolation, EvenniaTestCase):
    """quest-issuer-authorization: roster anchors reuse; imported carriers survive.

    The commissioner row used here is an internal robustness fixture: config
    validation rejects person-bound roster rows, so no shipped roster can
    carry one — the row exercises the sync interpreter's anchor-reuse path
    directly, exactly the path the row-anchor contract protects.
    """

    def _commissioner_row(self):
        return ServiceHostRow(
            name=COMMISSIONER_NAME,
            title="委託人灰婆婆",
            profession=get_profession("quest_issuer"),
            anchor_room=GUILD_HALL_TAG,
            service_id=COMMISSIONER_SERVICE_ID,
            authored_kwargs={},
        )

    def _sync_with_commissioner_row(self):
        catalog = get_catalog()
        self._patch_roster(tuple(catalog.service_hosts) + (self._commissioner_row(),))
        sync_service_content()

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-the-existing-service-host-component-shape",
    )
    def test_commissioner_blueprint_survives_repeated_roster_synchronization(self):
        self._sync_with_commissioner_row()
        host = NPC.objects.filter(db_key=COMMISSIONER_NAME).first()
        self.assertIsNotNone(host)
        component = host.components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, COMMISSIONER_SERVICE_ID)
        first_pk = host.pk

        # Second run: reuse through the service_id anchor, no duplicate host,
        # no duplicate component, no raise.
        self._sync_with_commissioner_row()
        hosts = NPC.objects.filter(db_key=COMMISSIONER_NAME)
        self.assertEqual(hosts.count(), 1)
        self.assertEqual(hosts.first().pk, first_pk)
        component = hosts.first().components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, COMMISSIONER_SERVICE_ID)

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_a_roster_created_commissioner_resolves_to_its_identity_form(self):
        # The roster projects only REQUIRED identity kwargs; issuer_key is
        # deliberately not one, so a roster-created commissioner is unauthored.
        self._sync_with_commissioner_row()
        host = NPC.objects.filter(db_key=COMMISSIONER_NAME).first()
        component = host.components.get(QuestIssuer.get_component_slot())
        self.assertIsNone(component.issuer_key)
        self.assertEqual(resolve_issuer_key(host), f"npc:#{host.pk}")

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_an_imported_person_bound_commissioner_survives_the_service_sync(self):
        # An imported commissioner carries a service_id the roster can never
        # claim (person-bound anchors are not roster-anchorable); convergence
        # must not treat it as shrunken-away residue and delete the host.
        sync_service_content()
        hall = search_object_by_tag(GUILD_HALL_TAG)[0]
        commissioner = create_object(NPC, key=COMMISSIONER_NAME, location=hall)
        assemble_profession_components(
            commissioner,
            get_profession("quest_issuer"),
            {
                "quest_issuer": {
                    "service_id": IMPORTED_COMMISSIONER_SERVICE_ID,
                    "issuer_key": "grey_granny",
                }
            },
            anchor_room=None,
        )

        sync_service_content()

        survivor = NPC.objects.filter(pk=commissioner.pk).first()
        self.assertIsNotNone(survivor)
        component = survivor.components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(resolve_issuer_key(survivor), "npc:grey_granny")

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_no_existing_npc_gains_issuing_authority_without_authored_content(self):
        sync_service_content()
        carriers = [
            host
            for host in NPC.objects.all_family()
            if host.components.has(QuestIssuer.name)
        ]
        self.assertEqual(carriers, [])


if __name__ == "__main__":
    unittest.main()
