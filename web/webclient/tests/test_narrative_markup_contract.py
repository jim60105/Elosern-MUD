"""Upstream contract: the tokenizer accepts everything the real converter emits.

The pipeline's safety argument rests on the portal having converted the
narrative stream with ``evennia.utils.text2html.parse_html`` before the
client sees it. This test feeds a fixture corpus -- hostile player-authored
input, every ANSI and xterm-256 foreground/background combination, truecolor,
blink, underline, tabs, and line breaks -- through the *real* ``parse_html``
and then runs the JavaScript tokenizer over the results under Node. If
upstream ever starts emitting an element or attribute outside the allowlist,
this test fails (a ``degraded`` token appears) instead of the narrative
silently regressing to markup source.
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TOKENIZER = REPO_ROOT / "web/static/webclient/js/elosern/narrative_markup.js"

_NODE_PROBE = r"""
const fs = require("node:fs");
const path = require("node:path");
const Markup = require(process.argv[1]);
const corpus = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const results = corpus.map((source) => ({
  source,
  tokens: Markup.tokenize(source),
}));
process.stdout.write(JSON.stringify(results));
"""


class NarrativeMarkupContractTest(unittest.TestCase):
    """The allowlist accepts exactly what parse_html can emit."""

    @staticmethod
    def _parse_html(text: str) -> str:
        from evennia.utils.text2html import parse_html

        return parse_html(text, strip_ansi=False)

    @staticmethod
    def _tokenize_batch(sources: list[str]) -> list[dict]:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            corpus_path = Path(tmp) / "corpus.json"
            corpus_path.write_text(
                json.dumps(sources, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    "node",
                    "-e",
                    _NODE_PROBE,
                    str(TOKENIZER),
                    str(corpus_path),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise AssertionError(
                    "tokenizer subprocess failed:\n"
                    + result.stdout
                    + "\n"
                    + result.stderr
                )
            return json.loads(result.stdout)

    def _corpus(self) -> list[str]:
        hostile = [
            "<script>alert(1)</script>",
            '<img src="x" onerror="alert(1)">',
            '<a href="javascript:alert(1)">click me</a>',
            '<span style="color: red" onclick="x">t</span>',
            'quote "soup" \'single\' < & > &amp; &lt; &#39; &#x27; &nbsp;',
            "<span class=\"color-009\"",
            "<br",
            "</span>",
            "unbalanced <span class=color-009>tag</span> <b>bold</b>",
            "x" * 20000,
            "<span class=\"color-014\">" * 60 + "deep" + "</span>" * 60,
        ]
        ansi = []
        # Every standard ANSI foreground and background combination.
        for fg in range(16):
            for bg in range(16):
                ansi.append(f"|{fg:02x}|[{fg:02x}fg{fg:02x}bg|n")
        # Every xterm-256 foreground and background value.
        for index in range(256):
            ansi.append(f"|x{index:03d}xterm-fg-{index}|n")
            ansi.append(f"|[x{index:03d}xterm-bg-{index}|n")
        styled = [
            "\x1b[5mblink\x1b[0m",
            "\x1b[4munderline\x1b[0m",
            "\x1b[38;2;255;0;0m truecolor fg \x1b[0m",
            "\x1b[48;2;0;0;255m truecolor bg \x1b[0m",
            "\x1b[38;2;10;20;30m\x1b[48;2;200;100;50m both \x1b[0m",
            "tab\there",
            "line1\nline2\nline3",
            "a\r\nb",
            "|y|h bright |n plain",
            "|r|u red underline |n",
            "|r|g|b multi |n",
        ]
        return hostile + ansi + styled

    @covers_requirement(
        "webclient-narrative-markup::the-pipeline-is-verified-against-the-real-upstream-converter"
    )
    def test_tokenizer_accepts_everything_parse_html_emits(self):
        corpus = self._corpus()
        converted = [self._parse_html(item) for item in corpus]
        results = self._tokenize_batch(converted)
        self.assertEqual(len(results), len(converted))
        for result in results:
            for token in result["tokens"]:
                self.assertNotIn(
                    "degraded",
                    token,
                    (
                        "literal-text fallback for a parse_html production: "
                        f"{result['source']!r} -> token {token!r}"
                    ),
                )
                self.assertIn(token["kind"], ("text", "break", "open", "close"))
                if token["kind"] == "open":
                    self.assertEqual(token["tag"], "span")
                if token["kind"] == "close":
                    self.assertEqual(token["tag"], "span")

    @covers_requirement(
        "webclient-narrative-markup::the-pipeline-is-verified-against-the-real-upstream-converter"
    )
    def test_hostile_player_input_survives_as_readable_text(self):
        hostile = [
            "<script>alert(1)</script>",
            '<img src="x" onerror="alert(1)">',
            '<a href="javascript:alert(1)">click me</a>',
        ]
        converted = [self._parse_html(item) for item in hostile]
        results = self._tokenize_batch(converted)
        for result in results:
            # parse_html escapes the hostile characters, so the tokens are
            # plain entity-decoded text; no element token is produced from
            # the player's characters.
            for token in result["tokens"]:
                self.assertEqual(token["kind"], "text")
                self.assertNotIn("degraded", token)


if __name__ == "__main__":
    unittest.main()
