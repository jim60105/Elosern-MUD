"""Load-contract tests for the fixed-title registry (title-system D2/D3).

The registry is immutable module-level data validated at import; these tests
exercise the pure validator with injected faces so every failure mode — a
dangling quest key, a duplicate key, a family carrying someone else's
parameter, a malformed threshold — is provable without mutating the shipped
rows or the startup sync order.
"""

import dataclasses
import unittest

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.titles import (
    FIXED_TITLE_REGISTRY,
    MAX_TITLE_DISPLAY_CODE_POINTS,
    STARTER_EPITHET,
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
    TitleRegistryError,
    _FAMILY_PARAMETER,
    _live_faces,
    validate_fixed_titles,
)

# One valid parameter value per family against the fixture faces below.
_FAMILY_SAMPLE = {
    TitlePredicateFamily.LINEAGE_COMPLETE: ("root_skill_key", "root_a"),
    TitlePredicateFamily.MASTERY_OWNED: ("element", "fire"),
    TitlePredicateFamily.FIRST_KILL_TIER: ("monster_tier", "high"),
    TitlePredicateFamily.QUEST_COMPLETED: ("quest_key", "quest_a"),
    TitlePredicateFamily.GUILD_RANK_REACHED: ("guild_rank", "F"),
    TitlePredicateFamily.SEXUAL_EXPERIENCE: ("experience_type", "自慰"),
    TitlePredicateFamily.COUNTER_THRESHOLD: ("counter", "watched_count"),
}

# Which injected face validates which predicate parameter.
_FACE_KEY = {
    "root_skill_key": "skill_keys",
    "element": "elements",
    "monster_tier": "monster_tiers",
    "quest_key": "quest_keys",
    "guild_rank": "guild_ranks",
    "experience_type": "experience_types",
}


def _row(
    key="t_row",
    family=TitlePredicateFamily.GUILD_RANK_REACHED,
    threshold=None,
    **params,
):
    """One registry row carrying exactly ``family``'s parameter values."""
    fields = dict(params)
    if threshold is not None:
        fields["threshold"] = threshold
    return FixedTitleDef(
        key,
        "測試稱號",
        TitleCategory.GUILD,
        "一段說明這枚稱號來由的風味文字。",
        "完成測試即可獲得。",
        TitlePredicate(family=family, **fields),
    )


def _faces(**overrides):
    faces = {
        "elements": {"fire"},
        "monster_tiers": {"high"},
        "guild_ranks": set(GUILD_RANK_REGISTRY),
        "quest_keys": {"quest_a"},
        "experience_types": {"自慰"},
        "skill_keys": {"root_a"},
    }
    faces.update(overrides)
    return faces


class FixedTitleRegistryContentTests(unittest.TestCase):
    """The shipped rows: the seven authorized guild pairings and nothing else."""

    def test_registry_holds_exactly_the_guild_pairings(self):
        self.assertEqual(
            set(FIXED_TITLE_REGISTRY),
            {definition.title_key for definition in GUILD_RANK_REGISTRY.values()},
        )

    def test_pairing_is_one_to_one_in_both_directions(self):
        for rank, definition in GUILD_RANK_REGISTRY.items():
            with self.subTest(rank=rank):
                # Rank keys are uppercase, title keys lowercase by convention.
                self.assertEqual(definition.title_key, f"g_{rank.lower()}_rank")
                row = FIXED_TITLE_REGISTRY[definition.title_key]
                self.assertEqual(row.key, definition.title_key)
                self.assertIs(row.predicate.family, TitlePredicateFamily.GUILD_RANK_REACHED)
                self.assertEqual(row.predicate.guild_rank, rank)
        keyed = {
            definition.title_key: definition.key
            for definition in GUILD_RANK_REGISTRY.values()
        }
        self.assertEqual(len(keyed), len(GUILD_RANK_REGISTRY))
        for key, rank in keyed.items():
            self.assertEqual(FIXED_TITLE_REGISTRY[key].predicate.guild_rank, rank)

    def test_rows_are_categorized_displayed_and_prosed(self):
        displays = set()
        for entry in FIXED_TITLE_REGISTRY.values():
            with self.subTest(key=entry.key):
                self.assertIsInstance(entry.category, TitleCategory)
                self.assertIs(entry.category, TitleCategory.GUILD)
                self.assertTrue(entry.display_name_zh.strip())
                self.assertTrue(entry.flavor_zh.strip())
                self.assertTrue(entry.hint_zh.strip())
                displays.add(entry.display_name_zh)
        self.assertEqual(len(displays), len(FIXED_TITLE_REGISTRY))

    def test_rows_and_predicates_are_frozen(self):
        entry = FIXED_TITLE_REGISTRY["g_f_rank"]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            entry.display_name_zh = "改名"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            entry.predicate.guild_rank = "S"
        self.assertTrue(dataclasses.is_dataclass(entry))

    def test_starter_epithet_is_a_frozen_display_and_basis_pair(self):
        self.assertIsInstance(STARTER_EPITHET, StarterEpithet)
        self.assertTrue(STARTER_EPITHET.display.strip())
        self.assertTrue(STARTER_EPITHET.origin_basis.strip())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            STARTER_EPITHET.display = "改名"

    def test_shipped_rows_validate_against_the_live_faces(self):
        self.assertIsNone(
            validate_fixed_titles(list(FIXED_TITLE_REGISTRY.values()), **_live_faces())
        )

    def test_registry_publication_is_immutable(self):
        # Consumers read through the mapping protocol; in-place lore mutation
        # is impossible on the published proxy.
        with self.assertRaises(TypeError):
            FIXED_TITLE_REGISTRY["g_tampered"] = _row(key="g_tampered")
        with self.assertRaises(AttributeError):
            FIXED_TITLE_REGISTRY.update({})
        self.assertNotIn("g_tampered", FIXED_TITLE_REGISTRY)


class FixedTitleValidatorTests(unittest.TestCase):
    """Every load-contract rule, with faces injected instead of mutated."""

    def test_every_family_validates_with_its_own_parameter(self):
        for family, (field, value) in _FAMILY_SAMPLE.items():
            with self.subTest(family=family.value):
                threshold = 5 if field == "counter" else None
                row = _row(
                    family=family, threshold=threshold, **{field: value}
                )
                self.assertIsNone(validate_fixed_titles([row], **_faces()))

    def test_every_declared_family_is_validated(self):
        self.assertEqual(set(_FAMILY_PARAMETER), set(TitlePredicateFamily))
        fields = {field.name for field in dataclasses.fields(TitlePredicate)}
        for parameter in _FAMILY_PARAMETER.values():
            self.assertIn(parameter, fields)

    def test_each_face_rejects_its_own_dangling_reference(self):
        for family, (field, value) in _FAMILY_SAMPLE.items():
            if field in ("quest_key", "counter"):
                continue  # quest has its own message test; counter has no face
            with self.subTest(face=field):
                row = _row(key=f"t_{field}", family=family, **{field: value})
                with self.assertRaises(TitleRegistryError) as caught:
                    validate_fixed_titles([row], **_faces(**{_FACE_KEY[field]: set()}))
                message = str(caught.exception)
                self.assertIn(f"t_{field}", message)
                self.assertIn(value, message)

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles(
                [_row(), _row(family=TitlePredicateFamily.MASTERY_OWNED, element="fire")],
                **_faces(),
            )
        self.assertIn("duplicate", str(caught.exception))

    def test_duplicate_display_names_are_rejected(self):
        # ``equip_fixed`` resolves display names, so two rows sharing one
        # display make equip ambiguous.
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles(
                [
                    _row(key="t_a"),
                    _row(
                        key="t_b",
                        family=TitlePredicateFamily.MASTERY_OWNED,
                        element="fire",
                    ),
                ],
                **_faces(),
            )
        self.assertIn("display collision", str(caught.exception))
        self.assertIn("t_b", str(caught.exception))

    def test_key_colliding_with_another_rows_display_is_rejected(self):
        first = _row(key="alpha")
        second = _row(
            key="測試稱號",
            family=TitlePredicateFamily.MASTERY_OWNED,
            element="fire",
        )
        object.__setattr__(second, "display_name_zh", "第二稱號")
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([first, second], **_faces())
        self.assertIn("key collision", str(caught.exception))
        self.assertIn("測試稱號", str(caught.exception))

    def test_a_row_may_share_its_own_key_and_display(self):
        row = _row(key="測試稱號", guild_rank="F")
        self.assertIsNone(validate_fixed_titles([row], **_faces()))

    def test_oversized_display_names_are_rejected(self):
        row = _row(key="t_long", guild_rank="F")
        object.__setattr__(row, "display_name_zh", "長" * (MAX_TITLE_DISPLAY_CODE_POINTS + 1))
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([row], **_faces())
        self.assertIn("t_long", str(caught.exception))
        # The bound itself is bankable content.
        object.__setattr__(row, "display_name_zh", "長" * MAX_TITLE_DISPLAY_CODE_POINTS)
        self.assertIsNone(validate_fixed_titles([row], **_faces()))

    def test_non_registry_row_is_rejected(self):
        with self.assertRaises(TitleRegistryError):
            validate_fixed_titles([{"key": "t_dict"}], **_faces())

    def test_missing_required_parameter_is_rejected(self):
        row = FixedTitleDef(
            "t_bare",
            "測試稱號",
            TitleCategory.GUILD,
            "風味文字。",
            "提示文字。",
            TitlePredicate(family=TitlePredicateFamily.MASTERY_OWNED),
        )
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([row], **_faces())
        self.assertIn("requires 'element'", str(caught.exception))

    def test_foreign_parameter_is_rejected(self):
        row = _row(
            key="t_greedy",
            family=TitlePredicateFamily.GUILD_RANK_REACHED,
            guild_rank="F",
            element="fire",
        )
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([row], **_faces())
        self.assertIn("unexpected parameters", str(caught.exception))
        self.assertIn("t_greedy", str(caught.exception))

    def test_threshold_shape_is_enforced(self):
        counter = TitlePredicateFamily.COUNTER_THRESHOLD
        bad = (
            _row(key="t_none", family=counter, counter="orgasms"),
            _row(key="t_zero", family=counter, counter="orgasms", threshold=0),
            _row(key="t_float", family=counter, counter="orgasms", threshold=2.5),
            _row(key="t_bool", family=counter, counter="orgasms", threshold=True),
            _row(key="t_text", family=counter, counter="orgasms", threshold="3"),
        )
        for row in bad:
            with self.subTest(key=row.key), self.assertRaises(TitleRegistryError):
                validate_fixed_titles([row], **_faces())
        # A threshold on any other family is equally invalid.
        misplaced = _row(
            key="t_misplaced",
            family=TitlePredicateFamily.MASTERY_OWNED,
            element="fire",
            threshold=3,
        )
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([misplaced], **_faces())
        self.assertIn("t_misplaced", str(caught.exception))

    def test_unknown_predicate_family_is_rejected(self):
        row = _row(key="t_strange")
        object.__setattr__(row.predicate, "family", "not_a_family")
        with self.assertRaises(TitleRegistryError) as caught:
            validate_fixed_titles([row], **_faces())
        self.assertIn("not_a_family", str(caught.exception))

    def test_blank_text_fields_are_rejected(self):
        cases = (
            ("display_name_zh", ""),
            ("flavor_zh", ""),
            ("hint_zh", ""),
            ("key", ""),
        )
        for field, blank in cases:
            with self.subTest(field=field):
                row = _row(key="t_blank")
                object.__setattr__(row, field, blank)
                with self.assertRaises(TitleRegistryError):
                    validate_fixed_titles([row], **_faces())

    def test_non_enum_category_is_rejected(self):
        row = _row(key="t_category")
        object.__setattr__(row, "category", "guild")
        with self.assertRaises(TitleRegistryError):
            validate_fixed_titles([row], **_faces())


