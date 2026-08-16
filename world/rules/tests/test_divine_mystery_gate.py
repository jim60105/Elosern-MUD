"""Race-gate and cast-path tests for the 神之秘法 skill family."""

"""Race-gate and cast-path tests for the 神之秘法 skill family."""

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
from world.skills.registry import SKILL_REGISTRY, SkillKind


class _FixedRng:
    @staticmethod
    def randint(lower, upper):
        return lower


DIVINE_SKILL_KEYS = (
    "divine_sexual_mastery",
    "divine_sexual_arts",
    "divine_time_dilation",
    "divine_space_distortion",
    "divine_matter_transmutation",
    "divine_life_extension",
)
UNMECHANIZED_KEYS = DIVINE_SKILL_KEYS[2:]


class DivineMysteryGateTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="divine-room")
        self.actor = create_object(PlayerCharacter, key="divine-actor")
        self.actor.location = self.room
        self.actor.race = "human"
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
        skill = SKILL_REGISTRY[skill_key]
        bucket = "passive" if skill.kind is SkillKind.PASSIVE else "active"
        self.actor.db.skills[bucket].append(skill_key)

    def _target(self, key="divine-target"):
        target = create_object(PlayerCharacter, key=key)
        target.race = "human"
        target.apply_race_baseline()
        target.location = self.room
        return target

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_non_elf_cannot_cast_any_divine_mystery_skill(self):
        for race_key in ("human", "beastfolk"):
            self.actor.race = race_key
            for skill_key in DIVINE_SKILL_KEYS:
                skill = SKILL_REGISTRY[skill_key]
                self.actor.db.skills = {"active": [], "passive": []}
                self._grant(skill_key)
                with self.subTest(race=race_key, skill=skill_key):
                    result = self.resolve(skill_key)
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
    def test_elf_casts_divine_sexual_arts_at_no_resource_cost(self):
        self.actor.race = "elf"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": ["divine_sexual_arts"], "passive": []}
        target = self._target()
        before = target.sexual.pleasure.value
        result = self.resolve(
            "divine_sexual_arts",
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
    def test_sexual_mastery_does_not_gate_divine_sexual_arts(self):
        self.actor.race = "elf"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": ["divine_sexual_arts"], "passive": []}
        target = self._target()
        result = self.resolve(
            "divine_sexual_arts",
            targets=[target],
            event_context={"sexual": {"rng": _FixedRng()}},
        )
        self.assertEqual(result.outcome, "success")

    @covers_requirement("divine-mystery::unmechanized-divine-mysteries-are-explicitly-declared-not-silently-missing")
    def test_unmechanized_mysteries_cast_without_state_change(self):
        self.actor.race = "elf"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        for skill_key in UNMECHANIZED_KEYS:
            self._grant(skill_key)
        for skill_key in UNMECHANIZED_KEYS:
            with self.subTest(skill=skill_key):
                before_arousal = self.actor.sexual.arousal.value
                result = self.resolve(skill_key)
                self.assertEqual(result.outcome, "success")
                self.assertEqual(self.actor.sexual.arousal.value, before_arousal)
                self.assertIsNone(self.actor.db.disguised_stats)
                self.assertEqual(
                    [entry.kind for entry in result.event_log.entries],
                    ["skill_practice"],
                )

    def test_preview_rejects_non_elf_divine_arts_like_resolution(self):
        self.actor.db.skills = {"active": ["divine_sexual_arts"], "passive": []}
        preview = preview_skill(
            self.actor,
            "divine_sexual_arts",
            RoomActionContext(self.room),
        )
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_actor_without_resolvable_race_is_rejected(self):
        self.actor.db.skills = {"active": ["divine_sexual_arts"], "passive": []}
        for race in (None, "unknown_race"):
            self.actor.race = race
            with self.subTest(race=race):
                result = self.resolve("divine_sexual_arts")
                self.assertIs(result.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    def test_elf_preview_enables_unmechanized_mystery(self):
        self.actor.race = "elf"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": ["divine_time_dilation"], "passive": []}
        preview = preview_skill(
            self.actor,
            "divine_time_dilation",
            RoomActionContext(self.room),
        )
        self.assertTrue(preview.enabled)

    def test_mechanized_divine_mystery_effect_rejects_without_commit(self):
        with patch(
            "world.rules.action.parse_effect",
            return_value=DivineMysteryEffect(name="時間加速", mechanized=True),
        ):
            with self.assertRaises(Exception) as caught:
                _handle_divine_mystery(self.actor, [], "divine_mystery:時間加速", {}, 1.0)
        self.assertEqual(caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
