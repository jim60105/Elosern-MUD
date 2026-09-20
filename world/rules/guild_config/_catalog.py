"""The validated catalog snapshot and its registration helper.

The cache variable ``CATALOG`` and the lazy loaders live in the package
``__init__`` (the patch seam); this module carries the snapshot class and the
idempotent offer registration.
"""

from world.rules.guild_offers import GuildQuestOffer

from ._types import ExamProfile, ServiceHostRow, ShopConfig


class GuildCatalog:
    """Validated, immutable snapshot of the fully-joined guild-economy catalog."""

    def __init__(
        self,
        merit_thresholds: dict[str, int],
        exam_profiles: dict[str, ExamProfile],
        shop_configs: dict[str, ShopConfig],
        quest_offers: list[GuildQuestOffer],
        service_hosts: tuple[ServiceHostRow, ...],
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


def register_catalog_offers(catalog: GuildCatalog) -> None:
    """Register every catalog offer idempotently (called by sync_guild_economy)."""
    from world.rules.guild_offers import register_guild_offer

    for offer in catalog.quest_offers:
        register_guild_offer(offer)
