"""The shared synthetic guild-economy catalog.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every body ships verbatim."""

from __future__ import annotations

from web.browser_support.browser_fixtures_data.fixture_values import (
    SYNTH_GUILD_OFFER_QUEST_KEY,
    SYNTH_SHOP_KEY,
)
from web.browser_support.browser_fixtures_data.grafting import (
    synth_next_entry_rank_key,
)

# ---------------------------------------------------------------------------
# The shared synthetic guild-economy catalog.
#
# The seed process and the managed server must agree on ONE catalog (same
# shop, offers, thresholds, exam profiles): the seed builds DB state against
# it and the server answers the services view from it. Both flagged
# processes call ``install_synth_services_catalog()`` right after the kit
# install — direct process-global assignment, because the shipped
# YAML-validated loader (``load_catalog_into_cache``) cannot resolve t_-only
# registries.
# ---------------------------------------------------------------------------

#: Offered kit items on the synthetic stall (fixed order drives offer rules).
SYNTH_SHOP_OFFERED_ITEM_KEYS = (
    "t_ember_spray",
    "t_huskapple",
    "t_thorn_knife",
    "t_iron_fang",
)


def build_synth_services_catalog():
    """One fully synthetic guild-economy catalog for the harness processes."""
    from world.rules.tests._guild_service_probes import (
        synth_catalog,
        synth_exam_profile,
        synth_exam_profiles,
        synth_merit_thresholds,
        synth_offer_rule,
        synth_shop_config,
        synth_quest_offers,
    )

    # The grafted F entry rank promotes to the kit's second rank; the exam
    # section needs a threshold + profile keyed by THAT rank key, derived
    # from the live registry (never a hardcoded rank key).
    next_rank = synth_next_entry_rank_key()
    # The potion (first offered item) ships below its stock cap so selling
    # the single held unit has headroom: the sell journey sells it out and
    # the row disappears — the shipped story's exact shape.
    potion_rule = synth_offer_rule(
        SYNTH_SHOP_OFFERED_ITEM_KEYS[0], max_stock=20, initial_stock=18
    )
    offers = tuple(
        potion_rule if rule.item_key == SYNTH_SHOP_OFFERED_ITEM_KEYS[0] else rule
        for rule in (synth_offer_rule(key) for key in SYNTH_SHOP_OFFERED_ITEM_KEYS)
    )
    return synth_catalog(
        shop_configs={
            SYNTH_SHOP_KEY: synth_shop_config(
                SYNTH_SHOP_KEY, (), offer_rules=offers
            )
        },
        # The board journeys pin a single-offer board (the fixture's quest),
        # so the harness catalog carries exactly that offer — unlike the
        # unit-probe default of every kit quest.
        quest_offers=tuple(
            offer
            for offer in synth_quest_offers()
            if offer.definition_key == SYNTH_GUILD_OFFER_QUEST_KEY
        ),
        merit_thresholds={**synth_merit_thresholds(), next_rank: 40},
        exam_profiles={
            **synth_exam_profiles(),
            next_rank: synth_exam_profile(next_rank),
        },
    )


def install_synth_services_catalog():
    """Assign the shared catalog process-globally, register offers + clock sources."""
    from world.rules import guild_config
    from world.rules.guild_config import register_catalog_offers

    catalog = build_synth_services_catalog()
    guild_config.CATALOG = catalog
    register_catalog_offers(catalog)
    # The skipped shipped sync normally registers these; both settlement
    # functions resolve exclusively through get_catalog(), so they serve the
    # synthetic shop identically (registration is idempotent).
    from world.rules.guild_economy import _register_clock_sources

    _register_clock_sources()
    return catalog


def install_synth_affinity_config() -> None:
    """Pre-load the affinity rulebook with a registry-resolvable quest key.

    ``world.rules.affinity_config.load_config`` validates every
    ``cap_breaks[].quest_key`` against the live quest-definition registry,
    and the shipped rulebook names the shipped intro quest — unknown under
    the t_-only install, so the first affinity gain would fail closed. The
    harness pre-assigns ``_CONFIG`` from a copy of the shipped rulebook whose
    cap-break quest keys are rewritten to a kit quest; every numeric rule
    (caps, decay, daily limits) stays the shipped rulebook's.
    """
    import tempfile
    from pathlib import Path

    import yaml

    from world.rules import affinity_config

    if affinity_config._CONFIG is not None:
        return
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY
    from world.tests.synthetic_data import SYNTH_QUESTS

    rulebook = Path(affinity_config.__file__).parent / "rulebook" / "affinity.yaml"
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    for entry in raw.get("cap_breaks", []):
        if isinstance(entry, dict) and "quest_key" in entry:
            # Every cap-break quest key collapses onto one kit quest; the
            # validator only checks registry membership, and the kit quests
            # are the only definitions the install carries.
            entry["quest_key"] = next(iter(SYNTH_QUESTS))
    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as handle:
        yaml.safe_dump(raw, handle, allow_unicode=True)
        temp_path = Path(handle.name)
    try:
        affinity_config._CONFIG = affinity_config.load_config(
            path=temp_path, definition_registry=QUEST_DEFINITION_REGISTRY
        )
    finally:
        temp_path.unlink(missing_ok=True)
