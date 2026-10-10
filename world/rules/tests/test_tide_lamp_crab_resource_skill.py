"""Data-contract test: crab resource skill production combat smoke contract

Formally constructs both ``tide_lamp_crab`` variants through the one production
entry point and drives real provider/resolver-backed combat sessions through the
shipped ``lamp_carapace_claw`` kit: a deterministic miss that still grants the
caster's own defense guard, a deterministic hit whose physical HP loss matches
the authored coefficient, mount refresh without magnitude stacking and expiry,
an ally-targeted attempt that damages nothing and still guards the caster, a
late failure at the last staged effect that restores every staged surface, both
exhaustion axes falling back to a resolved ``basic_attack``, pre-dice identity
and affordability rejection, the no-target and positional-contact rejections,
the inclusive 0.35 flee threshold, a depleted-gauge reload and a construction
rollback. No live generative or image service is called anywhere here.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    apply_buff,
    entity_active_buffs,
    has_positional_marker,
    remove_positional_markers,
    tick_buffs,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.combat_session.lifecycle import clear_session, engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    resolve_behaviour_profile,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.progression import practice_claims_for
from world.skills.registry import SKILL_REGISTRY

SKILL_KEY = "lamp_carapace_claw"
BUFF_KEY = "lamp_carapace_guard"

#: Both variants share the shipped kit, grade order and profile; the literal
#: rows are HP/MP/SP/atk_phys/agility/defense/magic_power plus the grade.
_EXPECTED_VARIANTS = {
    "shore_walker": (30, 20, 9, 5, 4, 5, 0, "F"),
    "reef_warden": (60, 30, 15, 12, 4, 7, 0, "E"),
}


def _buff_instances(entity, definition_key: str) -> list:
    """Every live buff instance of one definition key on an entity."""
    return [
        buff
        for buff in getattr(entity, "buffs", None).all.values()
        if buff.definition_key == definition_key
    ]


class TideLampCrabResourceSkillSmokeTests(EvenniaTestCase):
    """Production combat smoke test for the crab resource skill."""

    def _opponent(self, room: Room, key: str) -> PlayerCharacter:
        """One controlled valid opponent that survives the whole session."""
        player = create_object(PlayerCharacter, key=key)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 500
        player.traits.hp.current = 500
        player.traits.mp.base = 100
        player.traits.mp.current = 100
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        player.location = room
        return player

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-individual-construction::the-construction-entry-point-validates-the-declared-kit-and-behavior-binding",
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals",
        "monster-species-registry::variant-skill-kits-and-behavior-references-are-immutable-authored-configuration",
        "monster-flee-policy::every-monster-behaviour-archetype-declares-a-validated-flee-threshold",
        "skill-identity-eligibility::stored-identity-determines-actor-qualification",
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints",
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback",
        "positional-marker::a-displaced-holder-is-unreachable-to-single-target-physical-strikes-in-both-directions",
    )
    def test_production_crab_variants_combat_guard_and_reload(self):
        # 1. Formally construct BOTH variants through the production entry point.
        shore = construct_species_individual("tide_lamp_crab", "shore_walker")
        reef = construct_species_individual("tide_lamp_crab", "reef_warden")
        for monster, expected in (
            (shore, _EXPECTED_VARIANTS["shore_walker"]),
            (reef, _EXPECTED_VARIANTS["reef_warden"]),
        ):
            with self.subTest(variant=monster.variant_key):
                traits = monster.traits
                self.assertEqual(
                    (
                        traits.hp.current,
                        traits.mp.current,
                        traits.sp.current,
                        traits.atk_phys.base,
                        traits.agility.base,
                        traits.defense.base,
                        traits.magic_power.base,
                        monster.danger_grade,
                    ),
                    expected,
                )
                self.assertEqual(
                    monster.db.skills, {"active": [SKILL_KEY], "passive": []}
                )
                self.assertEqual(monster.db.behaviour_tree, "instinctive")
                # The special ability precedes both innate actions (the handler
                # appends unlocked sexual acts after this base set).
                self.assertEqual(
                    monster.skills.base_owned_keys(),
                    [SKILL_KEY, "flee", "basic_attack"],
                )
                self.assertEqual(
                    monster.skills.owned_keys()[:3],
                    [SKILL_KEY, "flee", "basic_attack"],
                )
                profile = resolve_behaviour_profile(monster)
                self.assertIs(profile, BEHAVIOUR_PROFILES["instinctive"])
                self.assertEqual(profile.skill_choice, "first_owned")
                self.assertEqual(profile.target_strategy, "lowest_hp")
                self.assertFalse(profile.prefer_area_when_multiple_enemies)
                self.assertEqual(profile.flee_hp_fraction, 0.35)

        # 2. One controlled valid opponent, one real hostile session.
        room = create_object(Room, key="tidal_flats")
        player = self._opponent(room, "crab_target")
        shore.location = room
        engage(player, shore)
        record = read_session(player)
        battlefield = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({shore.key})},
            {player.key: player, shore.key: shore},
        )
        context = BattlefieldActionContext(battlefield)

        # 3. The production policy selects the owned special ability.
        miss_request = _enemy_policy(shore, battlefield, record)
        self.assertEqual(miss_request.skill_key, SKILL_KEY)
        self.assertEqual(miss_request.targets, [player])

        # 4. Deterministic miss: the target takes nothing, but the self guard is
        #    part of the resolved attempt and both resources are still paid.
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            miss = ActionResolver.resolve(miss_request)
        self.assertEqual(miss.outcome, "success")
        self.assertEqual(player.traits.hp.current, 500)
        self.assertNotIn(BUFF_KEY, entity_active_buffs(player))
        self.assertIn(BUFF_KEY, entity_active_buffs(shore))
        self.assertEqual(evaluate_combat_modifiers(shore)["defense"], 2)
        self.assertEqual(shore.traits.mp.current, 10)
        self.assertEqual(shore.traits.sp.current, 6)

        # 5. Deterministic hit: physical HP loss from the authored coefficient,
        #    the guard refreshed on its single instance and the exact costs.
        hit_request = _enemy_policy(shore, battlefield, record)
        self.assertEqual(hit_request.skill_key, SKILL_KEY)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            hit = ActionResolver.resolve(hit_request)
        self.assertEqual(hit.outcome, "success")
        # 500 - 5: roll 80 with agility 4 gives margin 23, below combat.yaml's
        # solid_hit_margin 40, so the base multiplier applies:
        # round(5 atk_phys * 1.0 * 1.0 coefficient) = 5 over defense 0.
        self.assertEqual(player.traits.hp.current, 495)
        instances = _buff_instances(shore, BUFF_KEY)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].remaining_seconds, 20)
        self.assertEqual(evaluate_combat_modifiers(shore)["defense"], 2)
        self.assertEqual(shore.traits.mp.current, 0)
        self.assertEqual(shore.traits.sp.current, 3)

        # 6. Refresh before expiry: one instance, the literal magnitude and a
        #    restored lifetime (no stacking, no extra instance).
        shore.traits.mp.current = shore.traits.mp.base
        shore.traits.sp.current = shore.traits.sp.base
        refresh_request = _enemy_policy(shore, battlefield, record)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            refreshed = ActionResolver.resolve(refresh_request)
        self.assertEqual(refreshed.outcome, "success")
        self.assertEqual(player.traits.hp.current, 490)
        instances = _buff_instances(shore, BUFF_KEY)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].remaining_seconds, 20)
        self.assertEqual(evaluate_combat_modifiers(shore)["defense"], 2)

        # 7. An ally of the caster is selectable under ANY faction, but the
        #    enemy component delivers nothing to it while the self guard still
        #    mounts and both resources are still paid: the SELF audience keeps
        #    the resolved attempt alive after the ENEMIES audience routes empty.
        ally = self._opponent(room, "crab_ally")
        ally.traits.hp.base = 100
        ally.traits.hp.current = 100
        ally_battlefield = Battlefield(
            {
                "party": frozenset({player.key}),
                "foes": frozenset({shore.key, ally.key}),
            },
            {player.key: player, shore.key: shore, ally.key: ally},
        )
        ally_context = BattlefieldActionContext(ally_battlefield)
        shore.traits.mp.current = shore.traits.mp.base
        shore.traits.sp.current = shore.traits.sp.base
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            ally_result = ActionResolver.resolve(
                ActionRequest(shore, SKILL_KEY, [ally], ally_context)
            )
        self.assertEqual(ally_result.outcome, "success")
        self.assertEqual(ally.traits.hp.current, 100)
        self.assertEqual(ally.traits.mp.current, 100)
        self.assertEqual(evaluate_combat_modifiers(shore)["defense"], 2)
        self.assertEqual(shore.traits.mp.current, 10)
        self.assertEqual(shore.traits.sp.current, 6)

        # 8. Late failure at the LAST staged effect: damage, the self guard and
        #    both resource spends are already applied when the practice award
        #    raises, so this proves the transactional restore, not staging
        #    purity. Every touched surface and the practice claim set return to
        #    their pre-action values and an immediate retry lands the same delta.
        shore.traits.mp.current = shore.traits.mp.base
        shore.traits.sp.current = shore.traits.sp.base
        before = (
            player.traits.hp.current,
            player.traits.mp.current,
            shore.traits.mp.current,
            shore.traits.sp.current,
            len(entity_active_buffs(player)),
            len(_buff_instances(shore, BUFF_KEY)),
        )
        claims_before = practice_claims_for(shore, SKILL_KEY)
        failing_request = _enemy_policy(shore, battlefield, record)
        with patch(
            "world.rules.action.costs.grant_skill_practice_xp",
            side_effect=RuntimeError("injected late failure"),
        ):
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                failed = ActionResolver.resolve(failing_request)
        self.assertEqual(failed.outcome, "rejected")
        self.assertEqual(failed.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(
            (
                player.traits.hp.current,
                player.traits.mp.current,
                shore.traits.mp.current,
                shore.traits.sp.current,
                len(entity_active_buffs(player)),
                len(_buff_instances(shore, BUFF_KEY)),
            ),
            before,
        )
        self.assertEqual(practice_claims_for(shore, SKILL_KEY), claims_before)
        retry_request = _enemy_policy(shore, battlefield, record)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            retried = ActionResolver.resolve(retry_request)
        self.assertEqual(retried.outcome, "success")
        self.assertEqual(player.traits.hp.current, before[0] - 5)
        self.assertEqual(shore.traits.mp.current, before[2] - 10)
        self.assertEqual(shore.traits.sp.current, before[3] - 3)

        # 9. Expiry: the refreshed lifetime passes and the modifier is gone.
        tick_buffs(shore, 6)
        self.assertIn(BUFF_KEY, entity_active_buffs(shore))
        self.assertEqual(_buff_instances(shore, BUFF_KEY)[0].remaining_seconds, 14)
        tick_buffs(shore, 14)
        self.assertNotIn(BUFF_KEY, entity_active_buffs(shore))
        self.assertEqual(evaluate_combat_modifiers(shore).get("defense", 0), 0)

        # 10. Each exhaustion axis falls back to a resolved ordinary attack.
        shore.traits.mp.current = 0
        shore.traits.sp.current = 3
        mp_drained = _enemy_policy(shore, battlefield, record)
        self.assertEqual(mp_drained.skill_key, "basic_attack")
        hp_before_mp = player.traits.hp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            mp_drained_result = ActionResolver.resolve(mp_drained)
        self.assertEqual(mp_drained_result.outcome, "success")
        self.assertLess(player.traits.hp.current, hp_before_mp)
        self.assertEqual(shore.traits.mp.current, 0)
        self.assertEqual(shore.traits.sp.current, 3)

        shore.traits.mp.current = 20
        shore.traits.sp.current = 2
        sp_drained = _enemy_policy(shore, battlefield, record)
        self.assertEqual(sp_drained.skill_key, "basic_attack")
        hp_before_sp = player.traits.hp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            sp_drained_result = ActionResolver.resolve(sp_drained)
        self.assertEqual(sp_drained_result.outcome, "success")
        self.assertLess(player.traits.hp.current, hp_before_sp)
        self.assertEqual(shore.traits.mp.current, 20)
        self.assertEqual(shore.traits.sp.current, 2)

        # 11. Identity and affordability reject before any dice, costs, guard or
        #     practice: an ineligible owner and an under-resourced caster.
        corrupt = self._opponent(room, "corrupt_crab_holder")
        corrupt.db.skills = {"active": [SKILL_KEY], "passive": []}
        guard_instances_before = len(_buff_instances(shore, BUFF_KEY))
        sp_before_rejection = shore.traits.sp.current
        with patch("world.rules.combat.damage.roll_d100") as roller:
            identity_result = ActionResolver.resolve(
                ActionRequest(corrupt, SKILL_KEY, [player], context)
            )
            self.assertEqual(identity_result.outcome, "rejected")
            self.assertEqual(identity_result.reason, RejectReason.IDENTITY_INELIGIBLE)
            shore.traits.mp.current = 9
            under_resourced = ActionResolver.resolve(
                ActionRequest(shore, SKILL_KEY, [player], context)
            )
            self.assertEqual(under_resourced.outcome, "rejected")
            self.assertEqual(under_resourced.reason, RejectReason.INSUFFICIENT_RESOURCE)
            roller.assert_not_called()
        self.assertEqual(len(_buff_instances(shore, BUFF_KEY)), guard_instances_before)
        self.assertEqual(shore.traits.mp.current, 9)
        self.assertEqual(shore.traits.sp.current, sp_before_rejection)

        # 12. The ordinary SINGLE target gate rejects a no-target request, and
        #     the unchanged positional-contact gate rejects a displaced target;
        #     neither consumes anything and neither becomes a self-cast.
        shore.traits.mp.current = 20
        shore.traits.sp.current = 9
        no_target = ActionResolver.resolve(ActionRequest(shore, SKILL_KEY, [], context))
        self.assertEqual(no_target.outcome, "rejected")
        self.assertEqual(no_target.reason, RejectReason.TARGET_SPEC_MISMATCH)
        sp_before_displaced = shore.traits.sp.current
        apply_buff(player, "displaced")
        self.assertTrue(has_positional_marker(player))
        displaced = ActionResolver.resolve(
            ActionRequest(shore, SKILL_KEY, [player], context)
        )
        self.assertEqual(displaced.outcome, "rejected")
        self.assertEqual(displaced.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertEqual(shore.traits.mp.current, 20)
        self.assertEqual(shore.traits.sp.current, sp_before_displaced)
        # The strike-only kit cannot select a displaced enemy at all, so the
        # marker is cleared before any later step runs against this opponent.
        self.assertIsNone(_enemy_policy(shore, battlefield, record))
        remove_positional_markers(player)
        self.assertFalse(has_positional_marker(player))

        # 13. Scene prose and environment-looking facts are not mechanics: the
        #     same deterministic cast produces the identical delta after the
        #     room's description is rewritten with light/fog prose, and the
        #     declaration carries no cast condition to read one.
        self.assertEqual(SKILL_REGISTRY[SKILL_KEY].cast_conditions, ())
        room.db.desc = "礁隙間燈光搖曳，濃霧貼著潮池，甲殼反射著明明暗暗的節奏。"
        hp_before_prose = player.traits.hp.current
        prose_request = _enemy_policy(shore, battlefield, record)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            prose_result = ActionResolver.resolve(prose_request)
        self.assertEqual(prose_result.outcome, "success")
        self.assertEqual(player.traits.hp.current, hp_before_prose - 5)

        # 14. Inclusive flee threshold: exactly 0.35 disengages, above it the
        #     kit acts, and the request resolves through the shared resolver.
        shore.traits.mp.current = 20
        shore.traits.sp.current = 9
        shore.traits.hp.base = 20
        shore.traits.hp.current = 7
        self.assertEqual(
            _enemy_policy(shore, battlefield, record).skill_key, FLEE_SKILL_KEY
        )
        shore.traits.hp.current = 8
        self.assertEqual(
            _enemy_policy(shore, battlefield, record).skill_key, SKILL_KEY
        )
        shore.traits.hp.current = 7
        flee_request = _enemy_policy(shore, battlefield, record)
        self.assertEqual(flee_request.skill_key, FLEE_SKILL_KEY)
        self.assertEqual(flee_request.targets, [shore])
        with patch("world.rules.disengage.roll_d100", return_value=100):
            fled = ActionResolver.resolve(flee_request)
        self.assertEqual(fled.outcome, "success")
        self.assertIn(shore.key, battlefield.fled)

        # 15. Depleted production actors reload with identity, kit, binding and
        #     current gauges intact; construction does not recreate them.
        shore.traits.hp.base = 30
        shore.traits.hp.current = 30
        shore.traits.mp.current = 3
        shore.traits.sp.current = 2
        before_rows = Monster.objects.count()
        reloaded = Monster.objects.get(pk=shore.pk)
        self.assertEqual(reloaded.species_key, "tide_lamp_crab")
        self.assertEqual(reloaded.variant_key, "shore_walker")
        self.assertEqual(reloaded.db.skills, {"active": [SKILL_KEY], "passive": []})
        self.assertEqual(reloaded.db.behaviour_tree, "instinctive")
        self.assertEqual(reloaded.traits.mp.current, 3)
        self.assertEqual(reloaded.traits.sp.current, 2)
        self.assertEqual(Monster.objects.count(), before_rows)

        # 16. A late construction failure leaves no partial individual behind.
        from django.db import transaction

        rows_before_failure = Monster.objects.count()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                construct_species_individual("tide_lamp_crab", "reef_warden")
                raise RuntimeError("injected construction failure")
        self.assertEqual(Monster.objects.count(), rows_before_failure)

        # 17. The second variant resolves the same kit through the same path.
        clear_session(player)
        reef.location = room
        engage(player, reef)
        record_reef = read_session(player)
        battlefield_reef = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({reef.key})},
            {player.key: player, reef.key: reef},
        )
        reef_request = _enemy_policy(reef, battlefield_reef, record_reef)
        self.assertEqual(reef_request.skill_key, SKILL_KEY)
        hp_before_reef = player.traits.hp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            reef_result = ActionResolver.resolve(reef_request)
        self.assertEqual(reef_result.outcome, "success")
        # round(12 atk_phys * 1.0 * 1.0 coefficient) = 12 over defense 0.
        self.assertEqual(player.traits.hp.current, hp_before_reef - 12)
        self.assertIn(BUFF_KEY, entity_active_buffs(reef))
        self.assertEqual(evaluate_combat_modifiers(reef)["defense"], 2)
        self.assertEqual(reef.traits.mp.current, 20)
        self.assertEqual(reef.traits.sp.current, 12)
