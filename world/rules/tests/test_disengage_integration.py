"""Action-pipeline and landed-combat integration for fleeing."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

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
from world.tests.synthetic_data import SYNTH_SKILLS
from world.rules.tests.combat_fixtures import grant_lineage

from ._combat_session_helpers import (
    _race_key,
    _live_registry,
    open_synthetic_scope,
    synth_innate_overlay,
)

class DisengageResolverIntegrationTests(EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.pursuer = create_object(PlayerCharacter, key="pursuer")
        for entity in (self.actor, self.pursuer):
            entity.race = _race_key()
            entity.apply_race_baseline()
            # Static magic_power raised to the spell-casting fixture level so
            # the pursuer's element-gated synthetic cast passes.
            entity.traits.magic_power.base = 30
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
        skill = synth_innate_overlay()["skills"][FLEE_SKILL_KEY]
        self.assertEqual(skill.cost, {})
        self.assertFalse(skill.usable_out_of_combat)
        self.assertIn(FLEE_SKILL_KEY, self.actor.skills.owned_keys())

    @covers_requirement("disengage-action::flee-is-a-skilldef-resolved-through-the-unmodified-actionresolver-pipeline")
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
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(self.field.fled, set())
        self.assertEqual(self.actor.traits.atk_phys.value, before)

    def test_failed_flee_spends_turn_while_opponent_still_attacks(self):
        grant_lineage(self.pursuer, [SYNTH_SKILLS["t_ember_burst"].key])

        def provider(entity, field):
            if entity is self.actor:
                return self.request()
            return ActionRequest(
                self.pursuer,
                SYNTH_SKILLS["t_ember_burst"].key,
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
        # A stat-dominant pursuer makes the opening verdict well-formed (the
        # pursuing side overwhelms), so it is the successful flee — not a
        # None verdict — that ends the encounter.
        for key in ("atk_phys", "agility", "defense"):
            getattr(self.pursuer.traits, key).base = 300
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
