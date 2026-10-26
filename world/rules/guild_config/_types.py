"""Errors, rank constants, and the frozen config dataclasses.

The load-time rank projection (``RANK_ORDER``) is computed here exactly as the
original single module computed it, before any validation helper.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from world.lore.guild import GUILD_RANK_REGISTRY

if TYPE_CHECKING:
    from world.rules.npc_capabilities import CapabilityDeclaration


class GuildConfigError(ValueError):
    """The guild-economy rulebook violates the immutable-contract load rules."""


RANK_ORDER = tuple(rank.key for rank in sorted(GUILD_RANK_REGISTRY.values(), key=lambda r: r.order))
EXAM_RANKS = ("E", "D", "C", "B", "A", "S")


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
    """One service-host roster row derived from its place declaration.

    ``components`` holds the place's validated, frozen capability
    declarations — the complete set the sync assembles, with no blueprint
    behind it. ``spawn_room`` is the interior room tag the host is created in
    (and the anchor every place-bound component declares).

    ``host_key`` is the host's canonical stable authored identity: the place's
    ``host_profile_key``, which is also this row's ``profile_key``. It is the
    same canonical person identity the live NPC records as its profile
    provenance, so reuse never depends on a capability, a component order, a
    display name, a location or a component-level service identifier.
    """

    name: str
    spawn_room: str
    components: "tuple[CapabilityDeclaration, ...]"
    profile_key: str
    host_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.host_key, str) or not self.host_key.strip():
            raise GuildConfigError("guild_economy.yaml: host_key must be a non-empty string")
        if self.host_key != self.profile_key:
            raise GuildConfigError(
                f"guild_economy.yaml: host_key {self.host_key!r} must equal "
                f"profile_key {self.profile_key!r}; the canonical host identity "
                "is the authored profile key"
            )

    def component_types(self) -> tuple[str, ...]:
        """The declared capability type keys in declaration order."""
        return tuple(component.type for component in self.components)
