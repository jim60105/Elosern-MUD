"""Slice of ``test_scene_builder``: SceneBuilderCharacterizationTests.
"""
from contextlib import ExitStack
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest
from django.test import override_settings
from evennia.prototypes import prototypes as prototypes_module
from evennia.prototypes import spawner as spawner_module
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room
from world.ai.profiles import default_profiles
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.subjects import ArtSubjectKind
from world.art.worker import drain_synchronous
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import read_records
from world.quests.scene_builder import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    _validate_occupant_parent,
    materialize_stage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation, accept
from world.skills.registry import SkillPrerequisite
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.traits import build_initial_traits, trait_config_for_values
from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_ARCHETYPES,
    SYNTH_GUILD_ISSUER_KEY,
    SYNTH_NPC_TIERS,
    SYNTH_STATIC_TIERS,
    make_skill,
    synthetic_registries,
)
from tools.spec_traceability import covers_requirement
import json

from world.lore.npc_card import normalize_card
from world.quests.tests._card_fixtures import occupant_card, occupant_card_record
from world.rules.npc_persona import read_npc_persona, update_npc_persona

from ._support import (
    _T_ARCHETYPE,
    _T_ANCHOR,
    _T_NPC_TIER,
    _T_NPC_TIER_ALT,
    _T_SENTENCE,
    _instance_bound_payload,
    SceneBuilderTestBase,
)

class SceneBuilderCharacterizationTests(SceneBuilderTestBase):
    def _characterized(self, **overrides):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(overrides)
        return payload

    def _spawned_npc(self, payload):
        record, _ = self._accept(payload)
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        return next(obj for obj in result.room.contents if isinstance(obj, NPC))

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    @covers_requirement("npc-identity-titles::blueprint-scene-occupants-spawn-under-the-authored-name-with-the-authored-title")
    def test_surrounding_whitespace_never_reaches_the_entity_key(self):
        # Validators strip before deciding, so an otherwise-valid authored
        # identity may carry surrounding whitespace; the spawner and the
        # persisted display_name both take the normalized form.
        npc = self._spawned_npc(
            self._characterized(display_name="  黑鬍  ", title=" 林間盜匪首領 ")
        )
        self.assertEqual(npc.key, "黑鬍")
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertEqual(npc.npc_title, "林間盜匪首領")

    @covers_requirement("npc-identity-titles::blueprint-scene-occupants-spawn-under-the-authored-name-with-the-authored-title")
    def test_full_characterization_is_materialized_fully(self):
        npc = self._spawned_npc(
            self._characterized(
                display_name="黑鬍",
                title="林間盜匪首領",
                age=68,
                apparent_age=68,
                portrait={"stable_key": "forest_bandit_chief"},
            )
        )
        # The authored name IS the key; the title lands as the validated form.
        self.assertEqual(npc.key, "黑鬍")
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertEqual(npc.npc_title, "林間盜匪首領")
        self.assertEqual(npc.db.age, 68)
        self.assertEqual(npc.db.apparent_age, 68)
        self.assertEqual(
            npc.db.portrait_policy,
            {"mode": "named", "stable_key": "forest_bandit_chief"},
        )

    @covers_requirement("scene-builder::npc-characterization-carries-a-complete-compact-card-through-compile-restore-and-materialization")
    def test_card_survives_compile_restore_and_materialization_unchanged(self):
        from world.quests.compile import (
            _compiled_to_payload,
            payload_to_registrations,
        )

        raw = occupant_card_record("（存續）")
        # Surrounding whitespace is normalized once at compile; the stored,
        # restored, and spawned card are the normalized form leaf for leaf.
        raw["habit"] = "  " + raw["habit"] + "\r\n"
        expected = normalize_card(raw)
        payload = self._characterized(persona=raw)
        compiled = compile_quest_blueprint(payload)
        restored = payload_to_registrations(
            json.loads(json.dumps(_compiled_to_payload(compiled)))
        )
        self.assertEqual(restored, compiled)
        self.assertEqual(
            restored.stage_requirements[0].characterizations[0].persona, expected
        )

        record, _ = self._accept(payload)
        result = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        self.assertEqual(npc.db.persona, expected.to_record())
        meta = npc.db.npc_persona_meta
        self.assertEqual(meta["persona_version"], 1)
        self.assertEqual(
            meta["provenance"],
            {
                "kind": "generated_quest",
                "quest": record.definition_key,
                "stage": 0,
                "occupant": 0,
            },
        )
        snapshot = read_npc_persona(npc)
        self.assertEqual(snapshot.card, expected)

    @covers_requirement("scene-builder::npc-characterization-carries-a-complete-compact-card-through-compile-restore-and-materialization")
    def test_card_never_influences_stored_stats(self):
        plain = self._spawned_npc(self._characterized())
        other = occupant_card_record("（另一張）")
        other["personality"] = "力大無窮、身手矯健、刀槍不入的勇者。"
        record, _ = self._accept(
            self._characterized(display_name="另一人", persona=other)
        )
        result = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        carded = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        for trait in ("hp", "atk_phys", "agility", "defense", "magic_power"):
            with self.subTest(trait=trait):
                self.assertEqual(
                    getattr(carded.traits, trait).base,
                    getattr(plain.traits, trait).base,
                )

    @covers_requirement("scene-builder::npc-characterization-carries-a-complete-compact-card-through-compile-restore-and-materialization")
    def test_forged_invalid_card_is_rejected_before_any_spawn(self):
        from world.lore.npc_card import NpcCard, NpcCardIdentity

        record, _ = self._accept(self._characterized())
        empty_speech = NpcCard(
            identity=NpcCardIdentity(public="偽造的公開身分"),
            appearance="偽造外觀",
            personality="偽造性格",
            speech_style="",
            life_story="偽造經歷",
            habit="偽造習慣",
        )
        over_bound = NpcCard(
            identity=NpcCardIdentity(public="偽造的公開身分"),
            appearance="x" * 601,
            personality="偽造性格",
            speech_style="偽造語氣",
            life_story="偽造經歷",
            habit="偽造習慣",
        )
        for persona in (None, empty_speech, over_bound):
            with self.subTest(persona=persona):
                forged = (
                    StageSpawnRequirement(
                        index=0,
                        objective_kind=ObjectiveKind.DEFEAT,
                        location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                        archetype=_T_ARCHETYPE,
                        anchor_near=_T_ANCHOR,
                        scene_sentence=_T_SENTENCE,
                        npc_reqs=(("bandit", _T_NPC_TIER, None),),
                        characterizations=(
                            StageNpcCharacterization(
                                display_name="偽造者",
                                title="偽造測試員",
                                persona=persona,
                            ),
                        ),
                    ),
                )
                SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
                rooms_before = InstanceRoom.objects.all().count()
                npcs_before = NPC.objects.all().count()
                with self.assertRaisesRegex(SceneBuilderSpawnError, "persona"):
                    materialize_stage(
                        self.player, record.quest_id, origin_room=self.anchor
                    )
                self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
                self.assertEqual(NPC.objects.all().count(), npcs_before)
                current = next(
                    r for r in read_records(self.player)
                    if r.quest_id == record.quest_id
                )
                self.assertIsNone(current.stage_room_id)
                self.assertFalse(current.objective_target_ids)

    @covers_requirement("scene-builder::npc-characterization-carries-a-complete-compact-card-through-compile-restore-and-materialization")
    def test_rematerialization_keeps_an_edited_occupant_card(self):
        record, _ = self._accept(self._characterized())
        first = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        npc = next(obj for obj in first.room.contents if isinstance(obj, NPC))
        edited = occupant_card_record("（已編輯）")
        outcome = update_npc_persona(npc, edited, 1)
        self.assertEqual((outcome.status, outcome.version), ("updated", 2))

        again = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        self.assertEqual(again.room.pk, first.room.pk)
        self.assertEqual(npc.db.persona, normalize_card(edited).to_record())
        self.assertEqual(npc.db.npc_persona_meta["persona_version"], 2)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_portrait_only_occupant_receives_the_default_age(self):
        npc = self._spawned_npc(
            self._characterized(portrait={"stable_key": "forest_bandit_chief"})
        )
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        self.assertEqual(
            npc.db.portrait_policy,
            {"mode": "named", "stable_key": "forest_bandit_chief"},
        )

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_baseline_is_valid_for_elven_occupants(self):
        npc = self._spawned_npc(
            self._characterized(
                tier=_T_NPC_TIER_ALT,
                portrait={"stable_key": "forest_elf_scout"},
            )
        )
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        from world.art.subjects import character_ages

        self.assertEqual(character_ages(npc), (25, 25))

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_name_only_occupant_is_named_but_portrait_less(self):
        npc = self._spawned_npc(
            self._characterized(display_name="黑鬍", title="林間盜匪首領")
        )
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertIsNone(npc.db.age)
        self.assertIsNone(npc.db.apparent_age)
        self.assertIsNone(npc.db.portrait_policy)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_ages_only_occupant_sets_ages_but_no_policy(self):
        npc = self._spawned_npc(self._characterized(age=40, apparent_age=40))
        self.assertEqual(npc.db.age, 40)
        self.assertEqual(npc.db.apparent_age, 40)
        self.assertIsNone(npc.db.portrait_policy)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_a_portrait_bearing_occupant_always_carries_canonical_ages_before_policy(self):
        """Repository guard: the policy is only materialized after the ages.

        A forged requirement carrying a portrait but no ages still lands on the
        deterministic default age, so subject-age eligibility's canonical
        inputs are guaranteed present on every spawn path that sets a policy.
        """
        record, _ = self._accept(_instance_bound_payload())
        forged = (
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype=_T_ARCHETYPE,
                anchor_near=_T_ANCHOR,
                scene_sentence=_T_SENTENCE,
                npc_reqs=(("bandit", _T_NPC_TIER, None),),
                characterizations=(
                    StageNpcCharacterization(
                        display_name="偽造者",
                        title="偽造測試員",
                        portrait_stable_key="forged_key",
                        persona=occupant_card(),
                    ),
                ),
            ),
        )
        SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
        result = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        self.assertEqual(
            npc.db.portrait_policy, {"mode": "named", "stable_key": "forged_key"}
        )

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_forged_invalid_characterization_is_rejected_before_any_spawn(self):
        """Defense in depth: forged requirements cannot bypass the age bounds.

        The compile boundary validated the accepted blueprint, but a forged
        ``StageSpawnRequirement`` must still be re-checked: negative, non-int,
        and unpaired ages would otherwise be written to a spawned NPC (a
        permanently portrait-ineligible occupant). Each forged shape raises
        before any room or occupant is created.
        """
        _ids = {
            "display_name": "偽造者",
            "title": "偽造測試員",
            "persona": occupant_card(),
        }
        forged_shapes = (
            StageNpcCharacterization(**_ids, age=-1, apparent_age=-1),
            StageNpcCharacterization(**_ids, age="30", apparent_age="30"),
            StageNpcCharacterization(**_ids, age=30, apparent_age=None),
            StageNpcCharacterization(**_ids, age=True, apparent_age=30),
            # Missing identity fields are themselves fail-closed (design D6):
            # a nameless or titleless forged occupant never spawns.
            StageNpcCharacterization(title="缺名", persona=occupant_card()),
            StageNpcCharacterization(display_name="缺銜", persona=occupant_card()),
            None,
        )
        record, _ = self._accept(_instance_bound_payload())
        for shape in forged_shapes:
            with self.subTest(shape=shape):
                forged = (
                    StageSpawnRequirement(
                        index=0,
                        objective_kind=ObjectiveKind.DEFEAT,
                        location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                        archetype=_T_ARCHETYPE,
                        anchor_near=_T_ANCHOR,
                        scene_sentence=_T_SENTENCE,
                        npc_reqs=(("bandit", _T_NPC_TIER, None),),
                        characterizations=(shape,),
                    ),
                )
                SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
                rooms_before = InstanceRoom.objects.all().count()
                with self.assertRaises(SceneBuilderSpawnError):
                    materialize_stage(
                        self.player, record.quest_id, origin_room=self.anchor
                    )
                self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
