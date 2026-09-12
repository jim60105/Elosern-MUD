"""
OMP Evennia test-count runner.

Discovers the same Django/Evennia tests as the configured TEST_RUNNER,
but stops before database setup and test execution.
"""

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.utils.module_loading import import_string


COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__="

_THIS_RUNNER = (
    "omp_evennia_count_runner.CountOnlyRunner"
)

_DEFAULT_RUNNER = (
    "django.test.runner.DiscoverRunner"
)


def _get_base_runner():
    configured = getattr(
        settings,
        "TEST_RUNNER",
        _DEFAULT_RUNNER,
    )

    # Defensive recursion guard in case someone configures this runner
    # as TEST_RUNNER permanently.
    if configured == _THIS_RUNNER:
        return DiscoverRunner

    if isinstance(configured, str):
        return import_string(configured)

    return configured


BaseRunner = _get_base_runner()


class CountOnlyRunner(BaseRunner):
    """
    Set up the normal Evennia/Django test environment and discover the
    suite, but do not create databases or execute tests.
    """

    def run_tests(self, test_labels, **kwargs):
        self.setup_test_environment()

        try:
            suite = self.build_suite(
                test_labels,
                **kwargs,
            )

            count = suite.countTestCases()

            print(
                f"{COUNT_MARKER}{count}",
                flush=True,
            )

            # Django expects run_tests() to return the number of failures.
            # Discovery succeeded and no tests were executed.
            return 0

        finally:
            self.teardown_test_environment()
