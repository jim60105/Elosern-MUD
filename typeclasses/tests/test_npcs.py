"""Tests for the shared NPC adult-identity helper (fix-npc-adult-identity D1)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC, ensure_npc_adult_identity


class EnsureNpcAdultIdentityTests(EvenniaTest):
    def _fresh_npc(self):
        return create_object(NPC, key="identity-npc")

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_missing_identity_gets_the_adult_baseline(self):
        npc = self._fresh_npc()
        self.assertIsNone(npc.attributes.get("age"))
        self.assertIsNone(npc.attributes.get("apparent_age"))
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 18)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_existing_canonical_ages_are_preserved(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        npc.attributes.add("apparent_age", 28)
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 28)

    @covers_requirement("npc-adult-identity::procedurally-spawned-npcs-carry-canonical-adult-identity")
    def test_partial_identity_fills_only_the_missing_field(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        ensure_npc_adult_identity(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

        reverse = self._fresh_npc()
        reverse.attributes.add("apparent_age", 28)
        ensure_npc_adult_identity(reverse)
        self.assertEqual(int(reverse.attributes.get("apparent_age")), 28)
        self.assertEqual(int(reverse.attributes.get("age")), 18)


if __name__ == "__main__":
    import unittest

    unittest.main()
