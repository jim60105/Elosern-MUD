"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: ServiceHostRosterTests.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest import mock
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.shops import SHOP_REGISTRY
from world.lore.settlements.shops import validate_registry_identity_uniqueness
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import load_guild_catalog
from world.rules.guild_config import validate_service_hosts
import unittest
from ._support import (
    CatalogRegistryIsolation,
    raw_rulebook,
)


class ServiceHostRosterTests(CatalogRegistryIsolation):
    """Derived service-host roster: places yield rows; rejections are unchanged (design §3.2)."""

    # The rows the hand-authored service_hosts roster shipped before this
    # change removed it. The derived roster must reproduce them field for
    # field — that is the change's behaviour-neutrality gate.
    FORMER_YAML_ROWS = (
        {
            "name": "葛里安·衛登",
            "title": "阿爾托利亞分會會長",
            "profession": "guild_staff",
            "anchor_room": "altoria_guild_hall",
            "service_id": "altoria_guild_master",
            "branch_key": "guild_branch_altoria",
            "dialogue_key": "guild_staff",
        },
        {
            "name": "瑪爾特·金秤",
            "title": "阿爾托利亞雜貨商店老闆",
            "profession": "merchant",
            "anchor_room": "altoria_general_store",
            "service_id": "altoria_merchant",
            "shop_key": "altoria_general_store",
        },
    )

    def _assert_reproduces_former_rows(self, rows):
        self.assertEqual(
            [row.service_id for row in rows],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
                "ciaran_hailiel", "ciaran_lareneth",
                "ciaran_valwyn", "ciaran_vethiel",
            ],
        )
        for row, former in zip(rows, self.FORMER_YAML_ROWS):
            self.assertEqual(row.name, former["name"])
            self.assertEqual(row.title, former["title"])
            self.assertEqual(row.profession.key, former["profession"])
            self.assertEqual(row.anchor_room, former["anchor_room"])
            self.assertEqual(row.service_id, former["service_id"])
            expected_kwargs = {
                key: value
                for key, value in former.items()
                if key not in ("name", "title", "profession", "anchor_room", "service_id")
            }
            self.assertEqual(row.authored_kwargs, expected_kwargs)

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_shipped_roster_reproduces_the_removed_yaml_rows_exactly(self):
        rows = validate_service_hosts()
        self._assert_reproduces_former_rows(rows)
        guild, merchant = rows[0], rows[1]
        branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        store = SHOP_REGISTRY["altoria_general_store"]
        # The identity join that used to be hand-synchronized across four
        # files still holds: the guild host's authored identity is the guild
        # branch's, and the merchant host's is the derived shop's.
        self.assertEqual((guild.name, guild.title), (branch.host_name, branch.host_title))
        self.assertEqual((merchant.name, merchant.title), (store.host_name, store.host_title))

    def test_catalog_exposes_the_roster(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.service_id for row in catalog.service_hosts],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
                "ciaran_hailiel", "ciaran_lareneth",
                "ciaran_valwyn", "ciaran_vethiel",
            ],
        )
        self.assertEqual(
            set(catalog.host_by_service_id),
            {
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
                "ciaran_hailiel", "ciaran_lareneth",
                "ciaran_valwyn", "ciaran_vethiel",
            },
        )

    def test_rulebook_no_longer_hand_authors_a_service_hosts_roster(self):
        # The roster is derived from the place registry; a hand-authored
        # section would declare each host a second time. Derivation makes
        # disagreement unrepresentable, so the YAML section is gone and the
        # catalog still loads the full derived roster.
        self.assertNotIn("service_hosts", raw_rulebook())
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.service_id for row in catalog.service_hosts],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
                "ciaran_hailiel", "ciaran_lareneth",
                "ciaran_valwyn", "ciaran_vethiel",
            ],
        )

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_named_offenses_raise_the_catalog_error_family_without_db_access(self):
        store = PLACE_REGISTRY["altoria_general_store"]
        mutations = [
            # Empty (whitespace-only) required field.
            replace(store, key="t_offense", service_id="t_offense", host_title="   "),
            # Missing (empty) required field.
            replace(store, key="t_offense", service_id="t_offense", host_name=""),
            # Non-string anchor tag (the place key doubles as the room tag).
            replace(store, key=7, service_id="t_offense"),
            # Profession naming no registry row.
            replace(store, key="t_offense", service_id="t_offense", profession="blacksmith"),
            # Blueprint component identity kwargs the place fails to supply.
            replace(store, key="t_offense", service_id="t_offense", authored_kwargs=()),
            # Authored kwargs no blueprint component consumes.
            replace(
                store,
                key="t_offense",
                service_id="t_offense",
                authored_kwargs=(
                    ("shop_key", "t_offense_shop"),
                    ("branch_key", "guild_branch_altoria"),
                ),
            ),
        ]
        for position, place in enumerate(mutations):
            with self.subTest(mutation=position):
                with mock.patch.dict(
                    PLACE_REGISTRY, {"t_offense_place": place}, clear=True
                ):
                    with self.assertRaises(GuildConfigError):
                        validate_service_hosts()

    def test_duplicate_service_anchor_in_the_place_registry_is_rejected(self):
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        store = PLACE_REGISTRY["altoria_general_store"]
        colliding = replace(guild, key="t_colliding", service_id=store.service_id)
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_colliding": colliding}, clear=False
        ):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    def test_person_bound_profession_place_is_rejected_as_an_anchor(self):
        # The roster row IS the anchor registration: anchoring a blueprint
        # whose components co-presence by design (service-anchoring) is the
        # invalid combination, rejected before any host is ever created.
        from world.rules import profession_config
        from world.rules.profession_config import Profession, ProfessionComponent

        courier = Profession(
            key="courier",
            components=(ProfessionComponent("scripted_dialogue", "person"),),
            schedule_template=None,
            default_tier=None,
        )
        place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            key="t_courier_place",
            service_id="t_courier",
            profession="courier",
        )
        with mock.patch.object(profession_config, "TABLE", {"courier": courier}):
            with mock.patch.dict(
                PLACE_REGISTRY, {"t_courier_place": place}, clear=True
            ):
                with self.assertRaises(GuildConfigError):
                    validate_service_hosts()

    def test_malformed_profession_rulebook_surfaces_as_catalog_error(self):
        from world.rules import profession_config

        with mock.patch.object(
            profession_config,
            "get_profession",
            side_effect=profession_config.ProfessionConfigError("broken rulebook"),
        ):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_derived_shop_row_collision_with_guild_registry_row_is_rejected(self):
        # The authored-name uniqueness rule (shops x guild branches x guild
        # ranks) runs unchanged over the DERIVED shop rows: a planted
        # collision between the derived merchant row and a guild branch row
        # names both holders.
        merchant = SHOP_REGISTRY["altoria_general_store"]
        collision = replace(
            GUILD_BRANCH_REGISTRY["guild_branch_altoria"],
            host_name=merchant.host_name,
        )
        with self.assertRaises(ValueError) as caught:
            validate_registry_identity_uniqueness(
                branch_rows={
                    **GUILD_BRANCH_REGISTRY,
                    "guild_branch_altoria": collision,
                },
                rank_rows=GUILD_RANK_REGISTRY,
            )
        message = str(caught.exception)
        self.assertIn("shop:altoria_general_store", message)
        self.assertIn("guild_branch:guild_branch_altoria", message)


if __name__ == "__main__":
    unittest.main()
