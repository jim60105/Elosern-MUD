"""Behavior tests for the divine veil cast path (divine-veil-cast-path).

Covers the deterministic veil recipe (displayed combat five derived from the
race registry's mundane bands), the provenance record written beside the
display layer, and the provenance-scoped cast semantics: a cast at another
entity applies the derived veil, while a cast at the actor toggles only
against a veil this verb itself placed (a DIVINE veil is lifted, a mundane
or absent one is refreshed). The shared preview accepts the skill with an
empty ``event_context``, and a rolled-back resolution restores the display
mapping and the provenance byte-equal together.

All skills are file-local synthetic rows; no shipped-content skill names and
no data-contract tagging appear here.
"""

from tools.spec_traceability import covers_requirement

import unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.races import RACE_REGISTRY
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
    _snapshot_touched,
)
from world.rules.action_preview import preview_skill
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.skill_effects import (
    DISGUISE_PROVENANCE_DIVINE,
    DISGUISE_PROVENANCE_MUNDANE,
    apply_divine_disguise,
    apply_disguise_effect,
    clear_disguise_effect,
    disguise_provenance_of,
    mundane_veil_values,
    record_disguise_provenance,
)
from world.rules.targeting import RoomActionContext
from world.rules.traits import get_display_value
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import make_skill

from ._combat_session_helpers import open_synthetic_scope

_DISPLAYED_COMBAT_FIVE = ("atk_phys", "agility", "defense", "magic_power", "hp")

# File-local synthetic cast rows: the SELF veil and its SINGLE-target twin
# (the bestowed-veil shape), both zero-cost and context-free.
_T_VEIL = make_skill(
    "t_veil_cast", effects=["set_disguise"], target_spec=TargetSpec.SELF, cost={}
)
_T_VEIL_OTHER = make_skill(
    "t_veil_bestow",
    effects=["set_disguise"],
    target_spec=TargetSpec.SINGLE,
    cost={},
)


class _FakeDB:
    """Attribute-proxy double: a missing attribute reads as None."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)

    def __getattr__(self, name):
        return None


class _FakeEntity:
    def __init__(self, **attrs):
        self.db = _FakeDB(**attrs)


class VeilRecipeTests(unittest.TestCase):
    """The derivation rule: five keys at the mundane ceilings, registry-fed."""

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_recipe_returns_integers_for_exactly_the_displayed_five(self):
        values = mundane_veil_values()
        self.assertEqual(set(values), set(_DISPLAYED_COMBAT_FIVE))
        for key in _DISPLAYED_COMBAT_FIVE:
            self.assertIs(type(values[key]), int, key)

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_recipe_renders_each_key_at_the_top_of_the_mundane_band(self):
        human = RACE_REGISTRY["human"]
        values = mundane_veil_values()
        self.assertEqual(values["atk_phys"], human.static_baseline.atk_phys[1])
        self.assertEqual(values["agility"], human.static_baseline.agility[1])
        self.assertEqual(values["defense"], human.static_baseline.defense[1])
        self.assertEqual(values["magic_power"], human.static_baseline.magic_power[1])
        self.assertEqual(values["hp"], human.vital_baseline.hp[1])

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_changing_a_registry_band_changes_the_recipe_output(self):
        human = RACE_REGISTRY["human"]
        retuned = replace(
            human,
            static_baseline=replace(human.static_baseline, atk_phys=(1, 77)),
        )
        with patch.dict(RACE_REGISTRY, {"human": retuned}):
            self.assertEqual(mundane_veil_values()["atk_phys"], 77)
        # The other axes are untouched by the retune.
        self.assertEqual(
            mundane_veil_values()["atk_phys"],
            human.static_baseline.atk_phys[1],
        )


class VeilProvenanceRecordTests(unittest.TestCase):
    """The record beside the display mapping and its mundane default."""

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_absent_record_reads_as_mundane(self):
        entity = _FakeEntity()
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_MUNDANE)

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_divine_record_reads_divine_and_every_other_value_reads_mundane(self):
        entity = _FakeEntity()
        record_disguise_provenance(entity, DISGUISE_PROVENANCE_DIVINE)
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_DIVINE)
        entity.db.disguise_provenance = DISGUISE_PROVENANCE_MUNDANE
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_MUNDANE)
        entity.db.disguise_provenance = "foreign"
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_MUNDANE)

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_divine_write_records_provenance_beside_the_derived_mapping(self):
        entity = _FakeEntity()
        apply_divine_disguise(entity)
        self.assertEqual(entity.db.disguised_stats, mundane_veil_values())
        self.assertEqual(entity.db.disguise_provenance, DISGUISE_PROVENANCE_DIVINE)

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_clear_removes_the_layer_and_its_provenance_together(self):
        entity = _FakeEntity()
        apply_divine_disguise(entity)
        clear_disguise_effect(entity)
        self.assertIsNone(entity.db.disguised_stats)
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_MUNDANE)

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_narrow_write_primitive_only_touches_the_display_mapping(self):
        entity = _FakeEntity()
        apply_disguise_effect(entity, {"atk_phys": 60})
        self.assertEqual(entity.db.disguised_stats, {"atk_phys": 60})
        self.assertEqual(disguise_provenance_of(entity), DISGUISE_PROVENANCE_MUNDANE)


class _VeilCastTestCase(EvenniaTest):
    """Live-human cast fixture: the recipe reads the shipped human bands, so
    the cast tests run against the unscoped race registry (the same choice as
    the cast-settlement suite)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "skills",
            extra={"skills": {_T_VEIL.key: _T_VEIL, _T_VEIL_OTHER.key: _T_VEIL_OTHER}},
        )
        self.caster = create_object(PlayerCharacter, key="veil-caster")
        self.caster.race = "human"
        self.caster.apply_race_baseline()
        self.target = create_object(PlayerCharacter, key="veil-target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.caster.location = self.room1
        self.target.location = self.room1
        self.caster.db.skills = {
            "active": [_T_VEIL.key, _T_VEIL_OTHER.key],
            "passive": [],
        }

    def _cast(self, skill_key, *, targets=None, actor=None, event_context=None):
        actor = actor or self.caster
        return ActionResolver.resolve(
            ActionRequest(
                actor,
                skill_key,
                list(targets or []),
                RoomActionContext(actor.location, event_context or {}),
            )
        )

    def _true_traits(self, entity):
        return deepcopy(dict(entity.traits.trait_data))


class DivineVeilCastResolutionTests(_VeilCastTestCase):
    """Cast semantics: self toggles against a divine veil only; other applies."""

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_self_cast_with_empty_context_veils_the_caster_at_derived_values(self):
        before = self._true_traits(self.caster)
        result = self._cast(_T_VEIL.key)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.caster.db.disguised_stats, mundane_veil_values())
        self.assertEqual(
            disguise_provenance_of(self.caster), DISGUISE_PROVENANCE_DIVINE
        )
        # Display reads the derived values; every true trait is unchanged.
        self.assertEqual(get_display_value(self.caster, "atk_phys"), mundane_veil_values()["atk_phys"])
        self.assertEqual(self._true_traits(self.caster), before)
        self.assertIn(
            "disguise_set", [entry.kind for entry in result.event_log.entries]
        )

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_second_self_cast_lifts_only_the_divine_veil(self):
        self._cast(_T_VEIL.key)
        before = self._true_traits(self.caster)
        result = self._cast(_T_VEIL.key)
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.caster.attributes.has("disguised_stats"))
        self.assertFalse(self.caster.attributes.has("disguise_provenance"))
        self.assertEqual(disguise_provenance_of(self.caster), DISGUISE_PROVENANCE_MUNDANE)
        for key in _DISPLAYED_COMBAT_FIVE:
            self.assertEqual(
                get_display_value(self.caster, key),
                getattr(self.caster.traits, key).value,
            )
        self.assertEqual(self._true_traits(self.caster), before)
        self.assertIn(
            "disguise_lifted", [entry.kind for entry in result.event_log.entries]
        )

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_self_cast_over_an_authored_mundane_veil_refreshes_instead_of_lifting(self):
        # The shipped-preset case: the character card starts the game wearing
        # an authored disguise declaration with no provenance record.
        self.caster.db.disguised_stats = {"atk_phys": 7, "agility": 9}
        result = self._cast(_T_VEIL.key)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.caster.db.disguised_stats, mundane_veil_values())
        self.assertEqual(
            disguise_provenance_of(self.caster), DISGUISE_PROVENANCE_DIVINE
        )

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_other_cast_veils_the_target_and_leaves_the_caster_alone(self):
        caster_before = self._true_traits(self.caster)
        result = self._cast(_T_VEIL_OTHER.key, targets=[self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.db.disguised_stats, mundane_veil_values())
        self.assertEqual(
            disguise_provenance_of(self.target), DISGUISE_PROVENANCE_DIVINE
        )
        self.assertIsNone(self.caster.db.disguised_stats)
        self.assertEqual(self._true_traits(self.caster), caster_before)
        self.assertEqual(
            get_display_value(self.caster, "atk_phys"),
            getattr(self.caster.traits, "atk_phys").value,
        )

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_other_cast_on_an_already_veiled_target_refreshes_instead_of_lifting(self):
        first = self._cast(_T_VEIL_OTHER.key, targets=[self.target])
        self.assertEqual(first.outcome, "success")
        second = self._cast(_T_VEIL_OTHER.key, targets=[self.target])
        self.assertEqual(second.outcome, "success")
        self.assertEqual(self.target.db.disguised_stats, mundane_veil_values())
        self.assertEqual(
            disguise_provenance_of(self.target), DISGUISE_PROVENANCE_DIVINE
        )
        self.assertNotIn(
            "disguise_lifted", [entry.kind for entry in second.event_log.entries]
        )

    @covers_requirement("skill-handler::the-狀態偽裝-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_single_spec_cast_at_self_toggles_like_a_self_cast(self):
        # A bestowed-veil-shaped SINGLE skill aimed at the caster binds the
        # actor, so the divine toggle applies (N1 contract).
        self._cast(_T_VEIL.key)
        result = self._cast(_T_VEIL_OTHER.key, targets=[self.caster])
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.caster.attributes.has("disguised_stats"))
        self.assertIn(
            "disguise_lifted", [entry.kind for entry in result.event_log.entries]
        )


class DivineVeilPreviewTests(_VeilCastTestCase):
    """The shared preview no longer advertises and then refuses the skill."""

    @covers_requirement("effect-context-validation::effect-handlers-declare-their-required-event-context")
    def test_preview_with_empty_context_reports_no_missing_effect_context(self):
        preview = preview_skill(
            self.caster, _T_VEIL.key, RoomActionContext(self.room1, {})
        )
        self.assertTrue(preview.enabled)
        self.assertIsNot(preview.reason, RejectReason.MISSING_EFFECT_CONTEXT)

    @covers_requirement("effect-context-validation::effect-handlers-declare-their-required-event-context")
    def test_preview_in_combat_shape_with_empty_context_is_enabled(self):
        field = Battlefield(
            {
                "party": frozenset({self.caster.key}),
                "foes": frozenset({self.target.key}),
            },
            {self.caster.key: self.caster, self.target.key: self.target},
        )
        preview = preview_skill(
            self.caster,
            _T_VEIL.key,
            BattlefieldActionContext(field),
            [self.target, self.caster],
        )
        self.assertTrue(preview.enabled)
        self.assertIsNot(preview.reason, RejectReason.MISSING_EFFECT_CONTEXT)


class DivineVeilRollbackTests(_VeilCastTestCase):
    """A rolled-back resolution restores the layer and provenance together."""

    def _failing_effect(self, entity):
        return PendingEffect(
            entity,
            "injected failure",
            frozenset({"traits"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_apply_path_rolls_back_layer_and_provenance_byte_equal(self):
        before = _snapshot_touched(self.caster, frozenset({"traits"}))
        effects = [
            PendingEffect(
                self.caster,
                "disguise_set|veil-caster",
                frozenset({"traits"}),
                lambda: apply_divine_disguise(self.caster),
            ),
            self._failing_effect(self.caster),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char=str(self.caster.pk), action="test_disguise")
        self.assertEqual(
            _snapshot_touched(self.caster, frozenset({"traits"})), before
        )
        # The typeclass shell pre-initializes ``disguised_stats`` to None, so
        # the restored state is the shell default, not attribute absence.
        self.assertIsNone(self.caster.db.disguised_stats)
        self.assertFalse(self.caster.attributes.has("disguise_provenance"))

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_lift_path_rolls_back_layer_and_provenance_byte_equal(self):
        apply_divine_disguise(self.target)
        before = _snapshot_touched(self.target, frozenset({"traits"}))
        effects = [
            PendingEffect(
                self.target,
                "disguise_lifted|veil-target",
                frozenset({"traits"}),
                lambda: clear_disguise_effect(self.target),
            ),
            self._failing_effect(self.target),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char=str(self.caster.pk), action="test_disguise")
        self.assertEqual(
            _snapshot_touched(self.target, frozenset({"traits"})), before
        )
        self.assertEqual(self.target.db.disguised_stats, mundane_veil_values())
        self.assertEqual(
            disguise_provenance_of(self.target), DISGUISE_PROVENANCE_DIVINE
        )


if __name__ == "__main__":
    unittest.main()