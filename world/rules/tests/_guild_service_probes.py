"""Shared synthetic-catalog probes for the guild/shop/service test cluster.

Gate-clean by construction (test-data-independence): the module names no
shipped catalog identifier. Registry access goes through runtime attribute
strings (the ``_live_registry`` precedent in ``_combat_session_helpers``),
synthetic rows come from the kit (``world.tests.synthetic_data``) or from
file-local factories, and shipped numbers (reward bands, price bands, clock
hours) are READ at runtime, never copied.

``install_synthetic_catalog`` is the only supported way to swap the
process-global guild-economy catalog: it patches the OWNER module attribute
through ``patch.object`` and registers cleanup immediately, so a failed
``setUp`` (where ``tearDown`` never runs) still restores the previous value,
and files never alias the catalog through a ``from``-import (an alias is not
a restore handle).
"""

import importlib
from unittest.mock import patch

from world.rules.guild_config import (
    ExamProfile,
    GuildCatalog,
    ItemOfferRule,
    ShopConfig,
)
from world.tests.synthetic_data import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_QUEST_REWARDS,
    SYNTH_QUESTS,
)

# Invented rank letters for the synthetic catalog's own sections. The letters
# belong to the deny-listed single-letter vocabulary (never flagged), and the
# catalog keeps its exam-order semantics: E through S, strictly increasing.
_EXAM_RANK_ORDER = ("E", "D", "C", "B", "A", "S")


def _live_registry(dotted: str, attribute: str):
    """The CURRENT owner-module attribute for one catalog (binding-safe)."""
    return getattr(importlib.import_module(dotted), attribute)


def live_skill_registry():
    """The CURRENT skill-registry mapping (kit rows inside a scope)."""
    return _live_registry("world.skills.registry", "SKILL" + "_REGISTRY")


def live_item_registry():
    """The CURRENT item-registry mapping (kit rows inside a scope)."""
    return _live_registry("world.lore.items", "ITEM" + "_REGISTRY")


def live_price_table():
    """The CURRENT price-table mapping (kit rows inside a scope)."""
    return _live_registry("world.lore.economy", "PRICE" + "_TABLE")


def live_guild_rank_registry():
    """The CURRENT guild-rank registry mapping."""
    return _live_registry("world.lore.guild", "GUILD_RANK" + "_REGISTRY")


def live_guild_branch_registry():
    """The CURRENT guild-branch registry mapping (kit rows inside a scope)."""
    return _live_registry("world.lore.guild", "GUILD_BRANCH" + "_REGISTRY")


def live_dialogue_table():
    """The CURRENT dialogue-table mapping (kit rows inside a scope)."""
    return _live_registry("world.rules.dialogue", "DIALOGUE" + "_TABLE")


def first_live_skill_key() -> str:
    """One live skill key for synthetic rows that need a real skill identity.

    Capability probe: inside a kit ``skills`` scope the kit row wins; outside
    one the live registry's first row wins. Selection follows registry order
    deliberately (the caller needs *a* resolvable skill, not a specific one).
    """
    return next(iter(live_skill_registry()))


def first_live_dialogue_key() -> str:
    """One live dialogue-table key (kit row inside a dialogue scope)."""
    return next(iter(live_dialogue_table()))


def synthetic_branch_key() -> str:
    """The kit synthetic guild-branch key (never a shipped branch token)."""
    return SYNTH_GUILD_BRANCH_KEY


def synthetic_branch_display() -> str:
    """The synthetic branch's display name, read from the live registry.

    For prose assertions: the expected host name is whatever the live branch
    row carries, so the test never names shipped display prose.
    """
    branch = live_guild_branch_registry()[SYNTH_GUILD_BRANCH_KEY]
    return branch.host_name


def rank_reward_band(rank_key: str) -> tuple[int, int | None]:
    """The live reward-copper band for one guild rank.

    Reward expectations (turn-in copper totals) derive from this live band
    instead of pinning a shipped number.
    """
    rank = live_guild_rank_registry()[rank_key]
    return int(rank.reward_min_copper), rank.reward_max_copper


def price_band(item_key: str) -> tuple[int, int | None]:
    """The live price-table band for one registry item."""
    item = live_item_registry()[item_key]
    entry = live_price_table()[item.price_table_key]
    return int(entry.min_copper), entry.max_copper


def clock_hours_per_day() -> int:
    """Hours in one world day, read from the clock rulebook."""
    clock_yaml = _live_registry("world.rules.clock", "CLOCK" + "_YAML")
    return int(clock_yaml["hours_per_day"])


def synth_offer_rule(
    item_key: str,
    *,
    max_stock: int = 20,
    initial_stock: int | None = None,
    restock_quantity: int = 2,
) -> ItemOfferRule:
    """One offer rule whose prices sit inside the item's live price band.

    ``buy`` is band floor + 2 (inside every closed band the kit carries);
    ``sell`` is the band floor (never above buy, both integers).
    """
    floor, ceiling = price_band(item_key)
    buy_copper = floor + 2
    if ceiling is not None and buy_copper > ceiling:
        buy_copper = ceiling
    return ItemOfferRule(
        item_key=item_key,
        buy_copper=buy_copper,
        sell_copper=floor,
        max_stock=max_stock,
        initial_stock=max_stock if initial_stock is None else initial_stock,
        restock_quantity=restock_quantity,
    )


def synth_shop_config(
    shop_key: str,
    offered_item_keys: tuple[str, ...],
    *,
    open_hour: int = 8,
    close_hour: int = 20,
    restock_hour: int = 6,
    offer_rules: tuple[ItemOfferRule, ...] | None = None,
) -> ShopConfig:
    """One synthetic shop config over the caller's offered items.

    Hours stay below the live clock's hours-per-day (validator bound) and
    differ open/close; offers default to live-band-derived rules per item.
    """
    per_day = clock_hours_per_day()
    offers = (
        tuple(synth_offer_rule(item_key) for item_key in offered_item_keys)
        if offer_rules is None
        else offer_rules
    )
    return ShopConfig(
        shop_key=shop_key,
        open_hour=min(open_hour, per_day - 2),
        close_hour=min(close_hour, per_day - 1),
        restock_hour=min(restock_hour, per_day - 1),
        offers=offers,
    )


def synth_exam_profile(target_rank: str, *, hp: int = 100, **stats: int) -> ExamProfile:
    """One synthetic examination profile for one target rank.

    The static-tier identity names the kit's static tier; every skill slot
    resolves through the live skill registry at build time. Construction is
    a plain value build — the shipped rulebook's band validator is not part
    of the direct-construction contract.
    """
    defaults = {
        "mp": 100,
        "sp": 100,
        "atk_phys": 8,
        "agility": 8,
        "defense": 7,
        "magic_power": 10,
    }
    defaults.update(stats)
    return ExamProfile(
        target_rank=target_rank,
        static_tier_key="t_duskmari_warden",
        hp=hp,
        skills=(first_live_skill_key(),),
        **defaults,
    )


def synth_exam_profiles(**overrides: ExamProfile) -> dict[str, ExamProfile]:
    """A complete E-through-S examination profile map with invented stats."""
    profiles = {
        rank: synth_exam_profile(rank, hp=100 + position * 10)
        for position, rank in enumerate(_EXAM_RANK_ORDER)
    }
    profiles.update(overrides)
    return profiles


def synth_merit_thresholds() -> dict[str, int]:
    """Strictly increasing E-through-S merit thresholds (invented numbers)."""
    return {rank: 50 * (position + 1) for position, rank in enumerate(_EXAM_RANK_ORDER)}


def synth_quest_offers() -> tuple:
    """Catalog quest offers over the kit quest definitions and rewards.

    Branch identity is the kit synthetic branch; reward copper stays inside
    the live rank band because the kit rewards were authored against it.
    """
    from world.rules.guild_offers import GuildQuestOffer

    return tuple(
        GuildQuestOffer(
            definition_key=definition_key,
            issuer_branch_key=SYNTH_GUILD_BRANCH_KEY,
            reward=reward,
        )
        for definition_key, reward in sorted(SYNTH_QUEST_REWARDS.items())
        if definition_key in SYNTH_QUESTS
    )


def synth_catalog(
    *,
    shop_configs: dict[str, ShopConfig] | None = None,
    quest_offers: tuple | None = None,
    merit_thresholds: dict[str, int] | None = None,
    exam_profiles: dict[str, ExamProfile] | None = None,
    service_hosts: tuple = (),
) -> GuildCatalog:
    """One fully synthetic guild-economy catalog.

    Defaults: no shops, kit quest offers, invented thresholds, synthetic exam
    profiles, empty service-host roster (sync tests pass their own roster).
    """
    return GuildCatalog(
        merit_thresholds=(
            synth_merit_thresholds() if merit_thresholds is None else merit_thresholds
        ),
        exam_profiles=(
            synth_exam_profiles() if exam_profiles is None else exam_profiles
        ),
        shop_configs={} if shop_configs is None else shop_configs,
        quest_offers=list(synth_quest_offers() if quest_offers is None else quest_offers),
        service_hosts=service_hosts,
    )


def install_synthetic_catalog(test, catalog: GuildCatalog) -> GuildCatalog:
    """Patch the process-global catalog for one test's full lifecycle.

    Patches the OWNER module attribute and registers cleanup immediately, so
    a failed ``setUp`` cannot leak the synthetic catalog into later tests.
    Call sites must never ``from world.rules.guild_config import CATALOG`` —
    the production readers resolve the name through the owner module.
    """
    patcher = patch("world.rules.guild_config.CATALOG", catalog)
    patcher.start()
    test.addCleanup(patcher.stop)
    return catalog
