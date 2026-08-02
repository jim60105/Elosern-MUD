"""Re-export shim for ``evennia --settings browser_settings``.

Evennia's launcher resolves ``--settings <name>`` only under ``server.conf``,
so this module forwards to the real browser-test settings module living with
the browser harness. It contains no settings of its own.
"""

from web.tests.browser.browser_settings import *  # noqa: F401, F403
