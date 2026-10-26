"""Data-contract test: place-derived service host roster and current place-declaration contract

Slice of ``test_guild_config``: ServiceHostRosterTests. The derived service
hosts are exactly the hosted place declarations, checked in both directions;
each row carries the place's validated direct capability declarations, its
canonical authored profile identity and its spawn room. Every place key, kind,
exterior, doorway name, dwelling lineage and host-less shape assertion stays.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest import mock
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.settlements.places import (
    HOST_IDENTITY_FIELDS,
    PLACE_REGISTRY,
    place_capabilities,
    place_dialogue_keys,
    place_is_hostless,
    place_shop_identity,
    validate_place_registry,
)
from world.lore.settlements.shops import SHOP_REGISTRY
from world.lore.settlements.shops import validate_registry_identity_uniqueness
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.dialogue import NO_UNDERSTANDING_LINE
from world.rules.dialogue import table_response
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import load_guild_catalog
from world.rules.guild_config import validate_service_hosts
from world.rules.npc_capabilities import capability, person_bound, place_bound
import unittest
from ._support import (
    CatalogRegistryIsolation,
    raw_rulebook,
)


def _hosted_places():
    """Every shipped place that declares a host, in registry order."""
    return [
        place for place in PLACE_REGISTRY.values() if not place_is_hostless(place)
    ]


def _reanchored(place, key):
    """The place's declarations re-anchored at ``key`` (a planted place row)."""
    return tuple(
        replace(declaration, binding=place_bound(key))
        for declaration in place.components
    )


class ServiceHostRosterTests(CatalogRegistryIsolation):
    """Derived service-host roster: places yield rows; rejections are unchanged (design §3.2)."""

    def _assert_rows_follow_the_places(self, rows):
        """Both directions of the place-to-derived-roster correspondence."""
        places = _hosted_places()
        self.assertEqual(
            [row.host_key for row in rows],
            [place.host_profile_key for place in places],
            "the derived roster must be exactly the hosted places, in place order",
        )
        by_host = {row.host_key: row for row in rows}
        for place in places:
            row = by_host[place.host_profile_key]
            with self.subTest(host_key=place.host_profile_key):
                self.assertEqual(row.name, place.host_name)
                self.assertEqual(row.title, place.host_title)
                self.assertEqual(row.spawn_room, place.key)
                self.assertEqual(row.components, place.components)
                self.assertEqual(
                    row.component_types(),
                    tuple(declaration.type for declaration in place.components),
                )

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_derived_roster_is_the_current_place_delegation_projection(self):
        # No frozen roster: the derived rows ARE the current place
        # declarations, checked both ways, so a valid later authored personnel
        # or capability edit takes effect and a row with no hosted place fails.
        rows = validate_service_hosts()
        self._assert_rows_follow_the_places(rows)
        by_host = {row.host_key: row for row in rows}
        # The cross-registry identity join a hand-authored roster used to keep
        # synchronized still holds: the guild host's authored identity is the
        # guild branch record's, and each shop host's is its derived shop row's.
        guild_place = next(
            place
            for place in _hosted_places()
            if place_capabilities(place, "guild_staff")
        )
        branch_key = place_capabilities(guild_place, "guild_staff")[0].kwargs[
            "branch_key"
        ]
        branch = GUILD_BRANCH_REGISTRY[branch_key]
        guild_row = by_host[guild_place.host_profile_key]
        self.assertEqual(
            (guild_row.name, guild_row.title), (branch.host_name, branch.host_title)
        )
        for place in _hosted_places():
            shop_key = place_shop_identity(place)
            if shop_key is None:
                continue
            with self.subTest(place=place.key):
                shop = SHOP_REGISTRY[shop_key]
                row = by_host[place.host_profile_key]
                self.assertEqual(
                    (row.name, row.title), (shop.host_name, shop.host_title)
                )

    def test_catalog_exposes_the_roster(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.host_key for row in catalog.service_hosts],
            [place.host_profile_key for place in _hosted_places()],
        )
        self.assertEqual(
            set(catalog.host_by_host_key),
            {place.host_profile_key for place in _hosted_places()},
        )

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_every_row_carries_the_place_s_canonical_host_identity(self):
        rows = validate_service_hosts()
        for row in rows:
            with self.subTest(host_key=row.host_key):
                self.assertTrue(row.host_key)
                # The row's canonical identity is the authored profile key,
                # never a capability, a name or a service identifier.
                self.assertEqual(row.host_key, row.profile_key)
                self.assertEqual(
                    row.host_key,
                    PLACE_REGISTRY[row.spawn_room].host_profile_key,
                )
        self.assertEqual(
            len({row.host_key for row in rows}), len(rows), "host identities are unique"
        )

    def test_rulebook_no_longer_hand_authors_a_service_hosts_roster(self):
        # The roster is derived from the place registry; a hand-authored
        # section would declare each host a second time. Derivation makes
        # disagreement unrepresentable, so the YAML section is gone and the
        # catalog still loads the full derived roster.
        self.assertNotIn("service_hosts", raw_rulebook())

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_a_hosted_place_may_declare_zero_capabilities(self):
        # A person can exist at a place without offering a service: the row
        # carries no components, and the sync keeps the person while emptying
        # the managed set.
        place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            key="t_bare_host_place",
            host_profile_key="t_bare_host",
            assortment_keys=(),
            components=(),
        )
        with mock.patch.dict(PLACE_REGISTRY, {"t_bare_host_place": place}, clear=True):
            rows = validate_service_hosts()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].host_key, "t_bare_host")
        self.assertEqual(rows[0].components, ())
        self.assertEqual(rows[0].component_types(), ())

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_named_offenses_raise_the_catalog_error_family_without_db_access(self):
        store = PLACE_REGISTRY["altoria_general_store"]
        mutations = [
            # Empty (whitespace-only) required field.
            replace(store, key="t_offense", host_title="   "),
            # Missing (empty) required field.
            replace(store, key="t_offense", host_name=""),
            # Non-string spawn room tag (the place key doubles as the tag).
            replace(store, key=7),
            # A capability outside the closed vocabulary.
            replace(
                store,
                key="t_offense",
                components=(capability("blacksmith", binding=place_bound("t_offense")),),
            ),
            # A required authored kwarg the place fails to supply.
            replace(
                store,
                key="t_offense",
                components=(
                    capability(
                        "merchant",
                        binding=place_bound("t_offense"),
                        service_id="t_offense_service",
                    ),
                ),
            ),
            # A kwarg no component of that type consumes.
            replace(
                store,
                key="t_offense",
                components=(
                    capability(
                        "merchant",
                        binding=place_bound("t_offense"),
                        service_id="t_offense_service",
                        shop_key="t_offense_shop",
                        branch_key="guild_branch_altoria",
                    ),
                ),
            ),
            # A place capability bound to the person instead of the place.
            replace(
                store,
                key="t_offense",
                components=(
                    capability(
                        "scripted_dialogue",
                        binding=person_bound(),
                        dialogue_key="guild_staff",
                    ),
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
        service_id = place_capabilities(store, "merchant")[0].kwargs["service_id"]
        colliding = replace(
            guild,
            key="t_colliding",
            host_profile_key="t_colliding_host",
            components=tuple(
                replace(
                    declaration,
                    binding=place_bound("t_colliding"),
                    kwargs={**declaration.kwargs, "service_id": service_id},
                )
                for declaration in guild.components
            ),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_colliding": colliding}, clear=False
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        self.assertIn("duplicate service_id", str(caught.exception))

    def test_two_rows_claiming_one_authored_commission_identity_are_rejected(self):
        # A source-host declaration is commission authoring too: one authored
        # issuer_key is one commission identity, exactly like the import batch.
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        store = PLACE_REGISTRY["altoria_general_store"]
        first = replace(
            store,
            key="t_commission_first",
            host_profile_key="t_commission_first",
            assortment_keys=(),
            components=(
                capability(
                    "quest_issuer",
                    binding=place_bound("t_commission_first"),
                    service_id="t_commission_first_service",
                    issuer_key="t_shared_commission",
                ),
            ),
        )
        second = replace(
            guild,
            key="t_commission_second",
            host_profile_key="t_commission_second",
            components=(
                capability(
                    "quest_issuer",
                    binding=place_bound("t_commission_second"),
                    service_id="t_commission_second_service",
                    issuer_key="t_shared_commission",
                ),
            ),
        )
        with mock.patch.dict(
            PLACE_REGISTRY,
            {"t_commission_first": first, "t_commission_second": second},
            clear=True,
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        self.assertIn("t_shared_commission", str(caught.exception))

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_two_rows_claiming_one_canonical_identity_are_rejected(self):
        # The canonical authored profile identity selects the person, so two
        # rows sharing it would make reuse unanswerable before any write.
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        store = PLACE_REGISTRY["altoria_general_store"]
        colliding = replace(
            guild,
            key="t_colliding",
            components=_reanchored(guild, "t_colliding"),
            host_profile_key=store.host_profile_key,
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_colliding": colliding}, clear=False
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        self.assertIn("duplicate host_key", str(caught.exception))
        self.assertIn(store.host_profile_key, str(caught.exception))

    @covers_requirement(
        "merchant-dialogue::every-merchant-host-answers-when-spoken-to"
    )
    def test_a_merchant_place_authoring_no_dialogue_key_fails_load(self):
        # merchant-dialogue: every shopkeeper answers. A merchant place that
        # declares its trade capability without the dialogue capability is
        # rejected, naming the place and the missing capability.
        store = PLACE_REGISTRY["altoria_general_store"]
        silent = replace(
            store,
            key="t_silent_merchant_place",
            components=(
                replace(
                    place_capabilities(store, "merchant")[0],
                    binding=place_bound("t_silent_merchant_place"),
                ),
            ),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_silent_merchant_place": silent}, clear=True
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_service_hosts()
        message = str(caught.exception)
        self.assertIn("t_silent_merchant_place", message)
        self.assertIn("scripted_dialogue", message)

    @covers_requirement(
        "place-attendant-hosts::an-authored-host-is-bound-to-a-dialogue-table-that-exists"
    )
    def test_a_place_authoring_an_unregistered_dialogue_key_fails_load(self):
        # Authored resolution: the kwarg exists but resolves to nothing —
        # load names the place and the dead key (spec: bind to a table that
        # exists).
        store = PLACE_REGISTRY["altoria_general_store"]
        dead = replace(
            store,
            key="t_dead_dialogue_place",
            components=tuple(
                replace(
                    declaration,
                    binding=place_bound("t_dead_dialogue_place"),
                    kwargs={**declaration.kwargs, "dialogue_key": "t_unregistered_table"},
                )
                if declaration.type == "scripted_dialogue"
                else replace(declaration, binding=place_bound("t_dead_dialogue_place"))
                for declaration in store.components
            ),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_dead_dialogue_place": dead}, clear=True
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
        # The check keys off the DECLARED capability, not a place kind: the
        # shipped guild hall (a multi-capability host) must fail load just the
        # same when its authored table disappears.
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        broken = replace(
            guild,
            components=tuple(
                replace(
                    declaration,
                    kwargs={**declaration.kwargs, "dialogue_key": "t_guild_table_gone"},
                )
                if declaration.type == "scripted_dialogue"
                else declaration
                for declaration in guild.components
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
            host_profile_key=None,
            assortment_keys=(),
            components=(),
        )

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_host_less_place_contributes_no_roster_row(self):
        # The roster is the projection of the places that DECLARE a host: a
        # host-less row adds nothing, and the shipped rows keep their order
        # and identity untouched.
        baseline = validate_service_hosts()
        with mock.patch.dict(PLACE_REGISTRY, {"t_plaza": self._hostless()}):
            rows = validate_service_hosts()
        self.assertEqual(len(rows), len(baseline))
        self.assertEqual(
            [row.host_key for row in rows], [row.host_key for row in baseline]
        )
        self.assertNotIn("t_plaza", {row.spawn_room for row in rows})

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_partial_host_is_not_hostless_and_still_faces_the_rejections(self):
        # The skip must never turn malformed material into a silent empty
        # room: a row with a host name and no profile is NOT skipped — it
        # falls through to the roster's named rejections.
        partial = replace(self._hostless(), host_name="測試半人", host_title="測試殘缺")
        with mock.patch.dict(PLACE_REGISTRY, {"t_plaza": partial}, clear=True):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_every_shipped_place_authors_a_complete_host_except_the_sanctioned_emptiness(self):
        # hostless-places neutrality gate, widened by the content changes that
        # own each emptiness: every one of these places is deliberately
        # host-less, and every other shipped place declares the complete
        # identity group with at least zero capabilities.
        hostless = {
            place.key for place in PLACE_REGISTRY.values() if place_is_hostless(place)
        }
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
        # roster: the shelter's host-less shape and the two talk-only homes'
        # authored lineage and declaration are pinned there, and the derived
        # roster follows each place's own declaration.
        rows = {row.host_key: row for row in validate_service_hosts()}
        for key in ("ciaran_elenis_home", "ciaran_teliel_home"):
            place = PLACE_REGISTRY[key]
            with self.subTest(place=key):
                self.assertEqual(place.kind.value, "home")
                self.assertEqual(place.host_race, "elf")
                self.assertEqual(place.host_subrace, "ciaran")
                self.assertEqual(place.host_sex, "female")
                self.assertEqual(
                    [declaration.type for declaration in place.components],
                    ["scripted_dialogue"],
                )
                row = rows[place.host_profile_key]
                self.assertEqual(row.spawn_room, key)
                self.assertEqual(row.components, place.components)
        shelter = PLACE_REGISTRY["ciaran_shelter"]
        self.assertTrue(place_is_hostless(shelter))
        self.assertEqual(shelter.kind, "commons")
        self.assertEqual(shelter.components, ())
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
    #: host sex, assortment keys, declared dialogue tables).
    HOSPITALITY_PLACE_ROWS = {
        "altoria_tavern": (
            "tavern", (3970, 1120), "醉月酒館",
            "human", "female", (),
            ("altoria_tavern",),
        ),
        "altoria_lodging": (
            "lodging", (3970, 1120), "爐火旅店",
            "human", "female", (),
            ("altoria_lodging",),
        ),
        "altoria_bathhouse": (
            "bathhouse", (4830, 970), "公共浴場",
            "human", "female", (),
            ("altoria_bathhouse",),
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
                        place_dialogue_keys(place),
                    ),
                    expected,
                )

    #: The four altoria-crown-and-watch places pinned at the PLACE registry,
    #: where the map and dwelling contract lives (the HOSPITALITY_PLACE_ROWS
    #: pattern). The palace's host half stays the literal None pair, which is
    #: what keeps an attendant from quietly appearing behind the throne.
    CROWN_WATCH_PLACE_ROWS = {
        "altoria_palace": (
            "palace", (4500, 6350), "王宮",
            None, None, (), (),
        ),
        "altoria_noble_watch": (
            "watch_post", (3500, 4850), "貴族區衛所",
            "human", "male", (),
            ("altoria_noble_watch",),
        ),
        "altoria_drill_yard": (
            "training_ground", (2300, 3820), "校場",
            "human", "male", (),
            ("altoria_drill_yard",),
        ),
        "altoria_guardhouse": (
            "watch_post", (3050, 150), "衛兵駐所",
            "human", "male", (),
            ("altoria_guardhouse",),
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
                        place_dialogue_keys(place),
                    ),
                    expected,
                )

    @covers_requirement(
        "altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard"
    )
    def test_the_palace_row_is_host_less_in_the_shape_hostless_places_reserved(self):
        # The palace's emptiness is its own data contract (the shelter pin's
        # shape): every host scalar None, no capability, no goods.
        palace = PLACE_REGISTRY["altoria_palace"]
        self.assertTrue(place_is_hostless(palace))
        self.assertEqual(palace.kind, "palace")
        self.assertEqual(palace.components, ())
        self.assertEqual(palace.assortment_keys, ())
        self.assertEqual(palace.extra_item_keys, ())
        self.assertEqual(palace.excluded_item_keys, ())
        for field in HOST_IDENTITY_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(palace, field), field)
        # And the derived roster really carries no palace row.
        anchors = {row.spawn_room for row in validate_service_hosts()}
        self.assertNotIn("altoria_palace", anchors)

    #: The three altoria-learning-and-exchange places pinned at the PLACE
    #: registry, where the map and institutional contract lives (the
    #: CROWN_WATCH_PLACE_ROWS pattern).
    LEARNING_EXCHANGE_PLACE_ROWS = {
        "altoria_academy": (
            "academy", (5650, 5200), "王立魔法學院",
            "human", "male", (),
            ("altoria_academy",),
        ),
        "altoria_merchant_hall": (
            "merchant_hall", (5380, 2850), "商會公所",
            "human", "male", (),
            ("altoria_merchant_hall",),
        ),
        "altoria_market_stalls": (
            "market", (2420, 2700), "市集棚",
            None, None, (), (),
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
                        place_dialogue_keys(place),
                    ),
                    expected,
                )

    @covers_requirement(
        "altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls"
    )
    def test_the_stalls_row_is_host_less_in_the_shape_hostless_places_reserved(self):
        # The stalls' emptiness is its own data contract (the palace pin's
        # shape): the same all-or-nothing group wholly absent, so a host
        # cannot quietly appear behind the awnings.
        stalls = PLACE_REGISTRY["altoria_market_stalls"]
        self.assertTrue(place_is_hostless(stalls))
        self.assertEqual(stalls.kind, "market")
        self.assertEqual(stalls.components, ())
        self.assertEqual(stalls.assortment_keys, ())
        self.assertEqual(stalls.extra_item_keys, ())
        self.assertEqual(stalls.excluded_item_keys, ())
        for field in HOST_IDENTITY_FIELDS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(stalls, field), field)
        # And the derived roster carries no stalls row.
        anchors = {row.spawn_room for row in validate_service_hosts()}
        self.assertNotIn("altoria_market_stalls", anchors)

    def test_a_place_declaring_a_person_bound_capability_fails_place_validation(self):
        # A place host anchors at its own room: a person-bound declaration has
        # no meaning on a place record, and validation names the place.
        store = PLACE_REGISTRY["altoria_general_store"]
        broken = replace(
            store,
            key="t_person_bound_place",
            components=(
                capability(
                    "scripted_dialogue",
                    binding=person_bound(),
                    dialogue_key="guild_staff",
                ),
            ),
        )
        with self.assertRaises(ValueError) as caught:
            validate_place_registry({"t_person_bound_place": broken})
        self.assertIn("t_person_bound_place", caught.exception.args[0])


if __name__ == "__main__":
    unittest.main()
