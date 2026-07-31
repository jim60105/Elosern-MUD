"""Action-pipeline and landed-combat integration for fleeing."""

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    DEFAULT_CAST_SECONDS,
    PendingEffect,
    RejectReason,
    _commit,
)
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.overwhelm import (
    hit_rate_verdict,
    resolve_overwhelm,
    team_effective_power,
)
from world.skills.registry import SKILL_REGISTRY


class DisengageResolverIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.pursuer = create_object(PlayerCharacter, key="pursuer")
        for entity in (self.actor, self.pursuer):
            entity.race = "human"
            entity.apply_race_baseline()
            entity.db.skills = {"active": [], "passive": []}
        self.field = Battlefield(
            {
                "escaping": frozenset({"actor"}),
                "pursuing": frozenset({"pursuer"}),
            },
            {"actor": self.actor, "pursuer": self.pursuer},
        )

    def request(self, *, event_context=True):
        return ActionRequest(
            self.actor,
            FLEE_SKILL_KEY,
            [self.actor],
            BattlefieldActionContext(
                self.field,
                event_context=(
                    {"battlefield": self.field} if event_context else {}
                ),
            ),
        )

    def test_flee_definition_and_innate_ownership(self):
        skill = SKILL_REGISTRY[FLEE_SKILL_KEY]
        self.assertEqual(skill.cost, {})
        self.assertFalse(skill.usable_out_of_combat)
        self.assertIn(FLEE_SKILL_KEY, self.actor.skills.owned_keys())

    def test_out_of_combat_dead_and_already_fled_rejections(self):
        outside = ActionRequest(
            self.actor,
            FLEE_SKILL_KEY,
            [self.actor],
            type(
                "OutsideContext",
                (),
                {"battlefield": None, "event_context": {}},
            )(),
        )
        self.assertIs(
            ActionResolver.resolve(outside).reason,
            RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT,
        )
        self.actor.traits.hp.current = 0
        self.assertIs(
            ActionResolver.resolve(self.request()).reason,
            RejectReason.TARGET_DEAD,
        )
        self.actor.traits.hp.current = self.actor.traits.hp.max
        self.field.fled.add("actor")
        self.assertIs(
            ActionResolver.resolve(self.request()).reason,
            RejectReason.TARGET_OUT_OF_RANGE,
        )

    def test_success_ignores_resources_and_emits_timed_event(self):
        self.actor.traits.mp.current = 0
        self.actor.traits.sp.current = 0
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request())
        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.time_cost_seconds, DEFAULT_CAST_SECONDS)
        self.assertIn("actor", self.field.fled)
        self.assertEqual(result.event_log.entries[0].kind, "disengage_attempt")
        self.assertEqual(result.event_log.targets, ("actor",))

    def test_failure_and_missing_context_mutate_nothing(self):
        snapshots = {
            entity.key: {
                "traits": deepcopy(dict(entity.traits.trait_data)),
                "sexual": deepcopy(entity.db.sexual_traits),
                "buffs": deepcopy(entity.db.buffs or {}),
                "grants": deepcopy(entity.db.skill_grants or []),
            }
            for entity in (self.actor, self.pursuer)
        }
        with patch("world.rules.disengage.roll_d100", return_value=1):
            failed = ActionResolver.resolve(self.request())
        self.assertEqual(failed.outcome, "success")
        self.assertFalse(failed.event_log.entries[0].data["success"])
        self.assertEqual(self.field.fled, set())
        for entity in (self.actor, self.pursuer):
            self.assertEqual(
                dict(entity.traits.trait_data),
                snapshots[entity.key]["traits"],
            )
            self.assertEqual(entity.db.sexual_traits, snapshots[entity.key]["sexual"])
            self.assertEqual(entity.db.buffs or {}, snapshots[entity.key]["buffs"])
            self.assertEqual(
                entity.db.skill_grants or [],
                snapshots[entity.key]["grants"],
            )

    def test_landed_combat_consumers_exclude_fled_entity(self):
        self.field.fled.add("actor")
        with patch(
            "world.rules.combat.roll_initiative",
            return_value=["actor", "pursuer"],
        ):
            acted = []
            run_round(
                self.field,
                lambda entity, field: acted.append(entity.key),
            )
        self.assertEqual(acted, ["pursuer"])
        self.assertEqual(team_effective_power(self.field, "escaping"), 0)
        self.assertIsNone(
            hit_rate_verdict(self.field, "escaping", "pursuing")
        )

    def test_mixed_entity_and_battlefield_commit_rolls_back_both(self):
        before = self.actor.traits.atk_phys.value
        effects = [
            PendingEffect(
                self.field,
                "disengage_attempt|actor|1|100|10|10",
                frozenset({"battlefield"}),
                lambda: self.field.fled.add("actor"),
            ),
            PendingEffect(
                self.actor,
                "synthetic",
                frozenset({"traits"}),
                lambda: (
                    setattr(self.actor.traits.atk_phys, "value", before + 1),
                    (_ for _ in ()).throw(RuntimeError("injected")),
                ),
            ),
        ]
        with self.assertRaises(Exception) as caught:
            _commit(effects)
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(self.field.fled, set())
        self.assertEqual(self.actor.traits.atk_phys.value, before)

    def test_failed_flee_spends_turn_while_opponent_still_attacks(self):
        self.pursuer.db.skills = {"active": ["fire_ball"], "passive": []}

        def provider(entity, field):
            if entity is self.actor:
                return self.request()
            return ActionRequest(
                self.pursuer,
                "fire_ball",
                [self.actor],
                BattlefieldActionContext(field),
            )

        before = self.actor.traits.hp.value
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=["actor", "pursuer"],
            ),
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch("world.rules.combat.roll_d100", return_value=100),
        ):
            logs = run_round(self.field, provider)
        self.assertEqual(logs[0].entries[0].kind, "disengage_attempt")
        self.assertFalse(logs[0].entries[0].data["success"])
        self.assertIn("damage", [entry.kind for entry in logs[1].entries])
        self.assertLess(self.actor.traits.hp.value, before)

    def test_overwhelm_recomputes_after_successful_flee(self):
        self.pursuer.race = "elf"
        self.pursuer.apply_race_baseline()
        self.actor.traits.agility.value = self.pursuer.traits.agility.value

        def provider(entity, field):
            return self.request() if entity is self.actor else None

        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=["actor", "pursuer"],
            ),
            patch(
                "world.rules.disengage._attempt_flee",
                return_value=(
                    True,
                    {
                        "roll": 100,
                        "actor_agility": 92.0,
                        "pursuer_agility": 92.0,
                    },
                ),
            ),
        ):
            result = resolve_overwhelm(self.field, provider)
        self.assertEqual(result.rounds_elapsed, 1)
        self.assertTrue(result.battle_over)
        self.assertIn("actor", self.field.fled)
