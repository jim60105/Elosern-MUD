"""Data-contract test: place-derived service host roster and current place-declaration contract
Slice of ``test_guild_config``: ServiceHostRosterTests. The derived service
hosts are exactly the hosted place declarations, checked in both directions;
the authored host names, titles and personnel tables this file used to pin are
gone, while every place key, kind, exterior, doorway name, dwelling lineage and
host-less shape assertion stays.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest import mock
from world.lore.guild import GUILD_BRANCH_REGISTRY
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

    @staticmethod
    def _hosted_places():
        """Every shipped place that declares a service host, in registry order."""
        return [
            place for place in PLACE_REGISTRY.values() if place.service_id is not None
        ]

    def _assert_rows_follow_the_places(self, rows):
        """Both directions of the current place-to-derived-roster correspondence."""
        places = self._hosted_places()
        self.assertEqual(
            [row.service_id for row in rows],
            [place.service_id for place in places],
            "the derived roster must be exactly the hosted places, in place order",
        )
        by_service = {row.service_id: row for row in rows}
        for place in places:
            row = by_service[place.service_id]
            with self.subTest(service_id=place.service_id):
                self.assertEqual(row.name, place.host_name)
                self.assertEqual(row.title, place.host_title)
                self.assertEqual(row.profession.key, place.profession)
                self.assertEqual(row.anchor_room, place.key)
                self.assertEqual(row.authored_kwargs, dict(place.authored_kwargs))

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_derived_roster_is_the_current_place_delegation_projection(self):
        # No frozen roster: the derived rows ARE the current place
        # declarations, checked both ways, so a valid later authored personnel
        # or host edit takes effect and a row with no hosted place fails.
        rows = validate_service_hosts()
        self._assert_rows_follow_the_places(rows)
        by_service = {row.service_id: row for row in rows}
        # The cross-registry identity join a hand-authored roster used to keep
        # synchronized still holds: the guild host's authored identity is the
        # guild branch record's, and each shop host's is its derived shop row's.
        guild_place = next(
            place
            for place in self._hosted_places()
            if "branch_key" in dict(place.authored_kwargs)
        )
        branch = GUILD_BRANCH_REGISTRY[dict(guild_place.authored_kwargs)["branch_key"]]
        guild_row = by_service[guild_place.service_id]
        self.assertEqual(
            (guild_row.name, guild_row.title), (branch.host_name, branch.host_title)
        )
        for place in self._hosted_places():
            shop_key = dict(place.authored_kwargs).get("shop_key")
            if shop_key is None:
                continue
            with self.subTest(place=place.key):
                shop = SHOP_REGISTRY[shop_key]
                row = by_service[place.service_id]
                self.assertEqual(
                    (row.name, row.title), (shop.host_name, shop.host_title)
                )

    def test_catalog_exposes_the_roster(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.service_id for row in catalog.service_hosts],
            [place.service_id for place in self._hosted_places()],
        )
        self.assertEqual(
            set(catalog.host_by_service_id),
            {place.service_id for place in self._hosted_places()},
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
    def test_the_attendant_blueprint_changes_no_shipped_host(self):
        # Neutrality gate (place-attendant-profession, as modified by
        # ciaran-village-commons), both halves of the scenario: registering an
        # unused profession blueprint changes no shipped host, and a place that
        # later declares that blueprint creates only its own declared host. The
        # comparison is against the rows derived before the blueprint is
        # registered, never against a frozen roster.
        from world.rules import profession_config
        from world.rules.profession_config import Profession, ProfessionComponent

        def row_fields(row):
            return (
                row.name,
                row.title,
                row.profession.key,
                row.anchor_room,
                row.service_id,
                row.authored_kwargs,
            )

        before = validate_service_hosts()
        blueprint = Profession(
            key="t_unused_blueprint",
            components=(ProfessionComponent("scripted_dialogue", "place"),),
            schedule_template=None,
            default_tier=None,
        )
        table = {**profession_config.TABLE, blueprint.key: blueprint}
        with mock.patch.object(profession_config, "TABLE", table):
            after = validate_service_hosts()
            self.assertEqual([row_fields(row) for row in after], [row_fields(row) for row in before])
            new_place = replace(
                PLACE_REGISTRY["altoria_general_store"],
                key="t_new_blueprint_place",
                service_id="t_new_blueprint_host",
                profession=blueprint.key,
                assortment_keys=(),
                authored_kwargs=(("dialogue_key", "guild_staff"),),
            )
            with mock.patch.dict(PLACE_REGISTRY, {"t_new_blueprint_place": new_place}):
                grown = validate_service_hosts()
            self.assertEqual(
                [row.service_id for row in grown],
                [row.service_id for row in before] + ["t_new_blueprint_host"],
            )
            added = grown[-1]
            self.assertEqual(added.anchor_room, "t_new_blueprint_place")
            self.assertEqual(added.profession.key, blueprint.key)
            self.assertEqual(
                [(c.type_key, c.default_binding) for c in added.profession.components],
                [("scripted_dialogue", "place")],
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
        # The authored-name uniqueness rule (shops x guild branches x
        # persistent adventurers) runs unchanged over the DERIVED shop rows: a planted
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
            host_profile_key=None,
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
    def test_every_shipped_place_authors_a_complete_host_except_the_shelter(self):
        # hostless-places neutrality gate, as widened by
        # ciaran-village-commons: the one shipped host-less place is the
        # sanctioned 共食棚 commons, and every other shipped place declares
        # all six scalar host fields. The derived roster still reproduces
        # every pre-change baseline row field for field — no identity moved
        # into or out of the host-declaring set — while the roster itself
        # has grown with the content changes that own the new rows.
        from world.lore.settlements.places import HOST_IDENTITY_FIELDS, place_is_hostless

        hostless = {place.key for place in PLACE_REGISTRY.values() if place_is_hostless(place)}
        # altoria-crown-and-watch widens the sanctioned group with the
        # host-less 聖潔王都王宮: the palace is the capital's first place to
        # reach the rooms-only outcome hostless-places reserved for this
        # exact all-or-nothing shape. altoria-learning-and-exchange widens it
        # again with the host-less 聖潔王都市集棚 — host-less on the document's
        # authority (a market street's trade hangs on its stallholders, not a
        # fixed street-chief NPC), the second emptiness meant to stay empty.
        # The silver-feather correspondence change widens it a third time with
        # the two 銀羽驛站 branches: institution-run courier outposts whose
        # service runs from the ledger behind the counter, not a resident NPC
        # host, so they reach the rooms-only outcome hostless-places reserved.
        # Their letter_service flag, not a host row, drives the surface.
        # persistent-human-guild-hosts widens it a fourth time with the three
        # host-less HOME residences of the persistent adventurers
        # (霍克的家、卡珊卓的家、奧古斯丁的家): the resident is assembled by
        # the host system onto an ordinary connected home, so no place-host
        # row is authored for these three rooms.
        self.assertEqual(
            hostless,
            {
                "ciaran_shelter",
                "altoria_palace",
                "altoria_market_stalls",
                "ciaran_silverfeather",
                "altoria_silverfeather",
                "altoria_hok_home",
                "altoria_cassandra_home",
                "altoria_augustine_home",
            },
        )
        for place in PLACE_REGISTRY.values():
            if place_is_hostless(place):
                continue
            with self.subTest(place=place.key):
                for field in HOST_IDENTITY_FIELDS:
                    self.assertIsNotNone(getattr(place, field), field)
        # Every hosted place still contributes exactly one matching row, and
        # the sanctioned host-less group above contributes none.
        self._assert_rows_follow_the_places(validate_service_hosts())

    @covers_requirement(
        "ciaran-village-commons::the-village-has-a-communal-shelter-a-sword-instructor-and-an-elder"
    )
    def test_the_commons_places_keep_their_shape_and_staffing(self):
        # The dwelling contract lives at the place registry, not in a frozen
        # roster: the shelter's host-less shape (every host scalar None, no
        # profession, no service id, no kwargs, no goods) and the two attendant
        # homes' authored lineage and staff are pinned there, and the derived
        # roster follows each place's own declaration.
        from world.lore.settlements.places import HOST_IDENTITY_FIELDS, place_is_hostless

        rows = {row.service_id: row for row in validate_service_hosts()}
        for key in ("ciaran_elenis_home", "ciaran_teliel_home"):
            place = PLACE_REGISTRY[key]
            with self.subTest(place=key):
                self.assertEqual(place.kind.value, "home")
                self.assertEqual(place.host_race, "elf")
                self.assertEqual(place.host_subrace, "ciaran")
                self.assertEqual(place.host_sex, "female")
                self.assertEqual(place.profession, "attendant")
                row = rows[place.service_id]
                self.assertEqual(row.anchor_room, key)
                self.assertEqual(row.authored_kwargs, dict(place.authored_kwargs))
                self.assertEqual(row.profession.key, "attendant")
        shelter = PLACE_REGISTRY["ciaran_shelter"]
        self.assertTrue(place_is_hostless(shelter))
        self.assertEqual(shelter.kind, "commons")
        self.assertEqual(shelter.profession, None)
        self.assertEqual(shelter.service_id, None)
        self.assertEqual(shelter.authored_kwargs, ())
        self.assertEqual(shelter.assortment_keys, ())
        self.assertEqual(shelter.extra_item_keys, ())
        self.assertEqual(shelter.excluded_item_keys, ())
        for field in HOST_IDENTITY_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(shelter, field), field)

    #: The three hospitality places pinned at the PLACE registry, where the map
    #: and dwelling contract lives: the derived ServiceHostRow carries no
    #: coordinate or doorway field, so without this literal the lane could move
    #: to another exterior (or the bathhouse off 浴場前) while every derived
    #: comparison and every sync test stayed green. The hosts' authored names
    #: and titles are deliberately not pinned: they follow the current place
    #: declaration, which the correspondence test above checks both ways.
    #: Shape: place key -> (kind, exterior_xy, doorway name, host race,
    #: host sex, assortment keys, authored kwargs).
    HOSPITALITY_PLACE_ROWS = {
        "altoria_tavern": (
            "tavern", (4, 1), "醉月酒館",
            "human", "female", (),
            {"dialogue_key": "altoria_tavern"},
        ),
        "altoria_lodging": (
            "lodging", (4, 1), "爐火旅店",
            "human", "female", (),
            {"dialogue_key": "altoria_lodging"},
        ),
        "altoria_bathhouse": (
            "bathhouse", (5, 1), "公共浴場",
            "human", "female", (),
            {"dialogue_key": "altoria_bathhouse"},
        ),
    }

    @covers_requirement(
        "altoria-hospitality::the-capital-has-a-tavern-an-inn-and-a-bathhouse"
    )
    def test_the_hospitality_place_rows_pin_the_lane_and_bathhouse_front(self):
        # The lane's two doors sit on 客棧巷 (4,1) — one street, two names —
        # and the bathhouse on 浴場前 (5,1); the hosts are human women with
        # nothing to sell. Coordinated drift here decouples the rows from the
        # map's actual streets, which no derived comparison can see.
        for key, expected in self.HOSPITALITY_PLACE_ROWS.items():
            place = PLACE_REGISTRY[key]
            with self.subTest(place=key):
                self.assertEqual(
                    (
                        place.kind.value,
                        place.exterior_xy,
                        place.doorway_key_zh,
                        place.host_race,
                        place.host_sex,
                        place.assortment_keys,
                        dict(place.authored_kwargs),
                    ),
                    expected,
                )

    #: The four altoria-crown-and-watch places pinned at the PLACE registry,
    #: where the map and dwelling contract lives (the HOSPITALITY_PLACE_ROWS
    #: pattern): the derived ServiceHostRow carries no coordinate or doorway
    #: field, so without this literal the palace could move off 王宮前庭 or the
    #: guardhouse off 南門 while every derived comparison stayed green. The
    #: hosts' authored names and titles are deliberately not pinned; the
    #: palace's host half stays the literal None pair, which is what keeps an
    #: attendant from quietly appearing behind the throne.
    #: Shape: place key -> (kind, exterior_xy, doorway name, host race,
    #: host sex, assortment keys, authored kwargs).
    CROWN_WATCH_PLACE_ROWS = {
        "altoria_palace": (
            "palace", (4, 6), "王宮",
            None, None, (), {},
        ),
        "altoria_noble_watch": (
            "watch_post", (3, 5), "貴族區衛所",
            "human", "male", (),
            {"dialogue_key": "altoria_noble_watch"},
        ),
        "altoria_drill_yard": (
            "training_ground", (2, 4), "校場",
            "human", "male", (),
            {"dialogue_key": "altoria_drill_yard"},
        ),
        "altoria_guardhouse": (
            "watch_post", (3, 0), "衛兵駐所",
            "human", "male", (),
            {"dialogue_key": "altoria_guardhouse"},
        ),
    }

    @covers_requirement(
        "altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard"
    )
    def test_the_crown_watch_place_rows_pin_the_four_exteriors(self):
        # 王宮 off 王宮前庭 (4,6), the noble watch off 貴族區前 (3,5), the
        # drill yard off 校場外 (2,4), the guardhouse off 南門 (3,0): the four
        # squares the capital grid already carries and these doors land on.
        for key, expected in self.CROWN_WATCH_PLACE_ROWS.items():
            place = PLACE_REGISTRY[key]
            with self.subTest(place=key):
                self.assertEqual(
                    (
                        place.kind.value,
                        place.exterior_xy,
                        place.doorway_key_zh,
                        place.host_race,
                        place.host_sex,
                        place.assortment_keys,
                        dict(place.authored_kwargs),
                    ),
                    expected,
                )

    @covers_requirement(
        "altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard"
    )
    def test_the_palace_row_is_host_less_in_the_shape_hostless_places_reserved(self):
        # The palace's emptiness is its own data contract (the shelter pin's
        # shape): every host scalar None, no profession, no service id, no
        # component kwargs, no goods — the all-or-nothing group wholly absent,
        # not a partially authored host that validation would reject and a
        # careless reader might mistake for a host-less room.
        from world.lore.settlements.places import HOST_IDENTITY_FIELDS, place_is_hostless

        palace = PLACE_REGISTRY["altoria_palace"]
        self.assertTrue(place_is_hostless(palace))
        self.assertEqual(palace.kind, "palace")
        self.assertEqual(palace.profession, None)
        self.assertEqual(palace.service_id, None)
        self.assertEqual(palace.authored_kwargs, ())
        self.assertEqual(palace.assortment_keys, ())
        self.assertEqual(palace.extra_item_keys, ())
        self.assertEqual(palace.excluded_item_keys, ())
        for field in HOST_IDENTITY_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(palace, field), field)
        # And the derived roster really carries no palace row.
        anchors = {row.anchor_room for row in validate_service_hosts()}
        self.assertNotIn("altoria_palace", anchors)

    #: The three altoria-learning-and-exchange places pinned at the PLACE
    #: registry, where the map and institutional contract lives (the
    #: CROWN_WATCH_PLACE_ROWS pattern): the academy on the 學院前 square (5,5)
    #: the upper terrace's own, the merchant hall sharing 東市 (5,3) with the
    #: alchemist under a second door name, and the stalls the third door on
    #: 市場街 (2,3) behind the general store and the jeweller. The stalls' host
    #: half stays the literal None pair — the capital's second deliberate
    #: emptiness. The hosts' authored names and titles are deliberately not
    #: pinned: both hosts land as plain attendants whose whole authored payload
    #: is a dialogue key, and the correspondence test above checks that
    #: neither authored a branch, shop or quest kwarg.
    LEARNING_EXCHANGE_PLACE_ROWS = {
        "altoria_academy": (
            "academy", (5, 5), "王立魔法學院",
            "human", "male", (),
            {"dialogue_key": "altoria_academy"},
        ),
        "altoria_merchant_hall": (
            "merchant_hall", (5, 3), "商會公所",
            "human", "male", (),
            {"dialogue_key": "altoria_merchant_hall"},
        ),
        "altoria_market_stalls": (
            "market", (2, 3), "市集棚",
            None, None, (), {},
        ),
    }

    @covers_requirement(
        "altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls"
    )
    def test_the_learning_exchange_place_rows_pin_the_three_exteriors(self):
        # 學院前 (5,5), 東市 (5,3), 市場街 (2,3): the squares the capital grid
        # already carries and these doors land on — 東市 and 市場街 shared
        # with earlier shops, their distinctness owned here as literals and
        # by the registry's one-doorway-name-per-exterior rule.
        for key, expected in self.LEARNING_EXCHANGE_PLACE_ROWS.items():
            place = PLACE_REGISTRY[key]
            with self.subTest(place=key):
                self.assertEqual(
                    (
                        place.kind.value,
                        place.exterior_xy,
                        place.doorway_key_zh,
                        place.host_race,
                        place.host_sex,
                        place.assortment_keys,
                        dict(place.authored_kwargs),
                    ),
                    expected,
                )

    @covers_requirement(
        "altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls"
    )
    def test_the_stalls_row_is_host_less_in_the_shape_hostless_places_reserved(self):
        # The stalls' emptiness is its own data contract (the palace pin's
        # shape): every host scalar None, no profession, no service id, no
        # component kwargs, no goods — hostless-places' all-or-nothing group
        # wholly absent. What separates it from the palace is only why it is
        # empty (the document, not an unwritten story), and that lives in
        # the prose; the shape pin keeps a host from quietly appearing
        # behind the awnings.
        from world.lore.settlements.places import HOST_IDENTITY_FIELDS, place_is_hostless

        stalls = PLACE_REGISTRY["altoria_market_stalls"]
        self.assertTrue(place_is_hostless(stalls))
        self.assertEqual(stalls.kind, "market")
        self.assertEqual(stalls.profession, None)
        self.assertEqual(stalls.service_id, None)
        self.assertEqual(stalls.authored_kwargs, ())
        self.assertEqual(stalls.assortment_keys, ())
        self.assertEqual(stalls.extra_item_keys, ())
        self.assertEqual(stalls.excluded_item_keys, ())
        for field in HOST_IDENTITY_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(stalls, field), field)
        # And the derived roster carries no stalls row.
        anchors = {row.anchor_room for row in validate_service_hosts()}
        self.assertNotIn("altoria_market_stalls", anchors)


if __name__ == "__main__":
    unittest.main()
