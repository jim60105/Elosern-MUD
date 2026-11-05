"""Settings-primed unittest driver for the browser shards.

The CI browser shard command used to run ``coverage run -m unittest <labels>``,
which leaves the driver process with no Django settings. Every browser test
module imports cleanly without settings, but a growing number of journeys
perform function-local imports of rules-chain modules during the test body
(``world.tests.synthetic_data`` via the boot-mode fixture vocabulary,
``world.lore.names`` via the corpus validator, ``world.maps.wilderness_provider``
via the gate-cell probe). Those modules reach Evennia contrib code, which reads
``django.conf.settings`` at import time — so the journey crashes with
``ImproperlyConfigured`` the moment it touches the shipped-mode branch.

The harness's own precedents solve this by priming the process before any test
code runs: ``seed.main()`` sets ``DJANGO_SETTINGS_MODULE`` to the browser
settings, calls ``django.setup()``, then ``evennia._init()``. This driver does
exactly the same and hands over to ``unittest.main`` unchanged, so the shard
labels (modules, classes, methods) parse identically to ``python -m unittest``.

It also reports where a process list spends its time. A shard's budget is the
pair of process lists it runs concurrently, and ``unittest``'s own
``durations`` table times only the method interval (``setUp`` through
``doCleanups``): class and module fixtures run in the suite around it, and a
browser class boots its shared runtime in ``setUpClass``. The runner installed
here therefore prints, after the run, one line per test with the method time
**and** the boundary gap before it (previous ``stopTest`` to this
``startTest``, which carries the previous class's ``tearDownClass`` and this
class's ``setUpClass``), plus the run and process totals. The table is
diagnostic output only; it gates nothing, and every label, assertion and
timeout stays as it was.

It lives beside the harness rather than in ``web.tests.browser.__init__``
because the Evennia launcher's server process also imports the package through
the ``server/conf/browser_settings.py`` shim: a settings module must never
trigger ``django.setup()`` itself.

Usage (same argv tail as ``python -m unittest``)::

    uv run --locked coverage run -m web.tests.browser.unittest_driver <labels...>
"""

import os
import sys
import time
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings")

import django  # noqa: E402

django.setup()

import evennia  # noqa: E402

evennia._init()

#: Taken before any interpreter setup above, so the reported process total
#: includes the settings/Evennia priming that precedes the test run.
_PROCESS_STARTED = time.perf_counter()


class ShardTimingResult(unittest.TextTestResult):
    """Text result that prints method and fixture-boundary times per test."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_started = time.perf_counter()
        self._previous_end: float | None = None
        self._test_started = 0.0
        self._boundary = 0.0
        self._rows: list[tuple[str, float, float]] = []

    def startTest(self, test):
        super().startTest(test)
        now = time.perf_counter()
        self._boundary = 0.0 if self._previous_end is None else now - self._previous_end
        self._test_started = now

    def stopTest(self, test):
        super().stopTest(test)
        now = time.perf_counter()
        self._rows.append((test.id(), now - self._test_started, self._boundary))
        self._previous_end = now

    def stopTestRun(self):
        super().stopTestRun()
        run_seconds = time.perf_counter() - self._run_started
        method_seconds = sum(method for _, method, _ in self._rows)
        boundary_seconds = sum(boundary for _, _, boundary in self._rows)
        stream = self.stream
        stream.writeln(
            f"browser timing: {len(self._rows)} tests, method {method_seconds:.3f}s, "
            f"boundary {boundary_seconds:.3f}s, run {run_seconds:.3f}s, "
            f"process {time.perf_counter() - _PROCESS_STARTED:.3f}s"
        )
        for label, method, boundary in self._rows:
            stream.writeln(f"browser timing:   method {method:8.3f}s boundary {boundary:8.3f}s  {label}")
        stream.flush()


def main() -> None:
    # The shard's evidence file is a contracted artifact, not a side effect of
    # carrying an annotated test: a process list whose journeys carry no
    # requirement annotation still owes the workflow its (empty) file. The
    # decorator appends one record per passing annotated test; this only
    # guarantees the file exists so the shard's merge step never reports a
    # missing artifact for a successful run.
    evidence = os.environ.get("OPENSPEC_TEST_EVIDENCE")
    if evidence:
        open(evidence, "a", encoding="utf-8").close()
    runner = unittest.TextTestRunner(
        stream=sys.stderr,
        verbosity=1,
        resultclass=ShardTimingResult,
        durations=0,
    )
    unittest.main(module=None, argv=[sys.argv[0], *sys.argv[1:]], testRunner=runner, exit=True)


if __name__ == "__main__":
    main()