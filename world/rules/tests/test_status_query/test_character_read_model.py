"""Slice of ``test_status_query``: CharacterReadModelTests.
"""
from collections.abc import Mapping, Sequence
from dataclasses import replace
import unittest
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import apply_buff
from world.rules.combat_session import engage
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
    group_skill_keys,
)
from world.skills.handler import INNATE_SKILL_ORDER
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries
from .._combat_session_helpers import (
    _live_registry,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage`` (the ``universal-action-ownership`` dependency
# direction), so the grouping and split tests import it explicitly to keep
# ``flee`` in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


from ._support import (
    _LOCAL_SKILLS,
    _T_EL_A,
    _T_PASSIVE,
    _actor,
    _element_rows,
    _live_act_registry,
)


class CharacterReadModelTests(EvenniaTestCase):
    def setUp(self):
        # The skill/act catalogues are scoped to the kit rows plus this
        # file's local rows so the split tests name file-local keys; the
        # innate keys and seed acts are re-probed from the live registries
        # inside each assertion.
        open_synthetic_scope(
            self, "skills", "sexual_acts", "elements", "races", "subraces",
            "static_tiers",
        )
        # The element-bearing rows bind to the scope's live element registry,
        # so they are layered in only after the scope is open.
        self.element_keys, self.element_labels, element_rows = _element_rows()
        from world.skills.registry import SKILL_REGISTRY as _skills_view

        patcher = patch.dict(
            _skills_view,
            {**synth_innate_overlay()["skills"], **_LOCAL_SKILLS, **element_rows},
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()
        self.actor = _actor(self)

    def _seed_keys(self):
        """Unlocked-at-baseline act keys under the open scope."""
        return tuple(
            sorted(key for key, act in _live_act_registry().items() if not act.unlock)
        )

    def _traits(self):
        return dict(self.actor.attributes.get("traits", category="traits"))

    def _model(self):
        return build_character_read_model(self.actor)

    def test_reads_gauges_statics_and_counters(self):
        model = self._model()
        self.assertEqual(
            [trait.key for trait in model.traits],
            ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power", "guild_merit"],
        )
        hp = next(trait for trait in model.traits if trait.key == "hp")
        raw_hp = self._traits()["hp"]
        expected_max = int(round((raw_hp["base"] + raw_hp["mod"]) * raw_hp["mult"]))
        self.assertEqual(hp.current, expected_max)
        self.assertEqual(hp.maximum, expected_max)
        atk = next(trait for trait in model.traits if trait.key == "atk_phys")
        self.assertIsNone(atk.maximum)
        self.assertEqual(model.wallet, 0)

    def test_malformed_gauge_base_modifier_and_multiplier_fail_closed(self):
        for field in ("base", "mod", "mult"):
            traits = self._traits()
            traits["hp"] = {**traits["hp"], field: True}
            self.actor.attributes.add("traits", traits, category="traits")
            with self.assertRaises(StatusQueryError):
                self._model()

    def test_gauge_current_validation_fails_closed(self):
        for value in (True, -1, 10**9):
            traits = self._traits()
            traits["hp"]["current"] = value
            self.actor.attributes.add("traits", traits, category="traits")
            with self.assertRaises(StatusQueryError):
                self._model()

    def test_malformed_static_and_counter_traits_fail_closed(self):
        traits = self._traits()
        del traits["atk_phys"]
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()
        traits["atk_phys"] = {"base": True}
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()
        traits["guild_merit"] = {"base": -5}
        self.actor.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_non_sequence_passive_and_junk_accessories_are_skipped(self):
        self.actor.db.skills = {"active": [], "passive": "none"}
        model = self._model()
        self.assertEqual(model.passive_keys, ())
        self.actor.db.equipment = {
            "weapon_main": "t_status_blade",
            "weapon_off": None,
            "armor": None,
            "accessories": ["ring", 5, None],
        }
        model = self._model()
        self.assertEqual(
            [row.slot for row in model.equipment], ["weapon_main", "accessory"]
        )

    def test_malformed_disguise_fails_closed(self):
        self.actor.db.disguised_stats = "yes"
        with self.assertRaises(StatusQueryError):
            self._model()
        self.actor.db.disguised_stats = {"": 5}
        with self.assertRaises(StatusQueryError):
            self._model()
        self.actor.db.disguised_stats = {"atk_phys": True}
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_malformed_wallet_fails_closed(self):
        for value in (True, -1):
            self.actor.db.wallet = value
            with self.assertRaises(StatusQueryError):
                self._model()

    def _materialized_sexual_traits(self, pleasure_base=42, climax_today=2):
        def ordered(key, levels, value):
            return {
                "name": key.title(),
                "trait_type": "ordered_level",
                "value": value,
                "levels": list(levels),
                "min": 0,
                "max": len(levels) - 1,
            }

        return {
            "pleasure": {
                "name": "Pleasure",
                "trait_type": "counter",
                "base": pleasure_base,
                "min": 0,
                "max": 100,
            },
            "wetness": ordered("wetness", WETNESS_LEVELS, 1),
            "shame": ordered("shame", SHAME_LEVELS, 1),
            "exposure": ordered("exposure", EXPOSURE_LEVELS, 1),
            "climax_phase": ordered("climax_phase", CLIMAX_PHASE_LEVELS, 0),
            "climax_today": {
                "name": "Climax Today",
                "trait_type": "counter",
                "base": climax_today,
                "min": 0,
            },
            **{
                key: {
                    "name": key.title(),
                    "trait_type": "counter",
                    "base": 0,
                    "min": 0,
                }
                for key in _LIFETIME_COUNTER_KEYS
            },
        }

    def _materialize_sexual_traits(self, data):
        self.actor.attributes.add("sexual_traits", data, category="traits")

    def test_intimate_view_builds_from_materialized_record(self):
        self._materialize_sexual_traits(self._materialized_sexual_traits())
        model = self._model()
        self.assertEqual(model.intimate.arousal, "中等")
        self.assertEqual(model.intimate.wetness, "微濕")
        self.assertEqual(model.intimate.shame, "輕微")
        self.assertEqual(model.intimate.exposure, "低")
        self.assertEqual(model.intimate.climax_phase, "未達")
        self.assertEqual(model.intimate.climax_today, 2)

    def test_intimate_view_resolves_from_baseline_only(self):
        self.actor.db.sexual = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
            "climax_today": 2,
            "virgin": False,
            "sensitivity": {},
            "experience_types": frozenset(),
        }
        model = self._model()
        self.assertEqual(model.intimate.arousal, "中等")
        self.assertEqual(model.intimate.climax_today, 2)
        self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))

    def test_intimate_view_is_none_without_any_record(self):
        model = self._model()
        self.assertIsNone(model.intimate)

    def test_partial_materialized_record_fails_closed(self):
        data = self._materialized_sexual_traits()
        del data["climax_today"]
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_malformed_materialized_level_entries_fail_closed(self):
        # A truncated `levels` list (still non-empty, so the trait
        # deserializer accepts it) is rejected because it does not match
        # the field's fixed vocabulary.
        data = self._materialized_sexual_traits()
        data["wetness"]["levels"] = list(WETNESS_LEVELS[:2])
        data["wetness"]["max"] = 1
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits()
        data["shame"]["levels"] = list(reversed(list(SHAME_LEVELS)))
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits()
        data["exposure"]["value"] = True
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits()
        data["climax_phase"]["value"] = 99
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_malformed_pleasure_counter_fails_closed(self):
        data = self._materialized_sexual_traits()
        data["pleasure"] = "junk"
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits()
        data["pleasure"]["base"] = True
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits(pleasure_base=101)
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

        data = self._materialized_sexual_traits(pleasure_base=-3)
        self._materialize_sexual_traits(data)
        with self.assertRaises(StatusQueryError):
            self._model()

    def test_malformed_baseline_climax_today_fails_closed(self):
        baseline = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
            "virgin": False,
            "sensitivity": {},
            "experience_types": frozenset(),
        }
        for value in (True, -2, "2"):
            self.actor.db.sexual = {**baseline, "climax_today": value}
            with self.assertRaises(StatusQueryError):
                self._model()

    def test_build_model_has_no_attribute_side_effects(self):
        # The no-create read model must not create, materialize, or rewrite
        # any Attribute. Snapshots compare the `traits` and `sexual_traits`
        # attributes before and after the build; nested sequences are
        # normalized to tuples so the trait deserializer's in-memory
        # mutations (list-to-tuple) do not mask a genuine rewrite.

        def normalized(value):
            if isinstance(value, Mapping):
                return {key: normalized(item) for key, item in value.items()}
            if isinstance(value, Sequence) and not isinstance(value, str):
                return tuple(normalized(item) for item in value)
            return value

        def snapshot():
            return {
                "traits": normalized(
                    self.actor.attributes.get("traits", category="traits")
                ),
                "sexual_traits": normalized(
                    self.actor.attributes.get("sexual_traits", default=None, category="traits")
                ),
            }

        before = snapshot()
        self._model()
        self.assertEqual(snapshot(), before)
        self.assertIsNone(snapshot()["sexual_traits"])

        self.actor.db.sexual = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
            "climax_today": 2,
            "virgin": False,
            "sensitivity": {},
            "experience_types": frozenset(),
        }
        before = snapshot()
        self._model()
        self.assertEqual(snapshot(), before)
        self.assertIsNone(snapshot()["sexual_traits"])

        self._materialize_sexual_traits(self._materialized_sexual_traits())
        before = snapshot()
        self._model()
        self.assertEqual(snapshot(), before)

    def test_fresh_character_active_keys_include_innate_skills(self):
        # Regression for the shipped defect: the innate grants are
        # contributed by ``owned_keys()`` and never written into
        # ``entity.db.skills``, so they must surface from the corrected
        # owned-keys read instead of disappearing from the panel. The
        # unconditionally-owned seed acts are ACTIVE-kind and follow the
        # innates in ``owned_keys()`` order (both vocabularies probed live).
        model = self._model()
        self.assertEqual(
            model.active_keys, (*INNATE_SKILL_ORDER, *self._seed_keys())
        )
        self.assertEqual(model.passive_keys, ())

    def test_split_reads_keys_contributed_by_the_handler_beyond_storage(self):
        # Regression guard for the owned-acts contract: a key unlocked by the
        # sexual state (as the future unlocked sexual acts are) must surface
        # even though it is never written into db.skills. The patched
        # unlocked_act_keys_for simulates such a registry extension.
        self.actor.db.skills = {"active": [_T_EL_A], "passive": []}
        # The split lives in the read-model package's readers module; the
        # patch targets the module where ``unlocked_act_keys_for`` is bound.
        from world.rules.status_query import readers as status_query

        with patch.object(
            status_query,
            "unlocked_act_keys_for",
            return_value=frozenset({_T_PASSIVE}),
        ):
            model = self._model()
        self.assertEqual(model.active_keys, (_T_EL_A, *INNATE_SKILL_ORDER))
        self.assertEqual(model.passive_keys, (_T_PASSIVE,))

    def test_split_unknown_key_degrades_to_its_stored_bucket(self):
        self.actor.db.skills = {"active": [], "passive": ["no_such_skill"]}
        model = self._model()
        self.assertEqual(
            model.active_keys, (*INNATE_SKILL_ORDER, *self._seed_keys())
        )
        self.assertEqual(model.passive_keys, ("no_such_skill",))
        self.actor.db.skills = {"active": ["also_missing"], "passive": []}
        model = self._model()
        self.assertEqual(
            model.active_keys,
            ("also_missing", *INNATE_SKILL_ORDER, *self._seed_keys()),
        )
        self.assertEqual(model.passive_keys, ())

    def test_split_ignores_non_string_entries_in_stored_lists(self):
        self.actor.db.skills = {
            "active": [5, _T_EL_A],
            "passive": [None, _T_PASSIVE],
        }
        model = self._model()
        self.assertEqual(
            model.active_keys, (_T_EL_A, *INNATE_SKILL_ORDER, *self._seed_keys())
        )
        self.assertEqual(model.passive_keys, (_T_PASSIVE,))

    def test_split_routes_known_keys_by_registry_kind(self):
        # The local PASSIVE-kind row is stored in the active list; registry
        # kind wins over the stored bucket for known keys.
        self.actor.db.skills = {"active": [_T_PASSIVE], "passive": [_T_EL_A]}
        model = self._model()
        self.assertEqual(
            model.active_keys, (_T_EL_A, *INNATE_SKILL_ORDER, *self._seed_keys())
        )
        self.assertEqual(model.passive_keys, (_T_PASSIVE,))

    def test_split_de_duplicates_keys_across_both_stored_lists(self):
        # ``owned_keys()`` is a plain concatenation that does not de-duplicate;
        # the split must not render (or count) a repeated key twice.
        self.actor.db.skills = {
            "active": [_T_EL_A, _T_EL_A],
            "passive": [_T_EL_A, _T_PASSIVE],
        }
        model = self._model()
        self.assertEqual(
            model.active_keys, (_T_EL_A, *INNATE_SKILL_ORDER, *self._seed_keys())
        )
        self.assertEqual(model.passive_keys, (_T_PASSIVE,))

    def test_trait_key_union_matches_the_client_attribute_allowlist(self):
        # Pinned contract: the four true-attribute keys the WebClient's
        # CharacterStatusDrawer.vue ATTRIBUTE_KEYS allowlist hardcodes
        # (web/webclient-app/components/CharacterStatusDrawer.vue). If a
        # fifth key is ever added to _STATIC_KEYS or _COUNTER_KEYS, this
        # test fails by name and forces a conscious, lockstep update of the
        # client allowlist rather than a silent gap in the 屬性 section.
        from world.rules import status_query

        self.assertEqual(
            tuple(k for k in status_query._STATIC_KEYS + status_query._COUNTER_KEYS if k != "guild_merit"),
            ("atk_phys", "agility", "defense", "magic_power"),
        )
