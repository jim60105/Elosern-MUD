"""Creation proposal transient-fill validation regression (2026-08-11)."""
import unittest
from unittest.mock import patch
from web.webclient.presentation.creation import AFFINITY_ELEMENT_KEYS, MAX_PROPOSAL_NAME_CODE_POINTS, validate_creation
from ._support import _open_t_creation_scope, _proposal_wire, _shipped_race_affinity, _valid_payload


class ProposalTransientFillValidationTests(unittest.TestCase):
    """The v3 proposal slot's five optional transient-fill keys.

    Presence-only semantics: a carried value round-trips exactly, an absent
    key stays absent (never a null-valued copy), and every bound violation or
    null is a structural rejection (bump-creation-panel-proposal-v3 D1).
    """


    def setUp(self):
        _open_t_creation_scope(self)
        handle = patch(
            "web.webclient.presentation.creation._validate_affinity",
            _shipped_race_affinity,
        )
        handle.start()
        self.addCleanup(handle.stop)


    def _validate(self, proposal):
        return validate_creation(_valid_payload(proposal=proposal))["proposal"]


    def _rejects(self, proposal):
        with self.assertRaises(Exception):
            self._validate(proposal)


    def test_carried_transient_fill_keys_round_trip(self):
        fill = {
            "display_name": "莉雅",
            "age": 25,
            "apparent_age": 22,
            "background": "邊境孤女，隨商隊长大",
            "affinity_elements": ["fire", "water"],
        }
        proposal = self._validate(_proposal_wire(**fill))
        for key, value in fill.items():
            self.assertEqual(proposal[key], value)


    def test_absent_keys_stay_absent_not_null(self):
        proposal = self._validate(_proposal_wire())
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, proposal)


    def test_null_valued_transient_fill_keys_reject(self):
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            with self.subTest(key=key):
                self._rejects(_proposal_wire(**{key: None}))


    def test_bound_violations_reject(self):
        cases = {
            "under-zero age": _proposal_wire(age=-1),
            "over-bound age": _proposal_wire(age=10001),
            "boolean age": _proposal_wire(age=True),
            "under-zero apparent_age": _proposal_wire(apparent_age=-1),
            "float age": _proposal_wire(age=25.5),
            "empty display_name": _proposal_wire(display_name=""),
            "over-long display_name": _proposal_wire(
                display_name="莉" * (MAX_PROPOSAL_NAME_CODE_POINTS + 1)
            ),
            "empty background": _proposal_wire(background=""),
            "over-long background": _proposal_wire(background="長" * 601),
            "too many elements": _proposal_wire(
                affinity_elements=list(AFFINITY_ELEMENT_KEYS) + ["fire"]
            ),
            "unknown element": _proposal_wire(affinity_elements=["wood"]),
            "duplicate element": _proposal_wire(affinity_elements=["fire", "fire"]),
            "non-list affinity": _proposal_wire(affinity_elements={"fire": 1}),
            "unknown key": _proposal_wire(eye_color="琥珀"),
        }
        for label, proposal in cases.items():
            with self.subTest(label=label):
                self._rejects(proposal)


    def test_carried_empty_affinity_list_round_trips(self):
        # The normalized elf affinity value is a carried EMPTY set; only an
        # absent (None) value may omit the key.
        proposal = self._validate(_proposal_wire(affinity_elements=[]))
        self.assertEqual(proposal["affinity_elements"], [])


    def test_whitespace_only_prose_is_non_empty_not_non_blank(self):
        # Contract pin: the transient-fill prose fields are bounded NON-EMPTY
        # (1..N code points), deliberately not NON-BLANK like the persona
        # block — whitespace-only values must keep passing in both mirrors.
        proposal = self._validate(
            _proposal_wire(display_name=" ", background="  ")
        )
        self.assertEqual(proposal["display_name"], " ")
        self.assertEqual(proposal["background"], "  ")


if __name__ == "__main__":
    unittest.main()
