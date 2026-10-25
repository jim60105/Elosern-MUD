"""Behavior test: authored-dialogue physical condition evaluation and hints.

Covers the ``authored-dialogue-physical-conditions`` slice against the shared
synthetic kit: every physical leaf reads the acting body, companion presence
requires owner membership and local presence, world time wraps midnight,
skills use canonical ownership plus the canonical proficiency reader, exposure
uses the canonical effective reader, hints render canonical labels, and
selection delivers a qualified variant, a hidden absence or a zero-effect
refusal without ever consuming an item or materializing a handler.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from world.lore.dialogue.conditions import (
    All,
    Any as AnyCondition,
    Carries,
    CompanionPresent,
    Exposure,
    RaceIs,
    SkillOwned,
    SocialIdentityIs,
    TimePeriod,
)
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic, SceneVariant
from world.lore.scenes import scene_canonical_bytes, Scene, Speech
from world.lore.sexual_vocab import EXPOSURE_LEVELS
from world.rules.dialogue import (
    DialogueBudgetExceededError,
    TopicLockedError,
    TopicNotFoundError,
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_conditions import (
    DialogueConditionError,
    condition_hint,
    evaluate_condition,
    select_scene_variant,
)
from world.rules.dialogue_references import static_dialogue_references
from world.rules.party import join_party, leave_party
from world.rules.progression._constants import SKILL_PROFICIENCY_XP_PER_LEVEL
from world.rules.social_identity import set_social_identities
from world.skills.equipment import EquipmentSlot
from world.quests.catalog import register_catalog
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    synthetic_registries,
)

_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE_KEY = next(key for key in SYNTH_RACES if key != _RACE_KEY)
_SKILL_KEY = next(iter(SYNTH_SKILLS))
_OTHER_SKILL_KEY = next(key for key in SYNTH_SKILLS if key != _SKILL_KEY)
_ITEM_KEY = next(iter(SYNTH_ITEMS))
_WORN_KEY, _WORN_ITEM = next(
    (key, row) for key, row in SYNTH_ITEMS.items() if row.equipment_slot is not None
)

_TABLE_KEY = "t_conditioned_outfitter"
_RACE_TOPIC = f"{_TABLE_KEY}.race"
_FALLBACK_TOPIC = f"{_TABLE_KEY}.exposure"
_HIDDEN_TOPIC = f"{_TABLE_KEY}.hidden"
_LOCKED_TOPIC = f"{_TABLE_KEY}.locked"
_CARRIES_TOPIC = f"{_TABLE_KEY}.carried"
_PREDECESSOR_TOPIC = f"{_TABLE_KEY}.chained"
_BUDGET_TOPIC = f"{_TABLE_KEY}.budgeted"
_ANY_TOPIC = f"{_TABLE_KEY}.either"

_EXPOSURE_BOUND = 2
_EXPOSURE_BASELINE = EXPOSURE_LEVELS[_EXPOSURE_BOUND - 1]
_EXPOSURE_BASELINE_ORDINAL = _EXPOSURE_BOUND - 1
_WORN_MODIFIER_KEY = _WORN_ITEM.modifier_key


def _scene(scene_id: str, host_text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成條件問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _authored_dialogue() -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成條件店主抬眼：「有事就問。」",
        topics=(
            AuthoredTopic(
                topic_id=_RACE_TOPIC,
                keyword="合成種族",
                label="合成種族",
                fallback=_scene("t_conditioned_race_fallback", "合成通用答覆。"),
                variants=(
                    SceneVariant(
                        variant_id="race_match",
                        priority=10,
                        when=RaceIs(race_key=_RACE_KEY),
                        scene=_scene("t_conditioned_race_variant", "合成種族答覆。"),
                    ),
                ),
            ),
            AuthoredTopic(
                topic_id=_FALLBACK_TOPIC,
                keyword="合成衣著",
                label="合成衣著",
                fallback=_scene("t_conditioned_exposure_fallback", "合成衣著普通答覆。"),
                variants=(
                    SceneVariant(
                        variant_id="exposure_match",
                        priority=10,
                        when=Exposure(minimum=_EXPOSURE_BOUND),
                        scene=_scene("t_conditioned_exposure_variant", "合成衣著答覆。"),
                    ),
                ),
            ),
            AuthoredTopic(
                topic_id=_HIDDEN_TOPIC,
                keyword="合成秘密",
                label="合成秘密",
                fallback=_scene("t_conditioned_hidden_fallback", "合成秘密答覆。"),
                requires=RaceIs(race_key=_OTHER_RACE_KEY),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_LOCKED_TOPIC,
                keyword="合成保留",
                label="合成保留",
                fallback=_scene("t_conditioned_locked_fallback", "合成保留答覆。"),
                requires=RaceIs(race_key=_OTHER_RACE_KEY),
                unavailable="locked",
                refusal=_scene("t_conditioned_locked_refusal", "合成婉拒答覆。"),
            ),
            AuthoredTopic(
                topic_id=_CARRIES_TOPIC,
                keyword="合成持物",
                label="合成持物",
                fallback=_scene("t_conditioned_carries_fallback", "合成持物答覆。"),
                requires=Carries(item_key=_ITEM_KEY, minimum=2),
            ),
            AuthoredTopic(
                topic_id=_PREDECESSOR_TOPIC,
                keyword="合成接續",
                label="合成接續",
                fallback=_scene("t_conditioned_chain_fallback", "合成接續答覆。"),
                predecessors=(_RACE_TOPIC,),
            ),
            AuthoredTopic(
                topic_id=_BUDGET_TOPIC,
                keyword="合成預算",
                label="合成預算",
                fallback=_scene("t_conditioned_budget_fallback", "合成簡答。"),
                variants=(
                    SceneVariant(
                        variant_id="budget_variant",
                        priority=10,
                        when=RaceIs(race_key=_RACE_KEY),
                        scene=Scene(
                            scene_id="t_conditioned_budget_variant",
                            revision="r1",
                            lines=(
                                Speech(speaker="actor", text="合成預算問句。"),
                                Speech(speaker="host", text="合成長篇答覆。" * 120),
                            ),
                        ),
                    ),
                ),
            ),
            AuthoredTopic(
                topic_id=_ANY_TOPIC,
                keyword="合成其一",
                label="合成其一",
                fallback=_scene("t_conditioned_any_fallback", "合成其一答覆。"),
                requires=AnyCondition(
                    (Carries(item_key=_ITEM_KEY), RaceIs(race_key=_RACE_KEY))
                ),
                unavailable="hidden",
            ),
        ),
    )


def _empty_equipment() -> dict:
    return {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


def _exposure_rule(bias: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        exposure_bias=bias,
        adjustments={},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
    )


class DialoguePhysicalConditionTests(EvenniaTest):
    """Evaluator, hint, variant and selection behavior on synthetic data."""

    def setUp(self) -> None:
        super().setUp()
        # The affinity writer resolves its cap breaks through the registered
        # quest definitions, exactly as the runtime acceptance does.
        register_catalog()
        self.scope = synthetic_registries(
            "races",
            "items",
            "skills",
            "dialogue",
            extra={"dialogue": {_TABLE_KEY: _authored_dialogue()}},
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

        self.room1 = create_object(Room, key="合成條件廳")
        self.char1.location = self.room1
        self.char1.race = _RACE_KEY
        self.char1.apply_race_baseline()
        self.char1.db.inventory = []

        self.host = create_object(NPC, key="合成條件店主", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )

    def tearDown(self) -> None:
        clear_dialogue_session(self.char1)
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _context(self, *, actor=None, owner=None, host=None) -> SimpleNamespace:
        return SimpleNamespace(
            actor=self.char1 if actor is None else actor,
            owner=self.char1 if owner is None else owner,
            host=self.host if host is None else host,
            source_identity=None,
        )

    def _identity_key(self) -> str:
        return next(iter(static_dialogue_references().keys_for("social_identity")))

    def _companion(self, provenance: dict, *, location=None, owner=None) -> LLMNPC:
        companion = create_object(
            LLMNPC, key="合成同行者", location=location or self.room1
        )
        companion.race = _RACE_KEY
        companion.apply_race_baseline()
        companion.db.inventory = []
        companion.db.npc_persona_meta = {"persona_version": 1, "provenance": provenance}
        join_party(companion, owner or self.char1)
        return companion

    def _select(self, topic_id: str, *, selection_id: str = "sel-1", expected=None):
        return select_authored_topic(
            self.char1,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=expected,
        )

    # -- identity, inventory and companions -------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_race_reads_the_acting_body_only(self):
        owner = self.char2
        owner.race = _OTHER_RACE_KEY
        context = self._context(owner=owner)
        self.assertTrue(evaluate_condition(RaceIs(race_key=_RACE_KEY), context))
        self.assertFalse(evaluate_condition(RaceIs(race_key=_OTHER_RACE_KEY), context))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_unregistered_actor_race_fails_closed_with_one_event(self):
        self.char1.race = "t_unregistered_race"
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(RaceIs(race_key=_RACE_KEY), self._context())
            )
        self.assertEqual(log_warn.call_count, 1)
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "actor_race_unresolved"
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_social_identity_reads_actor_membership_and_rejects_corrupt_storage(self):
        identity_key = self._identity_key()
        set_social_identities(self.char1, [identity_key])
        context = self._context(owner=self.char2)
        self.assertTrue(evaluate_condition(SocialIdentityIs(identity_key), context))

        self.char1.attributes.add("social_identities", ["t_not_a_known_identity"])
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(SocialIdentityIs(identity_key), self._context())
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "actor_social_identities_malformed",
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_carries_counts_the_actors_own_repeated_items_without_consuming(self):
        self.char1.db.inventory = [_ITEM_KEY, _ITEM_KEY]
        self.char2.db.inventory = [_ITEM_KEY, _ITEM_KEY, _ITEM_KEY]
        self.assertTrue(
            evaluate_condition(Carries(item_key=_ITEM_KEY, minimum=2), self._context())
        )
        self.assertFalse(
            evaluate_condition(
                Carries(item_key=_ITEM_KEY, minimum=3),
                self._context(owner=self.char2),
            )
        )
        self.assertEqual(self.char1.db.inventory, [_ITEM_KEY, _ITEM_KEY])

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_malformed_inventory_fails_closed(self):
        self.char1.db.inventory = {_ITEM_KEY: 2}
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    Carries(item_key=_ITEM_KEY, minimum=1), self._context()
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "actor_inventory_malformed"
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_preset_companion_requires_owner_membership_and_local_presence(self):
        preset_key = next(iter(static_dialogue_references().keys_for("preset")))
        companion = self._companion(
            {
                "kind": "companion",
                "profile": preset_key,
                "owner": self.char1.pk,
            }
        )
        condition = CompanionPresent(source_kind="preset", source_key=preset_key)
        self.assertTrue(evaluate_condition(condition, self._context()))

        far_room = create_object(Room, key="合成遠處")
        companion.location = far_room
        self.assertFalse(evaluate_condition(condition, self._context()))

        companion.location = self.room1
        leave_party(companion, self.char1, reason="test")
        self.assertFalse(evaluate_condition(condition, self._context()))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_companion_of_another_owner_grants_nothing(self):
        other_owner = create_object(NPC, key="合成另一位主人", location=self.room1)
        preset_key = next(iter(static_dialogue_references().keys_for("preset")))
        self._companion(
            {
                "kind": "companion",
                "profile": preset_key,
                "owner": other_owner.pk,
            },
            owner=other_owner,
        )
        condition = CompanionPresent(source_kind="preset", source_key=preset_key)
        self.assertFalse(evaluate_condition(condition, self._context()))

    def test_profile_companion_matches_registry_provenance(self):
        profile_key = next(iter(static_dialogue_references().keys_for("profile")))
        companion = self._companion({"kind": "profile", "profile": profile_key})
        condition = CompanionPresent(source_kind="profile", source_key=profile_key)
        self.assertTrue(evaluate_condition(condition, self._context()))
        self.assertFalse(
            evaluate_condition(
                CompanionPresent(source_kind="profile", source_key=_OTHER_RACE_KEY),
                self._context(),
            )
        )
        leave_party(companion, self.char1, reason="test")

    def test_malformed_companion_provenance_fails_closed(self):
        preset_key = next(iter(static_dialogue_references().keys_for("preset")))
        companion = create_object(LLMNPC, key="合成同行者", location=self.room1)
        companion.race = _RACE_KEY
        companion.apply_race_baseline()
        companion.db.inventory = []
        companion.db.npc_persona_meta = {"persona_version": 1, "provenance": "corrupt"}
        join_party(companion, self.char1)
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    CompanionPresent(source_kind="preset", source_key=preset_key),
                    self._context(),
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "companion_provenance_malformed",
        )
        leave_party(companion, self.char1, reason="test")

    @covers_requirement(
        "authored-dialogue-conditions::generated-physical-references-retain-canonical-and-package-scope"
    )
    def test_package_role_companion_resolves_only_the_permitted_binding(self):
        companion = self._companion(
            {"kind": "companion", "profile": "t_any", "owner": self.char1.pk}
        )
        condition = CompanionPresent(source_kind="package_role", source_key="t_package_role")
        package = SimpleNamespace(status="published")
        binding = SimpleNamespace(npc_id=companion.pk, availability="bound")
        context = SimpleNamespace(
            actor=self.char1,
            owner=self.char1,
            host=self.host,
            source_identity=SimpleNamespace(package_id="t_pkg"),
        )
        store = {
            ("t_pkg", "t_package_role"): binding,
            ("t_foreign_pkg", "t_package_role"): binding,
        }
        with patch(
            "world.quests.scene_store.read_package", return_value=package
        ), patch(
            "world.quests.scene_store.get_role_binding",
            side_effect=lambda package_id, role_id: store.get((package_id, role_id)),
        ):
            self.assertTrue(evaluate_condition(condition, context))
            # The same local role id in a foreign package is not permitted.
            foreign = SimpleNamespace(
                actor=self.char1,
                owner=self.char1,
                host=self.host,
                source_identity=SimpleNamespace(package_id="t_other_pkg"),
            )
            with patch("world.rules.dialogue_conditions.log_warn"):
                self.assertFalse(evaluate_condition(condition, foreign))

        unbound = SimpleNamespace(npc_id=companion.pk, availability="detached")
        with patch(
            "world.quests.scene_store.read_package", return_value=package
        ), patch(
            "world.quests.scene_store.get_role_binding", return_value=unbound
        ), patch("world.rules.dialogue_conditions.log_warn"):
            self.assertFalse(evaluate_condition(condition, context))
        leave_party(companion, self.char1, reason="test")

    @covers_requirement(
        "authored-dialogue-conditions::generated-physical-references-retain-canonical-and-package-scope"
    )
    def test_package_role_requires_published_bound_present_and_owned(self):
        companion = self._companion(
            {"kind": "companion", "profile": "t_any", "owner": self.char1.pk}
        )
        condition = CompanionPresent(source_kind="package_role", source_key="t_package_role")
        context = SimpleNamespace(
            actor=self.char1,
            owner=self.char1,
            host=self.host,
            source_identity=SimpleNamespace(package_id="t_pkg"),
        )
        binding = SimpleNamespace(npc_id=companion.pk, availability="bound")
        published = SimpleNamespace(status="published")
        cancelled = SimpleNamespace(status="cancelled")

        cases = (
            ("cancelled package", cancelled, binding),
            (
                "deleted bound npc",
                published,
                SimpleNamespace(npc_id=999999, availability="bound"),
            ),
            ("remote companion", published, binding),
        )
        for label, package, role_binding in cases:
            with self.subTest(case=label), patch(
                "world.quests.scene_store.read_package", return_value=package
            ), patch(
                "world.quests.scene_store.get_role_binding", return_value=role_binding
            ), patch("world.rules.dialogue_conditions.log_warn"):
                if label == "remote companion":
                    companion.location = create_object(Room, key="合成遠處")
                self.assertFalse(evaluate_condition(condition, context))
                companion.location = self.room1

        # A companion bound to another owner grants nothing.
        other_owner = create_object(NPC, key="合成另一位主人", location=self.room1)
        leave_party(companion, self.char1, reason="test")
        join_party(companion, other_owner)
        with patch(
            "world.quests.scene_store.read_package", return_value=published
        ), patch(
            "world.quests.scene_store.get_role_binding", return_value=binding
        ):
            self.assertFalse(evaluate_condition(condition, context))
        leave_party(companion, other_owner, reason="test")

    @covers_requirement(
        "authored-dialogue-conditions::generated-physical-references-retain-canonical-and-package-scope"
    )
    def test_static_context_has_no_permitted_package_role(self):
        condition = CompanionPresent(source_kind="package_role", source_key="t_package_role")
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(evaluate_condition(condition, self._context()))
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "companion_package_unresolved",
        )

    # -- time -------------------------------------------------------------

    def _set_day_seconds(self, seconds: int) -> None:
        from world.rules.clock import get_world_clock

        get_world_clock()._persist(seconds)

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_time_period_wraps_midnight_half_open(self):
        from world.rules.clock import CLOCK_YAML

        dayparts = CLOCK_YAML["dayparts"]
        seconds_per_hour = CLOCK_YAML["seconds_per_hour"]
        condition = TimePeriod(start_daypart="dusk", end_daypart="dawn")

        def at(daypart: str) -> bool:
            self._set_day_seconds(dayparts[daypart] * seconds_per_hour)
            return evaluate_condition(condition, self._context())

        self.assertTrue(at("midnight"))
        self.assertFalse(at("dawn"))
        self.assertFalse(at("noon"))
        self.assertTrue(at("dusk"))

    def test_time_period_start_inclusive_and_missing_clock_fails_closed(self):
        from world.rules.clock import CLOCK_YAML

        dayparts = CLOCK_YAML["dayparts"]
        seconds_per_hour = CLOCK_YAML["seconds_per_hour"]
        self._set_day_seconds(dayparts["dawn"] * seconds_per_hour)
        self.assertTrue(
            evaluate_condition(
                TimePeriod(start_daypart="dawn", end_daypart="noon"), self._context()
            )
        )
        with patch("world.rules.clock.read_world_clock", return_value=None), patch(
            "world.rules.dialogue_conditions.log_warn"
        ) as log_warn:
            self.assertFalse(
                evaluate_condition(
                    TimePeriod(start_daypart="dawn", end_daypart="noon"),
                    self._context(),
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "world_clock_unresolved"
        )

    # -- skills and exposure ----------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_skill_owned_uses_exact_ownership_never_conferral(self):
        self.char1.db.skills = {"active": [_SKILL_KEY], "passive": []}
        self.assertTrue(
            evaluate_condition(SkillOwned(skill_key=_SKILL_KEY), self._context())
        )
        self.assertFalse(
            evaluate_condition(SkillOwned(skill_key=_OTHER_SKILL_KEY), self._context())
        )
        # A declared grant is not ownership.
        self.char1.db.skill_grants = [
            {"source_key": "t_source", "skill_key": _OTHER_SKILL_KEY, "fraction": 0.5}
        ]
        self.assertFalse(
            evaluate_condition(SkillOwned(skill_key=_OTHER_SKILL_KEY), self._context())
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_skill_proficiency_threshold_uses_the_canonical_reader(self):
        self.char1.db.skills = {"active": [_SKILL_KEY], "passive": []}
        self.char1.db.skill_proficiency = {_SKILL_KEY: SKILL_PROFICIENCY_XP_PER_LEVEL * 2.0}
        self.assertTrue(
            evaluate_condition(
                SkillOwned(skill_key=_SKILL_KEY, min_proficiency=2), self._context()
            )
        )
        self.assertFalse(
            evaluate_condition(
                SkillOwned(skill_key=_SKILL_KEY, min_proficiency=3), self._context()
            )
        )
        self.assertEqual(
            self.char1.db.skill_proficiency[_SKILL_KEY],
            SKILL_PROFICIENCY_XP_PER_LEVEL * 2.0,
        )

    def test_malformed_skill_records_fail_closed(self):
        self.char1.db.skills = [_SKILL_KEY]
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(SkillOwned(skill_key=_SKILL_KEY), self._context())
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "actor_skills_malformed"
        )

        self.char1.db.skills = {"active": [_SKILL_KEY], "passive": []}
        self.char1.db.skill_proficiency = {_SKILL_KEY: "lots"}
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    SkillOwned(skill_key=_SKILL_KEY, min_proficiency=1),
                    self._context(),
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "actor_proficiency_malformed",
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_exposure_bounds_are_inclusive_ordinals(self):
        self.char1.db.sexual = {"exposure": _EXPOSURE_BASELINE}
        self.char1.db.equipment = _empty_equipment()
        self.assertTrue(
            evaluate_condition(
                Exposure(
                    minimum=_EXPOSURE_BASELINE_ORDINAL,
                    maximum=_EXPOSURE_BASELINE_ORDINAL,
                ),
                self._context(),
            )
        )
        self.assertFalse(
            evaluate_condition(
                Exposure(minimum=_EXPOSURE_BASELINE_ORDINAL + 1), self._context()
            )
        )
        self.assertFalse(
            evaluate_condition(
                Exposure(maximum=_EXPOSURE_BASELINE_ORDINAL - 1), self._context()
            )
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_worn_equipment_changes_exposure_without_materializing_a_handler(self):
        self.char1.db.sexual = {"exposure": _EXPOSURE_BASELINE}
        self.char1.db.equipment = _empty_equipment()
        condition = Exposure(minimum=_EXPOSURE_BOUND)
        self.assertFalse(evaluate_condition(condition, self._context()))

        assert _WORN_ITEM.equipment_slot is EquipmentSlot.WEAPON_MAIN
        item = SimpleNamespace(
            key=_WORN_KEY,
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=_WORN_MODIFIER_KEY,
            display_name_zh="合成磨損護符",
        )
        with patch.dict("world.rules.equipment.ITEM_REGISTRY", {_WORN_KEY: item}), patch.dict(
            "world.rules.equipment_effects.ITEM_REGISTRY", {_WORN_KEY: item}
        ), patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
            {_WORN_MODIFIER_KEY: _exposure_rule()},
        ):
            self.char1.db.equipment = {**_empty_equipment(), "weapon_main": _WORN_KEY}
            self.assertTrue(evaluate_condition(condition, self._context()))
            self.assertNotIn("sexual", self.char1.__dict__)

    def test_malformed_equipment_fails_closed(self):
        self.char1.db.sexual = {"exposure": _EXPOSURE_BASELINE}
        self.char1.db.equipment = "corrupt"
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(Exposure(minimum=_EXPOSURE_BOUND - 1), self._context())
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "actor_equipment_malformed"
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_kit_exposure_accessory_crosses_the_bound_through_the_shipped_rulebook(self):
        """The browser fixture's gear shifts the canonical read with no rule patching."""
        accessory = next(
            key
            for key, row in SYNTH_ITEMS.items()
            if row.equipment_slot is EquipmentSlot.ACCESSORY
        )
        condition = Exposure(minimum=_EXPOSURE_BOUND)
        self.char1.db.sexual = {"exposure": _EXPOSURE_BASELINE}
        self.char1.db.equipment = _empty_equipment()
        self.assertFalse(evaluate_condition(condition, self._context()))

        self.char1.db.equipment = {**_empty_equipment(), "accessories": [accessory]}
        self.assertTrue(evaluate_condition(condition, self._context()))
        self.assertNotIn("sexual", self.char1.__dict__)

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_corrupt_materialized_exposure_never_becomes_valid(self):
        """A present malformed record never falls back to a valid baseline."""
        condition = Exposure(minimum=_EXPOSURE_BOUND - 1)
        self.char1.db.sexual = {"exposure": _EXPOSURE_BASELINE}
        self.char1.db.equipment = _empty_equipment()

        corrupt_records = (
            {
                "value": _EXPOSURE_BASELINE,
                "levels": ["合成甲", "合成乙"],
            },
            {"value": True, "levels": list(EXPOSURE_LEVELS)},
            {
                "value": len(EXPOSURE_LEVELS) + 3,
                "levels": list(EXPOSURE_LEVELS),
            },
        )
        for record in corrupt_records:
            with self.subTest(record=record):
                self.char1.attributes.add(
                    "sexual_traits", {"exposure": record}, category="traits"
                )
                with patch(
                    "world.rules.dialogue_conditions.log_warn"
                ) as log_warn:
                    self.assertFalse(
                        evaluate_condition(condition, self._context())
                    )
                self.assertEqual(log_warn.call_count, 1)
                self.assertEqual(
                    log_warn.call_args.kwargs["context"]["reason"],
                    "actor_exposure_unresolved",
                )
                self.assertNotIn("sexual", self.char1.__dict__)

    # -- combination, hints and variants ---------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_all_any_combine_and_bound_the_tree(self):
        context = self._context()
        self.assertTrue(
            evaluate_condition(
                All((RaceIs(race_key=_RACE_KEY),)), context
            )
        )
        self.assertTrue(
            evaluate_condition(
                AnyCondition(
                    (RaceIs(race_key=_OTHER_RACE_KEY), RaceIs(race_key=_RACE_KEY))
                ),
                context,
            )
        )
        nested = All((All((All((All((RaceIs(race_key=_RACE_KEY),)),)),)),))
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(evaluate_condition(nested, context))
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "condition_depth_exceeded",
        )

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hints_recurse_over_the_same_tree_with_canonical_labels(self):
        references = static_dialogue_references()
        race_label = references.label("race", _RACE_KEY)
        item_label = references.label("item", _ITEM_KEY)
        hint = condition_hint(
            All(
                (
                    RaceIs(race_key=_RACE_KEY),
                    AnyCondition(
                        (Carries(item_key=_ITEM_KEY, minimum=2), Exposure(minimum=1))
                    ),
                )
            ),
            self._context(),
        )
        self.assertTrue(hint.startswith("需要（"))
        self.assertIn(f"需要種族為{race_label}", hint)
        self.assertIn("）且（", hint)
        self.assertIn("）或（", hint)
        self.assertIn(f"需要持有{item_label}×2", hint)
        self.assertIn(EXPOSURE_LEVELS[1], hint)

    def test_integrity_failure_dominates_any_matching_alternative(self):
        """Corrupt state in one branch never lets another branch qualify the tree."""
        self.char1.db.inventory = {_ITEM_KEY: 1}
        condition = AnyCondition(
            (Carries(item_key=_ITEM_KEY), RaceIs(race_key=_RACE_KEY))
        )
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(evaluate_condition(condition, self._context()))
        self.assertEqual(log_warn.call_count, 1)
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "actor_inventory_malformed",
        )

    def test_runtime_group_bounds_fail_closed(self):
        for children in ((), tuple(RaceIs(race_key=_RACE_KEY) for _ in range(17))):
            broken = All.__new__(All)
            object.__setattr__(broken, "children", children)
            with self.subTest(count=len(children)):
                with patch(
                    "world.rules.dialogue_conditions.log_warn"
                ) as log_warn:
                    self.assertFalse(
                        evaluate_condition(broken, self._context())
                    )
                self.assertEqual(
                    log_warn.call_args.kwargs["context"]["reason"],
                    "condition_children_invalid",
                )

    def test_corrupt_world_clock_tick_fails_closed(self):
        class _CorruptClock:
            @property
            def calendar(self):
                raise TypeError("corrupt tick")

        with patch(
            "world.rules.clock.read_world_clock", return_value=_CorruptClock()
        ), patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    TimePeriod(start_daypart="dawn", end_daypart="noon"),
                    self._context(),
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "world_clock_unresolved"
        )

    def test_non_finite_skill_counter_fails_closed(self):
        from world.skills.sexual_acts import gated_counter_keys

        counter_key = next(iter(gated_counter_keys()))
        self.char1.db.skills = {"active": [_SKILL_KEY], "passive": []}
        self.char1.attributes.add(
            "sexual_traits",
            {counter_key: {"current": float("nan")}},
            category="traits",
        )
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(SkillOwned(skill_key=_SKILL_KEY), self._context())
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "actor_skills_malformed"
        )

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hint_for_unknown_catalog_label_raises(self):
        with self.assertRaises(DialogueConditionError):
            condition_hint(RaceIs(race_key="t_unlisted_race"), self._context())

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_variant_selection_takes_the_highest_matching_priority(self):
        low = SceneVariant(
            variant_id="low",
            priority=5,
            when=RaceIs(race_key=_RACE_KEY),
            scene=_scene("t_low", "合成低優先。"),
        )
        high = SceneVariant(
            variant_id="high",
            priority=30,
            when=RaceIs(race_key=_RACE_KEY),
            scene=_scene("t_high", "合成高優先。"),
        )
        skipped = SceneVariant(
            variant_id="skipped",
            priority=40,
            when=RaceIs(race_key=_OTHER_RACE_KEY),
            scene=_scene("t_skipped", "合成未命中。"),
        )
        topic = AuthoredTopic(
            topic_id=f"{_TABLE_KEY}.variant",
            keyword="合成變體",
            label="合成變體",
            fallback=_scene("t_variant_fallback", "合成變體通用。"),
            variants=(low, high, skipped),
        )
        self.assertEqual(select_scene_variant(topic, self._context()).scene_id, "t_high")
        topic_without_match = AuthoredTopic(
            topic_id=f"{_TABLE_KEY}.variant2",
            keyword="合成變體",
            label="合成變體",
            fallback=_scene("t_variant_fallback", "合成變體通用。"),
            variants=(skipped,),
        )
        self.assertEqual(
            select_scene_variant(topic_without_match, self._context()).scene_id,
            "t_variant_fallback",
        )

    # -- selection integration -------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_race_qualified_topic_delivers_the_variant_and_the_fallback(self):
        delivery = self._select(_RACE_TOPIC)
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.scene_id, "t_conditioned_race_variant")

        self.char2.location = self.room1
        self.char2.race = _OTHER_RACE_KEY
        self.char2.apply_race_baseline()
        fallback = select_authored_topic(
            self.char2,
            self.host,
            _RACE_TOPIC,
            selection_id="sel-2",
            expected_context_id=None,
        )
        self.assertEqual(fallback.scene_id, "t_conditioned_race_fallback")

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hidden_topic_behaves_as_unknown_and_writes_no_session(self):
        with self.assertRaises(TopicNotFoundError):
            self._select(_HIDDEN_TOPIC)
        self.assertIsNone(self.char1.db.dialogue_session)

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_corrupt_actor_state_cannot_qualify_an_any_requirement(self):
        self.char1.db.inventory = {_ITEM_KEY: 1}
        with self.assertRaises(TopicNotFoundError):
            self._select(_ANY_TOPIC)
        self.assertIsNone(self.char1.db.dialogue_session)

        # With readable state the same disjunction qualifies through the race
        # branch, proving the rejection above came from the corrupt branch.
        self.char1.db.inventory = []
        delivery = self._select(_ANY_TOPIC, selection_id="sel-any")
        self.assertEqual(delivery.kind, "formal")

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_locked_topic_delivers_its_refusal_with_zero_effects(self):
        affinity_before = self.host.relations.affinity_for(self.char1)
        delivery = self._select(_LOCKED_TOPIC)
        self.assertEqual(delivery.kind, "refusal")
        self.assertEqual(delivery.scene_id, "t_conditioned_locked_refusal")
        self.assertNotIn(
            "t_conditioned_locked_fallback", [line.text for line in delivery.lines]
        )
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)

        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        receipt = session.selection_receipts[-1]
        self.assertEqual(receipt["topic_id"], _LOCKED_TOPIC)

    def test_carried_requirement_never_consumes_the_item(self):
        self.char1.db.inventory = [_ITEM_KEY, _ITEM_KEY]
        delivery = self._select(_CARRIES_TOPIC)
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(self.char1.db.inventory, [_ITEM_KEY, _ITEM_KEY])

        self.char1.db.inventory = [_ITEM_KEY]
        with self.assertRaises(TopicNotFoundError):
            self._select(_CARRIES_TOPIC, selection_id="sel-short", expected=live_dialogue_session(self.char1).context_id)

    def test_predecessor_topic_stays_fail_closed(self):
        with self.assertRaises(TopicLockedError):
            self._select(_PREDECESSOR_TOPIC)
        self.assertIsNone(self.char1.db.dialogue_session)

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_replayed_selection_keeps_the_delivered_variant(self):
        delivery = self._select(_RACE_TOPIC, selection_id="sel-stable")
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        # The acting body no longer qualifies for the variant.
        self.char1.race = _OTHER_RACE_KEY
        self.char1.apply_race_baseline()
        replay = select_authored_topic(
            self.char1,
            self.host,
            _RACE_TOPIC,
            selection_id="sel-stable",
            expected_context_id=session.context_id,
        )
        self.assertEqual(replay.delivery_id, delivery.delivery_id)
        self.assertEqual(replay.scene_id, "t_conditioned_race_variant")

    def test_budget_checks_measure_the_selected_variant(self):
        topic = next(
            topic
            for topic in _authored_dialogue().topics
            if topic.topic_id == _BUDGET_TOPIC
        )
        fallback_bytes = scene_canonical_bytes(topic.fallback)
        variant_bytes = scene_canonical_bytes(topic.variants[0].scene)
        self.assertGreater(variant_bytes, fallback_bytes)

        with patch("world.rules.dialogue.DIALOGUE_SCENE_MAX_BYTES", fallback_bytes):
            # The matching actor would receive the oversized variant: the
            # selection is rejected before any effect or session write.
            with self.assertRaises(DialogueBudgetExceededError):
                self._select(_BUDGET_TOPIC)
            self.assertIsNone(self.char1.db.dialogue_session)

            # The same budget admits the (smaller) fallback for an actor that
            # cannot match the variant, proving the check measures the scene
            # actually selected rather than the declaration's fallback.
            self.char2.location = self.room1
            self.char2.race = _OTHER_RACE_KEY
            self.char2.apply_race_baseline()
            delivery = select_authored_topic(
                self.char2,
                self.host,
                _BUDGET_TOPIC,
                selection_id="sel-budget-fallback",
                expected_context_id=None,
            )
        self.assertEqual(delivery.scene_id, "t_conditioned_budget_fallback")
