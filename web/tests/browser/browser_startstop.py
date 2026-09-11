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
    # The status-display coverage table validates buff/rule keys against the
    # live catalogs at import; importing it against shipped data keeps the
    # presentation registry buildable under the install (the kit's own
    # condition rows are grafted in afterwards).
    "world.rules.status_display",
    "world.quests.bootstrap",
    # The monster-population model binds the shipped capital entry and its
    # immutable shipped-key region tables at import; importing it here keeps
    # the module loadable under the install, and the terrain graft rebinds
    # those tables to live kit rows afterwards.
    "world.maps.wilderness_population",
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

    # Production's register_adventurer seam hardcodes the "F" entry rank; the
    # server registers/accepts guild offers at runtime, so graft the harness
    # row into the live registry right after the install too.
    from web.browser_support.browser_fixtures_data import (
        graft_synth_entry_rank,
        graft_synth_status_display,
    )

    graft_synth_entry_rank()
    # The creation descriptor derives one affinity picker per LIVE registry
    # race while the shipped race-bound mapping knows only the shipped races;
    # graft one borrowed bound per kit race so the custom form renders.
    from web.browser_support.browser_fixtures_data import graft_synth_affinity_bounds

    graft_synth_affinity_bounds()
    # The status presenter resolves every displayable condition code through
    # the import-built coverage table (shipped rows, via the pre-install
    # import seam); the kit's own buff rows get authored labels grafted in.
    graft_synth_status_display()
    # Production's coordinate terrain partition returns shipped region keys
    # that the t_-only registry cannot answer — every wilderness room
    # activation KeyErrors at ``_region_display``/population planning. Graft
    # one kit-authored row per partition key and point the population tables
    # at a live threat tier.
    from web.browser_support.browser_fixtures_data import graft_synth_wilderness_terrain

    graft_synth_wilderness_terrain()

    # The shipped guild-catalog YAML cannot resolve against t_-only
    # registries, so the server installs the shared harness catalog directly
    # (same builder as the seed process) and registers its board offers —
    # the services view and runtime accepts answer from this catalog.
    from web.browser_support.browser_fixtures_data import (
        install_synth_affinity_config,
        install_synth_services_catalog,
    )

    install_synth_services_catalog()

    # The affinity rulebook validates its cap-break quest keys against the
    # quest registry; pre-load it against a kit-quest copy so the first
    # affinity gain does not fail closed on the shipped intro quest key.
    install_synth_affinity_config()


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
    # The shipped guild-catalog YAML cannot resolve against t_-only
    # registries, and its sync would reload the shipped YAML over the
    # harness catalog installed above — so under the install the step is
    # skipped outright (the harness catalog and its offers are already
    # registered by _install_synthetic_catalogs_if_flagged; the seed process
    # skips the same step in its own fixture). The world clock's shop-hours
    # and caravan sources come from the installed catalog instead.
    original = module._startup_step

    def _synth_startup_step(name, run, **kwargs):
        if name == "sync_guild_economy":
            return None
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
