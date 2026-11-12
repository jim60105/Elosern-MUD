"""Gallery category sources and subject admission (webclient-gallery-categories).

Characters and companions are created in each test; monster species, variants
and tiers come from the synthetic kit plus file-local factory rows.
"""

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from web.webclient.presentation.gallery_categories import (
    CATEGORY_KEYS,
    GalleryCategoryError,
    category_groups,
    category_of_subject,
    gallery_categories,
    is_subject_admitted,
)
from world.rules.lore_knowledge import record_species_sighting
from world.rules.party import bound_owner_of
from world.tests.synthetic_data import (
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
        companion.db.party_member = owner.pk
        owner.db.party = [*(owner.db.party or []), companion.pk]
        meta = dict(owner.db.party_meta or {})
        meta[str(companion.pk)] = {"general": True, "reasons": []}
        owner.db.party_meta = meta
        return companion

    def _subject_keys(self, groups):
        return [ref.subject.full() for group in groups for ref in group.subjects]

    def _group(self, key):
        return next(group for group in category_groups(self.actor, "monster") if group.key == key)

    # -- closed category set ------------------------------------------------

    def test_categories_arrive_in_the_fixed_order(self):
        keys = tuple(category.key for category in gallery_categories(self.actor))
        self.assertEqual(keys, ("mine", "party", "people", "monster", "scene"))
        self.assertEqual(keys, CATEGORY_KEYS)

    def test_unreleased_categories_are_disabled_with_a_reason(self):
        record_species_sighting(self.actor, T_A)
        by_key = {category.key: category for category in gallery_categories(self.actor)}
        for key in ("people", "scene"):
            self.assertFalse(by_key[key].enabled)
            self.assertTrue(by_key[key].reason)
            self.assertEqual(by_key[key].count, 0)
            self.assertEqual(category_groups(self.actor, key), ())
        for key in ("mine", "party", "monster"):
            self.assertTrue(by_key[key].enabled)
            self.assertIsNone(by_key[key].reason)
        # The count is listed subjects, not registered species: one sighting.
        self.assertEqual(by_key["monster"].count, 1)
        self.assertEqual(by_key["mine"].count, 1)
        with self.assertRaises(KeyError):
            category_groups(self.actor, "t_unknown_category")

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

    def test_a_companion_without_a_gallery_subject_is_skipped_alone(self):
        self._companion("無像測者", self.actor)
        self._companion("有像測者", self.actor, stable_key="t_portrait_companion")
        broken = self._companion("壞像測者", self.actor)
        broken.db.portrait_policy = {"mode": "named", "stable_key": "bad/key"}
        self.assertEqual(
            self._subject_keys(category_groups(self.actor, "party")),
            ["portrait:character:t_portrait_companion"],
        )

    # -- monster ------------------------------------------------------------

    def test_unseen_species_get_no_subject(self):
        record_species_sighting(self.actor, T_A)
        group = self._group(T_LOW)
        self.assertEqual(group.label, "低測級")
        self.assertEqual([ref.subject.full() for ref in group.subjects], [f"portrait:monster:{T_A}"])
        self.assertEqual((group.seen, group.total), (1, 2))
        self.assertIsNone(group.subjects[0].entity)

    def test_an_all_unseen_tier_still_draws_its_group(self):
        record_species_sighting(self.actor, T_A)
        groups = category_groups(self.actor, "monster")
        keys = [group.key for group in groups]
        high = groups[keys.index(T_HIGH)]
        self.assertEqual(keys.index(T_HIGH), keys.index(T_LOW) + 1)
        self.assertEqual((high.seen, high.total, high.subjects), (0, 1, ()))

    # -- admission ----------------------------------------------------------

    def test_a_party_companion_is_admitted_whichever_category_is_selected(self):
        self._companion("隊伍測者", self.actor, stable_key="t_admitted_companion")
        self.assertTrue(is_subject_admitted(self.actor, "portrait:character:t_admitted_companion"))
        self.assertEqual(category_of_subject(self.actor, "portrait:character:t_admitted_companion"), "party")

    def test_an_unsighted_species_is_not_admitted(self):
        record_species_sighting(self.actor, T_A)
        self.assertFalse(is_subject_admitted(self.actor, f"portrait:monster:{T_B}"))
        self.assertTrue(is_subject_admitted(self.actor, f"portrait:monster:{T_A}"))
        self.assertFalse(is_subject_admitted(self.actor, "portrait:character:t_nobody"))
