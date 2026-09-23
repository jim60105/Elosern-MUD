"""Repository-wide regression for scripts/fetch-translate-model.sh's volume
resolution (add-translate-model-download-policy D7 / task 4.1).

`podman compose` project-prefixes named volumes, so the printed seeding command
must reference the volume the server actually reads, and a failing `podman
volume ls` must be treated as no match — never an error. These contracts live
in a bash function under `set -euo pipefail`, so the test extracts the function
verbatim from the script and drives it against stub `podman` executables on
PATH, asserting the four observable resolution branches and the exit-status
invariance of a failing probe. Pure subprocess; no DB, no network, no Evennia.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "fetch-translate-model.sh"


def _extract_resolver() -> str:
    """Return the resolver function body from the script, verbatim."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    start = source.index("resolve_translate_volume()")
    # The function ends at the first closing brace at column zero after start.
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def _run_scenario(stub_podman: str | None, project: str | None = None) -> str:
    """Run the resolver with a stub podman (or none) and print the outcome."""
    with tempfile.TemporaryDirectory() as stubdir:
        extra = ""
        if stub_podman is not None:
            podman = Path(stubdir) / "podman"
            podman.write_text(stub_podman, encoding="utf-8")
            podman.chmod(0o755)
            extra = f"export PATH={stubdir}:$PATH"
        else:
            # No podman anywhere on PATH — the empty dir shadows nothing and
            # the host's /usr/bin (which may carry a real podman) stays out.
            extra = f"export PATH={stubdir}"
        command = "\n".join(
            [
                "set -euo pipefail",
                _extract_resolver(),
                "TRANSLATE_VOLUME=''",
                "TRANSLATE_VOLUME_RESOLVED=0",
                extra,
                f"export COMPOSE_PROJECT_NAME={project or ''}",
                "resolve_translate_volume",
                "printf 'volume=%s\\nresolved=%s\\n' "
                '"$TRANSLATE_VOLUME" "$TRANSLATE_VOLUME_RESOLVED"',
            ]
        )
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"resolver run failed: {result.stderr or result.stdout}"
            )
        return result.stdout


class FetchTranslateScriptResolverTests(unittest.TestCase):
    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_project_prefixed_volume_is_resolved(self):
        stub = "#!/usr/bin/env bash\nprintf 'mud_evennia-translate\\nunrelated\\n'\n"
        out = _run_scenario(stub)
        self.assertIn("volume=mud_evennia-translate\nresolved=1", out)

    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_exact_unprefixed_name_wins_over_scan(self):
        # Even with a project-prefixed candidate present, the exact name is
        # tried first (design D7's candidate order).
        stub = (
            "#!/usr/bin/env bash\n"
            "printf 'mud_evennia-translate\\nevennia-translate\\n'\n"
        )
        out = _run_scenario(stub)
        self.assertIn("volume=evennia-translate\nresolved=1", out)

    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_suffix_scan_matches_a_custom_project_prefixed_volume(self):
        stub = "#!/usr/bin/env bash\nprintf 'emu_evennia-translate\\n'\n"
        out = _run_scenario(stub, project="emu")
        self.assertIn("volume=emu_evennia-translate\nresolved=1", out)

    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_a_failing_podman_is_no_match_never_an_error(self):
        # The pipefail contract: a failing `podman volume ls` yields no
        # candidates, falls back to the annotated project-prefixed default,
        # and does not abort the script (set -euo pipefail stays satisfied).
        stub = "#!/usr/bin/env bash\nexit 1\n"
        out = _run_scenario(stub)
        self.assertIn("volume=mud_evennia-translate\nresolved=0", out)

    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_absent_podman_falls_back_to_the_annotated_default(self):
        stub = None
        out = _run_scenario(stub)
        self.assertIn("volume=mud_evennia-translate\nresolved=0", out)

    @covers_requirement(
        "art-prompt-translation::the-operator-seeding-helper-names-the-volume-compose-actually-created"
    )
    def test_custom_project_name_prefixes_the_fallback(self):
        stub = None
        out = _run_scenario(stub, project="other")
        self.assertIn("volume=other_evennia-translate\nresolved=0", out)


if __name__ == "__main__":
    unittest.main()