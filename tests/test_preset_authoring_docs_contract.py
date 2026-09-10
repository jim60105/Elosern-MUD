"""Data-contract test: authoring docs contract
Regression checks that the player-preset authoring guide cannot drift.

``docs/development/adding-player-presets.md`` is the authoring contract for
every field of ``world/lore.player_presets.PlayerPreset``. This module
cross-checks the dataclass field set against the guide (every field name must
appear as an inline-code span, so short names like ``key`` cannot be satisfied
incidentally by ordinary prose) and the sidebar registration, following the
top-level bootstrap pattern of ``tests/test_command_docs.py``. It opens no
database.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import fields
import os
import re
import unittest
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

from world.lore.player_presets import PlayerPreset

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "development" / "adding-player-presets.md"
SIDEBAR_PATH = REPO_ROOT / "docs" / "_sidebar.md"

GUIDE_SIDEBAR_LINK = "(/development/adding-player-presets)"
ITEMS_SIDEBAR_LINK = "(/development/adding-items)"
DEVELOPER_SECTION = "- 開發者指南"

# A field counts as documented only when the exact bare name stands alone
# between a pair of inline backticks. Fenced code blocks are stripped first so
# a fence artifact can never pair across real content, and a span carrying any
# surrounding text (`preset.key`, `allocations 的每一項`) does not count.
_FENCE_PATTERN = re.compile(r"```.*?```", re.DOTALL)
_INLINE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")


def undocumented_field_names(guide_text: str, field_names) -> list[str]:
    """Return the field names absent from ``guide_text`` as inline-code spans."""
    body = _FENCE_PATTERN.sub("", guide_text)
    spans = {span.strip() for span in _INLINE_SPAN_PATTERN.findall(body)}
    return [name for name in field_names if name not in spans]


class PresetAuthoringGuideContractTests(unittest.TestCase):
    @covers_requirement(
        "preset-authoring-docs::the-player-preset-authoring-guide-exists-and-is-reachable"
    )
    def test_guide_exists_and_is_registered_in_the_sidebar(self):
        self.assertTrue(
            GUIDE_PATH.is_file(),
            f"missing authoring guide {GUIDE_PATH.relative_to(REPO_ROOT)}",
        )
        sidebar = SIDEBAR_PATH.read_text(encoding="utf-8")
        lines = sidebar.splitlines()
        guide_lines = [
            index for index, line in enumerate(lines) if GUIDE_SIDEBAR_LINK in line
        ]
        self.assertEqual(
            len(guide_lines),
            1,
            "the docsify sidebar must link the guide exactly once, without the .md suffix",
        )
        guide_line = guide_lines[0]
        # The link's line must sit inside the 開發者指南 block (from that
        # top-level heading to the next top-level heading, if any), not merely
        # anywhere in the file, and immediately after the 新增物品指南 entry.
        top_level = [
            index
            for index, line in enumerate(lines)
            if line.startswith("- ") or line.startswith("## ")
        ]
        section_start = max(
            (index for index in top_level if lines[index].strip() == DEVELOPER_SECTION),
            default=-1,
        )
        self.assertGreaterEqual(
            section_start, 0, "sidebar must carry the 開發者指南 section"
        )
        section_end = next(
            (index for index in top_level if index > section_start), len(lines)
        )
        self.assertTrue(
            section_start < guide_line < section_end,
            "the guide entry must live under 開發者指南",
        )
        items_lines = [
            index for index, line in enumerate(lines) if ITEMS_SIDEBAR_LINK in line
        ]
        self.assertEqual(len(items_lines), 1, "sidebar must link 新增物品指南 once")
        self.assertEqual(
            guide_line,
            items_lines[0] + 1,
            "the guide entry must sit immediately after 新增物品指南",
        )

    @covers_requirement(
        "preset-authoring-docs::the-guide-stays-in-sync-with-the-registry-field-set"
    )
    def test_every_preset_field_is_documented_as_an_inline_code_span(self):
        guide = GUIDE_PATH.read_text(encoding="utf-8")
        field_names = [field.name for field in fields(PlayerPreset)]
        self.assertTrue(field_names)
        undocumented = undocumented_field_names(guide, field_names)
        self.assertEqual(
            undocumented,
            [],
            f"PlayerPreset fields missing from the guide as inline-code spans: "
            f"{', '.join(undocumented)}",
        )

    @covers_requirement(
        "preset-authoring-docs::the-guide-stays-in-sync-with-the-registry-field-set"
    )
    def test_prose_only_mention_does_not_count_as_documented(self):
        # A guide that mentions a field only in plain prose — and only ever
        # inside qualified spans like `preset.key` — must still be reported as
        # undocumented for that field.
        synthesized = (
            "身份欄的 key 決定 registry 鍵，範例見 `preset.key` 與 `key 的寫法`。\n"
            "```python\nkey = 1\n```\n"
        )
        self.assertEqual(undocumented_field_names(synthesized, ["key"]), ["key"])
        documented = synthesized + "另有 `key` 成對。\n"
        self.assertEqual(undocumented_field_names(documented, ["key"]), [])


if __name__ == "__main__":
    unittest.main()
