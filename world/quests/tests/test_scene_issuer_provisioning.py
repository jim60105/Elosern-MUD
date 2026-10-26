"""Rules-owned scoped issuer provisioning tests (quest-scene-encounters 2.2).

The generated package path must grant only the validated declared commission
scope to the exact bound actor, keep the existing component shape and key
grammar, and refuse a collision or an incompatible existing authority.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import QuestIssuer
from typeclasses.npcs import NPC
from world.quests.tests._scene_package_fixtures import issuer_plan
from world.rules.quest_issuance import (
    QuestIssuanceError,
    issuer_is_authorized,
    issuer_key_owner,
    npc_issuer_key,
    provision_scoped_issuer,
    resolve_issuer_key,
)

_SCOPE_KEY = "story_mother"


def _plan(content_key: str = _SCOPE_KEY):
    return issuer_plan(content_key)


class ScopedIssuerProvisioningTests(EvenniaTestCase):
    def test_provisioning_grants_only_the_declared_scope(self):
        host = create_object(NPC, key="generated issuer")
        self.assertIsNone(resolve_issuer_key(host))
        actual = provision_scoped_issuer(host, content_key=_SCOPE_KEY, plan=_plan())
        self.assertEqual(actual, npc_issuer_key(_SCOPE_KEY))
        self.assertEqual(resolve_issuer_key(host), actual)
        self.assertTrue(issuer_is_authorized(actual))

    def test_provisioning_refuses_an_incompatible_existing_authority(self):
        host = create_object(NPC, key="authored issuer")
        host.components.add(QuestIssuer.create(host, issuer_key="authored_key"))
        with self.assertRaises(QuestIssuanceError):
            provision_scoped_issuer(host, content_key=_SCOPE_KEY, plan=_plan())
        self.assertEqual(resolve_issuer_key(host), npc_issuer_key("authored_key"))

    def test_provisioning_refuses_a_key_owned_by_another_carrier(self):
        owner = create_object(NPC, key="existing carrier")
        owner.components.add(QuestIssuer.create(owner, issuer_key=_SCOPE_KEY))
        other = create_object(NPC, key="generated issuer")
        with self.assertRaises(QuestIssuanceError):
            provision_scoped_issuer(other, content_key=_SCOPE_KEY, plan=_plan())
        self.assertIsNone(resolve_issuer_key(other))
        self.assertEqual(issuer_key_owner(npc_issuer_key(_SCOPE_KEY)), owner)

    def test_provisioning_is_idempotent_for_the_same_scope(self):
        host = create_object(NPC, key="generated issuer")
        first = provision_scoped_issuer(host, content_key=_SCOPE_KEY, plan=_plan())
        second = provision_scoped_issuer(host, content_key=_SCOPE_KEY, plan=_plan())
        self.assertEqual(first, second)

    def test_a_plan_without_the_declared_capability_is_refused(self):
        from world.rules.npc_capabilities import validate_capabilities

        host = create_object(NPC, key="generated issuer")
        with self.assertRaises(QuestIssuanceError):
            provision_scoped_issuer(
                host, content_key=_SCOPE_KEY, plan=validate_capabilities([])
            )
        self.assertIsNone(resolve_issuer_key(host))

    def test_incompatible_existing_authored_state_is_not_repurposed(self):
        # A reused actor whose issuer capability is place-bound (or carries
        # another scoped service identity) is authored state, not a slot to
        # rewrite: the generated person-bound plan is refused before any write.
        from typeclasses.components import QuestIssuer

        for fields in (
            {"service_binding": "place"},
            {"anchor_room_id": 1},
            {"service_id": "another_scoped_service"},
        ):
            with self.subTest(fields=fields):
                host = create_object(NPC, key="incompatible issuer")
                component = QuestIssuer.create(host)
                for name, value in fields.items():
                    setattr(component, name, value)
                host.components.add(component)
                with self.assertRaises(QuestIssuanceError):
                    provision_scoped_issuer(
                        host, content_key=_SCOPE_KEY, plan=_plan()
                    )
                live = host.components.get(QuestIssuer.get_component_slot())
                for name, value in fields.items():
                    self.assertEqual(getattr(live, name), value)
                self.assertIsNone(live.issuer_key)
