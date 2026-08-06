"""Repository contract: the narrative stream stays parse_html-converted.

The narrative markup pipeline's safety argument rests on the portal having
converted and escaped server output before it reaches the client. That
assumption must stay bounded: no project code may send narrative text with
Evennia's ``raw`` or ``client_raw`` output options, which bypass conversion
and escaping. This test scans the project code and fails if any call site sets
either option.

It also asserts the two client-synthesized notices the stock handler inserts
straight into ``onText`` (the connection-close and reconnect messages) contain
no markup characters, so they tokenize to a single inert text token.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENIZER = REPO_ROOT / "web/static/webclient/js/elosern/narrative_markup.js"

CODEDIRS = ("commands", "server", "typeclasses", "web", "world")

_NODE_PROBE = r"""
const fs = require("node:fs");
const Markup = require(process.argv[1]);
const samples = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(samples.map((s) => Markup.tokenize(s))));
"""


class ConvertedStreamBoundContractTest(unittest.TestCase):
    """No project path bypasses parse_html; client notices stay inert."""

    @covers_requirement(
        "webclient-narrative-markup::the-converted-stream-assumption-is-bounded-and-enforced"
    )
    def test_no_project_code_sets_raw_or_client_raw(self):
        # The narrative markup pipeline assumes the portal ran parse_html.
        # Evennia's `send_text` (and `msg(..., options={...})`) accepts a
        # `raw`/`client_raw` output option that bypasses conversion; any
        # project call site that passes either would silently widen the
        # exception. No project code may call `send_text` at all, and no
        # `msg` call may carry the option as a keyword or inside its options
        # mapping.
        offenders: list[str] = []
        for codedir in CODEDIRS:
            root = REPO_ROOT / codedir
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.py")):
                if "/tests/" in "/" + path.as_posix():
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                relative = path.relative_to(REPO_ROOT).as_posix()
                for line_number, line in enumerate(content.splitlines(), 1):
                    if "send_text" in line:
                        offenders.append(f"{relative}:{line_number}: {line.strip()}")
                    if re.search(r"\bmsg\([^)]*\braw\s*=", line):
                        offenders.append(f"{relative}:{line_number}: {line.strip()}")
                    if re.search(r"\bmsg\([^)]*client_raw\s*=", line):
                        offenders.append(f"{relative}:{line_number}: {line.strip()}")
                    if re.search(r"""["']raw["']\s*[:=]""", line) and "options" in line:
                        offenders.append(f"{relative}:{line_number}: {line.strip()}")
                    if re.search(
                        r"""["']client_raw["']\s*[:=]""", line
                    ) and "options" in line:
                        offenders.append(f"{relative}:{line_number}: {line.strip()}")
        self.assertEqual(
            offenders,
            [],
            "project code must never pass raw/client_raw to send_text/msg; "
            "the narrative markup pipeline assumes parse_html conversion",
        )

    @covers_requirement(
        "webclient-narrative-markup::the-converted-stream-assumption-is-bounded-and-enforced"
    )
    def test_client_synthesized_notices_tokenize_to_one_text_token(self):
        notices = [
            "The connection was closed or lost.",
            "Attempting to reconnect...",
        ]
        with __import__("tempfile").TemporaryDirectory() as tmp:
            samples_path = Path(tmp) / "samples.json"
            samples_path.write_text(json.dumps(notices), encoding="utf-8")
            result = subprocess.run(
                [
                    "node",
                    "-e",
                    _NODE_PROBE,
                    str(TOKENIZER),
                    str(samples_path),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(
                result.returncode,
                0,
                "tokenizer subprocess failed:\n" + result.stdout + result.stderr,
            )
        token_lists = json.loads(result.stdout)
        self.assertEqual(len(token_lists), len(notices))
        for notice, tokens in zip(notices, token_lists):
            self.assertEqual(
                len(tokens),
                1,
                f"notice {notice!r} must tokenize to a single text token",
            )
            self.assertEqual(tokens[0]["kind"], "text")
            self.assertNotIn("degraded", tokens[0])


if __name__ == "__main__":
    unittest.main()
