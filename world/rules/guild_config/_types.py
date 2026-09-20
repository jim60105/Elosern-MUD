"""Errors, rank constants, and the frozen config dataclasses.

The load-time rank projection (``RANK_ORDER``) is computed here exactly as the
original single module computed it, before any validation helper.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from world.lore.guild import GUILD_RANK_REGISTRY

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
    """Validated opening-hour and offer rules for one shop.

    ``display_name_zh`` is the owning place's authored room name, populated
    during shop resolution so the player-facing listing can name the shop.
    """

    shop_key: str
    display_name_zh: str
    open_hour: int
    close_hour: int
    restock_hour: int
    offers: tuple[ItemOfferRule, ...]


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
