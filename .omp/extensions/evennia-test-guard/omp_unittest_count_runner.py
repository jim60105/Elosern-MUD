"""
OMP unittest-count driver.

Drop-in stand-in for ``python -m web.tests.browser.unittest_driver`` and
``python -m unittest`` that discovers the selected tests and prints the
discovered count as a machine-readable marker, then exits WITHOUT running
anything. Discovery mirrors the real drivers: prime Django/Evennia settings
first (function-local imports in browser journeys reach django.conf.settings
at import time), then use the stdlib unittest loader.

Any argv that the real runner would accept is accepted here; labels that
cannot be loaded are counted as one failure case each (fail closed: a
miscount must never under-count past the guard's maximum).
"""

import os
import sys
import unittest

COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__="

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "web.tests.browser.browser_settings",
)

import django  # noqa: E402

django.setup()

import evennia  # noqa: E402

evennia._init()

def _parse_argv(argv):
    """Split runner argv into (discover-form, verbosity, labels)."""
    discover = False
    start_dir = "."
    top_level = "."
    pattern = "test*.py"
    labels = []

    index = 0
    while index < len(argv):
        token = argv[index]

        if token == "discover":
            discover = True
            index += 1
            continue

        if token in ("-t", "--top-level-directory"):
            index += 1
            top_level = argv[index]
        elif token.startswith("--top-level-directory="):
            top_level = token.split("=", 1)[1]
        elif token in ("-s", "--start-directory"):
            index += 1
            start_dir = argv[index]
        elif token.startswith("--start-directory="):
            start_dir = token.split("=", 1)[1]
        elif token in ("-p", "--pattern"):
            index += 1
            pattern = argv[index]
        elif token.startswith("--pattern="):
            pattern = token.split("=", 1)[1]
        elif token.startswith("-"):
            # Remaining unittest flags (-v, -q, -c/--catch, -b/--buffer,
            # -f/--failfast, --locals, ...) are value-less.
            pass
        else:
            labels.append(token)

        index += 1

    return discover, start_dir, top_level, pattern, labels


def main() -> int:
    argv = sys.argv[1:]
    discover, start_dir, top_level, pattern, labels = _parse_argv(argv)

    loader = unittest.TestLoader()

    if discover:
        suite = loader.discover(
            start_dir=start_dir,
            pattern=pattern,
            top_level_dir=top_level,
        )
        print(f"{COUNT_MARKER}{suite.countTestCases()}", flush=True)
        return 0

    resolved = []

    for label in labels:
        try:
            resolved.append(loader.loadTestsFromNames([label]))
        except (ImportError, AttributeError, ValueError):
            # The real runner would report one error for this label.
            resolved.append(_ErrorLabelCase(label))

    if not resolved:
        # Bare invocation mirrors `python -m unittest`: discover from cwd.
        suite = loader.discover(start_dir=".", pattern="test*.py")
    else:
        suite = unittest.TestSuite(resolved)

    print(f"{COUNT_MARKER}{suite.countTestCases()}", flush=True)
    return 0


class _ErrorLabelCase(unittest.TestCase):
    """Placeholder counting an unloadable label as one test case."""

    def __init__(self, label):
        super().__init__("runTest")
        self._label = label

    def runTest(self):  # pragma: no cover - never executed
        raise RuntimeError(self._label)


if __name__ == "__main__":
    sys.exit(main())
