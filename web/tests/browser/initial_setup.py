"""Complete Evennia's one-time initial setup for a managed browser runtime.

``evennia start`` runs Evennia's initial setup on a database that has never
recorded ``last_initial_setup_step`` and ends that sequence by asking the
portal to restart the server in 'reset' mode
(``evennia/server/initial_setup.py``). The portal spawns the replacement
server as soon as the outgoing server's AMP connection drops, which is before
that process has closed its listening sockets, so on a packed runner the
replacement dies with ``CannotListenError: ... Address already in use`` on the
runtime's internal webserver port. The portal is then left proxying to
nothing: the harness's readiness poll burns its whole budget and the
port-conflict retry recreates the runtime, whose fresh database runs the same
setup and the same restart again (run 44121602063 lost five browser shards
this way, each after ~800 s of retries).

The harness runs this module between the deterministic seed and the managed
server's boot, so the database holds exactly the state the restarted server
would read: the runtime's own server boot is the only start that binds a port.
Every setup step (objects, at_initial_setup hook, collectstatic) still runs,
in this process, and the sequence's own ``last_initial_setup_step`` marker
makes the booted server skip it.

``TEST_ENVIRONMENT`` suppresses ``reset_server``, the sequence's last step,
which both writes ``server_epoch`` and asks the portal for the restart. The
epoch this module writes itself, in the same place in the sequence, so the
only behaviour given up is the restart.

Run as a one-off process against a migrated and seeded browser-test database:

    ELOSERN_BROWSER_* uv run --locked python -m web.tests.browser.initial_setup

Importing this module has no side effects; all work happens in ``main()``.
"""

import os
import time


def main() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings"
    )

    import django

    django.setup()

    import evennia

    evennia._init()

    from django.conf import settings

    from evennia.server import initial_setup
    from evennia.server.models import ServerConfig

    last_step = ServerConfig.objects.conf("last_initial_setup_step")
    if last_step in ("done", -1):
        return
    # ``reset_server`` is the sequence's last step: it writes ``server_epoch``
    # and asks the portal to restart the server the runtime has not booted
    # yet. Stand-in mode skips the restart request; the epoch is written below
    # instead, and ``handle_setup`` still records 'done'.
    settings.TEST_ENVIRONMENT = True
    initial_setup.handle_setup(last_step)
    ServerConfig.objects.conf("server_epoch", time.time())


if __name__ == "__main__":
    main()
