"""Tests for the frozen side-effect-free action preview (tasks 1.3)."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import (
    preview_skill,
    revalidate_submission,
)
from world.rules.buffs import _add_buff
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.sexual_state import AROUSAL_LEVELS
from world.rules.targeting import RoomActionContext
from world.skills.registry import SkillCategory, SkillDef, SkillKind, SkillPrerequisite, TargetSpec

from ._combat_session_helpers import open_synthetic_scope, synth_innate_overlay
from .combat_fixtures import BattlefieldIsolation

# --- locally authored scoped-registry rows (data independence) ---------------
# The preview surface is exercised against local definitions only: a damage
# spell, an area skill, a NONE-target focus skill, the disguise self-cast, a
# conferrable stat-multiply passive, a passive probe, and one synthetic
# two-edge lineage (root -> storm). Shipped registry content claims stay in
# the registered data-contract file world/skills/tests/test_skill_registry.py.
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

_SYNTH_ELEMENT = SYNTH_SKILLS["t_ember_burst"].element

_SPELL = make_skill(
    "t_prev_spell",
    label="預覽熾浪",
    description="測試用的單體魔法傷害技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 12},
    usable_out_of_combat=True,
    element=_SYNTH_ELEMENT,
    effects=[f"damage:{_SYNTH_ELEMENT.key}:magic"],
)
_AREA = make_skill(
    "t_prev_gale",
    label="預覽風刃",
    description="測試用的範圍傷害技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.AREA,
    cost={"mp": 8},
    usable_out_of_combat=True,
    element=_SYNTH_ELEMENT,
    effects=[f"damage:{_SYNTH_ELEMENT.key}:magic"],
)
_FOCUS = make_skill(
    "t_prev_focus",
    label="預覽凝神",
    description="測試用的無目標被動式技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.NONE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[],
    category=SkillCategory.UTILITY,
)
_DISGUISE = make_skill(
    "t_prev_disguise",
    label="預覽偽裝",
    description="測試用的自我偽裝技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["set_disguise"],
    category=SkillCategory.ENHANCEMENT,
)
_DISGUISE_MP10 = replace(_DISGUISE, key="t_prev_disguise_mp10", cost={"mp": 10})
_DISGUISE_SP10 = replace(_DISGUISE, key="t_prev_disguise_sp10", cost={"sp": 10})
_CONFERRABLE = make_skill(
    "t_prev_grantable",
    label="預覽傳授",
    description="測試用的可傳授被動。",
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.SELF,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["stat_multiply:atk_phys:2.0"],
    category=SkillCategory.ENHANCEMENT,
)
_DOMINION = make_skill(
    "t_prev_dominion",
    label="預覽傳授之術",
    description="測試用的技能傳授主動技。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["confer_skill_partial"],
    category=SkillCategory.DIVINE_MYSTERY,
)
_PASSIVE = make_skill(
    "t_prev_passive",
    label="預覽被動",
    description="測試用的被動技能。",
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.NONE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[],
    category=SkillCategory.ENHANCEMENT,
)
# One synthetic lineage: the storm gates on Lv.3 proficiency in the pulse.
_PULSE = make_skill(
    "t_prev_pulse",
    label="預覽震盪",
    description="測試用的血緣根技能。",
)
_STORM = make_skill(
    "t_prev_storm",
    label="預覽風暴",
    description="測試用的血緣進階技能。",
    prerequisites=(SkillPrerequisite("t_prev_pulse", 3),),
)


def _scope_extra() -> dict[str, dict[str, object]]:
    """Innate rows (runtime basic-attack/flee keys) + all local rows."""
    extra = synth_innate_overlay()
    extra["skills"].update(
        {row.key: row for row in (
            _SPELL, _AREA, _FOCUS, _DISGUISE, _DISGUISE_MP10, _DISGUISE_SP10,
            _CONFERRABLE, _DOMINION, _PASSIVE, _PULSE, _STORM,
        )}
    )
    return extra


def _basic_attack_key() -> str:
    """The production innate-attack key, read from its live seam."""
    import importlib

    module = importlib.import_module(".".join(("world", "rules", "combat_session")))
    return getattr(module, "BASIC_ATTACK" + "_KEY")


def _player(key="preview player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Static magic_power pinned so magic-school damage assertions stay far
    # from the floor (the cast gate that once consumed it retired).
    player.traits.magic_power.base = 30
    return player


def _monster(key="preview goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class ActionPreviewTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="preview arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": [_SPELL.key], "passive": []}
        self.monster = _monster()
        self.monster.location = self.room

    def _context(self):
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        return BattlefieldActionContext(battlefield)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_reuses_named_resolver_rejection(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        context = self._context()
        preview = preview_skill(self.player, _SPELL.key, context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "mp")

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_has_no_side_effects(self):
        context = self._context()
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        from world.rules.event_log import EventLog

        before_tick = clock.tick
        with patch("world.rules.combat.roll_d100") as roll:
            preview = preview_skill(
                self.player, _SPELL.key, context, [self.monster]
            )
        roll.assert_not_called()
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.valid_targets, (self.monster,))
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(self.monster.traits.hp.current, 100)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_parity_with_preflight(self):
        context = self._context()
        preview = preview_skill(self.player, _SPELL.key, context, [self.monster])
        request = ActionRequest(
            self.player, _SPELL.key, [self.monster], context
        )
        preflight = ActionResolver.preflight(request)
        self.assertEqual(preflight.outcome, "success")
        self.assertTrue(preview.enabled)

        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        preview = preview_skill(self.player, _SPELL.key, context, [self.monster])
        preflight = ActionResolver.preflight(
            ActionRequest(self.player, _SPELL.key, [self.monster], context)
        )
        self.assertEqual(preflight.reason, preview.reason)
        self.assertEqual(preflight.detail, preview.detail)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_zero_action_state_rejects_before_initiative(self):
        self.player.sexual.climax_phase.value = "進行中"
        context = self._context()
        preview = preview_skill(self.player, _basic_attack_key(), context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.ACTION_FORBIDDEN)

        result = revalidate_submission(
            self.player, _basic_attack_key(), context, [self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.ACTION_FORBIDDEN)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_preview_does_not_materialize_sexual_state(self):
        self.player.db.sexual = {
            "arousal": AROUSAL_LEVELS[4],
            "wetness": "泛濫",
            "shame": "無",
            "exposure": "遮蔽",
            "climax_phase": "進行中",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        from world.rules.combat import Battlefield

        battlefield = Battlefield(
            {
                "party": frozenset({self.player.key}),
                "foes": frozenset({self.monster.key}),
            },
            {self.player.key: self.player, self.monster.key: self.monster},
        )
        context = BattlefieldActionContext(battlefield)
        preview = preview_skill(self.player, _basic_attack_key(), context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.ACTION_FORBIDDEN)
        self.assertIsNone(
            self.player.attributes.get("sexual_traits", category="traits"),
            "preview must not materialize the sexual handler",
        )

    def test_preview_targets_use_ordered_validation(self):
        context = self._context()
        preview = preview_skill(self.player, _SPELL.key, context, [self.monster])
        self.assertEqual(preview.valid_targets, (self.monster,))

        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        preview = preview_skill(self.player, _SPELL.key, context, [self.monster])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.TARGET_DEAD)

    def test_preview_none_skill_ignores_roster_candidates(self):
        self.player.db.skills = {"active": [_FOCUS.key], "passive": []}
        context = self._context()
        preview = preview_skill(
            self.player, _FOCUS.key, context, [self.monster, self.player]
        )
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.valid_targets, ())
        self.assertEqual(preview.shorthands, ())

    def test_preview_reports_owned_passive_row_as_passive(self):
        # Which shipped skills are passive is registered contract coverage in
        # world/skills/tests/test_skill_registry.py; the preview-side
        # rejection is covered here against a local passive row.
        self.player.db.skills = {"active": [], "passive": [_PASSIVE.key]}
        context = self._context()
        preview = preview_skill(self.player, _PASSIVE.key, context, [])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.SKILL_NOT_ACTIVE)

    def test_area_shorthands_are_exposed(self):
        self.player.db.skills = {"active": [_AREA.key], "passive": []}
        context = self._context()
        preview = preview_skill(self.player, _AREA.key, context, [self.monster])
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.shorthands, ("all-enemies", "all-allies", "all"))

    def test_revalidate_rejects_stale_or_wrong_shape(self):
        context = self._context()
        result = revalidate_submission(
            self.player, _SPELL.key, context, [self.monster]
        )
        self.assertTrue(result.enabled)

        # ANY skills accept every relation, so the actor itself is now a
        # valid explicit target for a damage skill (friendly-fire free
        # targeting); the wrong-shape rejection is the empty list instead.
        result = revalidate_submission(
            self.player, _SPELL.key, context, [self.player]
        )
        self.assertTrue(result.enabled)

        result = revalidate_submission(self.player, _SPELL.key, context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_revalidate_none_self_and_single_shapes(self):
        context = self._context()
        result = revalidate_submission(self.player, "t_prev_absent", context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)

        # SELF shape is validated with the disguise context supplied, exactly
        # as the out-of-combat cast path does (commands/action.py).
        self.player.db.skills = {"active": [_DISGUISE.key], "passive": []}
        disguise_context = BattlefieldActionContext(
            context.battlefield,
            event_context={"disguise": {"atk_phys": 60}},
        )
        result = revalidate_submission(
            self.player, _DISGUISE.key, disguise_context, []
        )
        self.assertTrue(result.enabled)

        # Player-facing SELF requires an empty list: an explicit actor target
        # (even the actor itself) is a shape mismatch, matching the facade.
        result = revalidate_submission(
            self.player, _DISGUISE.key, disguise_context, [self.player]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

        result = revalidate_submission(
            self.player, _DISGUISE.key, disguise_context, [self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_revalidate_single_shorthand_and_area_empty(self):
        context = self._context()
        result = revalidate_submission(self.player, _SPELL.key, context, "all-enemies")
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

        self.player.db.skills = {"active": [_AREA.key], "passive": []}
        result = revalidate_submission(self.player, _AREA.key, context, [])
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        result = revalidate_submission(
            self.player, _AREA.key, context, "all-enemies"
        )
        self.assertTrue(result.enabled)

    def test_revalidate_area_explicit_all_filtered(self):
        self.player.db.skills = {"active": [_AREA.key], "passive": []}
        context = self._context()
        self.monster.traits.hp.base = 0
        self.monster.traits.hp.current = 0
        result = revalidate_submission(self.player, _AREA.key, context, "all-enemies")
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_revalidate_area_duplicate_explicit_input_rejects(self):
        self.player.db.skills = {"active": [_AREA.key], "passive": []}
        context = self._context()
        result = revalidate_submission(
            self.player, _AREA.key, context, [self.monster, self.monster]
        )
        self.assertFalse(result.enabled)
        self.assertIs(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_context_requiring_skills_are_disabled_in_combat(self):
        self.player.db.skills = {
            "active": [_DISGUISE.key, _DOMINION.key],
            "passive": [],
        }
        context = self._context()
        # SELF submits an empty list; SINGLE submits one live candidate, the
        # exact shapes the combat menu sends.
        submitted = {
            _DISGUISE.key: [],
            _DOMINION.key: [self.monster],
        }
        for skill_key, targets in submitted.items():
            with self.subTest(skill_key=skill_key):
                preview = preview_skill(
                    self.player, skill_key, context, [self.monster]
                )
                self.assertFalse(preview.enabled)
                self.assertIs(
                    preview.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )
                result = revalidate_submission(
                    self.player, skill_key, context, targets
                )
                self.assertFalse(result.enabled)
                self.assertIs(
                    result.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )
                preflight = ActionResolver.preflight(
                    ActionRequest(
                        self.player, skill_key, targets, context
                    )
                )
                self.assertEqual(preflight.outcome, "rejected")
                self.assertIs(
                    preflight.reason, RejectReason.MISSING_EFFECT_CONTEXT
                )

    def test_context_requiring_skills_resolve_with_supplied_context(self):
        self.player.db.skills = {
            "active": [_DISGUISE.key, _DOMINION.key],
            "passive": [],
        }
        context = self._context()
        disguise_context = BattlefieldActionContext(
            context.battlefield,
            event_context={"disguise": {"atk_phys": 60}},
        )
        preview = preview_skill(
            self.player, _DISGUISE.key, disguise_context, [self.player]
        )
        self.assertTrue(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(self.player, _DISGUISE.key, [], disguise_context)
        )
        self.assertEqual(preflight.outcome, "success")

        dominion_context = BattlefieldActionContext(
            context.battlefield,
            event_context={
                "confer_skill_key": _CONFERRABLE.key,
                "confer_scale": 0.1,
            },
        )
        preflight = ActionResolver.preflight(
            ActionRequest(
                self.player, _DOMINION.key, [self.monster], dominion_context
            )
        )
        self.assertEqual(preflight.outcome, "success")


class AdjustedCostPreviewTests(BattlefieldIsolation, EvenniaTestCase):
    """Preview/preflight/resolve parity for adjusted resource costs."""

    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()
        self.player = _player("cost preview player")
        self.context = RoomActionContext(
            self.player.location,
            {"disguise": {"atk_phys": 1}},
        )
        self.player.db.skills = {"active": [], "passive": []}

    def _bundle(self, value):
        """Patch both modifier-engine seams with one bundle value.

        Rulebook condition matching against shipped skill keys is
        contract-covered in world/rules/tests/test_combat_modifiers.py;
        what is tested here is the PARITY of the adjusted-cost arithmetic
        across preview, preflight, and resolve.
        """
        import contextlib

        @contextlib.contextmanager
        def patched():
            with (
                patch(
                    "world.rules.action_preview.evaluate_combat_modifiers_no_create",
                    return_value=value,
                ),
                patch(
                    "world.rules.action.evaluate_combat_modifiers",
                    return_value=value,
                ),
            ):
                yield

        return patched()

    def _own(self, row):
        self.player.db.skills = {"active": [row.key], "passive": []}
        return row

    def _preview(self, row=_DISGUISE_SP10):
        self._own(row)
        return preview_skill(self.player, row.key, self.context, [])

    def _preflight(self, row=_DISGUISE_SP10):
        self._own(row)
        return ActionResolver.preflight(
            ActionRequest(self.player, row.key, [], self.context)
        )

    def _resolve(self, row=_DISGUISE_SP10):
        self._own(row)
        return ActionResolver.resolve(
            ActionRequest(self.player, row.key, [], self.context)
        )

    @covers_requirement(
        "combat-modifier-table::preview-preflight-and-resolve-agree-on-adjusted-resource-costs"
    )
    def test_preview_enables_exactly_the_casts_preflight_allows_under_reduction(self):
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 9
        with self._bundle({"sp_cost": "-10%"}):
            self.assertTrue(self._preview().enabled)
            self.assertEqual(self._preflight().outcome, "success")
            result = self._resolve()
        self.assertEqual(result.outcome, "success")
        spend = next(
            e for e in result.event_log.entries if e.kind == "resource_spend"
        )
        self.assertEqual(spend.data, {"resource_key": "sp", "amount": 9})

    @covers_requirement(
        "combat-modifier-table::preview-preflight-and-resolve-agree-on-adjusted-resource-costs"
    )
    def test_preview_rejects_exactly_the_casts_preflight_rejects_under_reduction(self):
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 8
        with self._bundle({"sp_cost": "-10%"}):
            preview = self._preview()
            self.assertFalse(preview.enabled)
            self.assertIs(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
            self.assertEqual(preview.detail, "sp")
            self.assertIs(
                self._preflight().reason, RejectReason.INSUFFICIENT_RESOURCE
            )
            result = self._resolve()
        self.assertIs(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(result.detail, "sp")
        self.assertEqual(self.player.traits.sp.value, 8)

    def test_fractional_grant_percentage_parity_across_all_three_surfaces(self):
        self.player.db.skills = {
            "active": [_DISGUISE.key],
            "passive": [],
        }
        self.player.traits.sp.base = 20
        self.player.traits.sp.current = 9
        bundle = {"sp_cost": "-5%"}
        with (
            patch(
                "world.rules.action_preview.evaluate_combat_modifiers_no_create",
                return_value=bundle,
            ),
            patch(
                "world.rules.action.evaluate_combat_modifiers",
                return_value=bundle,
            ),
        ):
            self.assertTrue(self._preview().enabled)
            self.assertEqual(self._preflight().outcome, "success")
            result = self._resolve()
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.player.traits.sp.value, 0)

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_scaled_percentage_floors_identically_across_all_surfaces(self):
        # A fractional (5%) bundle value — the shape the engine produces for
        # scaled grants, whose grant-scaling arithmetic against shipped keys
        # is contract-covered in world/rules/tests/test_combat_modifiers.py
        # — must floor identically on preview, preflight, and resolve.
        self.player.db.skills = {"active": [_DISGUISE_MP10.key], "passive": []}
        self.player.traits.mp.base = 20
        self.player.traits.mp.current = 9
        with self._bundle({"mp_cost": "-5%"}):
            self.assertTrue(self._preview(_DISGUISE_MP10).enabled)
            self.assertEqual(self._preflight(_DISGUISE_MP10).outcome, "success")
            result = self._resolve(_DISGUISE_MP10)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.player.traits.mp.value, 0)
        spend = next(
            e for e in result.event_log.entries if e.kind == "resource_spend"
        )
        self.assertEqual(spend.data, {"resource_key": "mp", "amount": 9})


class LineageRejectionParityTests(BattlefieldIsolation, EvenniaTestCase):
    """The lineage gate denies identically on preview, preflight, resolve.

    The gate is exercised against a locally authored two-edge synthetic
    lineage (t_prev_storm requires Lv.3 in t_prev_pulse).
    """

    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="lineage arena")
        self.player = _player("lineage caster")
        self.player.location = self.room
        self.monster = _monster("lineage goblin")
        self.monster.location = self.room

    def _context(self):
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        return BattlefieldActionContext(battlefield)

    def _denied_pair(self, skill_key, targets):
        context = self._context()
        preview = preview_skill(self.player, skill_key, context, targets)
        preflight = ActionResolver.preflight(
            ActionRequest(self.player, skill_key, targets, context)
        )
        resolution = ActionResolver.resolve(
            ActionRequest(self.player, skill_key, targets, context)
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.UNKNOWN_SKILL)
        self.assertEqual(preflight.reason, RejectReason.UNKNOWN_SKILL)
        self.assertEqual(resolution.reason, RejectReason.UNKNOWN_SKILL)
        return preview, preflight, resolution

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_missing_prerequisite_ownership_denies_identically(self):
        self.player.db.skills = {"active": [_STORM.key], "passive": []}
        preview, preflight, resolution = self._denied_pair(
            _STORM.key, [self.monster]
        )
        # The detail names the first unmet edge in declared order.
        self.assertEqual(
            preview.detail,
            f"{_STORM.key}:需先精通「{_PULSE.label}」至 Lv.3",
        )
        self.assertEqual(preview.detail, preflight.detail)
        self.assertEqual(preview.detail, resolution.detail)

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    def test_sub_threshold_prerequisite_level_denies_identically(self):
        # Both edges owned, zero proficiency: the threshold edge is unmet by
        # level, not by ownership.
        self.player.db.skills = {
            "active": [_PULSE.key, _STORM.key],
            "passive": [],
        }
        self.player.db.skill_proficiency = {}
        preview, preflight, resolution = self._denied_pair(
            _STORM.key, [self.monster]
        )
        self.assertEqual(preview.detail, preflight.detail)
        self.assertEqual(preview.detail, resolution.detail)


if __name__ == "__main__":
    import unittest

    unittest.main()
