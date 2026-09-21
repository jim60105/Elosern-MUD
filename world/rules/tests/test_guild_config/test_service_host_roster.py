"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: ServiceHostRosterTests.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest import mock
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.places import validate_place_registry
from world.lore.settlements.shops import SHOP_REGISTRY
from world.lore.settlements.shops import validate_registry_identity_uniqueness
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.dialogue import NO_UNDERSTANDING_LINE
from world.rules.dialogue import table_response
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
    # field — that is the change's behaviour-neutrality gate. The merchant
    # row carries one extension since merchant-dialogue: a dialogue_key
    # beside the shop_key (the shopkeeper blueprint now answers too). The
    # guild row's two kwargs stay pinned exactly as they shipped.
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
            "dialogue_key": "altoria_general_store",
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

    @covers_requirement(
        "place-attendant-hosts::adding-the-blueprint-changes-no-shipped-host"
    )
    def test_the_attendant_blueprint_ships_unused(self):
        # Neutrality gate (place-attendant-profession): every derived row
        # equals the FULL pre-change baseline field by field — name, title,
        # profession, anchor, service_id, authored identity — so a shipped
        # host's identity cannot silently move while the two-row former-YAML
        # zip above still passes. NOT ONE row names the new attendant
        # blueprint: it ships available for content changes, used by nothing.
        rows = validate_service_hosts()
        self.assertEqual(len(rows), len(self.PRE_CHANGE_BASELINE))
        for row, expected in zip(rows, self.PRE_CHANGE_BASELINE):
            with self.subTest(service_id=row.service_id):
                self.assertEqual(
                    (
                        row.name,
                        row.title,
                        row.profession.key,
                        row.anchor_room,
                        row.service_id,
                        row.authored_kwargs,
                    ),
                    (
                        expected["name"],
                        expected["title"],
                        expected["profession"],
                        expected["anchor_room"],
                        expected["service_id"],
                        expected["authored_kwargs"],
                    ),
                )
        self.assertNotIn("attendant", {row.profession.key for row in rows})

    # The complete roster as it shipped BEFORE place-attendant-profession,
    # written as literals (never derived from the live registry): the fixed
    # nine rows the blueprint addition must reproduce untouched. Each
    # merchant row's authored_kwargs gained its dialogue_key with
    # merchant-dialogue (a shopkeeper both trades and answers); every other
    # field remains the pre-change literal, so an identity cannot silently
    # move under the extension.
    PRE_CHANGE_BASELINE = (
        {
            "name": "葛里安·衛登",
            "title": "阿爾托利亞分會會長",
            "profession": "guild_staff",
            "anchor_room": "altoria_guild_hall",
            "service_id": "altoria_guild_master",
            "authored_kwargs": {
                "branch_key": "guild_branch_altoria",
                "dialogue_key": "guild_staff",
            },
        },
        {
            "name": "瑪爾特·金秤",
            "title": "阿爾托利亞雜貨商店老闆",
            "profession": "merchant",
            "anchor_room": "altoria_general_store",
            "service_id": "altoria_merchant",
            "authored_kwargs": {
                "shop_key": "altoria_general_store",
                "dialogue_key": "altoria_general_store",
            },
        },
        {
            "name": "維爾登·黑潭",
            "title": "聖潔王都鍛造鋪鐵匠",
            "profession": "merchant",
            "anchor_room": "altoria_forge",
            "service_id": "altoria_blacksmith",
            "authored_kwargs": {
                "shop_key": "altoria_forge",
                "dialogue_key": "altoria_forge",
            },
        },
        {
            "name": "西格瑪·庫柏",
            "title": "聖潔王都餐館老闆",
            "profession": "merchant",
            "anchor_room": "altoria_eatery",
            "service_id": "altoria_eatery_owner",
            "authored_kwargs": {
                "shop_key": "altoria_eatery",
                "dialogue_key": "altoria_eatery",
            },
        },
        {
            "name": "妮絲塔·狐溪",
            "title": "聖潔王都裁縫坊坊主",
            "profession": "merchant",
            "anchor_room": "altoria_tailor",
            "service_id": "altoria_tailor",
            "authored_kwargs": {
                "shop_key": "altoria_tailor",
                "dialogue_key": "altoria_tailor",
            },
        },
        {
            "name": "海莉爾·斯塔爾法爾",
            "title": "暗影谷村鑄刃者",
            "profession": "merchant",
            "anchor_room": "ciaran_hailiel_home",
            "service_id": "ciaran_hailiel",
            "authored_kwargs": {
                "shop_key": "ciaran_hailiel_home",
                "dialogue_key": "ciaran_hailiel_home",
            },
        },
        {
            "name": "拉瑞內斯·妮特布倫",
            "title": "暗影谷村花饌好手",
            "profession": "merchant",
            "anchor_room": "ciaran_lareneth_home",
            "service_id": "ciaran_lareneth",
            "authored_kwargs": {
                "shop_key": "ciaran_lareneth_home",
                "dialogue_key": "ciaran_lareneth_home",
            },
        },
        {
            "name": "瓦爾溫·斯蒂爾瓦特爾",
            "title": "暗影谷村蒐羅者",
            "profession": "merchant",
            "anchor_room": "ciaran_valwyn_home",
            "service_id": "ciaran_valwyn",
            "authored_kwargs": {
                "shop_key": "ciaran_valwyn_home",
                "dialogue_key": "ciaran_valwyn_home",
            },
        },
        {
            "name": "維特希爾·威爾德布瑞亞爾",
            "title": "暗影谷村織衣者",
            "profession": "merchant",
            "anchor_room": "ciaran_vethiel_home",
            "service_id": "ciaran_vethiel",
            "authored_kwargs": {
                "shop_key": "ciaran_vethiel_home",
                "dialogue_key": "ciaran_vethiel_home",
            },
        },
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

    @covers_requirement(
        "merchant-dialogue::every-merchant-host-answers-when-spoken-to"
    )
    def test_a_merchant_place_authoring_no_dialogue_key_fails_load(self):
        # merchant-dialogue: the blueprint now demands a dialogue table from
        # every shopkeeper. A merchant place that kept only its shop_key (the
        # pre-change row shape) is rejected by the generic blueprint-coverage
        # rule — no loader change — and the error names the place and the
        # missing identity kwarg, so a silent shopkeeper is an authoring
        # error, never a default.
        store = PLACE_REGISTRY["altoria_general_store"]
        silent = replace(
            store,
            key="t_silent_merchant_place",
            service_id="t_silent_merchant",
            authored_kwargs=(("shop_key", "t_silent_merchant_shop"),),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_silent_merchant_place": silent}, clear=True
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        message = str(caught.exception)
        self.assertIn("t_silent_merchant_place", message)
        self.assertIn("dialogue_key", message)

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

    # ---- the attendant blueprint's rejections (place-attendant-profession) --

    def _attendant(self, **overrides):
        """A synthetic place naming the shipped attendant blueprint."""
        base = dict(
            key="t_attendant_place",
            service_id="t_attendant",
            profession="attendant",
            assortment_keys=(),
            authored_kwargs=(("dialogue_key", "guild_staff"),),
        )
        base.update(overrides)
        return replace(PLACE_REGISTRY["altoria_general_store"], **base)

    @covers_requirement(
        "place-attendant-hosts::a-place-whose-service-is-conversation-has-a-blueprint-to-host-it"
    )
    def test_an_attendant_authoring_a_trade_kwarg_is_rejected_as_dead(self):
        # The dialogue component consumes dialogue_key only: a shop_key on an
        # attendant row is exactly the dead-kwarg offense every profession
        # already obeys, named by place and kwarg.
        place = self._attendant(
            authored_kwargs=(
                ("dialogue_key", "guild_staff"),
                ("shop_key", "t_attendant_shop"),
            )
        )
        with mock.patch.dict(PLACE_REGISTRY, {"t_attendant_place": place}, clear=True):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        message = str(caught.exception)
        self.assertIn("t_attendant_place", message)
        self.assertIn("shop_key", message)

    @covers_requirement(
        "place-attendant-hosts::a-place-whose-service-is-conversation-has-a-blueprint-to-host-it"
    )
    def test_an_attendant_place_declaring_assortments_is_rejected(self):
        # Goods require a shop identity; the lore validator owns that rule
        # and fires on the place row alone.
        place = self._attendant(assortment_keys=("altoria_general_goods",))
        with self.assertRaises(ValueError) as caught:
            validate_place_registry({"t_attendant_place": place})
        message = str(caught.exception)
        self.assertIn("t_attendant_place", message)
        self.assertIn("assortments without a shop identity", message)

    @covers_requirement(
        "place-attendant-hosts::an-authored-host-is-bound-to-a-dialogue-table-that-exists"
    )
    def test_a_place_authoring_an_unregistered_dialogue_key_fails_load(self):
        # Authored resolution: the kwarg exists but resolves to nothing —
        # load names the place and the dead key (spec: bind to a table that
        # exists).
        place = self._attendant(
            key="t_dead_dialogue_place",
            service_id="t_dead_dialogue",
            authored_kwargs=(("dialogue_key", "t_unregistered_table"),),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_dead_dialogue_place": place}, clear=True
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        message = str(caught.exception)
        self.assertIn("t_dead_dialogue_place", message)
        self.assertIn("t_unregistered_table", message)

    @covers_requirement(
        "place-attendant-hosts::an-authored-host-is-bound-to-a-dialogue-table-that-exists"
    )
    def test_a_runtime_lookup_of_an_unregistered_key_still_degrades(self):
        # The load-time rejection above must NOT collapse into a runtime
        # raise: a key reaching the lookup from any other route still gets
        # the no-understanding line.
        self.assertEqual(
            table_response("t_unregistered_table", "住宿"),
            NO_UNDERSTANDING_LINE,
        )

    def test_the_dialogue_key_check_covers_every_dialogue_bearing_row(self):
        # The check keys off the COMPONENT, not the profession: the shipped
        # guild hall (a multi-component blueprint) must fail load just the
        # same when its authored table disappears — narrowing the rule to
        # attendants only would silently leave the guild host mute.
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        broken = replace(
            guild,
            authored_kwargs=(
                ("branch_key", "guild_branch_altoria"),
                ("dialogue_key", "t_guild_table_gone"),
            ),
        )
        with mock.patch.dict(PLACE_REGISTRY, {"altoria_guild_hall": broken}):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        message = str(caught.exception)
        self.assertIn("altoria_guild_hall", message)
        self.assertIn("t_guild_table_gone", message)

    # ---- host-less places (hostless-places) --------------------------------

    def _hostless(self, key="t_plaza"):
        """A synthetic place authoring no host at all (every field defaulted)."""
        return replace(
            PLACE_REGISTRY["altoria_general_store"],
            key=key,
            host_name=None,
            host_title=None,
            host_race=None,
            host_subrace=None,
            host_sex=None,
            profession=None,
            service_id=None,
            assortment_keys=(),
            authored_kwargs=(),
        )

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_host_less_place_contributes_no_roster_row(self):
        # The roster is the projection of the places that DECLARE a host: a
        # host-less row adds nothing, and the nine shipped rows keep their
        # order and identity untouched.
        baseline = validate_service_hosts()
        with mock.patch.dict(PLACE_REGISTRY, {"t_plaza": self._hostless()}):
            rows = validate_service_hosts()
        self.assertEqual(len(rows), len(baseline))
        self.assertEqual(
            [row.service_id for row in rows], [row.service_id for row in baseline]
        )
        self.assertNotIn("t_plaza", {row.anchor_room for row in rows})

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_partial_host_is_not_hostless_and_still_faces_the_rejections(self):
        # The skip must never turn malformed material into a silent empty
        # room: a row with a host name and no profession is NOT skipped —
        # it falls through to the roster's named rejections.
        partial = replace(self._hostless(), host_name="測試半人", host_title="測試殘缺")
        with mock.patch.dict(PLACE_REGISTRY, {"t_plaza": partial}, clear=True):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    @covers_requirement(
        "place-attendant-hosts::adding-the-blueprint-changes-no-shipped-host"
    )
    def test_every_shipped_place_still_authors_a_complete_host(self):
        # hostless-places neutrality gate (task 4.1): the capability ships
        # unused. Every shipped place declares all six scalar host fields,
        # and the derived roster is the fixed nine rows field for field —
        # nothing moved into or out of the host-declaring set.
        from world.lore.settlements.places import HOST_IDENTITY_FIELDS, place_is_hostless

        for place in PLACE_REGISTRY.values():
            with self.subTest(place=place.key):
                self.assertFalse(place_is_hostless(place))
                for field in HOST_IDENTITY_FIELDS:
                    self.assertIsNotNone(getattr(place, field), field)
        rows = validate_service_hosts()
        self.assertEqual(len(rows), len(self.PRE_CHANGE_BASELINE))
        for row, expected in zip(rows, self.PRE_CHANGE_BASELINE):
            with self.subTest(service_id=row.service_id):
                self.assertEqual(
                    (
                        row.name,
                        row.title,
                        row.profession.key,
                        row.anchor_room,
                        row.service_id,
                        row.authored_kwargs,
                    ),
                    (
                        expected["name"],
                        expected["title"],
                        expected["profession"],
                        expected["anchor_room"],
                        expected["service_id"],
                        expected["authored_kwargs"],
                    ),
                )


if __name__ == "__main__":
    unittest.main()
