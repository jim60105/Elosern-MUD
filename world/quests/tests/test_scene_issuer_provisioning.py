"""Rules-owned scoped issuer provisioning tests (quest-scene-encounters 2.2).

The generated package path must grant only the validated declared commission
scope to the exact bound actor, keep the existing component shape and key
grammar, and refuse a collision or an incompatible existing authority.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import QuestIssuer
from typeclasses.npcs import NPC
from world.rules.quest_issuance import (
    QuestIssuanceError,
    issuer_is_authorized,
    issuer_key_owner,
    npc_issuer_key,
    provision_scoped_issuer,
    resolve_issuer_key,
)

_SCOPE_KEY = "story_mother"


class ScopedIssuerProvisioningTests(EvenniaTestCase):
    def test_provisioning_grants_only_the_declared_scope(self):
        host = create_object(NPC, key="generated issuer")
        self.assertIsNone(resolve_issuer_key(host))
        actual = provision_scoped_issuer(host, content_key=_SCOPE_KEY)
        self.assertEqual(actual, npc_issuer_key(_SCOPE_KEY))
        self.assertEqual(resolve_issuer_key(host), actual)
        self.assertTrue(issuer_is_authorized(actual))

    def test_provisioning_refuses_an_incompatible_existing_authority(self):
        host = create_object(NPC, key="authored issuer")
        host.components.add(QuestIssuer.create(host, issuer_key="authored_key"))
        with self.assertRaises(QuestIssuanceError):
            provision_scoped_issuer(host, content_key=_SCOPE_KEY)
        self.assertEqual(resolve_issuer_key(host), npc_issuer_key("authored_key"))

    def test_provisioning_refuses_a_key_owned_by_another_carrier(self):
        owner = create_object(NPC, key="existing carrier")
        owner.components.add(QuestIssuer.create(owner, issuer_key=_SCOPE_KEY))
        other = create_object(NPC, key="generated issuer")
        with self.assertRaises(QuestIssuanceError):
            provision_scoped_issuer(other, content_key=_SCOPE_KEY)
        self.assertIsNone(resolve_issuer_key(other))
        self.assertEqual(issuer_key_owner(npc_issuer_key(_SCOPE_KEY)), owner)

    def test_provisioning_is_idempotent_for_the_same_scope(self):
        host = create_object(NPC, key="generated issuer")
        first = provision_scoped_issuer(host, content_key=_SCOPE_KEY)
        second = provision_scoped_issuer(host, content_key=_SCOPE_KEY)
        self.assertEqual(first, second)
