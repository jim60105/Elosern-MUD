"""Browser-harness startup-hook wrapper (add-test-synthetic-data-kit, D2b).

Installed as ``AT_SERVER_STARTSTOP_MODULE`` by ``browser_settings`` only when
``ELOSERN_BROWSER_SYNTH_CATALOGS=1``. The synthetic catalogs cannot be applied
while settings load: ``world.tests.synthetic_data`` imports Evennia contrib
code that captures the logger at import time, and the logger only exists after
``evennia._init()``. The first hook Evennia calls is ``at_server_init``, which
runs after that bootstrap and before every startup mirroring step — installing
there means the managed server's ``sync_all``/grid/clock steps all see the
synthetic catalogs, exactly like the ``ART_SD_CLIENT`` fake-client seam. Every
other hook delegates unchanged to the production startstop module.
"""

import os

_PRODUCTION_MODULE = "server.conf.at_server_startstop"

# Rule modules that cross-validate shipped YAML rulebooks against catalog
# registries AT IMPORT TIME (world.rules.equipment_effects binds the shipped
# equipment rulebook to the item registry's equipment projection). Their
# import-time validation must run against shipped data, so they are imported
# here before the install swaps in the t_-only catalogs; the frozen YAML
# rulebooks then stay shipped prose — the documented D1 seam class. A
# synthetic-compatible equipment rulebook belongs to
# migrate-browser-tests-off-real-data, not to the kit.
_IMPORT_BEFORE_INSTALL = (
    "world.rules.equipment_effects",
    "world.rules.combat_modifiers",
    "world.quests.bootstrap",
)
# Module-level bootstrap content validated against catalog registries at
# RUNTIME (sync_quest_runtime registers the hand-written intro quest, whose
# shipped keys the t_-only registries reject). Under the install the boot
# catalog is redirected to the kit's synthetic quests — the same harness
# wiring class as the seed's preset base character; shipped-data quest
# journeys resume when migrate-browser-tests-off-real-data supplies them.


def _install_synthetic_catalogs_if_flagged() -> None:
    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") != "1":
        return
    import importlib

    for dotted in _IMPORT_BEFORE_INSTALL:
        importlib.import_module(dotted)
    from world.tests.synthetic_data import install_synthetic_catalogs

    install_synthetic_catalogs()

    import world.quests.catalog as _quest_catalog
    from world.tests.synthetic_data import SYNTH_QUESTS

    _quest_catalog.QUEST_CATALOG = tuple(SYNTH_QUESTS.values())


def _production(name):
    import importlib

    module = importlib.import_module(_PRODUCTION_MODULE)
    hook = getattr(module, name, None)
    return hook


def at_server_init():
    _install_synthetic_catalogs_if_flagged()
    hook = _production("at_server_init")
    if hook is not None:
        return hook()


def at_server_start():
    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    _install_synthetic_catalogs_if_flagged()
    import importlib

    module = importlib.import_module(_PRODUCTION_MODULE)
    hook = getattr(module, "at_server_start", None)
    if hook is None:
        return None
    if not synth:
        return hook()
    # Known shipped-content bootstrap step: the guild-catalog YAML and the
    # production rank->tier map hardcode shipped lore keys, so
    # sync_guild_economy cannot resolve against t_-only registries; a
    # synthetic guild catalog is migrate-browser-tests-off-real-data's scope.
    # Degrade it through production's own tolerated-step machinery (exactly
    # one structured startup_step_degraded event) instead of aborting the
    # boot that every other step completes under the install.
    original = module._startup_step

    def _synth_startup_step(name, run, **kwargs):
        if name == "sync_guild_economy":
            return original(name, run, fail_loud=False, tolerant_on=(Exception,))
        return original(name, run, **kwargs)

    module._startup_step = _synth_startup_step
    try:
        return hook()
    finally:
        module._startup_step = original


def at_server_stop():
    hook = _production("at_server_stop")
    if hook is not None:
        return hook()


def at_server_reload_start():
    hook = _production("at_server_reload_start")
    if hook is not None:
        return hook()


def at_server_reload_stop():
    hook = _production("at_server_reload_stop")
    if hook is not None:
        return hook()


def at_server_cold_start():
    hook = _production("at_server_cold_start")
    if hook is not None:
        return hook()


def at_server_cold_stop():
    hook = _production("at_server_cold_stop")
    if hook is not None:
        return hook()
