"""Synthetic identity qualification, containment and presentation contracts."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.skills.eligibility import (
    actor_kind_for, record_identity_eligible, skill_identity_eligible,
    validate_skill_eligibility,
)
from world.skills.registry import SkillEligibility, SkillKind, SkillPrerequisite, TargetSpec
from world.tests.synthetic_data import (
    make_monster_species, make_monster_variant, make_race, make_subrace,
    make_skill, synthetic_registries,
)
from ._combat_session_helpers import live_skill_registry, open_synthetic_scope, synth_innate_overlay

RACE = make_race("t_identity_race", can_use_divine_arts=True)
OTHER = make_race("t_identity_other")
BRANCH = make_subrace("t_identity_branch", race_key=RACE.key)
WRONG = make_subrace("t_identity_wrong", race_key=OTHER.key)
MONSTER_ONLY = SkillEligibility(allowed_actor_kinds=("monster",))
RACIAL = SkillEligibility(allowed_races=(RACE.key,), allowed_subraces=(BRANCH.key,))
ROOT = make_skill("t_identity_root", eligibility=MONSTER_ONLY, target_spec=TargetSpec.SELF,
                  effects=["self_heal"], cost={"mp": 3}, usable_out_of_combat=True)
CHILD = make_skill("t_identity_child", eligibility=MONSTER_ONLY,
                   prerequisites=(SkillPrerequisite(ROOT.key, 1),))
RACIAL_ROOT = make_skill("t_identity_racial_root", eligibility=RACIAL)
RACIAL_CHILD = make_skill("t_identity_racial_child", eligibility=RACIAL,
                          prerequisites=(SkillPrerequisite(RACIAL_ROOT.key, 1),))
PASSIVE = make_skill("t_identity_passive", eligibility=MONSTER_ONLY,
                     kind=SkillKind.PASSIVE, effects=["stat_multiply:agility:2"])
ROWS = {row.key: row for row in (ROOT, CHILD, RACIAL_ROOT, RACIAL_CHILD, PASSIVE)}
EXTRA = {"races": {row.key: row for row in (RACE, OTHER)},
         "subraces": {row.key: row for row in (BRANCH, WRONG)},
         "skills": {**synth_innate_overlay()["skills"], **ROWS}}


class IdentityRecordTests(TestCase):
    def setUp(self):
        scope = synthetic_registries(
            "races", "subraces", "monster_species", "monster_variants", extra=EXTRA
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)

    # Future requirement: skill-identity-eligibility::identity-restrictions-are-immutable-closed-declarative-data
    def test_alternatives_and_capabilities_are_and_composed(self):
        rule = SkillEligibility(allowed_races=(RACE.key, OTHER.key),
                                required_capabilities=("can_use_divine_arts",))
        validate_skill_eligibility(rule)
        for kind in ("player", "npc"):
            self.assertTrue(record_identity_eligible(rule, kind, race=RACE.key))
            self.assertFalse(record_identity_eligible(rule, kind, race=OTHER.key))
        self.assertFalse(record_identity_eligible(rule, "monster", race=RACE.key))
        self.assertTrue(record_identity_eligible(SkillEligibility(), None))
        with self.assertRaises(FrozenInstanceError):
            rule.allowed_races = (OTHER.key,)
        with self.assertRaises(ValueError):
            SkillEligibility(allowed_races=[RACE.key])

    # Future requirement: skill-identity-eligibility::stored-identity-determines-actor-qualification
    def test_missing_and_wrong_parent_character_identity(self):
        for kind in ("player", "npc"):
            race_only = SkillEligibility(allowed_races=(RACE.key,))
            for race, branch, expected in (
                (RACE.key, None, True), (RACE.key, BRANCH.key, True),
                (None, BRANCH.key, False), (OTHER.key, BRANCH.key, False),
                (RACE.key, WRONG.key, False),
            ):
                with self.subTest(kind=kind, race_only=True, race=race, branch=branch):
                    self.assertEqual(
                        record_identity_eligible(
                            race_only, kind, race=race, subrace=branch
                        ),
                        expected,
                    )
            for race, branch, expected in (
                (RACE.key, BRANCH.key, True), (None, BRANCH.key, False),
                (RACE.key, None, False), (OTHER.key, BRANCH.key, False),
                (RACE.key, WRONG.key, False), (RACE.key, "t_unknown", False),
            ):
                with self.subTest(kind=kind, race=race, branch=branch):
                    self.assertEqual(record_identity_eligible(
                        RACIAL, kind, race=race, subrace=branch), expected)
        self.assertFalse(record_identity_eligible(RACIAL, "monster", race=RACE.key, subrace=BRANCH.key))

    def test_species_requires_valid_variant_membership(self):
        species = make_monster_species(
            "t_identity_species", default_variant_key="t_identity_variant"
        )
        variant = make_monster_variant(
            species.default_variant_key, species_key=species.key
        )
        other = make_monster_species(
            "t_identity_other_species", default_variant_key="t_identity_other_variant"
        )
        wrong = make_monster_variant(other.default_variant_key, species_key=other.key)
        scope = synthetic_registries(
            "monster_species", "monster_variants",
            extra={
                "monster_species": {row.key: row for row in (species, other)},
                "monster_variants": {row.key: row for row in (variant, wrong)},
            },
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        rule = SkillEligibility(allowed_species=(species.key,))
        validate_skill_eligibility(rule)
        for kind, key, variant_key, expected in (
            ("monster", species.key, variant.key, True),
            ("monster", species.key, wrong.key, False),
            ("monster", other.key, wrong.key, False),
            ("monster", species.key, None, False),
            ("monster", species.key, "t_unknown_variant", False),
            ("monster", None, variant.key, False),
            ("monster", "t_unknown", variant.key, False),
            ("npc", species.key, variant.key, False),
        ):
            self.assertEqual(record_identity_eligible(rule, kind, species_key=key, variant_key=variant_key), expected)
        self.assertTrue(record_identity_eligible(MONSTER_ONLY, "monster"))
        self.assertFalse(record_identity_eligible(MONSTER_ONLY, "player"))

    def test_invalid_authoring_fails_closed(self):
        for name in ("allowed_actor_kinds", "allowed_races", "allowed_subraces", "allowed_species"):
            with self.assertRaises(ValueError):
                SkillEligibility(**{name: ()})
            with self.assertRaises(ValueError):
                validate_skill_eligibility(SkillEligibility(**{name: ("t_unknown",)}))
        for rule in (
            SkillEligibility(required_capabilities=("t_unknown",)),
            SkillEligibility(allowed_actor_kinds=("monster",), allowed_races=(RACE.key,)),
            SkillEligibility(allowed_races=(OTHER.key,), required_capabilities=("can_use_divine_arts",)),
            SkillEligibility(allowed_races=(RACE.key,), allowed_subraces=(WRONG.key,)),
        ):
            with self.assertRaises(ValueError):
                validate_skill_eligibility(rule)


class IdentityRuntimeTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "races", "subraces", "skills", "sexual_acts", extra=EXTRA)
        self.room = create_object(Room, key="identity room")
        self.player = create_object(PlayerCharacter, key="identity player", location=self.room)
        self.player.race = RACE.key
        self.player.subrace = BRANCH.key
        self.player.apply_race_baseline()
        self.player.db.skills = {"active": [ROOT.key], "passive": [PASSIVE.key]}
        self.npc = create_object(NPC, key="identity npc")
        self.monster = create_object(Monster, key="identity monster")

    def test_typeclass_identity_cannot_be_spoofed_by_attributes(self):
        self.player.db.species_key = "t_fake_species"
        self.monster.db.race = RACE.key
        self.assertEqual(actor_kind_for(self.player), "player")
        self.assertEqual(actor_kind_for(self.npc), "npc")
        self.assertEqual(actor_kind_for(self.monster), "monster")
        self.assertFalse(skill_identity_eligible(self.player, ROOT))
        self.assertTrue(skill_identity_eligible(self.monster, ROOT))
        self.assertFalse(skill_identity_eligible(self.monster, RACIAL_ROOT))

    def test_missing_identity_reads_do_not_materialize_attributes(self):
        before = {(row.key, row.category): row.value for row in self.npc.attributes.all()}
        self.assertFalse(skill_identity_eligible(self.npc, RACIAL_ROOT))
        self.assertEqual(
            {(row.key, row.category): row.value for row in self.npc.attributes.all()}, before,
        )

    def test_rule_table_owned_and_conferred_adjustments_are_inert(self):
        from world.rules.combat_modifiers import matched_combat_modifiers, _conferred_rule_scale
        from world.rules.rulebook.schema import Rule, evaluate_condition
        from world.skills.handler import ConferredSkillGrant
        rule_skill = replace(PASSIVE, effects=["passive_buff:t_identity_rule"])
        self.player.db.skill_grants = [ConferredSkillGrant("t_source", PASSIVE.key, 0.5)]
        rule = Rule("t_identity_rule", {"skill_owned": PASSIVE.key}, {"defense": "+50%"})
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {PASSIVE.key: rule_skill}):
            with patch("world.rules.combat_modifiers._RULES", [rule]):
                self.assertFalse(evaluate_condition(rule.when, {"entity": self.player}))
                self.assertEqual(_conferred_rule_scale(self.player, PASSIVE.key), 0.0)
                self.assertEqual(matched_combat_modifiers(self.player, context={
                    "entity": self.player, "dual_wielding": False, "worn_item_keys": frozenset(),
                }), ())

    def test_unrestricted_passive_reuse_for_player_and_monster(self):
        from world.skills.handler import SkillHandler
        from world.rules.progression import can_use_skill

        unrestricted = replace(PASSIVE, eligibility=SkillEligibility())
        shared_active = replace(ROOT, eligibility=SkillEligibility())
        with patch.dict(live_skill_registry(), {
            PASSIVE.key: unrestricted, ROOT.key: shared_active,
        }):
            for owner in (self.player, self.monster):
                owner.attributes.add("traits", {"agility": {"value": 11}}, category="traits")
                owner.db.skills = {"active": [], "passive": []}
                self.assertFalse(can_use_skill(owner, shared_active))
                owner.db.skills = {"active": [ROOT.key], "passive": [PASSIVE.key]}
                self.assertTrue(can_use_skill(owner, shared_active))
                before = {(row.key, row.category): row.value for row in owner.attributes.all()}
                self.assertEqual(SkillHandler(owner).stored_effective_value("agility"), 22)
                self.assertEqual(
                    {(row.key, row.category): row.value for row in owner.attributes.all()}, before,
                )

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    # Future requirement: skill-lineage::identity-rejection-is-distinct-from-an-unmet-prerequisite
    # Future requirement: skill-identity-eligibility::qualification-does-not-grant-ownership-or-replace-action-validation
    def test_ineligible_owned_root_rejects_before_rolls_or_writes(self):
        from world.rules.action import ActionRequest, ActionResolver, RejectReason
        from world.rules.action_preview import preview_skill, revalidate_submission
        from world.rules.progression import can_use_skill
        from world.rules.targeting import RoomActionContext
        context = RoomActionContext(self.room)
        before = {row.key: row.value for row in self.player.attributes.all()}
        self.assertFalse(can_use_skill(self.player, ROOT))
        with patch("world.rules.action.gates.roll_d100") as roll:
            preview = preview_skill(self.player, ROOT.key, context, [self.player])
            self.assertIs(preview.reason, RejectReason.IDENTITY_INELIGIBLE)
            submission = revalidate_submission(self.player, ROOT.key, context, [])
            self.assertIs(submission.reason, RejectReason.IDENTITY_INELIGIBLE)
            for operation in (ActionResolver.preflight, ActionResolver.resolve):
                result = operation(ActionRequest(self.player, ROOT.key, [self.player], context))
                self.assertIs(result.reason, RejectReason.IDENTITY_INELIGIBLE)
            roll.assert_not_called()
        self.assertEqual({row.key: row.value for row in self.player.attributes.all()}, before)
        self.monster.db.skills = {"active": [], "passive": []}
        self.assertFalse(can_use_skill(self.monster, ROOT))
        self.monster.db.skills = {"active": [ROOT.key], "passive": []}
        self.assertTrue(can_use_skill(self.monster, ROOT))

    @covers_requirement("skill-handler::effective-value-is-the-sole-resolution-time-multiplier-application-point-and-never-writes-to-entity-traits")
    # Future requirement: skill-handler::identity-ineligible-owned-and-conferred-passive-effects-are-inert
    def test_owned_and_conferred_passives_and_grant_writes_are_contained(self):
        from world.rules.skill_effects import record_conferred_grant
        from world.rules.cross_lineage_unlock import grant_owned_skill
        from world.rules.action import RejectedAction, RejectReason
        from world.skills.handler import SkillHandler, ConferredSkillGrant
        base = self.player.traits.agility.value
        self.player.db.skill_grants = [ConferredSkillGrant("t_source", PASSIVE.key, 0.5)]
        before = {row.key: row.value for row in self.player.attributes.all()}
        self.assertEqual(SkillHandler(self.player).stored_effective_value("agility"), base)
        with self.assertRaises(RejectedAction) as caught:
            record_conferred_grant(self.player, "t_other", PASSIVE.key, 0.5)
        self.assertIs(caught.exception.reason, RejectReason.IDENTITY_INELIGIBLE)
        with self.assertRaises(ValueError):
            grant_owned_skill(self.player, PASSIVE.key, ROWS)
        self.assertEqual({row.key: row.value for row in self.player.attributes.all()}, before)

    def test_status_breakdown_matches_control_and_creates_no_handlers(self):
        from world.rules.status_query.breakdown import build_stat_breakdown
        from world.skills.handler import ConferredSkillGrant
        control = build_stat_breakdown(self.player)
        self.player.db.skill_grants = [ConferredSkillGrant("t_source", PASSIVE.key, 0.5)]
        before = {(row.key, row.category): row.value for row in self.player.attributes.all()}
        self.assertEqual(build_stat_breakdown(self.player), control)
        self.assertEqual(
            {(row.key, row.category): row.value for row in self.player.attributes.all()}, before,
        )

    @covers_requirement("skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free")
    # Future requirement: skill-identity-eligibility::player-catalogs-and-lineage-use-identity-filtering
    # Future requirement: skill-lineage-panel::lineage-filtering-preserves-racial-discovery-without-exposing-monster-chains
    def test_catalog_and_lineage_filter_without_ownership_or_resource_gates(self):
        from world.rules.lineage_query import build_lineage_view
        from world.rules.status_query.readers import _split_active_passive_keys
        from world.skills.registry import validate_prerequisite_graph
        validate_prerequisite_graph(live_skill_registry())
        self.player.db.skills = {"active": [ROOT.key, RACIAL_ROOT.key], "passive": [PASSIVE.key]}
        active, passive = _split_active_passive_keys(self.player)
        self.assertNotIn(ROOT.key, active)
        self.assertNotIn(PASSIVE.key, passive)
        self.assertIn(RACIAL_ROOT.key, active)
        view = build_lineage_view(self.player)
        keys = {node.skill_key for chain in view.chains for node in chain.nodes}
        self.assertNotIn(ROOT.key, keys)
        self.assertNotIn(CHILD.key, keys)
        self.assertIn(RACIAL_CHILD.key, keys)
        child = next(node for chain in view.chains for node in chain.nodes if node.skill_key == RACIAL_CHILD.key)
        self.assertFalse(child.owned)
        self.assertFalse(child.usable)
        self.assertEqual(build_lineage_view(self.player), view)

    # Future requirement: import-validation::imports-validate-complete-closed-kits-against-authored-identity
    def test_authored_import_and_preset_closure_reject_without_construction(self):
        from world.imports.validate import _check_skills
        from world.rules.progression import normalize_lineage_record
        from world.lore.player_presets.validation import _validate_preset_skill_kits
        child = replace(RACIAL_CHILD, prerequisites=(SkillPrerequisite(ROOT.key, 1),))
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {child.key: child}):
            record = normalize_lineage_record({"race": RACE.key, "subrace": BRANCH.key,
                                              "skills": [child.key], "passives": []})
            with patch("evennia.utils.create.create_object") as constructor:
                issues = _check_skills(record, "player")
                self.assertTrue(any(issue.field == "skills" and ROOT.key in issue.message for issue in issues))
                preset = SimpleNamespace(key="t_identity_preset", race=RACE.key, subrace=BRANCH.key,
                                         active_skills=(child.key,), passive_skills=())
                with self.assertRaisesRegex(ValueError, ROOT.key):
                    _validate_preset_skill_kits({preset.key: preset})
                constructor.assert_not_called()

    def test_companion_preset_kit_uses_npc_identity_before_construction(self):
        from world.lore.player_presets import StartingCompanion
        from world.lore.player_presets.validation import (
            _validate_preset_skill_kits,
            _validate_preset_starting_companions,
        )

        player_only = replace(
            RACIAL_ROOT, eligibility=SkillEligibility(allowed_actor_kinds=("player",))
        )
        companion = SimpleNamespace(
            key="t_identity_companion", race=RACE.key, subrace=BRANCH.key,
            active_skills=(player_only.key,), passive_skills=(), starting_companions=(),
        )
        owner = SimpleNamespace(
            key="t_identity_owner",
            starting_companions=(
                StartingCompanion(preset_key=companion.key, affinity=1, relationship="ally"),
            ),
        )
        with patch.dict(live_skill_registry(), {player_only.key: player_only}):
            _validate_preset_skill_kits({companion.key: companion})
            with patch("evennia.utils.create.create_object") as constructor:
                with self.assertRaisesRegex(ValueError, player_only.key):
                    _validate_preset_starting_companions(
                        {owner.key: owner, companion.key: companion}
                    )
                constructor.assert_not_called()
