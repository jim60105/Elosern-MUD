"""Behavior tests for climax phase empowerment and state reactions (light-climax-empowerment).

Pure synthetic fixtures exercising:
- Bare pleasure_peak parsing and payload rejection
- parse_effect complete recognized 34-prefix superset
- pleasure_peak actor-bound advance through canonical writer without direct phase set
- approaching phase no-artificial-extension guard
- already-locked caster rejection at capability check
- emergency recovery locking only caster
- qualified apotheosis ownership phase entry granting marker (both canonical sources)
- non-qualified ownership never granting marker
- mid-cycle acquisition not retroactive
- marker survival through afterglow and expiry at neutral
- qualification loss immediately disabling benefits without writes on reads
- marker idempotence across multiple cycles
- marker-max override vs higher authored coefficient and untouched fixed coefficients
- empowerment not bypassing cast prerequisites or gates
- transaction rollback restoring marker, phase, counters, buffs, and traits (action and clock paths)
- second synthetic non-light configuration proving generic mechanism reuse
- rejection of malformed peak syntax and unresolved markers at authoring time
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    active_buff_keys_from_storage,
    apply_buff,
    entity_active_buffs,
    remove_by_selector,
)
from world.rules.clock import (
    AdvanceSource,
    WorldClock,
    get_world_clock,
)
from world.rules.pleasure import apply_pleasure_gain, zero_pleasure
from world.rules.rulebook.schema import Rule
from world.rules.sexual_state import (
    _VALID_CLIMAX_TRANSITIONS,
    _apply_climax_phase_set,
)
from world.rules.sexual_transitions import apply_event
from world.rules.spell_conditions import CastCondition, CastConditionSubject
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_phase_reaction,
    is_empowered,
    load_state_reaction_rules,
    validate_state_reaction_rules,
)
from world.rules.targeting import RoomActionContext
from world.skills.effects import (
    EffectAudience,
    EffectPolicy,
    HealEffect,
    InteractionPolicy,
    PleasurePeakEffect,
    StateMagnitude,
    StateMagnitudeSubject,
    StimulusEffect,
    parse_effect,
)
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    _skill,
)
from world.tests.synthetic_data import synthetic_registries

from ._combat_session_helpers import _race_key, open_synthetic_scope

# --- Synthetic skill fixtures (file-local, never shipped content) ---------

_T_PREREQ_A = "t_synth_prereq_a"
_T_PREREQ_A_SKILL = _skill(
    _T_PREREQ_A,
    "合成前置A",
    "前置技能A測試用。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"mp": 5},
    usable_out_of_combat=True,
    effects=["self_heal"],
    category=SkillCategory.ENHANCEMENT,
)

_T_PREREQ_B = "t_synth_prereq_b"
_T_PREREQ_B_SKILL = _skill(
    _T_PREREQ_B,
    "合成前置B",
    "前置技能B測試用。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"mp": 5},
    usable_out_of_combat=True,
    effects=["self_heal"],
    category=SkillCategory.ENHANCEMENT,
)

_T_APOTHEOSIS = "bliss_apotheosis"
_T_APOTHEOSIS_SKILL = _skill(
    _T_APOTHEOSIS,
    "合成至福神格",
    "測試用神格技能，宣告雙前置Lv.10。",
    SkillKind.ACTIVE,
    TargetSpec.AREA,
    cost={"mp": 50},
    usable_out_of_combat=True,
    effects=["heal:area"],
    category=SkillCategory.ENHANCEMENT,
    prerequisites=(
        SkillPrerequisite(_T_PREREQ_A, 10),
        SkillPrerequisite(_T_PREREQ_B, 10),
    ),
    effect_policies=(
        EffectPolicy(audience=EffectAudience.ALLIES, coefficient=3.8),
    ),
)

_T_EMERGENCY_HEAL = "t_synth_emergency_heal"
_T_EMERGENCY_HEAL_SKILL = _skill(
    _T_EMERGENCY_HEAL,
    "合成緊急復甦",
    "單體治療受術者，自身快感推至頂點。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 20},
    usable_out_of_combat=True,
    effects=["heal:single", "pleasure_peak"],
    category=SkillCategory.ENHANCEMENT,
    effect_policies=(
        EffectPolicy(audience=EffectAudience.SELECTED, coefficient=2.0),
        EffectPolicy(audience=EffectAudience.SELF),
    ),
)

_T_KISS_CURVE = StateMagnitude(
    subject=StateMagnitudeSubject.ACTOR,
    field="arousal",
    base=3.2,
    per_ordinal=0.2,
    maximum=4.0,
    marker="climax_empowerment",
)

_T_KISS_LIKE = "t_synth_kiss_heal"
_T_KISS_LIKE_SKILL = _skill(
    _T_KISS_LIKE,
    "合成聖吻治癒",
    "以施法者興奮推進治療，高潮滿值時係數提升至4.0。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 10},
    usable_out_of_combat=True,
    effects=["heal:single", "stimulus:both"],
    category=SkillCategory.ENHANCEMENT,
    cast_conditions=(
        CastCondition(CastConditionSubject.ACTOR, {"field": "arousal", "gte": "微興奮"}),
        CastCondition(CastConditionSubject.EACH_TARGET, {"field": "arousal", "gte": "微興奮"}),
    ),
    interaction=InteractionPolicy(
        contact=True,
        distinct_participants=True,
        target_capable=False,
        resistible=True,
    ),
    effect_policies=(
        EffectPolicy(magnitude=_T_KISS_CURVE),
        EffectPolicy(),
    ),
)

_T_BOUNDED_STATE = "t_synth_bounded_heal"
_T_BOUNDED_STATE_SKILL = _skill(
    _T_BOUNDED_STATE,
    "合成雙重治癒",
    "驗證曲線部分取最大值，固定係數部分保持不變。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 15},
    usable_out_of_combat=True,
    effects=["heal:single", "heal:single"],
    category=SkillCategory.ENHANCEMENT,
    effect_policies=(
        EffectPolicy(
            magnitude=StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=2.0,
                per_ordinal=0.5,
                maximum=3.5,
                marker="climax_empowerment",
            )
        ),
        EffectPolicy(coefficient=2.8),
    ),
)

_T_SYNTH_WATER = "t_synth_water_surge"
_T_SYNTH_WATER_SKILL = _skill(
    _T_SYNTH_WATER,
    "合成水流激湧",
    "非光系合成法術，驗證通用機制複用。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"mp": 12},
    usable_out_of_combat=True,
    element="water",
    effects=["heal:single", "pleasure_peak"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    effect_policies=(
        EffectPolicy(
            audience=EffectAudience.SELF,
            magnitude=StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=1.5,
                per_ordinal=0.5,
                maximum=3.0,
                marker="climax_empowerment",
            ),
        ),
        EffectPolicy(audience=EffectAudience.SELF),
    ),
)

_T_HIGHER_AUTHORED = "t_synth_higher_authored"
_T_HIGHER_AUTHORED_SKILL = _skill(
    _T_HIGHER_AUTHORED,
    "合成高係數法術",
    "驗證曲線賦能選取其maximum(3.5)，取代其authored coefficient。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 15},
    usable_out_of_combat=True,
    effects=["heal:single"],
    category=SkillCategory.ENHANCEMENT,
    effect_policies=(
        EffectPolicy(
            coefficient=5.0,
            magnitude=StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=2.0,
                per_ordinal=0.5,
                maximum=3.5,
                marker="climax_empowerment",
            ),
        ),
    ),
)

_ALL_TEST_SKILLS = {
    _T_PREREQ_A_SKILL.key: _T_PREREQ_A_SKILL,
    _T_PREREQ_B_SKILL.key: _T_PREREQ_B_SKILL,
    _T_APOTHEOSIS_SKILL.key: _T_APOTHEOSIS_SKILL,
    _T_EMERGENCY_HEAL_SKILL.key: _T_EMERGENCY_HEAL_SKILL,
    _T_KISS_LIKE_SKILL.key: _T_KISS_LIKE_SKILL,
    _T_BOUNDED_STATE_SKILL.key: _T_BOUNDED_STATE_SKILL,
    _T_SYNTH_WATER_SKILL.key: _T_SYNTH_WATER_SKILL,
    _T_HIGHER_AUTHORED_SKILL.key: _T_HIGHER_AUTHORED_SKILL,
}


class PhaseSpellReactionsTests(EvenniaTest):
    """Behavior tests for climax phase empowerment and state reactions."""

    def setUp(self):
        super().setUp()
        register_catalog()
        open_synthetic_scope(
            self, "skills", "elements", "races", "subraces", "static_tiers"
        )
        self.actor = create_object(PlayerCharacter, key="caster", location=self.room1)
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": list(_ALL_TEST_SKILLS), "passive": []}

        self.target = create_object(PlayerCharacter, key="target", location=self.room1)
        self.target.race = _race_key()
        self.target.apply_race_baseline()

    def _catalogue(self, skills: dict[str, SkillDef] | None = None):
        if skills is None:
            skills = _ALL_TEST_SKILLS
        return synthetic_registries(
            "skills",
            "sexual_acts",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            extra={"skills": skills},
        )

    def _qualify_actor_for_apotheosis(self):
        """Set proficiency of prereqs to Level 10 (500 XP) and ensure ownership."""
        self.actor.db.skills = {
            "active": list(_ALL_TEST_SKILLS),
            "passive": [],
        }
        self.actor.db.skill_proficiency = {
            _T_PREREQ_A: 500.0,
            _T_PREREQ_B: 500.0,
        }

    def _request(self, skill_key: str, targets: list[Any] | None = None) -> ActionRequest:
        context = RoomActionContext(
            self.actor.location,
            {"disguise": {"atk_phys": 1}},
        )
        t_list = targets if targets is not None else [self.target]
        return ActionRequest(self.actor, skill_key, t_list, context)

    # --- 1. Parsing & Recognized Prefix Superset ---

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_bare_pleasure_peak_parses_and_rejects_payload(self):
        """pleasure_peak parses as bare dataclass; any payload or suffix raises ValueError."""
        parsed = parse_effect("pleasure_peak")
        self.assertIsInstance(parsed, PleasurePeakEffect)

        for invalid in ("pleasure_peak:100", "pleasure_peak:actor", "pleasure_peak:", "pleasure_peak:self"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_effect(invalid)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_parse_effect_superset_matches_recognized_set(self):
        """parse_effect classifies all 34 recognized prefixes and rejects retired or unknown keys."""
        # 34 prefixes including stimulus and pleasure_peak
        prefixes_and_samples = [
            ("stat_multiply", "stat_multiply:atk_phys:100"),
            ("growth_rate", "growth_rate:practice:100"),
            ("sexual_magic_mastery", "sexual_magic_mastery"),
            ("passive_buff", "passive_buff:focus"),
            ("combat_prediction", "combat_prediction:test"),
            ("passive_trait", "passive_trait:test"),
            ("movement", "movement:flight"),
            ("weapon_style", "weapon_style:dual_wield"),
            ("confer_skill_partial", "confer_skill_partial"),
            ("set_disguise", "set_disguise"),
            ("buff_apply", "buff_apply:focus"),
            ("self_buff_apply", "self_buff_apply:focus"),
            ("confer_growth_rate", "confer_growth_rate"),
            ("sexual_event", "sexual_event:kiss"),
            ("sexual_event_actor", "sexual_event_actor:kiss"),
            ("sexual_event_target", "sexual_event_target:kiss"),
            ("pleasure", "pleasure:kiss"),
            ("sexual_counter", "sexual_counter:kiss"),
            ("act_pair_event", "act_pair_event:kiss"),
            ("damage", "damage:dark:physical"),
            ("heal", "heal:single"),
            ("self_heal", "self_heal"),
            ("cleanse", "cleanse:status"),
            ("disengage", "disengage:self"),
            ("divine_mystery", "divine_mystery:test"),
            ("divine_pleasure_max", "divine_pleasure_max:test"),
            ("divine_climax_extension_stage", "divine_climax_extension_stage:1"),
            ("divine_drain", "divine_drain:test"),
            ("divine_saturate_sensitivity", "divine_saturate_sensitivity:test"),
            ("divine_clamp_shame", "divine_clamp_shame:test"),
            ("divine_mark_submission", "divine_mark_submission:test"),
            ("divine_restore_purity", "divine_restore_purity:test"),
            ("stimulus", "stimulus:actor"),
            ("pleasure_peak", "pleasure_peak"),
        ]
        self.assertEqual(len(prefixes_and_samples), 34)

        for prefix, sample in prefixes_and_samples:
            with self.subTest(prefix=prefix):
                parsed = parse_effect(sample)
                self.assertIsNotNone(parsed)

        # Retired and unknown prefixes fail closed
        with self.assertRaises(ValueError):
            parse_effect("element_mastery_rank:主宰")
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:magic:100")
        with self.assertRaises(ValueError):
            parse_effect("definitely_not_a_real_prefix:x")

    # --- 2. pleasure_peak Canonical Advance & Boundaries ---

    @covers_requirement(
        "phase-scoped-spell-empowerment::peak-effects-bind-declared-recipients-and-retain-action-locks"
    )
    def test_pleasure_peak_advances_phase_through_canonical_writer_not_direct_set(self):
        """pleasure_peak walks canonical cycle edges (未達 -> 接近 -> 進行中) without direct phase assignment."""
        with self._catalogue():
            self.assertEqual(self.actor.sexual.climax_phase.level, "未達")
            self.target.traits.hp.current = 10

            req = self._request(_T_EMERGENCY_HEAL, [self.target])
            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            # Caster is now in 進行中
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertEqual(self.actor.sexual.pleasure.base, 100)
            # Target was healed but did not receive pleasure_peak
            self.assertGreater(self.target.traits.hp.current, 10)
            self.assertEqual(self.target.sexual.climax_phase.level, "未達")

    @covers_requirement(
        "phase-scoped-spell-empowerment::peak-effects-bind-declared-recipients-and-retain-action-locks"
    )
    def test_pleasure_peak_approaching_phase_no_artificial_extension(self):
        """Caster starting at 接近 enters 進行中 without counting the zero-gain call as extension stimulus."""
        with self._catalogue():
            # Advance caster to 接近 (pleasure >= 85 is 極限)
            self.actor.sexual.pleasure.base = 85
            self.assertEqual(self.actor.sexual.arousal.level, "極限")
            _apply_climax_phase_set(self.actor, "接近")
            self.assertEqual(self.actor.sexual.climax_phase.level, "接近")

            req = self._request(_T_EMERGENCY_HEAL, [self.target])
            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            # pending_climax_extension must remain 0
            self.assertEqual(self.actor.sexual.pending_climax_extension, 0)

    @covers_requirement(
        "phase-scoped-spell-empowerment::peak-effects-bind-declared-recipients-and-retain-action-locks"
    )
    def test_already_locked_caster_cannot_cast(self):
        """An in-progress caster is rejected at capability check before MP or healing changes."""
        with self._catalogue():
            self.actor.sexual.climax_phase.value = "進行中"
            mp_before = self.actor.traits.mp.current
            hp_before = self.target.traits.hp.current = 10

            req = self._request(_T_EMERGENCY_HEAL, [self.target])

            # Preflight rejects
            pre_res = ActionResolver.preflight(req)
            self.assertEqual(pre_res.outcome, "rejected")
            self.assertEqual(pre_res.reason, RejectReason.ACTION_FORBIDDEN)

            # Resolve rejects
            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "rejected")
            self.assertEqual(res.reason, RejectReason.ACTION_FORBIDDEN)

            self.assertEqual(self.actor.traits.mp.current, mp_before)
            self.assertEqual(self.target.traits.hp.current, hp_before)

    @covers_requirement(
        "phase-scoped-spell-empowerment::peak-effects-bind-declared-recipients-and-retain-action-locks"
    )
    def test_emergency_recovery_locks_only_caster(self):
        """Caster is locked for subsequent casts, while healed target remains capable."""
        with self._catalogue():
            self.target.traits.hp.current = 10
            req = self._request(_T_EMERGENCY_HEAL, [self.target])
            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            # Caster is locked
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            req2 = self._request(_T_EMERGENCY_HEAL, [self.target])
            res2 = ActionResolver.resolve(req2)
            self.assertEqual(res2.outcome, "rejected")
            self.assertEqual(res2.reason, RejectReason.ACTION_FORBIDDEN)

            # Target is capable
            self.assertEqual(self.target.sexual.climax_phase.level, "未達")

    # --- 3. Qualified Climax Empowerment Marker Lifecycle ---

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_qualified_phase_entry_grants_marker_both_canonical_sources(self):
        """Qualified actor entering 進行中 via pleasure gain or rule event receives climax_empowerment."""
        with self._catalogue():
            # Source A: canonical pleasure gain
            self._qualify_actor_for_apotheosis()
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Reset back to neutral
            _apply_climax_phase_set(self.actor, "餘韻")
            _apply_climax_phase_set(self.actor, "未達")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Source B: rule event (stimulus_applied at 接近)
            self.actor.sexual.pleasure.base = 75
            _apply_climax_phase_set(self.actor, "接近")
            self.assertEqual(self.actor.sexual.climax_phase.level, "接近")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            apply_event(self.actor, "stimulus_applied")
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_non_qualified_owner_never_gets_marker(self):
        """Unqualified actor entering 進行中 never receives climax_empowerment."""
        with self._catalogue():
            # Case 1: owns apotheosis but prerequisites unmet
            self.actor.db.skills = {"active": [_T_APOTHEOSIS], "passive": []}
            self.actor.db.skill_proficiency = {_T_PREREQ_A: 0.0}

            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Case 2: has prerequisites at 10 but does not own apotheosis
            _apply_climax_phase_set(self.actor, "餘韻")
            _apply_climax_phase_set(self.actor, "未達")
            self.actor.db.skills = {"active": [_T_PREREQ_A, _T_PREREQ_B], "passive": []}
            self.actor.db.skill_proficiency = {_T_PREREQ_A: 500.0, _T_PREREQ_B: 500.0}

            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_mid_cycle_acquisition_not_retroactive(self):
        """Acquiring qualification after phase entry does not retroactively grant the marker."""
        with self._catalogue():
            # Enter 進行中 while unqualified
            self.actor.db.skills = {"active": [], "passive": []}
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Acquire qualification mid-cycle
            self._qualify_actor_for_apotheosis()
            # Still no marker!
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_marker_survives_afterglow_and_expires_at_neutral(self):
        """Marker survives afterglow and reload via attribute storage, allows ordinary actions, and expires at neutral."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Transition to 餘韻
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertEqual(self.actor.sexual.climax_phase.level, "餘韻")
            # Marker survives
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Survives reload: attribute-layer refetch from stored data without handler
            raw_buffs = self.actor.attributes.get("buffs", default={})
            self.assertTrue(
                any(b.get("definition_key") == "climax_empowerment" for b in raw_buffs.values())
            )

            # Ordinary actions resume in 餘韻: actor capability check passes
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            req = self._request(_T_KISS_LIKE, [self.target])
            with patch("world.rules.action.roll_d100", return_value=1):
                res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            # Transition to 未達
            _apply_climax_phase_set(self.actor, "未達")
            self.assertEqual(self.actor.sexual.climax_phase.level, "未達")
            # Marker removed
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_qualification_loss_disables_benefits_immediately(self):
        """Removing qualification mid-cycle disables marker benefits immediately without writes on reads."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # While qualified, empowered check is True
            self.assertTrue(is_empowered(self.actor, "climax_empowerment"))

            # Lose qualification (prereq proficiency drops)
            self.actor.db.skill_proficiency[_T_PREREQ_A] = 0.0

            # Empowered check is immediately False
            self.assertFalse(is_empowered(self.actor, "climax_empowerment"))

            # Marker is still in storage (no write on read)
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Magnitude calculation falls back to standard curve (not 4.0)
            self.actor.sexual.pleasure.base = 25  # 微興奮 -> ordinal 1 -> 3.2 + 0.2 = 3.4
            mag = _T_KISS_CURVE.compute(self.actor, actor=self.actor)
            self.assertAlmostEqual(mag, 3.4, places=5)

    @covers_requirement(
        "phase-scoped-spell-empowerment::qualified-phase-entry-grants-a-persistent-cycle-scoped-benefit"
    )
    def test_marker_idempotence_across_cycles(self):
        """Entering 進行中 across repeated cycles idempotently grants, retains, and removes marker."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()

            for cycle in range(2):
                with self.subTest(cycle=cycle):
                    apply_pleasure_gain(self.actor, 100)
                    apply_pleasure_gain(self.actor, 0)
                    self.assertEqual(self.actor.sexual.climax_phase.level, "進行中")
                    self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

                    _apply_climax_phase_set(self.actor, "餘韻")
                    self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

                    _apply_climax_phase_set(self.actor, "未達")
                    self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    # --- 4. Marker-Max Selection & Untouched Fixed Magnitudes ---

    @covers_requirement(
        "phase-scoped-spell-empowerment::empowerment-selects-configured-maxima-without-bypassing-conditions"
    )
    def test_marker_max_override_vs_higher_authored_coefficient(self):
        """Empowered curve selects authored maximum (3.5), replacing authored coefficient; fixed coefficients remain fixed."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertTrue(is_empowered(self.actor, "climax_empowerment"))

            # 1. Curve on higher-authored spell selects 3.5 instead of authored 5.0
            from world.rules.action import _bind_resolved_effect, _event_context
            req = self._request(_T_HIGHER_AUTHORED, [self.target])
            base_ctx = _event_context(req)
            effect_ctx = _bind_resolved_effect(
                base_ctx, _T_HIGHER_AUTHORED_SKILL, 0, actor=self.actor, targets=[self.target]
            )
            policy = effect_ctx["resolved_effect"].policy
            self.assertEqual(policy.coefficient, 3.5)

            # 2. Multi-component spell: curve selects 3.5, fixed component remains 2.8
            effect_ctx0 = _bind_resolved_effect(
                base_ctx, _T_BOUNDED_STATE_SKILL, 0, actor=self.actor, targets=[self.target]
            )
            effect_ctx1 = _bind_resolved_effect(
                base_ctx, _T_BOUNDED_STATE_SKILL, 1, actor=self.actor, targets=[self.target]
            )
            self.assertEqual(effect_ctx0["resolved_effect"].policy.coefficient, 3.5)
            self.assertEqual(effect_ctx1["resolved_effect"].policy.coefficient, 2.8)

            # 3. Fixed-coefficient-only spell (apotheosis itself at 3.8) remains 3.8
            effect_ctx_apo = _bind_resolved_effect(
                base_ctx, _T_APOTHEOSIS_SKILL, 0, actor=self.actor, targets=[self.target]
            )
            self.assertEqual(effect_ctx_apo["resolved_effect"].policy.coefficient, 3.8)

    @covers_requirement(
        "phase-scoped-spell-empowerment::empowerment-selects-configured-maxima-without-bypassing-conditions"
    )
    def test_marker_does_not_bypass_cast_prerequisites_or_gates(self):
        """Active marker does not bypass unmet target conditions or action capability."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertTrue(is_empowered(self.actor, "climax_empowerment"))

            # Actor is at 微興奮, but target is at 平靜 (fails target cast_condition)
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 0
            req = self._request(_T_KISS_LIKE, [self.target])

            pre_res = ActionResolver.preflight(req)
            self.assertEqual(pre_res.outcome, "rejected")
            self.assertEqual(pre_res.reason, RejectReason.CAST_CONDITION_UNMET)

    # --- 5. Rollback Consistency (Action and Clock paths) ---

    @covers_requirement(
        "phase-scoped-spell-empowerment::empowerment-selects-configured-maxima-without-bypassing-conditions"
    )
    def test_rollback_restores_marker_phase_and_traits_action_path(self):
        """Action transaction commit failure restores marker, buffs, phase, and traits."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            self.assertEqual(self.actor.sexual.climax_phase.level, "未達")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            # Staged effects: first advances phase into 進行中 (granting marker), second injects commit error
            effects = [
                PendingEffect(
                    self.actor,
                    f"pleasure_peak|{self.actor.key}|100",
                    frozenset({"sexual", "traits", "buffs"}),
                    lambda: (
                        apply_pleasure_gain(self.actor, 100),
                        apply_pleasure_gain(self.actor, 0),
                    ),
                ),
                PendingEffect(
                    self.actor,
                    "boom",
                    frozenset({"sexual", "traits", "buffs"}),
                    lambda: (_ for _ in ()).throw(RuntimeError("injected commit error")),
                ),
            ]
            with self.assertRaises(CommitFailed) as caught:
                _commit(effects, char="tester", action="test_emergency_heal")
            self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)

            # Rolled back completely
            self.assertEqual(self.actor.sexual.climax_phase.level, "未達")
            self.assertNotIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

    @covers_requirement(
        "phase-scoped-spell-empowerment::empowerment-selects-configured-maxima-without-bypassing-conditions"
    )
    def test_rollback_restores_marker_phase_and_buffs_clock_path(self):
        """Clock advance failure restores marker removed on transition to 未達."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))

            clock = get_world_clock()
            original_persist = clock._persist

            def failing_persist(tick):
                raise RuntimeError("simulated persist failure")

            clock._persist = failing_persist
            try:
                # Advance 300s causes decay_tick to transition 餘韻 -> 未達
                with self.assertRaises(RuntimeError):
                    clock.advance(300, AdvanceSource.COMMAND, [self.actor])

                # Rolled back via _restore_advance_registry: marker and 餘韻 are restored
                self.assertEqual(self.actor.sexual.climax_phase.level, "餘韻")
                self.assertIn("climax_empowerment", active_buff_keys_from_storage(self.actor))
            finally:
                clock._persist = original_persist

    # --- 6. Generic Reuse (Second Synthetic Configuration) ---

    @covers_requirement(
        "skill-effect-model::peak-effects-and-marker-selected-state-maxima-are-validated-typed-behavior"
    )
    def test_second_synthetic_non_light_configuration(self):
        """A synthetic water spell declares self peak and marker-bound state magnitude, reusing generic machinery."""
        with self._catalogue():
            self._qualify_actor_for_apotheosis()
            # Empower actor
            apply_pleasure_gain(self.actor, 100)
            apply_pleasure_gain(self.actor, 0)
            _apply_climax_phase_set(self.actor, "餘韻")
            self.assertTrue(is_empowered(self.actor, "climax_empowerment"))

            # Cast water spell
            from world.rules.action import _bind_resolved_effect, _event_context
            req = self._request(_T_SYNTH_WATER, [self.actor])
            base_ctx = _event_context(req)
            effect_ctx = _bind_resolved_effect(
                base_ctx, _T_SYNTH_WATER_SKILL, 0, actor=self.actor, targets=[self.actor]
            )
            policy = effect_ctx["resolved_effect"].policy
            # Marker-max selected: 3.0
            self.assertEqual(policy.coefficient, 3.0)

    # --- 7. Rejection of Malformed Declarations ---

    @covers_requirement(
        "skill-effect-model::peak-effects-and-marker-selected-state-maxima-are-validated-typed-behavior"
    )
    def test_malformed_peak_or_unresolved_marker_rejected(self):
        """Authoring supplies invalid marker references, bad peak syntax, or contradictory policies raises ValueError."""
        # Unresolved marker raises
        with self.assertRaises(ValueError):
            StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=1.0,
                per_ordinal=0.5,
                maximum=3.0,
                marker="non_existent_unregistered_marker_xyz",
            )

        # Marker without maximum raises
        with self.assertRaises(ValueError):
            StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=1.0,
                per_ordinal=0.5,
                marker="climax_empowerment",
            )

        # Marker with non-positive maximum raises
        with self.assertRaises(ValueError):
            StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="arousal",
                base=0.0,
                per_ordinal=0.5,
                maximum=0.0,
                marker="climax_empowerment",
            )
