"""Behaviour of the pure dream-proposal edit applier.

Fixture content is synthetic ASCII only: the applier is the subject, never
shipped lore. Byte figures in the aggregate-budget tests are the design's
canonical-JSON measure written out by hand, so they pin the budget rather than
re-derive it.
"""

from __future__ import annotations

import json
import unittest

from world.narrative import authoring
from world.narrative import dream_proposal
from world.narrative.dream_proposal import ProposalEditError


def _item(prefix: str, length: int) -> str:
    """One synthetic field line of exactly `length` characters."""
    return (prefix + "x" * length)[:length]


def _lines(prefix: str, count: int, length: int) -> str:
    """`count` distinct lines of exactly `length` characters, as field text."""
    return "\n".join(_item(f"{prefix}{index:02d}", length) for index in range(count))


def _block(prefix: str) -> str:
    """Thirty-two distinct 200-character lines: one full tag list as text."""
    return _lines(prefix, 32, 200)


def _requirement_lines(count: int) -> str:
    """`count` distinct, valid `place: ...` rows as field text."""
    return "\n".join(f"place: stop {index}" for index in range(count))


def _create(path: str, text: str) -> dict:
    return {"command": "create", "path": path, "file_text": text}


def _canonical_bytes(value) -> int:
    return len(
        json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


class TestEditCommands(unittest.TestCase):
    def setUp(self):
        self.proposal = {
            "summary": "the harbour at dusk",
            "themes": ["tide"],
            "atmosphere": ["salt"],
            "participants": [],
            "emphasis": [],
            "exclusions": [],
            "requirements": [],
        }

    def test_each_command_succeeds(self):
        edits = [
            {
                "command": "str_replace",
                "path": "summary",
                "old_str": "dusk",
                "new_str": "dawn",
            },
            {
                "command": "insert",
                "path": "themes",
                "insert_line": 1,
                "insert_text": "lanterns",
            },
            _create("atmosphere", "rain\nmist"),
        ]

        result = dream_proposal.apply_edits(self.proposal, edits)

        self.assertEqual(result["summary"], "the harbour at dawn")
        self.assertEqual(result["themes"], ["tide", "lanterns"])
        self.assertEqual(result["atmosphere"], ["rain", "mist"])
        self.assertEqual(self.proposal["summary"], "the harbour at dusk")
        self.assertEqual(self.proposal["themes"], ["tide"])
        self.assertEqual(self.proposal["atmosphere"], ["salt"])

    def test_later_edits_see_earlier_ones(self):
        edits = [
            _create("themes", "harbour light"),
            {
                "command": "str_replace",
                "path": "themes",
                "old_str": "harbour light",
                "new_str": "dock light",
            },
        ]

        self.assertEqual(
            dream_proposal.apply_edits(self.proposal, edits)["themes"],
            ["dock light"],
        )

    def test_str_replace_spans_line_boundaries(self):
        proposal = dict(self.proposal, themes=["tide", "salt"])
        edits = [
            {
                "command": "str_replace",
                "path": "themes",
                "old_str": "tide\nsalt",
                "new_str": "tide\nsalt mist",
            }
        ]

        self.assertEqual(
            dream_proposal.apply_edits(proposal, edits)["themes"],
            ["tide", "salt mist"],
        )

    def test_search_text_does_not_match_exactly_once(self):
        cases = [
            ("the harbour at dusk", "tide", "no_match"),
            ("tide and tide", "tide", "multiple_matches"),
        ]
        for summary, old_str, code in cases:
            with self.subTest(code=code):
                proposal = dict(self.proposal, summary=summary)
                edits = [
                    {
                        "command": "str_replace",
                        "path": "summary",
                        "old_str": old_str,
                        "new_str": "calm",
                    }
                ]

                with self.assertRaises(ProposalEditError) as caught:
                    dream_proposal.apply_edits(proposal, edits)

                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.index, 0)
                self.assertEqual(proposal["summary"], summary)

    def test_unknown_command_field_or_malformed_edit(self):
        cases = [
            ("not an edit", "malformed_edit"),
            ({"path": "summary"}, "unknown_command"),
            ({"command": "append", "path": "summary", "file_text": "x"}, "unknown_command"),
            ({"command": "create", "path": "title", "file_text": "x"}, "unknown_path"),
            ({"command": "create", "path": 7, "file_text": "x"}, "unknown_path"),
            ({"command": "create", "path": "summary"}, "malformed_edit"),
            (
                {
                    "command": "create",
                    "path": "summary",
                    "file_text": "x",
                    "old_str": "y",
                },
                "malformed_edit",
            ),
            (_create("themes", _block("t")), None),
            (_create("summary", "x" * 6501), "malformed_edit"),
            ({"command": "create", "path": "summary", "file_text": 7}, "malformed_edit"),
            (
                {
                    "command": "str_replace",
                    "path": "summary",
                    "old_str": "",
                    "new_str": "x",
                },
                "malformed_edit",
            ),
            (
                {
                    "command": "insert",
                    "path": "themes",
                    "insert_line": 5,
                    "insert_text": "x",
                },
                "insert_out_of_range",
            ),
            (
                {
                    "command": "insert",
                    "path": "themes",
                    "insert_line": -1,
                    "insert_text": "x",
                },
                "insert_out_of_range",
            ),
            (
                {
                    "command": "insert",
                    "path": "themes",
                    "insert_line": True,
                    "insert_text": "x",
                },
                "malformed_edit",
            ),
            (
                {
                    "command": "insert",
                    "path": "themes",
                    "insert_line": "1",
                    "insert_text": "x",
                },
                "malformed_edit",
            ),
        ]
        for edit, code in cases:
            with self.subTest(code=code, edit=edit):
                if code is None:
                    dream_proposal.apply_edits(self.proposal, [edit])
                    continue

                with self.assertRaises(ProposalEditError) as caught:
                    dream_proposal.apply_edits(self.proposal, [edit])

                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.index, 0)
                self.assertEqual(self.proposal["themes"], ["tide"])

    def test_insert_at_start_of_an_empty_field(self):
        proposal = dict(self.proposal, themes=[])
        edits = [
            {
                "command": "insert",
                "path": "themes",
                "insert_line": 0,
                "insert_text": "moon",
            }
        ]

        self.assertEqual(
            dream_proposal.apply_edits(proposal, edits)["themes"], ["moon"]
        )

        late = [dict(edits[0], insert_line=1)]
        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.apply_edits(proposal, late)
        self.assertEqual(caught.exception.code, "insert_out_of_range")
        self.assertEqual(caught.exception.index, 0)

    def test_failure_after_a_valid_edit_rolls_back(self):
        edits = [
            _create("themes", "moon"),
            {
                "command": "insert",
                "path": "atmosphere",
                "insert_line": 9,
                "insert_text": "x",
            },
        ]

        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.apply_edits(self.proposal, edits)

        self.assertEqual(caught.exception.code, "insert_out_of_range")
        self.assertEqual(caught.exception.index, 1)
        self.assertEqual(self.proposal["themes"], ["tide"])

    def test_empty_edit_set(self):
        result = dream_proposal.apply_edits(self.proposal, [])

        self.assertEqual(result, self.proposal)
        self.assertIsNot(result, self.proposal)

    def test_edit_set_container(self):
        self.assertEqual(dream_proposal.apply_edits(self.proposal, ()), self.proposal)

        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.apply_edits(self.proposal, "create")
        self.assertEqual(caught.exception.code, "malformed_edit")
        self.assertIsNone(caught.exception.index)

        too_many = [
            {
                "command": "insert",
                "path": "themes",
                "insert_line": 0,
                "insert_text": f"line{index}",
            }
            for index in range(dream_proposal.MAX_EDITS + 1)
        ]
        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.apply_edits(self.proposal, too_many)
        self.assertEqual(caught.exception.code, "too_many_edits")
        self.assertIsNone(caught.exception.index)


class TestFieldNormalization(unittest.TestCase):
    def test_list_normalization(self):
        edits = [_create("themes", "  tide  \n\n tide \n dawn ")]

        result = dream_proposal.apply_edits(dream_proposal.empty_proposal(), edits)

        self.assertEqual(result["themes"], ["tide", "dawn"])

    def test_create_with_empty_text_clears_a_list(self):
        proposal = {"themes": ["tide", "salt"]}

        result = dream_proposal.apply_edits(proposal, [_create("themes", "")])

        self.assertEqual(result["themes"], [])

    def test_requirement_rows_parse_and_render(self):
        edits = [
            _create(
                "requirements",
                "place: the harbour\n\nnew_character: a ferryman",
            )
        ]

        result = dream_proposal.apply_edits(dream_proposal.empty_proposal(), edits)

        self.assertEqual(
            result["requirements"],
            [
                {"kind": "place", "text": "the harbour"},
                {"kind": "new_character", "text": "a ferryman"},
            ],
        )
        self.assertEqual(
            dream_proposal.field_text(result, "requirements"),
            "place: the harbour\nnew_character: a ferryman",
        )

        repeated = dream_proposal.apply_edits(
            dream_proposal.empty_proposal(),
            [_create("requirements", "place: the harbour\nplace：the harbour")],
        )
        self.assertEqual(
            repeated["requirements"], [{"kind": "place", "text": "the harbour"}]
        )

    def test_full_width_colon(self):
        cases = [
            ("place：the harbour", "place", "the harbour"),
            ("place ： the harbour", "place", "the harbour"),
            ("place: Harbour: North Dock", "place", "Harbour: North Dock"),
        ]
        for line, kind, text in cases:
            with self.subTest(line=line):
                result = dream_proposal.apply_edits(
                    dream_proposal.empty_proposal(), [_create("requirements", line)]
                )

                self.assertEqual(
                    result["requirements"], [{"kind": kind, "text": text}]
                )
                self.assertEqual(
                    dream_proposal.field_text(result, "requirements"),
                    f"{kind}: {text}",
                )

    def test_malformed_requirement_line(self):
        cases = ["the harbour", "vessel: a ship", "place:", "place:   "]
        for line in cases:
            with self.subTest(line=line):
                with self.assertRaises(ProposalEditError) as caught:
                    dream_proposal.apply_edits(
                        dream_proposal.empty_proposal(),
                        [_create("requirements", line)],
                    )

                self.assertEqual(caught.exception.code, "malformed_requirement")
                self.assertEqual(caught.exception.index, 0)

    def test_bounds(self):
        empty = dream_proposal.empty_proposal()

        summary = dream_proposal.apply_edits(empty, [_create("summary", "s" * 2000)])
        self.assertEqual(len(summary["summary"]), 2000)
        items = dream_proposal.apply_edits(empty, [_create("themes", _block("t"))])
        self.assertEqual(len(items["themes"]), 32)
        longest = dream_proposal.apply_edits(empty, [_create("themes", _item("t", 200))])
        self.assertEqual(len(longest["themes"][0]), 200)
        rows = dream_proposal.apply_edits(
            empty, [_create("requirements", _requirement_lines(8))]
        )
        self.assertEqual(len(rows["requirements"]), 8)
        longest_row = dream_proposal.apply_edits(
            empty, [_create("requirements", "place: " + "r" * 200)]
        )
        self.assertEqual(len(longest_row["requirements"][0]["text"]), 200)

        over = [
            (_create("summary", "s" * 2001), "summary_too_long"),
            (_create("themes", _lines("t", 33, 150)), "too_many_items"),
            (_create("themes", _item("t", 201)), "item_too_long"),
            (_create("requirements", _requirement_lines(9)), "too_many_requirements"),
            (_create("requirements", "place: " + "r" * 201), "requirement_too_long"),
        ]
        for edit, code in over:
            with self.subTest(code=code):
                with self.assertRaises(ProposalEditError) as caught:
                    dream_proposal.apply_edits(empty, [edit])

                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.index, 0)


class TestBoundsMatchTheDirectionStore(unittest.TestCase):
    def test_bounds_match_the_direction_store(self):
        self.assertEqual(
            dream_proposal.MAX_SUMMARY_CHARACTERS, authoring.MAX_SUMMARY_CHARACTERS
        )
        self.assertEqual(dream_proposal.MAX_LIST_ITEMS, authoring.MAX_LIST_ITEMS)
        self.assertEqual(
            dream_proposal.MAX_ITEM_CHARACTERS, authoring.MAX_ITEM_CHARACTERS
        )
        self.assertEqual(dream_proposal.MAX_REQUIREMENTS, authoring.MAX_REQUIREMENTS)
        self.assertEqual(
            dream_proposal.MAX_REQUIREMENT_TEXT, authoring.MAX_REQUIREMENT_TEXT
        )
        self.assertEqual(
            set(dream_proposal.REQUIREMENT_KINDS), set(authoring.REQUIREMENT_KINDS)
        )


class TestAggregateBudgets(unittest.TestCase):
    def _full_proposal(self) -> dict:
        """Summary plus two full tag lists: # 108 + 2000 + 6495 + 6495 bytes."""
        proposal = dream_proposal.apply_edits(
            dream_proposal.empty_proposal(), [_create("summary", "s" * 2000)]
        )
        proposal = dream_proposal.apply_edits(proposal, [_create("themes", _block("t"))])
        return dream_proposal.apply_edits(
            proposal, [_create("atmosphere", _block("a"))]
        )

    def _participants_text(self, last_item_length: int) -> str:
        """Six 200-character lines plus one line of `last_item_length`."""
        lines = [_item(f"p0{index}", 200) for index in range(6)]
        return "\n".join([*lines, _item("p06", last_item_length)])

    def test_result_inside_both_budgets_is_accepted(self):
        before = self._full_proposal()
        proposal = dream_proposal.apply_edits(
            before, [_create("participants", self._participants_text(66))]
        )

        # 108 skeleton + 2000 summary + 6495 themes + 6495 atmosphere + 1286.
        self.assertEqual(_canonical_bytes(before), 15098)
        self.assertEqual(_canonical_bytes(proposal), 16384)
        self.assertLessEqual(
            _canonical_bytes(dream_proposal.diff(before, proposal)), 8192
        )

    def test_aggregate_size(self):
        before = self._full_proposal()

        with self.subTest(budget="proposal"):
            with self.assertRaises(ProposalEditError) as caught:
                dream_proposal.apply_edits(
                    before, [_create("participants", self._participants_text(67))]
                )

            self.assertEqual(caught.exception.code, "proposal_too_large")
            self.assertEqual(caught.exception.index, 0)

        with self.subTest(budget="change report"):
            rewrites = [
                _create("themes", _block("T")),
                _create("atmosphere", _block("A")),
            ]
            with self.assertRaises(ProposalEditError) as caught:
                dream_proposal.apply_edits(before, rewrites)

            self.assertEqual(caught.exception.code, "changes_too_large")
            self.assertIsNone(caught.exception.index)


class TestChangeReport(unittest.TestCase):
    def setUp(self):
        self.proposal = {
            "summary": "the harbour at dusk",
            "themes": ["tide", "salt"],
            "atmosphere": [],
            "participants": [],
            "emphasis": [],
            "exclusions": [],
            "requirements": [],
        }

    def test_added_and_removed_list_items(self):
        after = dream_proposal.apply_edits(
            self.proposal,
            [
                {
                    "command": "str_replace",
                    "path": "themes",
                    "old_str": "salt",
                    "new_str": "mist",
                }
            ],
        )

        report = dream_proposal.diff(self.proposal, after)

        self.assertEqual(report["lists"]["themes"], {"added": ["mist"], "removed": ["salt"]})
        for field in ("atmosphere", "participants", "emphasis", "exclusions"):
            self.assertEqual(report["lists"][field], {"added": [], "removed": []})
        self.assertIsNone(report["summary"])
        self.assertEqual(report["requirements"], {"added": [], "removed": []})

    def test_summary_first_takes_shape_then_changes(self):
        empty = dream_proposal.empty_proposal()
        formed = dream_proposal.apply_edits(
            empty, [_create("summary", "the harbour at dusk")]
        )
        changed = dream_proposal.apply_edits(
            formed,
            [
                {
                    "command": "str_replace",
                    "path": "summary",
                    "old_str": "dusk",
                    "new_str": "dawn",
                }
            ],
        )

        self.assertEqual(dream_proposal.diff(empty, formed)["summary"], "formed")
        self.assertEqual(dream_proposal.diff(formed, changed)["summary"], "changed")
        self.assertEqual(
            dream_proposal.diff(empty, formed)["lists"]["themes"],
            {"added": [], "removed": []},
        )

    def test_nothing_changed(self):
        report = dream_proposal.diff(self.proposal, dict(self.proposal))

        self.assertIsNone(report["summary"])
        self.assertEqual(set(report["lists"]), set(dream_proposal.LIST_FIELDS))
        for field in dream_proposal.LIST_FIELDS:
            self.assertEqual(report["lists"][field], {"added": [], "removed": []})
        self.assertEqual(report["requirements"], {"added": [], "removed": []})

    def test_requirement_rows_compare_by_kind_and_text(self):
        before = {
            "requirements": [{"kind": "place", "text": "the harbour"}],
        }

        text_changed = dream_proposal.apply_edits(
            before, [_create("requirements", "place: the north harbour")]
        )
        text_report = dream_proposal.diff(before, text_changed)
        self.assertEqual(
            text_report["requirements"],
            {
                "added": [{"kind": "place", "text": "the north harbour"}],
                "removed": [{"kind": "place", "text": "the harbour"}],
            },
        )

        kind_changed = dream_proposal.apply_edits(
            before, [_create("requirements", "new_character: the harbour")]
        )
        kind_report = dream_proposal.diff(before, kind_changed)
        self.assertEqual(
            kind_report["requirements"],
            {
                "added": [{"kind": "new_character", "text": "the harbour"}],
                "removed": [{"kind": "place", "text": "the harbour"}],
            },
        )

        kind_report["requirements"]["added"][0]["text"] = "mutated"
        self.assertEqual(
            kind_changed["requirements"],
            [{"kind": "new_character", "text": "the harbour"}],
        )


class TestProposalHelpers(unittest.TestCase):
    def test_empty_proposal(self):
        self.assertEqual(
            dream_proposal.empty_proposal(),
            {
                "summary": "",
                "themes": [],
                "atmosphere": [],
                "participants": [],
                "emphasis": [],
                "exclusions": [],
                "requirements": [],
            },
        )

    def test_normalize_proposal_returns_a_canonical_copy(self):
        raw = {
            "summary": "  the harbour at dusk  ",
            "themes": ["  tide  ", "tide", "", "salt"],
            "requirements": [{"kind": "place", "text": "  the harbour  "}],
            "note": "ignored",
        }

        normalized = dream_proposal.normalize_proposal(raw)

        self.assertEqual(
            normalized,
            {
                "summary": "the harbour at dusk",
                "themes": ["tide", "salt"],
                "atmosphere": [],
                "participants": [],
                "emphasis": [],
                "exclusions": [],
                "requirements": [{"kind": "place", "text": "the harbour"}],
            },
        )
        normalized["themes"].append("dawn")
        normalized["requirements"][0]["text"] = "mutated"
        self.assertEqual(raw["themes"], ["  tide  ", "tide", "", "salt"])
        self.assertEqual(
            raw["requirements"], [{"kind": "place", "text": "  the harbour  "}]
        )

    def test_normalize_proposal_defaults_missing_keys(self):
        self.assertEqual(
            dream_proposal.normalize_proposal({}), dream_proposal.empty_proposal()
        )

    def test_normalize_proposal_rejects_wrong_types(self):
        cases = [
            "not a proposal",
            {"summary": 7},
            {"themes": "tide"},
            {"themes": ["tide", 7]},
            {"requirements": "place: the harbour"},
            {"requirements": ["place: the harbour"]},
            {"requirements": [{"kind": "place", "text": "the harbour", "note": "x"}]},
            {"requirements": [{"kind": 7, "text": "the harbour"}]},
            {"requirements": [{"kind": "place", "text": 7}]},
            {"requirements": [{"kind": "vessel", "text": "the harbour"}]},
            {"requirements": [{"kind": "place", "text": "   "}]},
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ProposalEditError) as caught:
                    dream_proposal.normalize_proposal(value)

                self.assertEqual(caught.exception.code, "malformed_proposal")
                self.assertIsNone(caught.exception.index)

    def test_normalize_proposal_passes_bound_codes_through(self):
        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.normalize_proposal({"summary": "s" * 2001})
        self.assertEqual(caught.exception.code, "summary_too_long")
        self.assertIsNone(caught.exception.index)

        oversized = dream_proposal.empty_proposal()
        oversized["themes"] = [_item(f"t{index:02d}", 200) for index in range(32)]
        oversized["atmosphere"] = [_item(f"a{index:02d}", 200) for index in range(32)]
        oversized["participants"] = [
            _item(f"p{index:02d}", 200) for index in range(32)
        ]
        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.normalize_proposal(oversized)
        self.assertEqual(caught.exception.code, "proposal_too_large")
        self.assertIsNone(caught.exception.index)

    def test_is_empty(self):
        self.assertTrue(dream_proposal.is_empty(dream_proposal.empty_proposal()))
        self.assertTrue(dream_proposal.is_empty({"summary": "   "}))
        self.assertFalse(dream_proposal.is_empty({"summary": "the harbour"}))
        self.assertFalse(dream_proposal.is_empty({"themes": ["tide"]}))
        self.assertFalse(
            dream_proposal.is_empty(
                {"requirements": [{"kind": "place", "text": "the harbour"}]}
            )
        )

    def test_field_text_and_numbered_lines(self):
        proposal = {
            "summary": "the harbour at dusk",
            "themes": ["tide", "salt"],
            "requirements": [{"kind": "place", "text": "the harbour"}],
        }

        self.assertEqual(
            dream_proposal.field_text(proposal, "summary"), "the harbour at dusk"
        )
        self.assertEqual(dream_proposal.field_text(proposal, "themes"), "tide\nsalt")
        self.assertEqual(
            dream_proposal.field_text(proposal, "requirements"), "place: the harbour"
        )
        self.assertEqual(
            dream_proposal.numbered_lines(proposal, "themes"),
            [{"line": 1, "text": "tide"}, {"line": 2, "text": "salt"}],
        )
        self.assertEqual(dream_proposal.numbered_lines(proposal, "emphasis"), [])

        with self.assertRaises(ProposalEditError) as caught:
            dream_proposal.field_text(proposal, "title")
        self.assertEqual(caught.exception.code, "unknown_path")
        self.assertIsNone(caught.exception.index)


if __name__ == "__main__":
    unittest.main()
