"""Tests for the QuestIssuer component, its authorization, and key resolution."""

import unittest
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.components import Merchant, QuestIssuer, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.guild import GuildServiceError, resolve_local_service_host
from world.rules.profession_config import PROFESSION_COMPONENT_TYPES
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    IssuerKeyError,
    resolve_issuer_key,
)

class _NoLookupRegistry(dict):
    """A registry stub that fails the test the moment it is consulted."""

    def get(self, *args, **kwargs):
        raise AssertionError("registry consulted")


class QuestIssuerComponentShapeTests(unittest.TestCase):
    """The component is a capability marker and identity holder only (R2)."""

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-"
        "the-existing-service-host-component-shape"
    )
    def test_component_declares_exactly_the_four_identity_fields(self):
        self.assertEqual(
            set(QuestIssuer._fields),
            {"service_id", "issuer_key", "service_binding", "anchor_room_id"},
        )

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-"
        "the-existing-service-host-component-shape"
    )
    def test_component_is_a_marker_and_identity_holder_only(self):
        # No own methods: no quest, reward, or record mutation lives on the
        # component; every such mutation delegates to the deterministic core.
        own = {
            name: value
            for name, value in vars(QuestIssuer).items()
            if not name.startswith("__")
        }
        self.assertEqual([name for name, value in own.items() if callable(value)], [])

    @covers_requirement(
        "quest-issuer-authorization::authority-to-issue-a-private-commission-is-authored-never-inferred"
    )
    def test_component_is_registered_under_its_declared_name(self):
        self.assertIs(PROFESSION_COMPONENT_TYPES["quest_issuer"], QuestIssuer)
        self.assertEqual(QuestIssuer.name, "quest_issuer")


class IssuerHostHarness(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="issuer room")
        self.actor = create_object(NPC, key="wandering hero", location=self.room)

    def _carrier(self, key="grey granny", **kwargs):
        npc = create_object(NPC, key=key, location=self.room)
        npc.components.add(QuestIssuer.create(npc, **kwargs))
        return npc

    def _attach_other_service_components(self, npc):
        npc.components.add(Merchant.create(npc, service_id="s", shop_key="k"))
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key="d"))


class AuthorizationTests(IssuerHostHarness):
    """Authority to issue is authored by the component, never inferred (R1)."""

    @covers_requirement(
        "quest-issuer-authorization::authority-to-issue-a-private-"
        "commission-is-authored-never-inferred",
    )
    def test_an_ordinary_npc_cannot_issue_a_commission(self):
        self.assertIsNone(resolve_issuer_key(self.actor))

    @covers_requirement(
        "quest-issuer-authorization::authority-to-issue-a-private-"
        "commission-is-authored-never-inferred",
    )
    def test_a_merchant_without_the_component_is_still_not_a_commissioner(self):
        self._attach_other_service_components(self.actor)
        self.assertIsNone(resolve_issuer_key(self.actor))


class ResolveIssuerKeyTests(IssuerHostHarness):
    """Exactly two authored forms; no registry lookup (R4)."""

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_authored_key_resolves_to_the_content_form(self):
        carrier = self._carrier(issuer_key="grey_granny")
        self.assertEqual(resolve_issuer_key(carrier), "npc:grey_granny")

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_resolution_succeeds_with_no_registered_issuance_and_no_lookup(self):
        carrier = self._carrier(issuer_key="grey_granny")
        with mock.patch(
            "world.rules.quest_issuance.QUEST_ISSUANCE_REGISTRY", _NoLookupRegistry()
        ):
            self.assertEqual(resolve_issuer_key(carrier), "npc:grey_granny")
        self.assertEqual(len(QUEST_ISSUANCE_REGISTRY), 0)

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_unauthored_key_resolves_to_the_identity_form(self):
        for authored in (None, ""):
            with self.subTest(authored=authored):
                carrier = self._carrier(key=f"unauthored {authored}", issuer_key=authored)
                self.assertEqual(resolve_issuer_key(carrier), f"npc:#{carrier.pk}")

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_a_malformed_authored_key_rejects(self):
        # "#5" is NOT malformed: it parses as the npc:#<pk> identity form,
        # which the grammar deliberately reserves; authored use of it is a
        # content-authoring choice the grammar accepts.
        for authored in ("a:b", "123", "npc:x", "guild:branch"):
            with self.subTest(authored=authored):
                carrier = self._carrier(key=f"malformed {authored}", issuer_key=authored)
                with self.assertRaises(IssuerKeyError):
                    resolve_issuer_key(carrier)

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_a_non_string_issuer_key_rejects_without_coercion(self):
        for authored in (42, False, [], ("grey",)):
            with self.subTest(authored=authored):
                carrier = self._carrier(key=f"nonstring {authored}", issuer_key=authored)
                with self.assertRaises(IssuerKeyError):
                    resolve_issuer_key(carrier)

    @covers_requirement(
        "quest-issuer-authorization::an-issuer-key-resolves-in-exactly-two-authored-forms"
    )
    def test_an_unpersisted_host_rejects_rather_than_inventing_an_identity(self):
        component = mock.Mock()
        component.issuer_key = None
        host = mock.Mock()
        host.components.get.return_value = component
        host.pk = None
        with self.assertRaises(IssuerKeyError):
            resolve_issuer_key(host)


class LocalHostResolverTests(IssuerHostHarness):
    """The generic resolver finds a co-located commissioner unchanged (R2)."""

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-"
        "the-existing-service-host-component-shape"
    )
    def test_a_single_co_located_commissioner_resolves(self):
        carrier = self._carrier()
        self.assertIs(resolve_local_service_host(self.actor, QuestIssuer), carrier)

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-"
        "the-existing-service-host-component-shape"
    )
    def test_zero_carriers_report_the_no_host_outcome(self):
        with self.assertRaises(GuildServiceError) as caught:
            resolve_local_service_host(self.actor, QuestIssuer)
        self.assertIn("no local service host", str(caught.exception))

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-"
        "the-existing-service-host-component-shape"
    )
    def test_several_carriers_report_the_ambiguous_outcome(self):
        self._carrier(key="first granny")
        self._carrier(key="second granny")
        with self.assertRaises(GuildServiceError) as caught:
            resolve_local_service_host(self.actor, QuestIssuer)
        self.assertIn("multiple local service hosts", str(caught.exception))
