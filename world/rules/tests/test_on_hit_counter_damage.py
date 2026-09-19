"""Synthetic behavior tests for on-hit counter-damage and source-targeted reactions.

Covers requirements:
- damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event
- damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion
"""

import importlib
import math
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    COMBAT_YAML,
    _handle_damage,
)
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_outcome_reaction,
    validate_state_reaction_rules,
)
from world.rules.tests.combat_fixtures import grant_lineage
from world.skills.effects import EffectAudience, EffectPolicy, ResolvedEffect
from world.skills.registry import (
    DamageEffect,
    DamagePolicy,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_skill(
    key: str,
    effects: tuple[str, ...] | list[str] = (),
    *,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = None,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    category: SkillCategory = SkillCategory.MARTIAL_ARTS,
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] = (),
) -> SkillDef:
    elem = _ELEMENT_MAP.get(element) if element is not None else None
    parsed = []
    for eff in effects:
        parts = eff.split(":")
        if parts[0] == "damage":
            parsed.append(DamageEffect(element=parts[1], school=parts[2]))
    if not effect_policies and effects:
        effect_policies = [EffectPolicy(coefficient=1.0, audience=EffectAudience.SELECTED)]
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=elem,
        effects=list(effects),
        category=category,
        effect_policies=tuple(effect_policies),
        parsed_effects=tuple(parsed),
    )


class OnHitCounterDamageBehaviorTests(EvenniaTest):
    """Behavior tests for on-hit counter-damage mechanics using synthetic fixtures."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_room")
        self.actor = create_object(PlayerCharacter, key="synth_actor")
        self.target = create_object(PlayerCharacter, key="synth_target")
        self.third = create_object(PlayerCharacter, key="synth_third")

        for entity in (self.actor, self.target, self.third):
            entity.location = self.room
            entity.race = "human"
            entity.apply_race_baseline()
            entity.traits.hp.base = 200
            entity.traits.hp.current = 200
            entity.traits.mp.base = 500
            entity.traits.mp.current = 500
            entity.traits.atk_phys.base = 50
            entity.traits.defense.base = 10
            entity.traits.agility.base = 10
            entity.traits.magic_power.base = 30

    def _register_synth_skill(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def _register_synth_buff(self, buff: BuffDefinition) -> BuffDefinition:
        patcher = patch.dict(BUFF_DEFINITIONS, {buff.key: buff}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return buff

    def _grant_skill(
        self, entity: Any, skill_key: str, kind: SkillKind = SkillKind.PASSIVE
    ) -> None:
        raw = dict(entity.db.skills or {"active": [], "passive": []})
        actives = list(raw.get("active", []))
        passives = list(raw.get("passive", []))
        if kind == SkillKind.PASSIVE:
            if skill_key not in passives:
                passives.append(skill_key)
        else:
            if skill_key not in actives:
                actives.append(skill_key)
        grant_lineage(entity, active=actives, passive=passives)

    def _make_battlefield(self, actor: Any, *foes: Any) -> Battlefield:
        all_entities = (actor, *foes)
        roster = {ent.key: ent for ent in all_entities}
        party_keys = frozenset({actor.key})
        foe_keys = frozenset(ent.key for ent in foes)
        return Battlefield({"party": party_keys, "foes": foe_keys}, roster)

    # -------------------------------------------------------------------------
    # Requirement 1: A qualifying physical strike dispatches one source-attributed on-hit event
    # -------------------------------------------------------------------------

    @covers_requirement(
        "damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event"
    )
    def test_landed_physical_hit_fires_event_once_with_source(self):
        """Scenario: A landed physical hit fires the event once with its source.

        WHEN a synthetic physical strike from caster A lands positive HP loss on a target
        while a synthetic physical_hit-keyed reaction rule is loaded
        THEN the rule executes exactly once for that strike against the target, and its action
        sees A as the event source with the strike's captured tier.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_on_hit_passive", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_hit_received",
                duration=60,
                tick_interval=None,
                stacking="refresh",
                modifiers={},
                polarity="buff",
            )
        )

        rule = Rule(
            id="synth_on_physical_hit_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"apply_buff": buff_def.key},
        )
        with patch("world.rules.state_reactions.STATE_REACTION_RULES", STATE_REACTION_RULES + [rule]):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_slash", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            self.assertLess(self.target.traits.hp.current, 200)
            self.assertIn("synth_hit_received", entity_active_buffs(self.target))

    @covers_requirement(
        "damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event"
    )
    def test_non_qualifying_writes_stay_silent(self):
        """Scenario: Non-qualifying writes stay silent.

        WHEN a magic strike, a missed physical swing, a zero-loss physical write
        and a damaging rate tick all settle against the same reactor
        THEN the physical_hit rule executes zero times while each source's existing hp_loss
        behavior is unchanged.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_silent_passive", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_should_never_apply",
                duration=60,
                tick_interval=None,
                stacking="refresh",
                modifiers={},
                polarity="buff",
            )
        )

        rule = Rule(
            id="synth_silent_check_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"apply_buff": buff_def.key},
        )
        with patch("world.rules.state_reactions.STATE_REACTION_RULES", STATE_REACTION_RULES + [rule]):
            bf = self._make_battlefield(self.actor, self.target)

            # 1. Magic strike -> dispatches hp_loss, but physical_hit stays silent
            magic_skill = self._register_synth_skill(
                _make_synth_skill("synth_fireball", ["damage:fire:magic"], category=SkillCategory.ELEMENTAL_MAGIC)
            )
            self._grant_skill(self.actor, magic_skill.key, SkillKind.ACTIVE)
            req_magic = ActionRequest(self.actor, magic_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res_magic = ActionResolver.resolve(req_magic)
            self.assertEqual(res_magic.outcome, "success")
            self.assertNotIn("synth_should_never_apply", entity_active_buffs(self.target))

            # 2. Missed physical swing -> to_hit returns False
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_strike_miss", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)
            req_miss = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat._to_hit", return_value=(False, -20.0)):
                res_miss = ActionResolver.resolve(req_miss)
            self.assertEqual(res_miss.outcome, "success")
            self.assertNotIn("synth_should_never_apply", entity_active_buffs(self.target))

            # 3. Zero-loss physical write -> target is already at 0 HP; _handle_damage staged apply produces zero loss
            self.target.traits.hp.current = 0
            with patch("world.rules.combat.roll_d100", return_value=100):
                pending = _handle_damage(
                    self.actor,
                    [self.target],
                    "damage:earth:physical",
                    {"battlefield": bf},
                    1.0,
                )
                for eff in pending:
                    eff.apply()
            self.assertNotIn("synth_should_never_apply", entity_active_buffs(self.target))

            # 4. Damaging rate tick -> periodic tick on buff
            self.target.traits.hp.current = 100
            dot_buff = self._register_synth_buff(
                BuffDefinition(
                    key="synth_bleed_dot",
                    duration=60,
                    tick_interval=10,
                    stacking="refresh",
                    modifiers={"rate": {"target": "hp", "delta": -10}},
                    polarity="debuff",
                )
            )
            apply_buff(self.target, dot_buff.key)
            records = tick_buffs(self.target, 10)
            self.assertTrue(len(records) > 0)
            self.assertNotIn("synth_should_never_apply", entity_active_buffs(self.target))

    @covers_requirement(
        "damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event"
    )
    def test_unknown_event_value_fails_load_closed(self):
        """Scenario: An unknown event value fails the load closed.

        WHEN a synthetic rule file declares when.event: turned_to_stone
        THEN rule loading raises naming the rule id, and the shipped rule file loads unchanged.
        """
        bad_rule = Rule(
            id="bad_event_stone_rule",
            when={"event": "turned_to_stone"},
            then={"pleasure_gain": 10},
        )
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([bad_rule])
        self.assertIn("bad_event_stone_rule", str(ctx.exception))
        self.assertIn("turned_to_stone", str(ctx.exception))

        # Boolean event value rejected
        bool_rule = Rule(
            id="bad_event_bool_rule",
            when={"event": True},
            then={"pleasure_gain": 10},
        )
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([bool_rule])
        self.assertIn("bad_event_bool_rule", str(ctx.exception))

        # Shipped rules validate cleanly
        validate_state_reaction_rules(STATE_REACTION_RULES)

    @covers_requirement(
        "damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event"
    )
    def test_multi_strike_policy_fires_per_qualifying_strike(self):
        """Scenario: Multi-strike policies fire per qualifying strike.

        WHEN a policy-declared double-strike lands both strikes physically on the reactor
        THEN the event dispatches once per landing strike, each carrying the same source,
        and a first miss dispatches nothing for the missed strike.
        """
        hit_counts: list[str] = []

        def counting_dispatch(entity, event, *args, **kwargs):
            if event == "physical_hit":
                hit_counts.append(kwargs.get("source").key)

        policy = DamagePolicy(
            repeat_when="forced_interaction",
            extra_strikes=1,
            unconditional_defense_bypass=False,
            bypass_defense=False,
            predicate=(),
            attack_multiplier=1.0,
            max_hp_fraction=0.0,
        )

        double_skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_double_strike",
                ["damage:earth:physical"],
                effect_policies=[
                    EffectPolicy(
                        coefficient=1.0,
                        audience=EffectAudience.SELECTED,
                        damage=policy,
                    )
                ],
            )
        )
        self._grant_skill(self.actor, double_skill.key, SkillKind.ACTIVE)
        bf = self._make_battlefield(self.actor, self.target)
        resolved = ResolvedEffect(
            policy=EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELECTED,
                damage=policy,
            ),
            source_skill=double_skill,
        )

        # 1. Both strikes land
        with (
            patch("world.rules.combat.has_action_evidence", return_value=True),
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat.dispatch_outcome_reaction", side_effect=counting_dispatch),
        ):
            pending = _handle_damage(
                self.actor,
                [self.target],
                "damage:earth:physical",
                {"battlefield": bf, "resolved_effect": resolved},
                1.0,
            )
            for eff in pending:
                eff.apply()

        self.assertEqual(len(hit_counts), 2)
        self.assertEqual(hit_counts, [self.actor.key, self.actor.key])

        # 2. First strike misses, second strike hits
        hit_counts.clear()
        to_hit_results = [(False, -10.0), (True, 10.0)]
        with (
            patch("world.rules.combat.has_action_evidence", return_value=True),
            patch("world.rules.combat._to_hit", side_effect=lambda a, t, r: to_hit_results.pop(0)),
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat.dispatch_outcome_reaction", side_effect=counting_dispatch),
        ):
            pending = _handle_damage(
                self.actor,
                [self.target],
                "damage:earth:physical",
                {"battlefield": bf, "resolved_effect": resolved},
                1.0,
            )
            for eff in pending:
                eff.apply()

        self.assertEqual(len(hit_counts), 1)
        self.assertEqual(hit_counts, [self.actor.key])

    # -------------------------------------------------------------------------
    # Requirement 2: Source-targeted reaction actions settle once, in-transaction, without recursion
    # -------------------------------------------------------------------------

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_thorn_counter_returns_coefficient_priced_damage_to_attacker(self):
        """Scenario: A thorn-shaped counter returns coefficient-priced damage to the attacker.

        WHEN a synthetic reactor with a physical_hit + counter_damage: 1.0 rule is hit
        for positive physical loss by a living attacker
        THEN the attacker loses the holder's effective-attack x 1.0 amount minus its ordinary
        defense exactly once, the initiating strike's damage and practice settlement are unchanged,
        and the attacker's own hp_loss reactions fire once for the counter's loss.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_thorn_passive", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        # Attacker also has hp_loss reaction (e.g. gains pleasure on taking damage)
        attacker_passive = self._register_synth_skill(
            _make_synth_skill("synth_attacker_feedback", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.actor, attacker_passive.key, SkillKind.PASSIVE)

        rule_counter = Rule(
            id="synth_thorn_counter_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"counter_damage": 1.0},
        )
        rule_attacker_loss = Rule(
            id="synth_attacker_loss_rule",
            when={"event": "hp_loss", "skill_qualified": attacker_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_counter, rule_attacker_loss],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_attack", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            # Target atk_phys is 50. Attacker defense is 10.
            # Expected counter damage: max(1, round(50 * 1.0) - 10) = 40.
            actor_hp_before = self.actor.traits.hp.current
            target_hp_before = self.target.traits.hp.current

            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            # Target took damage from strike
            self.assertLess(self.target.traits.hp.current, target_hp_before)

            # Attacker took counter damage of exactly 40
            expected_counter = 40
            self.assertEqual(
                actor_hp_before - self.actor.traits.hp.current,
                expected_counter,
            )

            # Attacker's hp_loss reaction fired once, priced by the counter's
            # own actual loss (40 of 200 max HP): floor(140 x 40 / 200) = 28.
            self.assertEqual(self.actor.sexual.pleasure.base, 28)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_counters_cannot_chain(self):
        """Scenario: Counters cannot chain.

        WHEN the attacker also holds a physical_hit + counter_damage rule of its own
        THEN only the struck reactor's counter settles for the initiating strike, the
        attacker's rule does not execute on the counter's loss, and HP movement terminates
        after one counter per strike.
        """
        passive_target = self._register_synth_skill(
            _make_synth_skill("synth_thorn_target", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive_target.key, SkillKind.PASSIVE)

        passive_actor = self._register_synth_skill(
            _make_synth_skill("synth_thorn_actor", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.actor, passive_actor.key, SkillKind.PASSIVE)

        rule_target_thorn = Rule(
            id="synth_target_thorn",
            when={"event": "physical_hit", "skill_qualified": passive_target.key},
            then={"counter_damage": 1.0},
        )
        rule_actor_thorn = Rule(
            id="synth_actor_thorn",
            when={"event": "physical_hit", "skill_qualified": passive_actor.key},
            then={"counter_damage": 1.0},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_target_thorn, rule_actor_thorn],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_strike", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            # Target took strike damage (once).
            # Actor took counter damage from target (once: 40 loss).
            # Target did NOT take a second counter from actor!
            target_hp_after_strike = self.target.traits.hp.current
            self.assertEqual(self.actor.traits.hp.current, 200 - 40)
            # Initiating strike landed critical hit (roll=100 -> 2.0x mult: 50 * 2.0 - 10 def = 90 damage)
            # Target HP must be exactly 110 (200 - 90), proving no secondary counter settled (which would be 70)
            self.assertEqual(target_hp_after_strike, 110)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_counter_settles_and_rolls_back_with_its_round(self):
        """Scenario: The counter settles and rolls back with its round.

        WHEN a synthetic settlement fails at a commit step after the counter already moved HP
        THEN the initiating loss, the counter HP and every staged surface restore together,
        leaving neither party changed.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_thorn_rb", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        rule_counter = Rule(
            id="synth_rb_counter_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"counter_damage": 1.0},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_counter],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_strike_rb", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))

            # Simulate a late failure in _commit by injecting an effect that fails during apply
            import world.rules.action as action_mod
            orig_stage = action_mod._step5_effect_resolution

            def failing_step5(*args, **kwargs):
                effects = orig_stage(*args, **kwargs)

                def bomb_apply():
                    raise ValueError("simulated late commit failure")

                bomb = PendingEffect(
                    entity=self.target,
                    description="bomb|failure",
                    surfaces=frozenset({"traits"}),
                    apply=bomb_apply,
                )
                return effects + [bomb]

            actor_hp_before = self.actor.traits.hp.current
            target_hp_before = self.target.traits.hp.current

            with (
                patch("world.rules.action.resolver._step5_effect_resolution", side_effect=failing_step5),
                patch("world.rules.combat.roll_d100", return_value=100),
            ):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "rejected")
            # Both parties' HP are completely restored
            self.assertEqual(self.actor.traits.hp.current, actor_hp_before)
            self.assertEqual(self.target.traits.hp.current, target_hp_before)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_ignite_shaped_source_buff_rides_same_event_as_data(self):
        """Scenario: An ignite-shaped source buff rides the same event as data.

        WHEN a synthetic reactor with a physical_hit + apply_buff_to_source rule is hit
        physically by a living attacker not immune to the named debuff, and separately
        by an immune attacker and a sourceless write
        THEN the first attacker holds the live instance with grant-time attribution to the reactor,
        the immune attacker holds nothing, the sourceless write applies nothing, and no counter
        vocabulary is involved.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_ignite_passive", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        ignite_buff = self._register_synth_buff(
            BuffDefinition(
                key="synth_ignite_debuff",
                duration=30,
                tick_interval=10,
                stacking="unique_per_source",
                modifiers={"rate": {"target": "hp", "delta": -5}},
                polarity="debuff",
            )
        )

        rule_ignite = Rule(
            id="synth_ignite_on_hit_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"apply_buff_to_source": ignite_buff.key},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_ignite],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_strike_ignite", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            # 1. First attacker is hit by reactor's reaction -> gets unique_per_source ignite
            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            expected_instance_key = f"{ignite_buff.key}:{self.target.key}"
            self.assertIn(expected_instance_key, self.actor.buffs.all)
            instance = self.actor.buffs.all[expected_instance_key]
            self.assertEqual(instance.source_key, self.target.key)

            # 2. Immune attacker -> holds nothing
            immune_actor = create_object(PlayerCharacter, key="synth_immune_actor")
            immune_actor.location = self.room
            immune_actor.race = "human"
            immune_actor.apply_race_baseline()
            immune_actor.traits.atk_phys.base = 50
            immune_actor.traits.defense.base = 10
            immune_actor.traits.agility.base = 10
            self._grant_skill(immune_actor, physical_skill.key, SkillKind.ACTIVE)

            with patch(
                "world.rules.equipment_effects.equipment_immune_buff_keys",
                return_value=frozenset({ignite_buff.key}),
            ):
                bf_immune = self._make_battlefield(immune_actor, self.target)
                req_immune = ActionRequest(immune_actor, physical_skill.key, [self.target], BattlefieldActionContext(bf_immune))
                with patch("world.rules.combat.roll_d100", return_value=100):
                    res_imm = ActionResolver.resolve(req_immune)
                self.assertEqual(res_imm.outcome, "success")
                self.assertNotIn(expected_instance_key, immune_actor.buffs.all)
                self.assertNotIn(ignite_buff.key, entity_active_buffs(immune_actor))

            # 3. Sourceless write -> dispatch_outcome_reaction called with source=None
            target_buffs_before = set(self.target.buffs.all.keys())
            dispatch_outcome_reaction(self.target, "physical_hit", source=None)
            self.assertEqual(set(self.target.buffs.all.keys()), target_buffs_before)

            # 4. Dead attacker -> silent no-write
            dead_actor = create_object(PlayerCharacter, key="synth_dead_actor")
            dead_actor.location = self.room
            dead_actor.race = "human"
            dead_actor.apply_race_baseline()
            dead_actor.traits.hp.current = 0
            dispatch_outcome_reaction(self.target, "physical_hit", source=dead_actor)
            self.assertNotIn(expected_instance_key, dead_actor.buffs.all)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_malformed_source_actions_fail_load_closed(self):
        """Scenario: Malformed source actions fail the rule load closed.

        WHEN rules declare counter_damage: -1, counter_damage: abc, a boolean coefficient,
        apply_buff_to_source naming an unknown definition, both source actions in one then,
        or a source action alongside a legacy action
        THEN each raises at load time naming the offending rule id, and every previously
        valid rule file loads unchanged.
        """
        # Negative counter_damage
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="neg_counter", when={"event": "physical_hit"}, then={"counter_damage": -1})
            ])
        self.assertIn("neg_counter", str(ctx.exception))

        # String counter_damage
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="str_counter", when={"event": "physical_hit"}, then={"counter_damage": "abc"})
            ])
        self.assertIn("str_counter", str(ctx.exception))

        # Boolean counter_damage
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="bool_counter", when={"event": "physical_hit"}, then={"counter_damage": True})
            ])
        self.assertIn("bool_counter", str(ctx.exception))

        # Zero counter_damage
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="zero_counter", when={"event": "physical_hit"}, then={"counter_damage": 0})
            ])
        self.assertIn("zero_counter", str(ctx.exception))

        # Non-finite counter_damage
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="inf_counter", when={"event": "physical_hit"}, then={"counter_damage": math.inf})
            ])
        self.assertIn("inf_counter", str(ctx.exception))

        # Unknown buff definition for apply_buff_to_source
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="unknown_buff_rule", when={"event": "physical_hit"}, then={"apply_buff_to_source": "nonexistent_buff_xyz"})
            ])
        self.assertIn("unknown_buff_rule", str(ctx.exception))

        # Boolean apply_buff_to_source
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="bool_buff_rule", when={"event": "physical_hit"}, then={"apply_buff_to_source": True})
            ])
        self.assertIn("bool_buff_rule", str(ctx.exception))

        # Both source actions in one then
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="both_source", when={"event": "physical_hit"}, then={"counter_damage": 1.0, "apply_buff_to_source": "blind"})
            ])
        self.assertIn("both_source", str(ctx.exception))

        # Source action alongside legacy action
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([
                Rule(id="mixed_actions", when={"event": "physical_hit"}, then={"counter_damage": 1.0, "apply_buff": "blind"})
            ])
        self.assertIn("mixed_actions", str(ctx.exception))

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_protected_source_floors_at_one_with_knockout_mark(self):
        """Test that a nonlethal-protected attacker taking fatal counter damage floors at 1 HP

        and receives a battlefield.knocked_out mark without dying or reviving.
        """
        passive = self._register_synth_skill(
            _make_synth_skill("synth_thorn_ko", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        rule_counter = Rule(
            id="synth_ko_counter_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"counter_damage": 1.0},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_counter],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_strike_ko", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            # Actor HP is 20. Target atk_phys=50, Actor defense=10 -> counter damage=40 > 20 (lethal).
            self.actor.traits.hp.current = 20
            bf = self._make_battlefield(self.actor, self.target)

            with (
                patch("world.rules.combat.roll_d100", return_value=100),
            ):
                pending = _handle_damage(
                    self.actor,
                    [self.target],
                    "damage:earth:physical",
                    {
                        "battlefield": bf,
                        "nonlethal_keys": frozenset({str(self.actor.key)}),
                    },
                    1.0,
                )
                for eff in pending:
                    eff.apply()

            # Attacker was protected: floored at 1 HP
            self.assertEqual(int(self.actor.traits.hp.current), 1)
            # Battlefield marked attacker as knocked_out
            self.assertIn(str(self.actor.key), bf.knocked_out)

            # 2. Session-flag nonlethal (empty nonlethal_keys): floors at 1 HP without battlefield mark
            self.actor.traits.hp.current = 20
            bf2 = self._make_battlefield(self.actor, self.target)
            with patch("world.rules.combat.roll_d100", return_value=100):
                pending2 = _handle_damage(
                    self.actor,
                    [self.target],
                    "damage:earth:physical",
                    {
                        "battlefield": bf2,
                        "nonlethal": True,
                        "nonlethal_keys": frozenset(),
                    },
                    1.0,
                )
                for eff in pending2:
                    eff.apply()

            self.assertEqual(int(self.actor.traits.hp.current), 1)
            self.assertNotIn(str(self.actor.key), bf2.knocked_out)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_dead_source_counter_produces_silent_no_write(self):
        """Test that counter damage against an already-dead source is a silent no-write."""
        passive = self._register_synth_skill(
            _make_synth_skill("synth_thorn_dead_src", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        rule_counter = Rule(
            id="synth_dead_src_counter_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"counter_damage": 1.0},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_counter],
        ):
            self.actor.traits.hp.current = 0
            dispatch_outcome_reaction(self.target, "physical_hit", source=self.actor)
            # Actor stays at 0, never revives
            self.assertEqual(int(self.actor.traits.hp.current), 0)

    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_killing_blow_against_holder_still_triggers_counter(self):
        """Test that a strike that kills the reactor still triggers the counter damage against the attacker."""
        passive = self._register_synth_skill(
            _make_synth_skill("synth_thorn_kill_blow", kind=SkillKind.PASSIVE)
        )
        self._grant_skill(self.target, passive.key, SkillKind.PASSIVE)

        rule_counter = Rule(
            id="synth_kill_blow_counter_rule",
            when={"event": "physical_hit", "skill_qualified": passive.key},
            then={"counter_damage": 1.0},
        )

        with patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_counter],
        ):
            physical_skill = self._register_synth_skill(
                _make_synth_skill("synth_kill_strike", ["damage:earth:physical"])
            )
            self._grant_skill(self.actor, physical_skill.key, SkillKind.ACTIVE)

            # Target has only 5 HP; strike deals ~40, killing target
            self.target.traits.hp.current = 5
            actor_hp_before = self.actor.traits.hp.current

            bf = self._make_battlefield(self.actor, self.target)
            req = ActionRequest(self.actor, physical_skill.key, [self.target], BattlefieldActionContext(bf))
            with patch("world.rules.combat.roll_d100", return_value=100):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            self.assertEqual(int(self.target.traits.hp.current), 0)
            # Attacker still takes the counter damage (40)
            self.assertEqual(self.actor.traits.hp.current, actor_hp_before - 40)
