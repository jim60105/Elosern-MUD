"""Catalog loader joining the guild-economy rulebook to immutable lore identities (D-1/D-8).

``guild_economy.yaml`` carries the tunable numbers: merit thresholds, exam
opponent profiles, and per-shop price/hour/stock rules. This module validates
every entry against the immutable registries and exposes frozen dataclasses,
so deterministic APIs never duplicate balance constants.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import yaml

from world.lore.economy import PRICE_TABLE
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.races import STATIC_TIER_REGISTRY
from world.lore.shops import SHOP_REGISTRY
from world.rules.guild_offers import (
    GuildOfferError,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.skills.registry import SKILL_REGISTRY

if TYPE_CHECKING:
    from world.rules.profession_config import Profession


class GuildConfigError(ValueError):
    """The guild-economy rulebook violates the immutable-contract load rules."""


RANK_ORDER = tuple(rank.key for rank in sorted(GUILD_RANK_REGISTRY.values(), key=lambda r: r.order))
EXAM_RANKS = ("E", "D", "C", "B", "A", "S")
RANK_TO_TIER = {
    "E": "human_adventurer",
    "D": "human_adventurer",
    "C": "human_elite",
    "B": "human_elite",
    "A": "human_veteran",
    "S": "human_swordmaster",
}


@dataclass(frozen=True)
class ExamProfile:
    """The deterministic opponent used by one target-rank guild examination."""

    target_rank: str
    static_tier_key: str
    hp: int
    mp: int
    sp: int
    atk_phys: int
    agility: int
    defense: int
    magic_power: int
    skills: tuple[str, ...]


@dataclass(frozen=True)
class ItemOfferRule:
    """Exact integer trade and stock rules for one offered item."""

    item_key: str
    buy_copper: int
    sell_copper: int
    max_stock: int
    initial_stock: int
    restock_quantity: int


@dataclass(frozen=True)
class ShopConfig:
    """Validated opening-hour and offer rules for one shop."""

    shop_key: str
    open_hour: int
    close_hour: int
    restock_hour: int
    offers: tuple[ItemOfferRule, ...]


_SERVICE_HOST_REQUIRED_FIELDS = ("name", "title", "profession", "anchor_room", "service_id")
_SERVICE_HOST_KWARG_FIELDS = ("shop_key", "branch_key", "dialogue_key")


@dataclass(frozen=True)
class ServiceHostRow:
    """One declarative service-host roster row (declarative-service-hosts D7).

    ``profession`` is the RESOLVED registry row, not a key: sync executes the
    exact row config validation approved, so a rulebook reload between config
    load and sync can never mix blueprints (the change-2 snapshot decision).
    ``authored_kwargs`` holds the row's flat identity kwargs (``shop_key`` /
    ``branch_key`` / ``dialogue_key``); the shared assembly helper projects
    them per blueprint component.
    """

    name: str
    title: str
    profession: "Profession"
    anchor_room: str
    service_id: str
    authored_kwargs: "Mapping[str, str]"


def _error(message: str) -> GuildConfigError:
    return GuildConfigError(f"guild_economy.yaml: {message}")


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{field} must be a non-empty string")
    return value


def _require_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise _error(f"{field} must be at least {minimum}")
    return value


def load_config() -> dict[str, Any]:
    raw = yaml.safe_load(
        (Path(__file__).parent / "rulebook" / "guild_economy.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    return dict(raw)


def validate_merit_thresholds(raw: Mapping[str, Any]) -> dict[str, int]:
    """Require strictly increasing non-negative E-through-S thresholds."""
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"merit_thresholds missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"merit_thresholds has unknown ranks {sorted(unknown)}")
    values = {
        rank: _require_int(raw[rank], f"merit_thresholds.{rank}", minimum=0)
        for rank in EXAM_RANKS
    }
    for lower_rank, upper_rank in zip(EXAM_RANKS, EXAM_RANKS[1:]):
        if not values[lower_rank] < values[upper_rank]:
            raise _error(
                f"merit_thresholds must be strictly increasing: "
                f"{lower_rank}={values[lower_rank]} is not below "
                f"{upper_rank}={values[upper_rank]}"
            )
    return values


def validate_exam_profiles(raw: Mapping[str, Any]) -> dict[str, ExamProfile]:
    """Validate every target-rank profile against its required lore band."""
    if not isinstance(raw, Mapping):
        raise _error("exam_profiles must be a mapping")
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"exam_profiles missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"exam_profiles has unknown ranks {sorted(unknown)}")

    profiles: dict[str, ExamProfile] = {}
    for rank in EXAM_RANKS:
        entry = raw[rank]
        if not isinstance(entry, Mapping):
            raise _error(f"exam_profiles.{rank} must be a mapping")
        static_tier_key = entry.get("static_tier")
        if static_tier_key != RANK_TO_TIER[rank]:
            raise _error(
                f"exam_profiles.{rank} must use tier {RANK_TO_TIER[rank]!r}, "
                f"got {static_tier_key!r}"
            )
        tier = STATIC_TIER_REGISTRY[static_tier_key]
        if tier.race_key != "human":
            raise _error(f"exam_profiles.{rank} tier must belong to the human race")
        physical = {
            axis: _require_int(
                entry.get(axis), f"exam_profiles.{rank}.{axis}", minimum=0
            )
            for axis in ("atk_phys", "agility", "defense")
        }
        band = tier.band
        band_floor, band_ceiling = band
        for axis, value in physical.items():
            if not band_floor <= value <= (band_ceiling if band_ceiling is not None else value):
                raise _error(
                    f"exam_profiles.{rank}.{axis}={value} is outside tier "
                    f"{static_tier_key!r} band {(band_floor, band_ceiling)}"
                )
        skills = entry.get("skills")
        if not isinstance(skills, list) or not skills:
            raise _error(f"exam_profiles.{rank}.skills must be a non-empty list")
        if any(not isinstance(key, str) or key not in SKILL_REGISTRY for key in skills):
            raise _error(f"exam_profiles.{rank} references an unknown skill key")
        profiles[rank] = ExamProfile(
            target_rank=rank,
            static_tier_key=static_tier_key,
            hp=_require_int(entry.get("hp"), f"exam_profiles.{rank}.hp", minimum=1),
            mp=_require_int(entry.get("mp"), f"exam_profiles.{rank}.mp", minimum=0),
            sp=_require_int(entry.get("sp"), f"exam_profiles.{rank}.sp", minimum=0),
            atk_phys=physical["atk_phys"],
            agility=physical["agility"],
            defense=physical["defense"],
            magic_power=_require_int(
                entry.get("magic_power"), f"exam_profiles.{rank}.magic_power", minimum=0
            ),
            skills=tuple(skills),
        )
    return profiles


def validate_shop_configs(raw: Any) -> dict[str, ShopConfig]:
    """Join YAML shop rules to immutable ShopDefinition/ItemDefinition identities."""
    if not isinstance(raw, list):
        raise _error("shops must be a list")
    known_parents = {definition.merchant_component_key: definition.key for definition in SHOP_REGISTRY.values()}
    configs: dict[str, ShopConfig] = {}
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"shops[{position}] must be a mapping")
        shop_key = entry.get("shop_key")
        if shop_key not in SHOP_REGISTRY:
            raise _error(f"shops[{position}].shop_key {shop_key!r} is unknown")
        if shop_key in configs:
            raise _error(f"duplicate shop_key {shop_key!r} in shops")
        shop = SHOP_REGISTRY[shop_key]
        offered_keys = set(shop.offered_item_keys)
        from world.rules.clock import CLOCK_YAML

        hours_per_day = int(CLOCK_YAML["hours_per_day"])
        open_hour = _require_int(entry.get("open_hour"), f"shops.{shop_key}.open_hour", minimum=0)
        close_hour = _require_int(entry.get("close_hour"), f"shops.{shop_key}.close_hour", minimum=0)
        restock_hour = _require_int(entry.get("restock_hour"), f"shops.{shop_key}.restock_hour", minimum=0)
        for label, hour in (
            ("open_hour", open_hour),
            ("close_hour", close_hour),
            ("restock_hour", restock_hour),
        ):
            if hour >= hours_per_day:
                raise _error(
                    f"shops.{shop_key}.{label}={hour} must be below "
                    f"hours_per_day={hours_per_day}"
                )
        if open_hour == close_hour:
            raise _error(f"shops.{shop_key} open and close hours cannot be equal")
        offers_entry = entry.get("offers")
        if not isinstance(offers_entry, list):
            raise _error(f"shops.{shop_key}.offers must be a list")
        offers: list[ItemOfferRule] = []
        seen_items: set[str] = set()
        for offer_position, offer in enumerate(offers_entry, start=1):
            if not isinstance(offer, Mapping):
                raise _error(f"shops.{shop_key}.offers[{offer_position}] must be a mapping")
            item_key = offer.get("item_key")
            if item_key not in ITEM_REGISTRY:
                raise _error(f"shops.{shop_key}.offers[{offer_position}].item_key {item_key!r} is unknown")
            if item_key not in offered_keys:
                raise _error(
                    f"shops.{shop_key}.offers includes {item_key!r} which is not offered "
                    f"by ShopDefinition {shop_key!r}"
                )
            if item_key in seen_items:
                raise _error(f"duplicate offered item {item_key!r} in shop {shop_key!r}")
            seen_items.add(item_key)
            buy_copper = _require_int(offer.get("buy_copper"), f"shops.{shop_key}.{item_key}.buy_copper", minimum=0)
            sell_copper = _require_int(offer.get("sell_copper"), f"shops.{shop_key}.{item_key}.sell_copper", minimum=0)
            if sell_copper > buy_copper:
                raise _error(
                    f"shops.{shop_key}.{item_key}: sell_copper {sell_copper} exceeds "
                    f"buy_copper {buy_copper}"
                )
            price_entry = PRICE_TABLE.get(ITEM_REGISTRY[item_key].price_table_key)
            if price_entry is None:
                raise _error(f"shops.{shop_key}.{item_key} has no price-table entry")
            band_floor, band_ceiling = price_entry.min_copper, price_entry.max_copper
            if not band_floor <= buy_copper <= (band_ceiling if band_ceiling is not None else buy_copper):
                raise _error(
                    f"shops.{shop_key}.{item_key} buy_copper {buy_copper} is outside "
                    f"price-table band {(band_floor, band_ceiling)}"
                )
            max_stock = _require_int(offer.get("max_stock"), f"shops.{shop_key}.{item_key}.max_stock", minimum=1)
            initial_stock = _require_int(offer.get("initial_stock"), f"shops.{shop_key}.{item_key}.initial_stock", minimum=0)
            if initial_stock > max_stock:
                raise _error(
                    f"shops.{shop_key}.{item_key}: initial_stock {initial_stock} exceeds "
                    f"max_stock {max_stock}"
                )
            restock_quantity = _require_int(
                offer.get("restock_quantity"), f"shops.{shop_key}.{item_key}.restock_quantity", minimum=1
            )
            offers.append(
                ItemOfferRule(
                    item_key=item_key,
                    buy_copper=buy_copper,
                    sell_copper=sell_copper,
                    max_stock=max_stock,
                    initial_stock=initial_stock,
                    restock_quantity=restock_quantity,
                )
            )
        missing = offered_keys - seen_items
        if missing:
            raise _error(
                f"shops.{shop_key} is missing offers for {sorted(missing)}"
            )
        configs[shop_key] = ShopConfig(
            shop_key=shop_key,
            open_hour=open_hour,
            close_hour=close_hour,
            restock_hour=restock_hour,
            offers=tuple(offers),
        )
        known_parents.pop(shop.merchant_component_key, None)
    if known_parents:
        raise _error(
            f"shops is missing rules for {sorted(known_parents.values())}"
        )
    return configs


def validate_service_hosts(raw: Any) -> tuple[ServiceHostRow, ...]:
    """Validate the declarative service-host roster (declarative-service-hosts D7).

    Config load never touches the database: ``anchor_room`` is validated as a
    non-empty tag string only (room existence is a sync-time fact), and the
    profession prerequisite is the YAML-only profession registry. A malformed
    professions rulebook surfaces inside this catalog's named error family
    rather than escaping as ``ProfessionConfigError``.
    """
    from world.rules import profession_config
    from world.rules.profession_assembly import identity_fields

    if not isinstance(raw, list):
        raise _error("service_hosts must be a list")
    rows: list[ServiceHostRow] = []
    seen_service_ids: set[str] = set()
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"service_hosts[{position}] must be a mapping")
        unknown = sorted(set(entry) - set(_SERVICE_HOST_REQUIRED_FIELDS) - set(_SERVICE_HOST_KWARG_FIELDS))
        if unknown:
            raise _error(f"service_hosts[{position}] has unknown field(s) {unknown}")
        fields = {
            name: _require_text(entry.get(name), f"service_hosts[{position}].{name}")
            for name in _SERVICE_HOST_REQUIRED_FIELDS
        }
        service_id = fields["service_id"]
        if service_id in seen_service_ids:
            raise _error(
                f"duplicate service_id {service_id!r} in service_hosts; "
                "one roster row per service anchor"
            )
        seen_service_ids.add(service_id)
        try:
            profession = profession_config.get_profession(fields["profession"])
        except profession_config.ProfessionConfigError as error:
            raise _error(
                f"service_hosts[{position}].profession {fields['profession']!r} "
                f"cannot load: {error}"
            ) from error
        if profession is None:
            raise _error(
                f"service_hosts[{position}].profession {fields['profession']!r} "
                "is not a profession rulebook row"
            )
        authored = {
            name: _require_text(entry[name], f"service_hosts[{position}].{name}")
            for name in _SERVICE_HOST_KWARG_FIELDS
            if name in entry
        }
        # Blueprint coverage: every component's identity fields except the
        # row-level service_id anchor must be authored by the row.
        consumed: set[str] = set()
        for component in profession.components:
            needed = set(identity_fields(component.type_key)) - {"service_id"}
            lacking = sorted(needed - set(authored))
            if lacking:
                raise _error(
                    f"service_hosts[{position}] profession {fields['profession']!r} "
                    f"component {component.type_key!r} needs authored kwargs {lacking}"
                )
            consumed |= needed
        dead = sorted(set(authored) - consumed)
        if dead:
            raise _error(
                f"service_hosts[{position}] authors kwargs {dead} that no component "
                f"of profession {fields['profession']!r} consumes"
            )
        rows.append(
            ServiceHostRow(
                name=fields["name"],
                title=fields["title"],
                profession=profession,
                anchor_room=fields["anchor_room"],
                service_id=service_id,
                authored_kwargs=authored,
            )
        )
    return tuple(rows)


def validate_quest_rewards(raw: Any, definition_registry: Mapping[str, Any]) -> list[GuildQuestOffer]:
    """Validate YAML hand-written rewards into immutable offers.

    ``definition_registry`` is supplied by the caller so catalog loading can run
    before quest synchronization registers definitions without importing state.
    Validation is side-effect free; callers register the returned offers
    explicitly through ``register_catalog_offers``.
    """
    if not isinstance(raw, list):
        raise _error("quest_rewards must be a list")
    offers: list[GuildQuestOffer] = []
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"quest_rewards[{position}] must be a mapping")
        definition_key = entry.get("definition_key")
        if definition_key not in definition_registry:
            raise _error(f"quest_rewards[{position}].definition_key {definition_key!r} is unknown")
        reward_entry = entry.get("reward")
        if not isinstance(reward_entry, Mapping):
            raise _error(f"quest_rewards[{position}].reward must be a mapping")
        copper = _require_int(reward_entry.get("copper"), f"quest_rewards.{definition_key}.copper", minimum=0)
        merit = _require_int(reward_entry.get("merit"), f"quest_rewards.{definition_key}.merit", minimum=0)
        items_entry = reward_entry.get("items")
        if not isinstance(items_entry, list):
            raise _error(f"quest_rewards.{definition_key}.items must be a list")
        quantities: list[ItemQuantity] = []
        seen: set[str] = set()
        for item_position, item in enumerate(items_entry, start=1):
            if not isinstance(item, Mapping):
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}] must be a mapping")
            item_key = item.get("item_key")
            if item_key not in ITEM_REGISTRY:
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}].item_key {item_key!r} is unknown")
            if item_key in seen:
                raise _error(f"quest_rewards.{definition_key} has duplicate item {item_key!r}")
            seen.add(item_key)
            quantity = _require_int(item.get("quantity"), f"quest_rewards.{definition_key}.{item_key}.quantity", minimum=1)
            quantities.append(ItemQuantity(item_key=item_key, quantity=quantity))
        offer = GuildQuestOffer(
            definition_key=definition_key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(copper=copper, items=tuple(quantities), merit=merit),
        )
        # Validate the full offer contract (known branch, rank band, items)
        # without touching the process-global offer registry.
        validate_guild_offer_side_effect_free(offer)
        offers.append(offer)
    return offers


def validate_guild_offer_side_effect_free(offer: GuildQuestOffer) -> None:
    """Run ``register_guild_offer``'s validation without mutating the registry."""
    from world.rules.guild_offers import GuildOfferError, validate_offer

    try:
        validate_offer(offer)
    except GuildOfferError as error:
        raise _error(f"catalog offer {offer.definition_key!r} is invalid: {error}") from error


class GuildCatalog:
    """Validated, immutable snapshot of the fully-joined guild-economy catalog."""

    def __init__(
        self,
        merit_thresholds: dict[str, int],
        exam_profiles: dict[str, ExamProfile],
        shop_configs: dict[str, ShopConfig],
        quest_offers: list[GuildQuestOffer],
        service_hosts: tuple[ServiceHostRow, ...] = (),
    ):
        self.merit_thresholds = {**merit_thresholds}
        self.exam_profiles = {**exam_profiles}
        self.shop_configs = {**shop_configs}
        self.quest_offers = tuple(quest_offers)
        self.service_hosts = tuple(service_hosts)

    @property
    def offer_by_definition(self) -> dict[str, GuildQuestOffer]:
        return {offer.definition_key: offer for offer in self.quest_offers}

    @property
    def host_by_service_id(self) -> dict[str, ServiceHostRow]:
        return {row.service_id: row for row in self.service_hosts}


def load_guild_catalog(definition_registry: Mapping[str, Any]) -> GuildCatalog:
    """Load and validate the complete guild-economy rulebook.

    The quest reward section requires the caller's current definition registry;
    every other section validates against immutable lore registries alone.
    """
    raw = load_config()
    return GuildCatalog(
        merit_thresholds=validate_merit_thresholds(raw["merit_thresholds"]),
        exam_profiles=validate_exam_profiles(raw["exam_profiles"]),
        shop_configs=validate_shop_configs(raw["shops"]),
        quest_offers=validate_quest_rewards(raw["quest_rewards"], definition_registry),
        service_hosts=validate_service_hosts(raw["service_hosts"]),
    )


CATALOG: GuildCatalog | None = None


def get_catalog() -> GuildCatalog:
    """Return the cached guild-economy catalog, loading it on first use.

    Loading is side-effect free: it never mutates the process-global offer
    registry. Startup registers catalog offers explicitly through
    ``register_catalog_offers``.
    """
    global CATALOG
    if CATALOG is None:
        CATALOG = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
    return CATALOG


def load_catalog_into_cache() -> GuildCatalog:
    """Rebuild ``CATALOG`` against the current quest definition registry.

    Called by ``sync_guild_economy`` after quest synchronization has populated
    ``QUEST_DEFINITION_REGISTRY``; catalog offers are then registered by the
    same composition root.
    """
    global CATALOG
    CATALOG = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
    return CATALOG


def register_catalog_offers(catalog: GuildCatalog) -> None:
    """Register every catalog offer idempotently (called by sync_guild_economy)."""
    from world.rules.guild_offers import register_guild_offer

    for offer in catalog.quest_offers:
        register_guild_offer(offer)