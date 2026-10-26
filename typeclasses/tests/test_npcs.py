"""NPC typeclass tests: the canonical-age helper."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC, ensure_npc_canonical_age


class EnsureNpcCanonicalAgeTests(EvenniaTestCase):
    def _fresh_npc(self):
        return create_object(NPC, key="identity-npc")

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_missing_ages_get_the_default_age(self):
        npc = self._fresh_npc()
        self.assertIsNone(npc.attributes.get("age"))
        self.assertIsNone(npc.attributes.get("apparent_age"))
        ensure_npc_canonical_age(npc)
        self.assertEqual(int(npc.attributes.get("age")), 18)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_existing_canonical_ages_are_preserved(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        npc.attributes.add("apparent_age", 28)
        ensure_npc_canonical_age(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 28)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_partial_identity_fills_only_the_missing_field(self):
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        ensure_npc_canonical_age(npc)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 18)

        reverse = self._fresh_npc()
        reverse.attributes.add("apparent_age", 28)
        ensure_npc_canonical_age(reverse)
        self.assertEqual(int(reverse.attributes.get("apparent_age")), 28)
        self.assertEqual(int(reverse.attributes.get("age")), 18)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_explicit_authored_ages_applied_when_missing(self):
        npc = self._fresh_npc()
        ensure_npc_canonical_age(npc, age=980, apparent_age=42)
        self.assertEqual(int(npc.attributes.get("age")), 980)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 42)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_partial_identity_with_authored_pair_fills_only_missing(self):
        # Age present (35), apparent_age missing -> gets authored apparent_age 42, age stays 35
        npc = self._fresh_npc()
        npc.attributes.add("age", 35)
        ensure_npc_canonical_age(npc, age=980, apparent_age=42)
        self.assertEqual(int(npc.attributes.get("age")), 35)
        self.assertEqual(int(npc.attributes.get("apparent_age")), 42)

        # Reverse: apparent_age present (28), age missing -> gets authored age 980, apparent_age stays 28
        reverse = self._fresh_npc()
        reverse.attributes.add("apparent_age", 28)
        ensure_npc_canonical_age(reverse, age=980, apparent_age=42)
        self.assertEqual(int(reverse.attributes.get("apparent_age")), 28)
        self.assertEqual(int(reverse.attributes.get("age")), 980)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_invalid_explicit_age_rejected(self):
        npc = self._fresh_npc()
        for bad_val in (True, False, -1, 10001, "20"):
            with self.subTest(bad_val=bad_val):
                with self.assertRaises(ValueError):
                    ensure_npc_canonical_age(npc, age=bad_val)
                with self.assertRaises(ValueError):
                    ensure_npc_canonical_age(npc, apparent_age=bad_val)

    @covers_requirement("npc-canonical-age::procedurally-spawned-npcs-carry-canonical-age-attributes")
    def test_invalid_second_field_does_not_mutate_first_field(self):
        npc = self._fresh_npc()
        with self.assertRaises(ValueError):
            ensure_npc_canonical_age(npc, age=35, apparent_age=True)
        self.assertIsNone(npc.attributes.get("age"))
        self.assertIsNone(npc.attributes.get("apparent_age"))


if __name__ == "__main__":
    import unittest

    unittest.main()
