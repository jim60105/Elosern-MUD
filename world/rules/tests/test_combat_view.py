"""Frozen combat-session view model tests (tasks 1.4)."""

import importlib
from dataclasses import replace
import unittest

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
from world.skills.registry import SkillKind
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
        # The movement skill is granted before the elemental one, but the
        # enum declares elemental_magic before movement.
        movement = replace(
            SYNTH_SKILLS["t_cinder_cleave"],
            key="t_gale_blink",
            label="馭風殘影",
            description="化作一縷風殘影位移的合成身法。",
            category=SkillCategory.MOVEMENT,
        )
        groups = self._categories(movement, _T_CAST)
        self.assertEqual(
            [category.category for category in groups],
            ["elemental_magic", "movement"],
        )
        self.assertEqual(
            [category.label for category in groups],
            [CATEGORY_LABELS[SkillCategory.ELEMENTAL_MAGIC],
             CATEGORY_LABELS[SkillCategory.MOVEMENT]],
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
    def test_category_with_zero_owned_skills_is_omitted(self):
        groups = self._categories(_T_CAST)
        self.assertNotIn(
            "sexual_act", [category.category for category in groups]
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


if __name__ == "__main__":
    unittest.main()
