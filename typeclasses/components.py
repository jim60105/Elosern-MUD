"""Project-authored service components for guild-economy NPC hosts (D-1/D-9).

Components are capability markers and persistent service-data holders only.
They contain stable service/branch identifiers and the Merchant's persisted
stock state; every registration, quest, trade, examination, wallet, merit,
inventory, and rank mutation delegates to a deterministic-core API.
"""

from evennia.contrib.base_systems.components import Component, DBField


class GuildStaff(Component):
    """Capability marker and branch identity of one guild service host."""

    name = "guild_staff"
    service_id = DBField(default=None)
    branch_key = DBField(default=None)


class GuildExaminer(Component):
    """Capability marker and branch identity of one guild examiner host."""

    name = "guild_examiner"
    service_id = DBField(default=None)
    branch_key = DBField(default=None)


class Merchant(Component):
    """Capability marker, shop identity, and persisted stock state of one merchant.

    ``merchant_stock`` maps offered item keys to the live finite stock quantity
    and ``last_restock_day`` records the last deterministic restock day. Both
    are service data; the economy APIs own every read and write.
    """

    name = "merchant"
    service_id = DBField(default=None)
    shop_key = DBField(default=None)
    merchant_stock = DBField(default=None)
    last_restock_day = DBField(default=None)