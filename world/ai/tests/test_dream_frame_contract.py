"""Data-contract test: approved dream frame divine-identity refusal contract

The explicit dream presentation keeps the obscured goddess-like counterpart
unresolved: she must never be identified as one of the canonical deities or
disclose the hidden divine mysteries. These tests pin the shipped marker
vocabulary the guardrail validator enforces, so an accidental edit of the
canonical names fails here.
"""

from __future__ import annotations

import unittest

from world.ai.dream import (
    FORBIDDEN_DIVINE_MARKERS,
    FORBIDDEN_DIVINE_MYSTERY_MARKERS,
)


class DreamFrameContractTests(unittest.TestCase):
    def test_forbidden_divine_identity_names_the_canonical_deities(self):
        self.assertEqual(
            set(FORBIDDEN_DIVINE_MARKERS),
            {"光明女神", "暗之女神", "知識女神"},
        )

    def test_forbidden_divine_mysteries_are_declared(self):
        self.assertTrue(FORBIDDEN_DIVINE_MYSTERY_MARKERS)
        for marker in FORBIDDEN_DIVINE_MYSTERY_MARKERS:
            with self.subTest(marker=marker):
                self.assertIsInstance(marker, str)
                self.assertTrue(marker.strip())


if __name__ == "__main__":
    unittest.main()
