"""Frozen combat-session view model tests (tasks 1.4)."""

import importlib
from dataclasses import fields, replace
import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.combat_session import engage
from world.rules.combat_view import (
    CATEGORY_LABELS,
    CombatViewError,
    ROOT_ACTIONS,
    SECONDARY_ACTIONS,
    SkillCategory,
    SkillDescriptorView,
    build_combat_view,
    group_skill_views,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_LADDER,
    PROFICIENCY_TIP_CAP,
    scaled_mp_cost,
)
from world.lore.elements import Element
from world.skills.effects import EffectAudience, EffectPolicy
from world.skills.effects import combat as effects_combat
from world.skills.effects import passives as effects_passives
from world.skills.effects import sexual as effects_sexual
from world.skills.effects.polarity import (
    EFFECT_TARGET_POLARITY,
    POLARITY_CLASSES,
    skill_target_polarity,
)
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

from ._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)

_T_CAST = SYNTH_SKILLS["t_ember_burst"]
_T_AREA = SYNTH_SEAM_AREA_SKILL
_T_PASSIVE = SYNTH_SKILLS["t_steady_stride"]
_T_ELEMENT = _T_CAST.element.key
# Zero-cost, no-target passive: the "owned but never a descriptor" fixture.
_T_FOCUS = make_skill("t_focus_focus", label="斂息")
# A second elemental spell, borrowed for the expensive-spell case only.
_T_STORM = replace(
    _T_CAST,
    key="t_ember_cascade",
    label="燼焰傾瀑",
    description="連貫的燼焰一波接一波地淹沒目標。",
    cost={"mp": 30},
)


def _mastery_key() -> str:
    """The element-mastery passive key the production entitlement derives.

    ``progression.freeform_mastery_entitled`` hardcodes ``f"{element}_mastery"``
    — a production vocabulary, like the innate attack/flee keys. The row is
    built from the synthetic passive template under that runtime-derived key
    (the ``synth_innate_overlay`` precedent), so the test never names the
    shipped mastery identifier literally.
    """
    return f"{_T_ELEMENT}_mastery"


def _mastery_row():
    return replace(
        SYNTH_SKILLS["t_steady_stride"],
        key=_mastery_key(),
        label="合成元素精通",
        description="對該元素達到最高造詣的合成被動。",
        effects=["passive_trait:element_mastery"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_T_ELEMENT,
    )


# A shape-eligible spell on the kit's synthetic element — the second element
# of the patched registry, so it is the cross-element fixture for both the
# freeform gate and the sub-group ordering. The Element instance bypasses the
# pre-patch string resolution while the patched registry knows the key.
_T_GLOW = replace(
    _T_CAST,
    key="t_glow_spire",
    label="光沼尖刺",
    description="自光沼抽出一根尖刺貫穿目標。",
    element=Element("t_glowmire", "光沼", "Synthetic element."),
    group="t_glowmire",
    effects=["damage:t_glowmire:magic"],
)


def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


def _open_scope(test):
    open_synthetic_scope(
        test,
        "skills",
        "elements",
        "sexual_acts",
        "races",
        "subraces",
        "static_tiers",
        extra={
            "skills": {
                **synth_innate_overlay()["skills"],
                _T_AREA.key: _T_AREA,
                _mastery_row().key: _mastery_row(),
                _T_STORM.key: _T_STORM,
                _T_FOCUS.key: _T_FOCUS,
                _T_GLOW.key: _T_GLOW,
            }
        },
    )


def _innate_keys() -> tuple[str, str]:
    return (
        _live_registry("world.rules.disengage", "FLEE_SKILL_KEY"),
        _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY"),
    )


def _owned(*rows) -> dict[str, list[str]]:
    """A ``db.skills`` payload carrying the given rows in active/passive order."""
    return {
        "active": [row.key for row in rows if row.kind is SkillKind.ACTIVE],
        "passive": [row.key for row in rows if row.kind is SkillKind.PASSIVE],
    }


def _descriptor(skill) -> SkillDescriptorView:
    """Build one minimal frozen skill descriptor from a SkillDef."""
    return SkillDescriptorView(
        key=skill.key,
        label=skill.label,
        description=skill.description,
        cost=dict(skill.cost),
        target_spec=skill.target_spec.value,
        element=skill.element.key if skill.element is not None else None,
        category=skill.category.value,
        group=skill.group,
        enabled=True,
        reason_code=None,
        reason_message=None,
        valid_target_ids=(),
        shorthands=(),
        freeform_scales=(),
        hostile=False,
        beneficial=False,
    )


def _skills(*skills) -> tuple[SkillDescriptorView, ...]:
    return tuple(_descriptor(skill) for skill in skills)


class CombatViewTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="view arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST.key], [_T_PASSIVE.key])
        self.monster = _monster()
        self.monster.location = self.room

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_view_preserves_persisted_participant_order_and_tokens(self):
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        self.assertFalse(view.recovery)
        self.assertEqual(view.session.mode, "hostile")
        self.assertEqual(view.session.round, 0)
        self.assertEqual(view.session.state, "ready")
        self.assertIsNone(view.session.reason)
        self.assertEqual(
            [(p.token, p.team, p.identity) for p in view.participants],
            [("a1", "party", self.player.pk), ("e1", "foes", self.monster.pk)],
        )
        self.assertEqual(view.root_actions, ROOT_ACTIONS)
        self.assertEqual(view.secondary_actions, SECONDARY_ACTIONS)
        entities = {int(self.player.pk): self.player, int(self.monster.pk): self.monster}
        for participant in view.participants:
            self.assertEqual(
                participant.portrait_ref, str(participant.identity)
            )
            self.assertGreater(participant.identity, 0)
            self.assertEqual(participant.state, "active")
            # The view mirrors each participant's own trait ceiling, whatever
            # the fixture race/tier baseline produced.
            self.assertEqual(
                participant.hp_maximum, entities[int(participant.identity)].traits.hp.max
            )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_skills_follow_handler_order_and_exclude_passives(self):
        # The synthetic rows carry no prerequisite closure, so the stored
        # active order stays the grant order: AREA skill, then the spell.
        grant_lineage(
            self.player,
            [_T_AREA.key, _T_CAST.key],
            [_T_PASSIVE.key],
        )
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        keys = [skill.key for skill in view.skills]
        flee_key, attack_key = _innate_keys()
        act_registry = _live_registry(
            "world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY"
        )
        self.assertEqual(
            keys,
            [
                _T_AREA.key,
                _T_CAST.key,
                flee_key,
                attack_key,
                *sorted(
                    key
                    for key, act in act_registry.items()
                    if not act.unlock
                ),
            ],
        )
        self.assertNotIn(_T_PASSIVE.key, keys)
        wind = next(skill for skill in view.skills if skill.key == _T_AREA.key)
        self.assertEqual(wind.target_spec, "area")
        # With free targeting every approved shorthand expands to valid
        # candidates, so all three are exposed as conveniences.
        self.assertEqual(wind.shorthands, ("all-enemies", "all-allies", "all"))
        self.assertTrue(wind.enabled)
        # With ANY scope every relation passes the faction check, so the
        # actor itself is also a valid explicit target for the area skill.
        self.assertEqual(wind.valid_target_ids, (self.player.pk, self.monster.pk))
        fire = next(skill for skill in view.skills if skill.key == _T_CAST.key)
        self.assertEqual(fire.cost, dict(_T_CAST.cost))
        self.assertEqual(fire.element, _T_ELEMENT)

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_freeform_scales_only_for_a_masters_eligible_spells(self):
        self.player.db.skills = _owned(_T_AREA, _T_FOCUS)
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == _T_AREA.key)
        self.assertEqual(wind.freeform_scales, ())
        focus = next(skill for skill in view.skills if skill.key == _T_FOCUS.key)
        self.assertEqual(focus.freeform_scales, ())

        # The full ladder shows only with the spell itself at the top rung.
        # Nobody consumes the synthetic spell, so its derived tip cap is the
        # global cap; the expected entries are computed from the same ladder
        # authority instead of pinned numbers.
        top_level = max(min_level for _, min_level in FREEFORM_SCALE_LADDER)
        assert top_level <= PROFICIENCY_TIP_CAP
        grant_lineage(
            self.player,
            [_T_AREA.key, _T_FOCUS.key],
            [_mastery_key()],
            rungs={_T_AREA.key: top_level},
        )
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == _T_AREA.key)
        base_mp = int(_T_AREA.cost["mp"])
        # At the top rung under the global tip cap, every canonical scale is
        # allowed — computed from the shared ladder/cost authorities, never
        # pinned as literals.
        self.assertEqual(
            wind.freeform_scales,
            tuple(
                (scale, label, scaled_mp_cost(base_mp, scale))
                for scale, label in FREEFORM_CAST_SCALES
            ),
        )
        focus = next(skill for skill in view.skills if skill.key == _T_FOCUS.key)
        self.assertEqual(focus.freeform_scales, ())

        # Element mastery never advertises scales for another element's spells.
        self.player.db.skills = _owned(_T_GLOW, _mastery_row())
        view = build_combat_view(self.player)
        light = next(skill for skill in view.skills if skill.key == _T_GLOW.key)
        self.assertEqual(light.freeform_scales, ())

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_disabled_skill_keeps_stable_reason(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == _T_CAST.key)
        self.assertFalse(fire.enabled)
        self.assertEqual(fire.reason_code, "insufficient_resource")
        self.assertTrue(fire.reason_message.strip())
        self.assertTrue(fire.label.strip())
        self.assertTrue(fire.description.strip())

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_spell_descriptor_ignores_numeric_magic_power(self):
        """magic-xp-engine-retirement: no numeric tier gate on descriptors."""
        grant_lineage(self.player, [_T_STORM.key])
        self.player.traits.mp.base = 50
        self.player.traits.mp.current = 50
        engage(self.player, self.monster)

        # An owned, affordable spell stays enabled at any static magic_power:
        # interim eligibility is ownership + MP only.
        self.player.traits.magic_power.base = 15
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == _T_STORM.key)
        self.assertTrue(fire.enabled)

        self.player.traits.magic_power.base = 30
        view = build_combat_view(self.player)
        fire = next(skill for skill in view.skills if skill.key == _T_STORM.key)
        self.assertTrue(fire.enabled)

    @covers_requirement("webclient-combat-menu::menu-target-shorthands-are-convenience-ui")
    def test_any_skill_offers_companion_as_explicit_target_alongside_shorthands(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="view companion", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        grant_lineage(self.player, [_T_AREA.key, _T_CAST.key])
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        wind = next(skill for skill in view.skills if skill.key == _T_AREA.key)
        self.assertTrue(wind.enabled)
        # The menu's all-enemies shorthand remains a convenience, while the
        # freely-targetable skill also lists the ally companion as an explicit
        # target — the shorthand neither widens nor narrows the scope.
        self.assertEqual(wind.shorthands, ("all-enemies", "all-allies", "all"))
        self.assertIn(self.monster.pk, wind.valid_target_ids)
        self.assertIn(companion.pk, wind.valid_target_ids)
        fire = next(skill for skill in view.skills if skill.key == _T_CAST.key)
        self.assertIn(companion.pk, fire.valid_target_ids)

    @covers_requirement("webclient-combat-menu::combat-context-actions-are-an-exact-read-only-panel")
    def test_view_is_read_only(self):
        engage(self.player, self.monster)
        before = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
            "mp": self.player.traits.mp.current,
        }
        view = build_combat_view(self.player)
        self.assertTrue(view.participants)
        after = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
            "mp": self.player.traits.mp.current,
        }
        self.assertEqual(before, after)

    @covers_requirement(
        "player-combat-session::all-personal-skill-choices-and-costs-are-actor-scoped"
    )
    def test_view_parameterized_for_actor_and_unauthorized_rejection(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="view companion 2", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        grant_lineage(companion, [_T_CAST.key])
        engage(self.player, self.monster)

        # Authorized companion view
        comp_view = build_combat_view(self.player, for_actor=companion)
        self.assertIn(_T_CAST.key, [s.key for s in comp_view.skills])

        # Unauthorized view: enemy as for_actor
        with self.assertRaises(CombatViewError):
            build_combat_view(self.player, for_actor=self.monster)

    @covers_requirement('npc-identity-titles::compact-presentation-rows-keep-the-plain-npc-name')
    def test_titled_npc_participant_row_stays_plain_name(self):
        # npc-title-identity-core compact-row pin: the combat panel renders
        # the plain key even when the participant carries a title, so a later
        # change cannot widen this surface silently.
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="塞提斯", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        companion.npc_title = "南門守衛"
        join_party(companion, self.player)
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        row = next(p for p in view.participants if p.identity == companion.pk)
        self.assertEqual(row.display_name, "塞提斯")
        self.assertNotIn("\u3000", row.display_name)
        self.assertNotIn("南門守衛", row.display_name)

    def _condition_scope(self, codes):
        """Synthetic buff definitions plus literal display metadata.

        Every code but ``t_unlisted`` gets a display row, so a buff on that
        definition exercises the missing-metadata path.
        """
        from world.rules.buffs.definitions import BuffDefinition

        displays = {
            "t_ash_burn": ("合成灼燒", "harmful"),
            "t_moss_veil": ("合成苔幕", "beneficial"),
            **{f"t_mark_{index}": (f"合成印記{index}", "warning") for index in range(10)},
        }
        definitions = {
            code: BuffDefinition(
                key=code, duration=30, tick_interval=None, stacking="refresh",
                modifiers={}, polarity="buff",
            )
            for code in codes
        }

        def display(code):
            label, severity = displays[code]
            return SimpleNamespace(label=label, severity=severity)

        from world.rules.status_display import MissingDisplayMetadataError

        def strict_display(code):
            if code not in displays:
                raise MissingDisplayMetadataError(code)
            return display(code)

        patcher = patch.dict("world.rules.buffs.BUFF_DEFINITIONS", definitions)
        patcher.start()
        self.addCleanup(patcher.stop)
        display_patch = patch(
            "world.rules.status_query.status.display_for", side_effect=strict_display
        )
        display_patch.start()
        self.addCleanup(display_patch.stop)

    @staticmethod
    def _apply(entity, *codes):
        from world.rules.buffs import apply_buff

        for code in codes:
            apply_buff(entity, code)

    def _row(self, view, entity):
        return next(p for p in view.participants if p.identity == entity.pk)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_participants_carry_their_status_conditions(self):
        from typeclasses.npcs import NPC
        from world.rules.combat_view import ConditionRow
        from world.rules.party import join_party

        self._condition_scope(["t_ash_burn", "t_moss_veil"])
        companion = create_object(NPC, key="view companion", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        engage(self.player, self.monster)
        self._apply(self.monster, "t_ash_burn")
        self._apply(companion, "t_moss_veil")
        stored = dict(self.monster.attributes.get("buffs"))
        view = build_combat_view(self.player)
        self.assertEqual(
            self._row(view, self.monster).conditions,
            (ConditionRow("t_ash_burn", "合成灼燒", "harmful"),),
        )
        self.assertEqual(
            self._row(view, companion).conditions,
            (ConditionRow("t_moss_veil", "合成苔幕", "beneficial"),),
        )
        self.assertEqual(self._row(view, self.player).conditions, ())
        # Reading conditions leaves the stored buff state untouched.
        self.assertEqual(dict(self.monster.attributes.get("buffs")), stored)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_more_than_eight_conditions_keep_the_first_eight_in_order(self):
        codes = [f"t_mark_{index}" for index in range(10)]
        self._condition_scope(codes)
        engage(self.player, self.monster)
        self._apply(self.monster, *codes)
        view = build_combat_view(self.player)
        self.assertEqual(
            [row.code for row in self._row(view, self.monster).conditions],
            codes[:8],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_unmodelled_or_unlabelled_conditions_give_an_empty_list(self):
        self._condition_scope(["t_ash_burn", "t_unlisted"])
        from world.rules import combat_view
        from world.rules.status_query import StatusQueryError

        engage(self.player, self.monster)
        self._apply(self.monster, "t_ash_burn", "t_unlisted")
        self._apply(self.player, "t_ash_burn")
        # A condition without display metadata (MissingDisplayMetadataError)
        # empties that participant's list; the other participant keeps its row.
        view = build_combat_view(self.player)
        self.assertFalse(view.recovery)
        self.assertEqual(self._row(view, self.monster).conditions, ())
        self.assertEqual(
            [row.code for row in self._row(view, self.player).conditions],
            ["t_ash_burn"],
        )
        # An entity the read model does not model (StatusQueryError).
        real = combat_view.build_status_read_model

        def unmodelled(entity):
            if entity.pk == self.monster.pk:
                raise StatusQueryError("unmodelled")
            return real(entity)

        with patch.object(combat_view, "build_status_read_model", side_effect=unmodelled):
            view = build_combat_view(self.player)
        self.assertFalse(view.recovery)
        self.assertEqual(self._row(view, self.monster).conditions, ())

    def test_an_over_bound_condition_label_empties_only_that_list(self):
        from world.rules import combat_view
        from world.rules.status_query.models import ConditionValue

        engage(self.player, self.monster)
        real = combat_view.build_status_read_model

        def long_label(entity):
            model = real(entity)
            if entity.pk != self.monster.pk:
                return model
            row = ConditionValue(
                code="t_mark", label="長" * (combat_view.MAX_PARTICIPANT_CONDITION_LABEL + 1),
                severity="warning", remaining_seconds=None, modifiers={},
                provenance=None,
            )
            return replace(model, conditions=(row,))

        with patch.object(combat_view, "build_status_read_model", side_effect=long_label):
            view = build_combat_view(self.player)
        self.assertFalse(view.recovery)
        self.assertEqual(self._row(view, self.monster).conditions, ())

    def test_condition_rows_have_no_owner_only_visibility_to_filter(self):
        """Design D2 tripwire: the status rows carry no visibility facet.

        Participant conditions reach the opposing player unfiltered because
        the status read model has no hidden or owner-only flag. A new field
        on either record fails here so the disclosure decision is revisited.
        """
        from world.rules.status_display import ConditionDisplay
        from world.rules.status_query.models import ConditionValue

        self.assertEqual(
            {field.name for field in fields(ConditionDisplay)},
            {"code", "label", "severity"},
        )
        self.assertEqual(
            {field.name for field in fields(ConditionValue)},
            {"code", "label", "severity", "remaining_seconds", "modifiers", "provenance"},
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_descriptors_carry_target_polarity(self):
        engage(self.player, self.monster)
        view = build_combat_view(self.player)
        cast = next(skill for skill in view.skills if skill.key == _T_CAST.key)
        # The kit cast is a single elemental damage spell.
        self.assertEqual((cast.hostile, cast.beneficial), (True, False))
        flee_key, _ = _innate_keys()
        flee = next(skill for skill in view.skills if skill.key == flee_key)
        self.assertEqual((flee.hostile, flee.beneficial), (False, False))

    def test_no_session_raises_view_error(self):
        with self.assertRaises(CombatViewError):
            build_combat_view(self.player)

    def test_unreconstructable_participant_yields_recovery_view(self):
        engage(self.player, self.monster)
        self.monster.delete()
        view = build_combat_view(self.player)
        self.assertTrue(view.recovery)
        self.assertIsNotNone(view.session.reason)
        self.assertEqual(view.root_actions, ())
        self.assertEqual(view.secondary_actions, ("forfeit",))
        self.assertEqual(view.participants, ())
        self.assertEqual(view.skills, ())

    def test_participant_states_fled_knocked_out_and_defeated(self):
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        engage(self.player, self.monster)
        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [self.monster.pk],
            }
        )
        _persist(self.player, record)
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "fled")

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [],
                "knocked_out_ids": [self.monster.pk],
            }
        )
        _persist(self.player, record)
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "knocked_out")

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "fled_ids": [],
                "knocked_out_ids": [],
            }
        )
        _persist(self.player, record)
        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertEqual(monster_view.state, "defeated")

    def test_hp_maximum_falls_back_when_trait_max_missing(self):
        engage(self.player, self.monster)
        from unittest.mock import patch

        with patch.object(type(self.monster.traits.hp), "max", None, create=True):
            view = build_combat_view(self.player)
        monster_view = next(
            p for p in view.participants if p.identity == self.monster.pk
        )
        self.assertGreaterEqual(monster_view.hp_maximum, 1)


class GroupSkillViewsTests(unittest.TestCase):
    """Pure ``group_skill_views()`` grouping and ordering tests (task 5.1).

    Runs inside a kit scope (opened per test via ``_open_scope``) so the
    synthetic rows it classifies exist in the patched registries the module
    reads — the grouping itself never consults shipped content.
    """

    def setUp(self):
        _open_scope(self)
        super().setUp()

    def _categories(self, *rows):
        return group_skill_views(_skills(*rows))

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_category_order_follows_enum_declaration_not_ownership(self):
        # The martial arts skill is granted before the elemental one, but the
        # enum declares elemental_magic before martial_arts.
        martial = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_iron_fist",
            label="鐵拳",
            description="剛猛的合成拳術。",
            category=SkillCategory.MARTIAL_ARTS,
        )
        groups = self._categories(martial, _T_CAST)
        self.assertEqual(
            [category.category for category in groups],
            ["elemental_magic", "martial_arts"],
        )
        self.assertEqual(
            [category.label for category in groups],
            [CATEGORY_LABELS[SkillCategory.ELEMENTAL_MAGIC],
             CATEGORY_LABELS[SkillCategory.MARTIAL_ARTS]],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_elemental_sub_groups_follow_registry_order(self):
        # The borrowed-element spell is owned first, but the patched element
        # registry declares the kit element first, so the kit sub-group must
        # come first regardless of ownership order.
        borrowed_key = _T_ELEMENT
        groups = self._categories(_T_GLOW, _T_CAST)
        elemental = next(
            category for category in groups if category.category == "elemental_magic"
        )
        self.assertEqual(
            [sub_group.group for sub_group in elemental.groups],
            ["t_glowmire", borrowed_key],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_enhancement_sub_groups_follow_tag_order(self):
        # Enhancement sub-groups follow fixed order: None -> 天賦 -> 身法,
        # independent of ownership order.
        step = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_step",
            label="瞬步測試",
            category=SkillCategory.ENHANCEMENT,
            group="身法",
        )
        boon = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_boon",
            label="天賦測試",
            category=SkillCategory.ENHANCEMENT,
            group="天賦",
        )
        untagged = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_untagged",
            label="強化測試",
            category=SkillCategory.ENHANCEMENT,
            group=None,
        )
        groups = self._categories(step, boon, untagged)
        enh = next(c for c in groups if c.category == "enhancement")
        self.assertEqual(
            [g.group for g in enh.groups],
            [None, "天賦", "身法"],
        )
        self.assertEqual(
            [g.label for g in enh.groups],
            [None, "天賦", "身法"],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_holy_rite_sub_groups_follow_tag_order(self):
        # Holy rite sub-groups follow fixed order: None -> "聖禮",
        # independent of ownership order.
        tagged = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_rite_tagged",
            label="聖禮測試",
            category=SkillCategory.HOLY_RITE,
            group="聖禮",
        )
        untagged = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_rite_untagged",
            label="聖儀測試",
            category=SkillCategory.HOLY_RITE,
            group=None,
        )
        groups = self._categories(tagged, untagged)
        holy_rite = next(c for c in groups if c.category == "holy_rite")
        self.assertEqual(
            [g.group for g in holy_rite.groups],
            [None, "聖禮"],
        )
        self.assertEqual(
            [g.label for g in holy_rite.groups],
            [None, "聖禮"],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_category_with_zero_owned_skills_is_omitted(self):
        groups = self._categories(_T_CAST)
        self.assertNotIn(
            "sexual_act", [category.category for category in groups]
        )
        self.assertNotIn(
            "divine_mystery", [category.category for category in groups]
        )
        self.assertNotIn(
            "movement", [category.category for category in groups]
        )
        self.assertNotIn(
            "innate_gift", [category.category for category in groups]
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_no_group_category_emits_one_null_keyed_sub_group(self):
        groups = self._categories(SYNTH_SKILLS["t_cinder_cleave"])
        martial = next(
            category for category in groups if category.category == "martial_arts"
        )
        self.assertEqual(len(martial.groups), 1)
        self.assertIsNone(martial.groups[0].group)
        self.assertIsNone(martial.groups[0].label)
        self.assertEqual(
            [skill.key for skill in martial.groups[0].skills],
            [SYNTH_SKILLS["t_cinder_cleave"].key],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_owned_keys_order_is_preserved_within_each_sub_group(self):
        groups = self._categories(_T_CAST, _T_STORM, _T_GLOW)
        elemental = next(
            category for category in groups if category.category == "elemental_magic"
        )
        fire = next(
            sub_group
            for sub_group in elemental.groups
            if sub_group.group == _T_ELEMENT
        )
        self.assertEqual(
            [skill.key for skill in fire.skills],
            [_T_CAST.key, _T_STORM.key],
        )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_sexual_act_sub_groups_follow_first_seen_order(self):
        # The 燼祭 line is granted before the 合成 lines, so 燼祭 must lead
        # even though it sorts after 合成.
        first = replace(SYNTH_SKILLS["t_hush_brush"], key="t_ember_rite", group="t_燼祭")
        second = replace(
            SYNTH_SKILLS["t_hush_brush"], key="t_hush_song", group="t_合成"
        )
        third = replace(SYNTH_SKILLS["t_hush_brush"], key="t_quiet_touch", group="t_甲組")
        fourth = replace(
            SYNTH_SKILLS["t_hush_brush"], key="t_still_breath", group="t_乙組"
        )
        groups = self._categories(first, second, third, fourth)
        sexual = next(
            category for category in groups if category.category == "sexual_act"
        )
        self.assertEqual(
            [sub_group.label for sub_group in sexual.groups],
            ["t_燼祭", "t_合成", "t_甲組", "t_乙組"],
        )

    def test_sexual_act_null_group_skill_is_not_dropped(self):
        # A sexual_act skill without a group still gets presented in its own
        # null-keyed sub-group instead of being silently omitted.
        bare = _descriptor(SYNTH_SKILLS["t_hush_brush"])
        descriptor = SkillDescriptorView(
            key=bare.key,
            label=bare.label,
            description=bare.description,
            cost=bare.cost,
            target_spec=bare.target_spec,
            element=bare.element,
            category=bare.category,
            group=None,
            enabled=True,
            reason_code=None,
            reason_message=None,
            valid_target_ids=(),
            shorthands=(),
            freeform_scales=(),
            hostile=False,
            beneficial=False,
        )
        groups = group_skill_views((descriptor,))
        sexual = next(
            category for category in groups if category.category == "sexual_act"
        )
        self.assertEqual(len(sexual.groups), 1)
        self.assertIsNone(sexual.groups[0].group)
        self.assertIsNone(sexual.groups[0].label)
        self.assertEqual(
            [skill.key for skill in sexual.groups[0].skills],
            [SYNTH_SKILLS["t_hush_brush"].key],
        )

    def test_empty_skills_yield_no_categories(self):
        self.assertEqual(group_skill_views(()), ())


# Synthetic buff polarities for the pure classification cases: the lookup the
# polarity function receives instead of the live buff registry.
_T_BUFF_POLARITY = {"t_ward": "buff", "t_hex": "debuff"}.__getitem__


def _polar(key, effects, *, audiences=None, target_spec=TargetSpec.SINGLE):
    """One synthetic active row with the given effects and audiences."""
    policies = (
        ()
        if audiences is None
        else tuple(EffectPolicy(audience=audience) for audience in audiences)
    )
    return make_skill(
        key, effects=list(effects), effect_policies=policies, target_spec=target_spec
    )


class SkillTargetPolarityTests(unittest.TestCase):
    """Pure target-side polarity of skill descriptors (context_actions v6)."""

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_ten_skill_cases_read_their_declared_polarity(self):
        cases = (
            ("t_strike", ["damage:none:physical"], None, (True, False)),
            ("t_mend", ["heal:single"], None, (False, True)),
            ("t_purge", ["cleanse:status"], None, (False, True)),
            ("t_curse", ["buff_apply:t_hex"], None, (True, False)),
            ("t_sap", ["gauge_transfer:mp:drain:fixed:5"], None, (True, False)),
            ("t_tease", ["stimulus:target"], None, (True, False)),
            ("t_bless", ["buff_apply:t_ward"], None, (False, True)),
            (
                "t_scatter",
                ["damage:none:magic"],
                (EffectAudience.ENEMIES,),
                (False, False),
            ),
            ("t_glide", ["movement:flight"], None, (False, False)),
            ("t_mixed", ["damage:none:physical", "heal:single"], None, (True, True)),
        )
        for key, effects, audiences, expected in cases:
            with self.subTest(key=key):
                skill = _polar(key, effects, audiences=audiences)
                self.assertEqual(
                    skill_target_polarity(skill, _T_BUFF_POLARITY), expected
                )

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_gauge_restore_and_actor_bound_effects(self):
        restore = _polar("t_refill", ["gauge_transfer:mp:restore:fixed:5"])
        self.assertEqual(skill_target_polarity(restore), (False, True))
        # An actor-only stimulus and the actor's own self-heal never reach
        # the chosen targets.
        actor_only = _polar("t_self_tease", ["stimulus:actor", "self_heal"])
        self.assertEqual(skill_target_polarity(actor_only), (False, False))
        # A self-routed damage component does not count either.
        self_routed = _polar(
            "t_recoil", ["damage:none:physical"], audiences=(EffectAudience.SELF,)
        )
        self.assertEqual(skill_target_polarity(self_routed), (False, False))

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_self_skill_with_selected_hostile_effect_reads_hostile(self):
        skill = _polar(
            "t_penance", ["damage:none:physical"], target_spec=TargetSpec.SELF
        )
        self.assertEqual(skill_target_polarity(skill), (True, False))

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_every_effect_kind_is_classified_exactly_once(self):
        produced = {
            obj
            for module in (effects_combat, effects_passives, effects_sexual)
            for _, obj in inspect.getmembers(module, inspect.isclass)
            if obj.__module__ == module.__name__
            and hasattr(obj, "__dataclass_fields__")
        }
        parser = importlib.import_module("world.skills.effects.parser")
        parsed_kinds = {
            obj
            for obj in vars(parser).values()
            if inspect.isclass(obj) and obj.__name__.endswith("Effect")
        }
        self.assertEqual(parsed_kinds, produced)
        self.assertEqual(set(EFFECT_TARGET_POLARITY), produced)
        self.assertTrue(set(EFFECT_TARGET_POLARITY.values()) <= POLARITY_CLASSES)

    def test_rulebook_fallback_agrees_with_the_loaded_buff_definitions(self):
        import sys

        from world.rules.buffs import BUFF_DEFINITIONS
        from world.skills.effects import polarity

        loaded = {key: definition.polarity for key, definition in BUFF_DEFINITIONS.items()}
        polarity._rulebook_buff_polarities.cache_clear()
        with patch.dict(sys.modules, {"world.rules.buffs": None}):
            fallback = {key: polarity._loaded_buff_polarity(key) for key in loaded}
            with self.assertRaises(KeyError):
                polarity._loaded_buff_polarity("t_no_such_buff")
        self.assertEqual(fallback, loaded)

    def test_unclassified_kind_fails_closed(self):
        skill = SimpleNamespace(
            parsed_effects=(object(),), effect_policies=(EffectPolicy(),)
        )
        with self.assertRaises(KeyError):
            skill_target_polarity(skill)


if __name__ == "__main__":
    unittest.main()
