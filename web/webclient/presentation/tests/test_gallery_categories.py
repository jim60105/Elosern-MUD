"""Gallery category sources and subject admission (webclient-gallery-categories).

Characters and companions are created in each test; monster species, variants
and tiers come from the synthetic kit plus file-local factory rows. A met place
is a synthetic terrain region published through the geography fixture, so the
group label comes from the published region view rather than the key.
"""

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import TerrainRoom
from web.webclient.presentation.gallery_categories import (
    CATEGORY_KEYS,
    GalleryCategoryError,
    category_groups,
    category_of_subject,
    gallery_categories,
    is_subject_admitted,
)
from world.lore.wilderness_regions import WildernessRegion
from world.maps import geography as geography_module
from world.maps import wilderness_provider
from world.rules.lore_knowledge import record_species_sighting
from world.rules.met_people import PLACE_REGION, record_person_interaction
from world.rules.party import bound_owner_of
from world.rules.scene_visits import record_scene_entry
from world.tests.geography_fixture import publish_geography
from world.tests.synthetic_data import (
    make_archetype,
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    synthetic_registries,
)

T_LOW = "t_low"
T_HIGH = "t_high"
T_A = "t_a"
T_B = "t_b"
T_C = "t_c"


def _database_state():
    """Every stored object, attribute and tag row, values included."""
    return (
        list(ObjectDB.objects.order_by("id").values_list(
            "id", "db_key", "db_typeclass_path", "db_location_id", "db_account_id"
        )),
        [
            (attribute.id, attribute.db_key, attribute.db_category, repr(attribute.value))
            for attribute in Attribute.objects.order_by("id")
        ],
        list(Tag.objects.order_by("id").values_list("id", "db_key", "db_category")),
    )


def _species_rows(key, tier, name):
    variant_key = f"{key}_v"
    return (
        make_monster_species(key, display_name_zh=name, default_variant_key=variant_key),
        make_monster_variant(
            variant_key,
            species_key=key,
            threat_tier=tier,
            ordinary_variant=True,
            danger_grade=None,
        ),
    )


_ROWS = (
    _species_rows(T_A, T_LOW, "甲測獸"),
    _species_rows(T_B, T_LOW, "乙測獸"),
    _species_rows(T_C, T_HIGH, "丙測獸"),
)
EXTRA = {
    "monster_species": {species.key: species for species, _ in _ROWS},
    "monster_variants": {variant.key: variant for _, variant in _ROWS},
    "monster_tiers": {
        T_LOW: make_monster_tier(T_LOW, display_name_zh="低測級"),
        T_HIGH: make_monster_tier(T_HIGH, display_name_zh="高測級"),
    },
}


@synthetic_registries("monster_species", "monster_variants", "monster_tiers", extra=EXTRA)
class GalleryCategoryTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.characters.add(self.char1)
        self.actor = self.char1

    def _add_character(self, key):
        character = create_object(PlayerCharacter, key=key, location=self.room1)
        character.account = self.account
        self.account.characters.add(character)
        return character

    def _companion(self, key, owner, stable_key=None):
        companion = create_object(NPC, key=key, location=self.room1)
        if stable_key is not None:
            companion.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        return self._enlist(companion, owner)

    def _enlist(self, companion, owner):
        companion.db.party_member = owner.pk
        owner.db.party = [*(owner.db.party or []), companion.pk]
        meta = dict(owner.db.party_meta or {})
        meta[str(companion.pk)] = {"general": True, "reasons": []}
        owner.db.party_meta = meta
        return companion

    def _publish_regions(self, regions):
        """Publish synthetic terrain regions so a place label reads its name."""
        previous = geography_module.current()
        self.addCleanup(publish_geography, previous)
        publish_geography(replace(previous, regions=MappingProxyType(dict(regions))))

    def _terrain(self, key, coordinates):
        room = create_object(TerrainRoom, key=key, location=None)
        room.ndb.active_coordinates = coordinates
        return room

    def _named_npc(self, key):
        # A named NPC never needs to stand in the recorded place, and a fresh
        # object inside a terrain room would trip the wilderness receive hook.
        npc = create_object(NPC, key=key, location=self.room1)
        npc.db.portrait_policy = {"mode": "named", "stable_key": key}
        return npc

    def _meet(self, npc, room, region_key, actor=None):
        actor = actor or self.actor
        actor.location = room
        with patch.object(
            wilderness_provider, "region_for_coordinates", return_value=region_key
        ):
            record_person_interaction(actor, npc)

    def _subject_keys(self, groups):
        return [ref.subject.full() for group in groups for ref in group.subjects]

    def _group(self, key):
        return next(group for group in category_groups(self.actor, "monster") if group.key == key)

    # -- closed category set ------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::the-gallery-has-a-closed-ordered-category-set"
    )
    def test_categories_arrive_in_the_fixed_order(self):
        keys = tuple(category.key for category in gallery_categories(self.actor))
        self.assertEqual(keys, ("mine", "party", "people", "monster", "scene"))
        self.assertEqual(keys, CATEGORY_KEYS)

    @covers_requirement(
        "webclient-gallery-categories::the-gallery-has-a-closed-ordered-category-set"
    )
    def test_every_released_category_is_enabled_without_a_reason(self):
        record_species_sighting(self.actor, T_A)
        by_key = {category.key: category for category in gallery_categories(self.actor)}
        for key in CATEGORY_KEYS:
            self.assertTrue(by_key[key].enabled, key)
            self.assertIsNone(by_key[key].reason, key)
        # scene is enabled but this character has entered no scene yet.
        self.assertEqual(by_key["scene"].count, 0)
        self.assertEqual(category_groups(self.actor, "scene"), ())
        # people is enabled but this character has met nobody yet.
        self.assertEqual(by_key["people"].count, 0)
        self.assertEqual(category_groups(self.actor, "people"), ())
        # The count is listed subjects, not registered species: one sighting.
        self.assertEqual(by_key["monster"].count, 1)
        self.assertEqual(by_key["mine"].count, 1)
        with self.assertRaises(KeyError):
            category_groups(self.actor, "t_unknown_category")

    @covers_requirement(
        "webclient-gallery-categories::the-gallery-has-a-closed-ordered-category-set"
    )
    def test_building_reads_only(self):
        self._companion("同行測者", self.actor, stable_key="t_reader_companion")
        record_species_sighting(self.actor, T_A)

        def build():
            return (
                gallery_categories(self.actor),
                tuple(category_groups(self.actor, key) for key in CATEGORY_KEYS),
                is_subject_admitted(self.actor, f"portrait:monster:{T_B}"),
            )

        build()  # warm attribute caches so both measured runs start alike
        before = _database_state()
        first = build()
        second = build()
        self.assertEqual(first, second)
        # Evennia's account character handler re-saves its unchanged list on
        # every read, so the claim is checked on stored state, not on SQL verbs.
        self.assertEqual(_database_state(), before)

    # -- mine ---------------------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::the-mine-category-lists-the-owning-account-s-characters"
    )
    def test_the_live_character_comes_first(self):
        self._add_character("測者乙")
        self._add_character("測者丙")
        low, mid, high = sorted(self.account.characters.all(), key=lambda char: char.pk)
        self.actor = high
        groups = category_groups(high, "mine")
        self.assertEqual(len(groups), 1)
        self.assertIsNone(groups[0].label)
        refs = groups[0].subjects
        self.assertEqual([ref.entity.pk for ref in refs], [high.pk, low.pk, mid.pk])
        self.assertEqual([ref.is_current for ref in refs], [True, False, False])
        # A character with no named policy is listed under its numeric identity
        # and is admitted.
        self.assertEqual(refs[1].subject.full(), f"portrait:character:{low.pk}")
        self.assertEqual(category_of_subject(high, f"portrait:character:{low.pk}"), "mine")

    @covers_requirement(
        "webclient-gallery-categories::the-mine-category-lists-the-owning-account-s-characters"
    )
    def test_an_invalid_policy_falls_back_to_the_numeric_identity_in_mine(self):
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "bad/key"}
        refs = category_groups(self.actor, "mine")[0].subjects
        self.assertEqual(
            [ref.subject.full() for ref in refs], [f"portrait:character:{self.actor.pk}"]
        )

    @covers_requirement(
        "webclient-gallery-categories::the-mine-category-lists-the-owning-account-s-characters"
    )
    def test_possession_keeps_the_account_characters(self):
        other = self._add_character("測者丁")
        companion = self._companion("附身測者", other, stable_key="t_possessed_companion")
        companion.account = self.account
        companion.db.possessed_by = other.pk
        self.assertEqual(bound_owner_of(companion), other)
        refs = category_groups(companion, "mine")[0].subjects
        self.assertEqual(
            [(ref.entity.pk, ref.is_current) for ref in refs],
            [(other.pk, True), (self.char1.pk, False)],
        )
        self.assertNotIn(companion.pk, [ref.entity.pk for ref in refs])
        # The owning character's party is listed while possessing.
        self.assertEqual(
            self._subject_keys(category_groups(companion, "party")),
            ["portrait:character:t_possessed_companion"],
        )

    def test_possession_without_a_bound_owner_is_refused(self):
        stray = create_object(NPC, key="無主測者", location=self.room1)
        stray.account = self.account
        stray.db.possessed_by = self.char1.pk
        for key in ("mine", "party"):
            with self.assertRaises(GalleryCategoryError):
                category_groups(stray, key)

    # -- party --------------------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::the-party-category-lists-the-owner-s-live-companions"
    )
    def test_party_order_is_kept(self):
        first = create_object(NPC, key="先測者", location=self.room1)
        second = create_object(NPC, key="後測者", location=self.room1)
        for companion, stable_key in ((first, "t_companion_a"), (second, "t_companion_b")):
            companion.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
            companion.db.party_member = self.actor.pk
        self.actor.db.party = [second.pk, first.pk]
        self.actor.db.party_meta = {
            str(second.pk): {"general": True, "reasons": []},
            str(first.pk): {"general": True, "reasons": []},
        }
        groups = category_groups(self.actor, "party")
        self.assertEqual(len(groups), 1)
        self.assertIsNone(groups[0].label)
        self.assertEqual(
            self._subject_keys(groups), ["portrait:character:t_companion_b", "portrait:character:t_companion_a"]
        )

    @covers_requirement(
        "webclient-gallery-categories::the-party-category-lists-the-owner-s-live-companions"
    )
    def test_a_companion_without_a_gallery_subject_is_skipped_alone(self):
        self._companion("無像測者", self.actor)
        self._companion("有像測者", self.actor, stable_key="t_portrait_companion")
        broken = self._companion("壞像測者", self.actor)
        broken.db.portrait_policy = {"mode": "named", "stable_key": "bad/key"}
        self.assertEqual(
            self._subject_keys(category_groups(self.actor, "party")),
            ["portrait:character:t_portrait_companion"],
        )

    # -- people -------------------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::the-people-category-lists-met-named-npcs-grouped-by-place"
    )
    def test_people_groups_follow_recency(self):
        self._publish_regions({
            "t_region_a": WildernessRegion("t_region_a", "測試甲地", None, ()),
            "t_region_b": WildernessRegion("t_region_b", "測試乙地", None, ()),
        })
        room_a = self._terrain("t_room_a", (1, 1))
        room_b = self._terrain("t_room_b", (2, 2))
        npc_a = self._named_npc("t_npc_a")
        npc_b = self._named_npc("t_npc_b")
        npc_c = self._named_npc("t_npc_c")
        self._meet(npc_a, room_a, "t_region_a")  # oldest
        self._meet(npc_c, room_a, "t_region_a")
        self._meet(npc_b, room_b, "t_region_b")  # newest
        # Another player's character is never listed, even when recorded.
        other = self._add_character("他者測者")
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_other_player"}
        self._meet(other, room_b, "t_region_b")

        groups = category_groups(self.actor, "people")
        self.assertEqual(
            [(group.key, group.label) for group in groups],
            [
                (f"{PLACE_REGION}:t_region_b", "測試乙地"),
                (f"{PLACE_REGION}:t_region_a", "測試甲地"),
            ],
        )
        self.assertEqual(
            self._subject_keys(groups),
            [
                "portrait:character:t_npc_b",
                "portrait:character:t_npc_c",
                "portrait:character:t_npc_a",
            ],
        )
        by_key = {category.key: category for category in gallery_categories(self.actor)}
        self.assertEqual(
            (by_key["people"].enabled, by_key["people"].reason, by_key["people"].count),
            (True, None, 3),
        )

    @covers_requirement(
        "webclient-gallery-categories::the-people-category-lists-met-named-npcs-grouped-by-place"
    )
    def test_a_party_member_is_listed_only_under_party(self):
        self._publish_regions({
            "t_region_a": WildernessRegion("t_region_a", "測試甲地", None, ()),
        })
        room = self._terrain("t_room_a", (1, 1))
        npc = self._named_npc("t_npc_b")
        self._meet(npc, room, "t_region_a")
        self.assertEqual(
            self._subject_keys(category_groups(self.actor, "people")),
            ["portrait:character:t_npc_b"],
        )
        self._enlist(npc, self.actor)
        self.assertEqual(category_groups(self.actor, "people"), ())
        self.assertEqual(
            self._subject_keys(category_groups(self.actor, "party")),
            ["portrait:character:t_npc_b"],
        )

    @covers_requirement(
        "webclient-gallery-categories::the-people-category-lists-met-named-npcs-grouped-by-place"
    )
    def test_a_vanished_npc_is_not_listed(self):
        self._publish_regions({
            "t_region_a": WildernessRegion("t_region_a", "測試甲地", None, ()),
            "t_region_b": WildernessRegion("t_region_b", "測試乙地", None, ()),
        })
        room_a = self._terrain("t_room_a", (1, 1))
        room_b = self._terrain("t_room_b", (2, 2))
        npc_a = self._named_npc("t_npc_a")
        npc_b = self._named_npc("t_npc_b")
        self._meet(npc_a, room_a, "t_region_a")
        self._meet(npc_b, room_b, "t_region_b")
        npc_a.delete()
        groups = category_groups(self.actor, "people")
        self.assertEqual([group.key for group in groups], [f"{PLACE_REGION}:t_region_b"])
        self.assertEqual(self._subject_keys(groups), ["portrait:character:t_npc_b"])
        npc_b.delete()
        self.assertEqual(category_groups(self.actor, "people"), ())

    @covers_requirement(
        "webclient-gallery-categories::the-people-category-lists-met-named-npcs-grouped-by-place"
    )
    def test_possession_lists_the_owner_s_people(self):
        self._publish_regions({
            "t_region_a": WildernessRegion("t_region_a", "測試甲地", None, ()),
        })
        owner = self._add_character("測者乙")
        companion = self._companion("附身測者", owner, stable_key="t_possessed_companion")
        companion.account = self.account
        companion.db.possessed_by = owner.pk
        room = self._terrain("t_room_a", (1, 1))
        npc = self._named_npc("t_npc_a")
        self._meet(npc, room, "t_region_a", actor=owner)

        self.assertEqual(bound_owner_of(companion), owner)
        self.assertEqual(
            self._subject_keys(category_groups(companion, "people")),
            ["portrait:character:t_npc_a"],
        )
        self.assertEqual(category_groups(self.actor, "people"), ())

    # -- monster ------------------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::the-monster-category-lists-sighted-species-by-threat-tier"
    )
    def test_unseen_species_get_no_subject(self):
        record_species_sighting(self.actor, T_A)
        group = self._group(T_LOW)
        self.assertEqual(group.label, "低測級")
        self.assertEqual([ref.subject.full() for ref in group.subjects], [f"portrait:monster:{T_A}"])
        self.assertEqual((group.seen, group.total), (1, 2))
        self.assertIsNone(group.subjects[0].entity)

    @covers_requirement(
        "webclient-gallery-categories::the-monster-category-lists-sighted-species-by-threat-tier"
    )
    def test_an_all_unseen_tier_still_draws_its_group(self):
        record_species_sighting(self.actor, T_A)
        groups = category_groups(self.actor, "monster")
        keys = [group.key for group in groups]
        high = groups[keys.index(T_HIGH)]
        self.assertEqual(keys.index(T_HIGH), keys.index(T_LOW) + 1)
        self.assertEqual((high.seen, high.total, high.subjects), (0, 1, ()))

    # -- admission ----------------------------------------------------------

    @covers_requirement(
        "webclient-gallery-categories::admission-is-membership-of-any-enabled-category"
    )
    def test_a_party_companion_is_admitted_whichever_category_is_selected(self):
        self._companion("隊伍測者", self.actor, stable_key="t_admitted_companion")
        self.assertTrue(is_subject_admitted(self.actor, "portrait:character:t_admitted_companion"))
        self.assertEqual(category_of_subject(self.actor, "portrait:character:t_admitted_companion"), "party")

    @covers_requirement(
        "webclient-gallery-categories::admission-is-membership-of-any-enabled-category"
    )
    def test_an_unsighted_species_is_not_admitted(self):
        record_species_sighting(self.actor, T_A)
        self.assertFalse(is_subject_admitted(self.actor, f"portrait:monster:{T_B}"))
        self.assertTrue(is_subject_admitted(self.actor, f"portrait:monster:{T_A}"))
        self.assertFalse(is_subject_admitted(self.actor, "portrait:character:t_nobody"))


T_ARCH = "t_arch"
T_OTHER = "t_other"
T_THIRD = "t_third"
SCENE_EXTRA = {
    "archetypes": {
        T_ARCH: make_archetype(T_ARCH, display_name_zh="甲測景"),
        T_OTHER: make_archetype(T_OTHER, display_name_zh="乙測景"),
        T_THIRD: make_archetype(T_THIRD, display_name_zh="丙測景"),
    },
}


@synthetic_registries("archetypes", extra=SCENE_EXTRA)
class SceneCategoryTests(EvenniaTest):
    """The scene category lists the owning character's entered archetypes."""

    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.characters.add(self.char1)
        self.actor = self.char1

    @covers_requirement(
        "webclient-gallery-categories::the-scene-category-lists-entered-archetypes"
    )
    def test_only_entered_archetypes_are_listed_in_registry_order(self):
        record_scene_entry(self.actor, T_THIRD)
        record_scene_entry(self.actor, T_ARCH)
        groups = category_groups(self.actor, "scene")
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual((group.key, group.label, group.seen, group.total), ("scene", None, None, None))
        self.assertEqual(
            [ref.subject.full() for ref in group.subjects], [f"scene:{T_ARCH}", f"scene:{T_THIRD}"]
        )
        self.assertEqual([ref.display_name for ref in group.subjects], ["甲測景", "丙測景"])
        self.assertTrue(all(ref.entity is None and not ref.is_current for ref in group.subjects))
        by_key = {category.key: category for category in gallery_categories(self.actor)}
        self.assertEqual((by_key["scene"].count, by_key["scene"].enabled), (2, True))

    @covers_requirement(
        "webclient-gallery-categories::the-scene-category-lists-entered-archetypes"
    )
    def test_nothing_entered_lists_nothing(self):
        by_key = {category.key: category for category in gallery_categories(self.actor)}
        self.assertEqual(
            (by_key["scene"].enabled, by_key["scene"].reason, by_key["scene"].count), (True, None, 0)
        )
        self.assertEqual(category_groups(self.actor, "scene"), ())

    @covers_requirement(
        "webclient-gallery-categories::the-scene-category-lists-entered-archetypes"
    )
    def test_an_entered_scene_is_admitted_and_an_unentered_one_is_not(self):
        record_scene_entry(self.actor, T_ARCH)
        self.assertTrue(is_subject_admitted(self.actor, f"scene:{T_ARCH}"))
        self.assertEqual(category_of_subject(self.actor, f"scene:{T_ARCH}"), "scene")
        self.assertFalse(is_subject_admitted(self.actor, f"scene:{T_OTHER}"))

    @covers_requirement(
        "webclient-gallery-categories::the-scene-category-lists-entered-archetypes"
    )
    def test_a_possessed_companion_lists_its_owners_scenes(self):
        record_scene_entry(self.actor, T_OTHER)
        companion = create_object(NPC, key="同行測者", location=self.room1)
        companion.db.party_member = self.actor.pk
        self.actor.db.party = [companion.pk]
        self.actor.db.party_meta = {str(companion.pk): {"general": True, "reasons": []}}
        companion.db.possessed_by = self.actor.pk
        refs = category_groups(companion, "scene")[0].subjects
        self.assertEqual([ref.subject.full() for ref in refs], [f"scene:{T_OTHER}"])
