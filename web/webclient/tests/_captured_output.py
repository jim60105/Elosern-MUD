"""ANSI normalisation for captured child-process output.

The evidence bridges run the Node toolchain (Vitest, Storybook, the Node
gates) with ``capture_output=True`` and then assert on the captured text.
Vitest colorizes its human reporter whenever its own environment detection
says the runner supports color, so the same command carries SGR escapes on a
CI runner and none on a developer machine; the escapes are presentation, not
content, and every ``Test Files``/``Tests`` count assertion must see the same
text in both places.
"""

from __future__ import annotations

import re
import subprocess

_SGR = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def without_ansi(
    result: subprocess.CompletedProcess[str],
) -> subprocess.CompletedProcess[str]:
    """Return ``result`` with ANSI escape sequences removed from both streams."""
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        _SGR.sub("", result.stdout),
        _SGR.sub("", result.stderr),
    )
