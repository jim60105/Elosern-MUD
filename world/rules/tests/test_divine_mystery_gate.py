"""Race-gate and cast-path tests for the divine-mystery skill family.

Runs on synthetic rows: a divine-arts-capable race and two mundane races,
plus mastery/arts gate rows and unmechanized mystery rows carrying the
registered flavor effect prefix. The mechanized-rejection branch is driven
directly with a patched effect parser.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _handle_divine_mystery,
)
from world.rules.action_preview import preview_skill
from world.rules.targeting import RoomActionContext
from world.skills.effects import DivineMysteryEffect
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import make_race, make_skill

from ._combat_session_helpers import open_synthetic_scope, synth_innate_overlay


class _FixedRng:
    @staticmethod
    def randint(lower, upper):
        return lower


# Race rows: one divine-capable, two mundane (the gate reads the profile
# flag, never a race name).
_DIVINE_RACE = make_race("t_starlit", can_use_divine_arts=True)
_MUNDANE_RACES = (make_race("t_mudlit"), make_race("t_reedfolk"))

# Gate rows mirroring the family shape: a mastery passive gating the
# sexual-arts family, an act row firing the legacy stimulus event, and
# explicitly-declared unmechanized rows.
_SEXUAL_MASTERY = make_skill(
    "t_divine_mastery",
    label="神性精通",
    description="解鎖情魔法族的合成被動。",
    kind=SkillKind.PASSIVE,
    requires_divine_arts=True,
    effects=["sexual_magic_mastery"],
    category=SkillCategory.SEXUAL_ACT,
)
_SEXUAL_ARTS = make_skill(
    "t_divine_arts",
    label="神之情藝",
    description="對目標施加情觸的合成術式。",
    requires_divine_arts=True,
    effects=["sexual_event:stimulus_applied"],
    category=SkillCategory.SEXUAL_ACT,
)
_UNMECHANIZED = tuple(
    make_skill(
        f"t_mystery_{suffix}",
        label=f"神秘_{suffix}",
        description="宣告存在但尚未機裝化的合成神秘。",
        requires_divine_arts=True,
        target_spec=TargetSpec.NONE,
        effects=[f"divine_mystery:t_{suffix}"],
        category=SkillCategory.DIVINE_MYSTERY,
    )
    for suffix in ("time", "space", "matter", "life")
)
_GATE_SKILLS = (_SEXUAL_MASTERY, _SEXUAL_ARTS) + _UNMECHANIZED
_GATE_ROWS = {skill.key: skill for skill in _GATE_SKILLS}

_SCOPE_EXTRA = {
    "races": {race.key: race for race in (_DIVINE_RACE,) + _MUNDANE_RACES},
    "skills": {
        **synth_innate_overlay()["skills"],
        **_GATE_ROWS,
    },
}


class DivineMysteryGateTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        # setUp constructs entities against the scoped catalogs, so the scope
        # opens here (the kit's class decorator covers test* methods only).
        # sexual_acts joins: an unmaterialized actor enumerates act keys
        # through the act registry, which must stay consistent with the
        # scoped skill rows.
        open_synthetic_scope(self, "races", "skills", "sexual_acts", extra=_SCOPE_EXTRA)
        self.room = create_object(Room, key="divine-room")
        self.actor = create_object(PlayerCharacter, key="divine-actor")
        self.actor.location = self.room
        self.actor.race = _MUNDANE_RACES[0].key
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}

    def resolve(self, skill_key, targets=(), event_context=None):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                skill_key,
                list(targets),
                RoomActionContext(self.room, event_context),
            )
        )

    def _grant(self, skill_key):
        skill = _GATE_ROWS[skill_key]
        bucket = "passive" if skill.kind is SkillKind.PASSIVE else "active"
        self.actor.db.skills[bucket].append(skill_key)

    def _target(self, key="divine-target"):
        target = create_object(PlayerCharacter, key=key)
        target.race = _MUNDANE_RACES[0].key
        target.apply_race_baseline()
        target.location = self.room
        return target

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_races_without_the_flag_cannot_cast_any_divine_mystery_skill(self):
        for race in _MUNDANE_RACES:
            self.actor.race = race.key
            for skill in _GATE_SKILLS:
                self.actor.db.skills = {"active": [], "passive": []}
                self._grant(skill.key)
                with self.subTest(race=race.key, skill=skill.key):
                    result = self.resolve(skill.key)
                    self.assertEqual(result.outcome, "rejected")
                    if skill.kind is SkillKind.PASSIVE:
                        self.assertIs(
                            result.reason, RejectReason.SKILL_NOT_ACTIVE
                        )
                    else:
                        self.assertIs(
                            result.reason, RejectReason.DIVINE_ARTS_FORBIDDEN
                        )

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_flagged_race_casts_sexual_arts_at_no_resource_cost(self):
        self.actor.race = _DIVINE_RACE.key
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [_SEXUAL_ARTS.key], "passive": []}
        target = self._target()
        before = target.sexual.pleasure.value
        result = self.resolve(
            _SEXUAL_ARTS.key,
            targets=[target],
            event_context={"sexual": {"rng": _FixedRng()}},
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.reason, None)
        self.assertGreater(target.sexual.pleasure.value, before)
        self.assertIn(
            "sexual_transition",
            [entry.kind for entry in result.event_log.entries],
        )

    @covers_requirement("skill-registry::divine-sexual-mastery-and-divine-sexual-arts-exist-as-distinct-skills")
    def test_mastery_row_does_not_gate_the_arts_row(self):
        self.actor.race = _DIVINE_RACE.key
        self.actor.apply_race_baseline()
        # Only the arts row is held; the mastery row's absence must not block.
        self.actor.db.skills = {"active": [_SEXUAL_ARTS.key], "passive": []}
        target = self._target()
        result = self.resolve(
            _SEXUAL_ARTS.key,
            targets=[target],
            event_context={"sexual": {"rng": _FixedRng()}},
        )
        self.assertEqual(result.outcome, "success")

    @covers_requirement("divine-mystery::unmechanized-divine-mysteries-are-explicitly-declared-not-silently-missing")
    def test_unmechanized_mysteries_cast_without_state_change(self):
        self.actor.race = _DIVINE_RACE.key
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        for skill in _UNMECHANIZED:
            self._grant(skill.key)
        for skill in _UNMECHANIZED:
            with self.subTest(skill=skill.key):
                before_arousal = self.actor.sexual.arousal.value
                result = self.resolve(skill.key)
                self.assertEqual(result.outcome, "success")
                self.assertEqual(self.actor.sexual.arousal.value, before_arousal)
                self.assertIsNone(self.actor.db.disguised_stats)
                self.assertEqual(
                    [entry.kind for entry in result.event_log.entries],
                    ["skill_practice"],
                )

    def test_preview_rejects_unflagged_race_divine_arts_like_resolution(self):
        self.actor.db.skills = {"active": [_SEXUAL_ARTS.key], "passive": []}
        preview = preview_skill(
            self.actor,
            _SEXUAL_ARTS.key,
            RoomActionContext(self.room),
        )
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_actor_without_resolvable_race_is_rejected(self):
        self.actor.db.skills = {"active": [_SEXUAL_ARTS.key], "passive": []}
        for race in (None, "t_no_such_race"):
            self.actor.race = race
            with self.subTest(race=race):
                result = self.resolve(_SEXUAL_ARTS.key)
                self.assertIs(result.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    def test_flagged_race_preview_enables_unmechanized_mystery(self):
        self.actor.race = _DIVINE_RACE.key
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [_UNMECHANIZED[0].key], "passive": []}
        preview = preview_skill(
            self.actor,
            _UNMECHANIZED[0].key,
            RoomActionContext(self.room),
        )
        self.assertTrue(preview.enabled)

    def test_mechanized_divine_mystery_effect_rejects_without_commit(self):
        with patch(
            "world.rules.action.parse_effect",
            return_value=DivineMysteryEffect(name="t_mystery_time", mechanized=True),
        ):
            with self.assertRaises(Exception) as caught:
                _handle_divine_mystery(
                    self.actor, [], _UNMECHANIZED[0].effects[0], {}, 1.0
                )
        self.assertEqual(
            caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED
        )
