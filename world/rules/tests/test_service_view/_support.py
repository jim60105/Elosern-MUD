"""Synthetic service-view fixtures and fakes for the `test_service_view` slices.

Module-level fixtures, helpers, fakes, and the isolation base moved verbatim
from the original flat module (not a collected test module).
"""
import unittest


from types import SimpleNamespace


from unittest.mock import patch


from tools.spec_traceability import covers_requirement


from typeclasses.components import GuildExaminer, GuildStaff, Merchant


from world.lore.items import (
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)


from world.quests.catalog import register_catalog


from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)


from world.quests.runtime import QuestRecord, QuestState, to_storage


from world.quests.tests._fixtures import TEST_ISSUER_KEY, register_catalog_once


from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)


from world.rules.tests._combat_session_helpers import (
    live_item_effect_profiles,
    open_synthetic_scope,
)


from world.rules.tests._guild_service_probes import (
    a_live_monster_tier_key,
    install_synthetic_catalog,
    live_item_registry,
    live_monster_tier_keys,
    price_band,
    rank_reward_band,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
    synthetic_branch_key,
)


from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_SHOPS,
)


# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process.
# Registered at import (no synthetic scope is open yet).
register_catalog_once()


# The services panel is exercised on kit rows only: the guild branch is the
# kit synthetic branch, the store is one synthetic shop config over kit
# items, and every asserted number below is authored by this file.
BRANCH = synthetic_branch_key()


T_SHOP = next(iter(SYNTH_SHOPS))


T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key


T_FANG = SYNTH_ITEMS["t_iron_fang"].key


T_APPLE = SYNTH_ITEMS["t_huskapple"].key


# The unsellable kit row (exercises the sellable filter's negative path).
T_PASS = SYNTH_ITEMS["t_wayfarer_pass"].key


# The kit's slotted weapon: equip-toggle rows need real equipment slots.
T_KNIFE = SYNTH_ITEMS["t_thorn_knife"].key


# F/E ladder letters are production rank-ladder identifiers (never flagged
# tokens); board quests ride them with rewards inside the live rank bands.
BOARD_QUEST = "services_board_quest"


BOARD_QUEST_DISPLAY = "測試看板委託"


E_QUEST = "services_e_quest"


def _buy_copper(item_key: str) -> int:
    """The synthetic offer's buy price (mirrors synth_offer_rule derivation)."""
    floor, ceiling = price_band(item_key)
    buy = floor + 2
    if ceiling is not None and buy > ceiling:
        buy = ceiling
    return buy


def _sell_copper(item_key: str) -> int:
    return price_band(item_key)[0]


def _shop_config():
    """Built inside the scope: offer rules read live price bands."""
    return synth_shop_config(
        T_SHOP,
        (T_SPRAY, T_FANG, T_APPLE),
        offer_rules=(
            synth_offer_rule(T_SPRAY, max_stock=20),
            synth_offer_rule(T_FANG, max_stock=3),
            synth_offer_rule(T_APPLE, max_stock=20),
        ),
    )


from world.rules.service_view import (
    ACTION_ACCEPT,
    ACTION_BUY,
    ACTION_REGISTER,
    ACTION_SELL,
    ServicesViewError,
    build_services_view,
)


TICK_NOON = 12 * 3600


TICK_NIGHT = 3 * 3600  # before 08:00 opening


_REGISTRATION_TRAIT_KEYS = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)


class FakeComponent:
    """One service component fake exposing name, slot, and service fields."""

    def __init__(self, name, **fields):
        self.name = name
        self.slot = name
        for key, value in fields.items():
            setattr(self, key, value)


class FakeComponents:
    def __init__(self, *components):
        self._by_name = {component.name: component for component in components}

    def has(self, name):
        return name in self._by_name

    def get(self, slot):
        return self._by_name.get(slot)


class FakeHost:
    def __init__(self, key, pk, *components, location=None):
        self.key = key
        self.pk = pk
        self.components = FakeComponents(*components)
        self.location = location


class FakeRoom:
    def __init__(self, *contents):
        self.contents = list(contents)


class FakeTraitSurface:
    """Handler-surface double of one gauge trait.

    The shared target resolver's aliveness validator reads ``entity.traits.hp``
    (the same stored-gauge reader every skill cast consults), so an actor
    fake that passes the target-aware item preflight must carry that surface.
    It wraps the very dict the storage accessor reads — no second copy, no
    write surface.
    """

    trait_type = "gauge"

    def __init__(self, data):
        self._data = data


class FakeTraits:
    def __init__(self, hp_data=None):
        if hp_data is not None:
            self.hp = FakeTraitSurface(hp_data)


class FakeAttributes:
    def __init__(self, traits=None):
        self._store = {}
        if traits is not None:
            self._store[("traits", "traits")] = traits

    def get(self, key, default=None, category=None):
        return self._store.get((key, category), default)


def guild_staff(**fields):
    return FakeComponent(GuildStaff.name, branch_key=BRANCH, **fields)


def guild_examiner(**fields):
    return FakeComponent(GuildExaminer.name, branch_key=BRANCH, **fields)


def merchant(**fields):
    fields.setdefault("shop_key", T_SHOP)
    fields.setdefault(
        "merchant_stock",
        {T_APPLE: 20, T_SPRAY: 3, T_FANG: 1},
    )
    return FakeComponent(Merchant.name, **fields)


def actor(
    *,
    pk=1,
    key="player",
    location=None,
    wallet=1000,
    inventory=None,
    quest_log=None,
    registration=None,
    claims=None,
    equipment=None,
    merit=0,
    guild_rank=None,
    hp_current=None,
    hp_maximum=100,
):
    traits = {
        "guild_merit": {
            "base": merit,
            "current": merit,
            "min": 0,
            "max": None,
            "trait_type": "counter",
        }
    }
    if hp_current is not None:
        traits["hp"] = {
            "base": hp_maximum,
            "mod": 0,
            "mult": 1,
            "current": hp_current,
            "trait_type": "gauge",
        }
    return SimpleNamespace(
        pk=pk,
        key=key,
        location=location,
        guild_rank=guild_rank,
        traits=FakeTraits(traits.get("hp")),
        attributes=FakeAttributes(traits=traits),
        db=SimpleNamespace(
            wallet=wallet,
            inventory=list(inventory or []),
            quest_log=list(quest_log or []),
            guild_registration=registration,
            guild_reward_claims=list(claims or []),
            equipment=equipment,
            active_combat=None,
            disguised_stats=None,
        ),
    )


def registration(**overrides):
    record = {
        "branch_key": BRANCH,
        "registered_tick": 0,
        "displayed_stats": {key: 0 for key in _REGISTRATION_TRAIT_KEYS},
    }
    record.update(overrides)
    return record


def quest_record(quest_id=None, state=QuestState.IN_PROGRESS, progress=0):
    record = QuestRecord(
        quest_id=quest_id or f"{BOARD_QUEST}:1",
        definition_key=BOARD_QUEST,
        issuer_key=TEST_ISSUER_KEY,
        state=state,
        stage_index=0,
        stage_progress=progress,
        deadline_tick=None,
        accepted_tick=0,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason=None if state is not QuestState.FAILED else "abandoned",
    )
    return to_storage(record)


class ServiceRegistryIsolation(unittest.TestCase):
    def setUp(self):
        # Scope before construction: shop/item/tier identities resolve against
        # kit rows. The rank ladder stays shipped so the F→E→S progression
        # asserted below is the real production ladder.
        open_synthetic_scope(
            self, "items", "prices", "shops", "monster_tiers", "guild_branches"
        )
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: _shop_config()})
        )
        # Two invented board quests (F and E ladder ranks) with rewards inside
        # the live rank bands; the F quest is this suite's default log row.
        self.board_reward = QuestReward(
            copper=rank_reward_band("F")[0],
            items=(ItemQuantity(T_SPRAY, 2),),
            merit=25,
        )
        register_quest_definition(
            QuestDefinition(
                key=BOARD_QUEST,
                display_name=BOARD_QUEST_DISPLAY,
                quest_type=QuestType.DEFEAT,
                rank="F",
                stages=(
                    QuestStage(
                        index=0,
                        objective=QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=2,
                            monster_tier=a_live_monster_tier_key(),
                        ),
                    ),
                ),
                deadline_hours=None,
            )
        )
        register_guild_offer(
            GuildQuestOffer(
                definition_key=BOARD_QUEST,
                issuer_branch_key=BRANCH,
                reward=self.board_reward,
            )
        )

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        super().tearDown()


if __name__ == "__main__":
    unittest.main()


