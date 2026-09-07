"""Render-contract stubs for the Narrator aftermath overlay (D-D5).

Pure render pins: a disabled (``None``) or failing profile degrades to the
deterministic template render byte-for-byte, and a succeeding profile
appends exactly one prose paragraph per entry in entry order without
rewriting or duplicating the fixed wake/template lines.
"""

import unittest

from tools.spec_traceability import covers_requirement
from world.ai.narrator import render_aftermath

_ENTRIES = (
    {"kind": "defeat_settle", "line": "你眼前一黑倒了下去。"},
    {"kind": "violation_act", "line": "哥布林 得逞了。"},
    {"kind": "digest_outcome", "line": "你身體的餘韻沉澱下來。"},
)

_OFFLINE_RENDER = "你眼前一黑倒了下去。\n哥布林 得逞了。\n你身體的餘韻沉澱下來。"


def _succeeding(entries):
    return [f"旁白段落{index}" for index in range(len(entries))]


class RenderAftermathDisabledTests(unittest.TestCase):
    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_disabled_profile_renders_templates_only_byte_identical(self):
        self.assertEqual(render_aftermath(_ENTRIES, None), _OFFLINE_RENDER)


class RenderAftermathFailureTests(unittest.TestCase):
    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_raising_profile_discards_the_overlay(self):
        def _timeout(entries):
            raise TimeoutError("narrator timeout")

        self.assertEqual(render_aftermath(_ENTRIES, _timeout), _OFFLINE_RENDER)

    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_malformed_answer_count_discards_the_overlay(self):
        self.assertEqual(
            render_aftermath(_ENTRIES, lambda entries: ["只有一段"]), _OFFLINE_RENDER
        )

    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_blank_or_non_string_paragraph_discards_the_overlay(self):
        for paragraphs in (["", "x", "y"], [1, 2, 3]):
            with self.subTest(paragraphs=paragraphs):
                self.assertEqual(
                    render_aftermath(_ENTRIES, lambda entries, p=paragraphs: p),
                    _OFFLINE_RENDER,
                )


class RenderAftermathSuccessTests(unittest.TestCase):
    @covers_requirement(
        "defeat-aftermath-digest::the-narrator-overlays-aftermath-entries-and-always-degrades-to-templates",
    )
    def test_succeeding_profile_appends_exactly_one_paragraph_per_entry(self):
        rendered = render_aftermath(_ENTRIES, _succeeding)
        base, *overlay = rendered.split("\n\n")
        self.assertEqual(base, _OFFLINE_RENDER)
        self.assertEqual(
            overlay, ["旁白段落0", "旁白段落1", "旁白段落2"]
        )

    def test_empty_entries_render_empty_without_an_overlay(self):
        self.assertEqual(render_aftermath((), _succeeding), "")
