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

It lives beside the harness rather than in ``web.tests.browser.__init__``
because the Evennia launcher's server process also imports the package through
the ``server/conf/browser_settings.py`` shim: a settings module must never
trigger ``django.setup()`` itself.

Usage (same argv tail as ``python -m unittest``)::

    uv run --locked coverage run -m web.tests.browser.unittest_driver <labels...>
"""

import os
import sys
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings")

import django  # noqa: E402

django.setup()

import evennia  # noqa: E402

evennia._init()


def main() -> None:
    unittest.main(module=None, argv=[sys.argv[0], *sys.argv[1:]], exit=True)


if __name__ == "__main__":
    main()
