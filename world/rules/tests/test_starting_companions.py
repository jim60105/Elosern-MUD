"""Tests for the preset companion declaration bounds and the NPC builder.

The lore-side shape validation lives with its validator in
``world/lore/tests/test_player_presets.py``; this module covers the rules-side
bounds sweep and the deterministic builder, including the differential parity
claim: a companion built from a card must equal a PLAYER activated from the
same card, not merely re-read the same helper the builder itself calls.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from django.test import override_settings

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.invite import CmdInvite
from commands.leave import CmdLeave
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import LLMNPC
from typeclasses.rooms import Room
from world.lore.player_presets import (
    PLAYER_PRESET_REGISTRY,
    PlayerPreset,
    StartingCompanion,
)
from world.lore.races import SUBRACE_REGISTRY
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.affinity_config import get_config
from world.rules.party import (
    JOINED_MESSAGE,
    PARTY_MAX_COMPANIONS,
    PartyJoinError,
    REASON_PARTY_FULL,
    is_companion,
    join_party,
    leave_party,
    party_size,
)
from world.rules import starting_companions as starting_companions_module

# The import-gate test below reloads the module (exercising the module-bottom
# sweep on the real import path) and a reload rebinds the module's own
# functions, so every call routes through the live module object. The
# exception name below is rebound by the reload test's repair step so every
# later assertRaises sees the class the live module actually raises.
StartingCompanionError = starting_companions_module.StartingCompanionError


def _validate_preset_companion_bounds(registry):
    return starting_companions_module._validate_preset_companion_bounds(registry)


def build_starting_companion(player, declaration):
    return starting_companions_module.build_starting_companion(player, declaration)


_YUKA = "yuka_darknight"
_YUNA = "yuna_darknight"


_HUMAN_ALLOCATIONS = (
    ("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
    ("agility", 10), ("defense", 11), ("magic_power", 43),
)


def _probe_preset(**overrides) -> PlayerPreset:
    values = dict(
        key="probe", display_name="探測者", age=18, apparent_age=18, race="human",
        subrace="human_commoner", allocations=_HUMAN_ALLOCATIONS, emphasis="e",
        sex="female",
    )
    values.update(overrides)
    return PlayerPreset(**values)


class CompanionBoundsSweepTests(unittest.TestCase):
    """The rules-side sweep over PARTY_MAX_COMPANIONS and NATURAL_CAP bounds."""

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_registry_ships_within_the_swept_bounds(self):
        # The import-time sweep already accepted the shipped registry; running
        # it again proves the shipped cards stay inside the rules constants.
        _validate_preset_companion_bounds(PLAYER_PRESET_REGISTRY)

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_over_bound_companion_count_names_the_offending_preset(self):
        from world.rules.party import PARTY_MAX_COMPANIONS

        preset = _probe_preset(
            starting_companions=tuple(
                StartingCompanion(key, 50, "夥伴")
                for key in list(PLAYER_PRESET_REGISTRY)[: PARTY_MAX_COMPANIONS + 1]
            )
        )
        with self.assertRaisesRegex(
            StartingCompanionError, "more than the party cap"
        ):
            _validate_preset_companion_bounds({"probe": preset})

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_out_of_range_affinity_names_the_offending_preset(self):
        from world.rules.affinity import NATURAL_CAP

        partner = next(key for key in PLAYER_PRESET_REGISTRY if key != "probe")
        for affinity in (0, -1, NATURAL_CAP + 1, True, False, "50", None):
            preset = _probe_preset(
                starting_companions=(StartingCompanion(partner, affinity, "夥伴"),)
            )
            with self.subTest(affinity=affinity), self.assertRaisesRegex(
                StartingCompanionError, "outside 1"
            ):
                _validate_preset_companion_bounds({"probe": preset})
        # The 1 and NATURAL_CAP boundaries pass.
        for affinity in (1, NATURAL_CAP):
            _validate_preset_companion_bounds(
                {
                    "probe": _probe_preset(
                        starting_companions=(
                            StartingCompanion(partner, affinity, "夥伴"),
                        )
                    )
                }
            )

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_an_overlong_relationship_label_names_the_offending_preset(self):
        # The label is injected into the built persona's social_connection,
        # which PersonaStore renders as prose under the same field cap.
        from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH

        partner = next(key for key in PLAYER_PRESET_REGISTRY if key != "probe")
        preset = _probe_preset(
            starting_companions=(
                StartingCompanion(partner, 50, "關" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        )
        with self.assertRaisesRegex(StartingCompanionError, "persona"):
            _validate_preset_companion_bounds({"probe": preset})


class _BuilderCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(
            Room,
            key="companion hall",
        )
        self.owner = create_object(PlayerCharacter, key="悠奈的持有者")
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        self.owner.location = self.hall


class CompanionBuildTests(_BuilderCase):
    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_built_companion_matches_a_player_activated_from_the_same_card(self):
        """Differential parity: companion vs. real activation, not vs. helpers."""
        account = create_account(
            "twin-account", "twin@example.test", "testpassword", typeclass=Account
        )
        shell = create_object(PlayerCharacter, key="twin-shell")
        account.at_post_create_character(shell)
        # yuka_darknight now binds its twin during activation, which spawns
        # at the shell's location (preset-companion-activation).
        shell.location = self.hall
        activate_player_character(
            account, shell, CharacterCreationRequest(mode="preset", preset_key=_YUKA)
        )
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertEqual(companion.race, shell.race)
        self.assertEqual(companion.subrace, shell.subrace)
        self.assertEqual(companion.sex, shell.sex)
        for axis in ALLOCATABLE_AXES + ("guild_merit",):
            self.assertEqual(
                companion.traits[axis].value, shell.traits[axis].value, msg=axis
            )
        self.assertEqual(companion.db.skills, shell.db.skills)
        self.assertEqual(
            companion.db.skill_proficiency, shell.db.skill_proficiency
        )
        self.assertEqual(companion.db.inventory, shell.db.inventory)
        self.assertEqual(companion.db.equipment, shell.db.equipment)
        self.assertEqual(
            companion.db.affinity_elements, shell.db.affinity_elements
        )
        self.assertEqual(companion.db.age, shell.db.age)
        self.assertEqual(companion.db.apparent_age, shell.db.apparent_age)
        self.assertEqual(companion.db.disguised_stats, shell.db.disguised_stats)
        # The persona is the card's record plus exactly the owner link.
        self.assertEqual(
            companion.db.persona,
            {
                **shell.db.persona,
                "social_connection": {
                    **shell.db.persona["social_connection"],
                    self.owner.key: "雙胞胎姊姊",
                },
            },
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_companion_is_an_llmnpc_beside_its_owner(self):
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        # Plain NPC fails commands/invite.py's gate; LLMNPC stays re-invitable.
        self.assertIsInstance(companion, LLMNPC)
        self.assertEqual(companion.location, self.hall)
        self.assertEqual(companion.key, "悠花")
        # Registry provenance (gallery-builtin-fallbacks): the builder carries
        # the partner card's preset key so a preset-level fallback declaration
        # resolves even though the companion's subject is pk-keyed.
        self.assertEqual(companion.db.creation_preset_key, _YUKA)

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_an_elf_companion_seeds_affinity_elements_from_its_subrace(self):
        preset = PLAYER_PRESET_REGISTRY[_YUKA]
        self.assertEqual(preset.race, "elf")
        self.assertEqual(preset.affinity_elements, ())
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        seed = SUBRACE_REGISTRY[preset.subrace].affinity_elements
        self.assertEqual(companion.db.affinity_elements, list(seed))

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_declared_equipment_is_worn_with_buffs_and_synced_ceilings(self):
        # A temporary card carries AND declares worn: the toggle preflight
        # requires canonical inventory ownership, exactly like shipped cards.
        # knight_platemail carries the rulebook {hp: 15} gauge cap;
        # apothecary_beads attaches the item_regen_light buff.
        card = _probe_preset(
            key="gear_probe",
            display_name="武裝探測者",
            starting_items=(
                ("knight_platemail", 1), ("apothecary_beads", 1),
                ("healing_potion", 1),
            ),
            starting_equipment=("knight_platemail", "apothecary_beads"),
        )
        PLAYER_PRESET_REGISTRY["gear_probe"] = card
        self.addCleanup(PLAYER_PRESET_REGISTRY.pop, "gear_probe", None)
        companion = build_starting_companion(
            self.owner, StartingCompanion("gear_probe", 40, "夥伴")
        )
        equipment = companion.db.equipment
        self.assertEqual(equipment["armor"], "knight_platemail")
        self.assertEqual(equipment["accessories"], ["apothecary_beads"])
        # Equipped items remain in canonical inventory.
        self.assertIn("knight_platemail", companion.db.inventory)
        self.assertEqual(companion.traits.hp.mod, 15)
        self.assertIn(
            "item_regen_light:apothecary_beads", set(companion.buffs.all)
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_persona_names_the_owning_player(self):
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUNA, 95, "雙胞胎妹妹")
        )
        self.assertEqual(
            companion.db.persona["social_connection"][self.owner.key],
            "雙胞胎妹妹",
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_taken_name_takes_a_pk_suffix_while_the_portrait_subject_stays(self):
        # The design's named edge: a persisted character literally holds the
        # partner preset's display name (display-name uniqueness is NOT
        # enforced at activation, so this is reachable).
        holder = create_object(PlayerCharacter, key="悠花")
        holder.location = self.hall
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertEqual(companion.key, f"悠花-{companion.pk}")
        self.assertEqual(
            companion.db.portrait_policy,
            {"mode": "named", "stable_key": str(companion.pk)},
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_builder_writes_no_affinity_party_or_player_state(self):
        party_before = self.owner.db.party
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertIsNone(companion.db.relations_data)
        self.assertEqual(companion.relations.affinity_for(self.owner), 0)
        self.assertIsNone(companion.db.party_member)
        self.assertEqual(self.owner.db.party, party_before)

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_failure_mid_build_leaves_no_persisted_companion(self):
        # A late mechanical step (imported at the builder's top level) fails
        # after the object exists: the compensation must delete it and re-raise.
        with patch(
            "world.rules.starting_companions.ensure_npc_canonical_age",
            side_effect=RuntimeError("simulated write failure"),
        ):
            with self.assertRaises(RuntimeError):
                build_starting_companion(
                    self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
                )
        self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_rejected_equipment_toggle_fails_the_build(self):
        card = _probe_preset(
            key="bad_gear_probe",
            display_name="壞裝探測者",
            starting_items=(("knight_platemail", 1),),
            # Declared worn but NOT carried -> ITEM_NOT_HELD rejection.
            starting_equipment=("apothecary_beads",),
        )
        PLAYER_PRESET_REGISTRY["bad_gear_probe"] = card
        self.addCleanup(PLAYER_PRESET_REGISTRY.pop, "bad_gear_probe", None)
        with self.assertRaisesRegex(StartingCompanionError, "was rejected"):
            build_starting_companion(
                self.owner, StartingCompanion("bad_gear_probe", 40, "夥伴")
            )
        self.assertFalse(
            ObjectDB.objects.filter(db_key="壞裝探測者").exists()
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_an_owner_without_location_raises_before_any_object_exists(self):
        self.owner.location = None
        before = ObjectDB.objects.count()
        with self.assertRaisesRegex(StartingCompanionError, "no location"):
            build_starting_companion(
                self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
            )
        self.assertEqual(ObjectDB.objects.count(), before)


class CompanionBoundsSweepRegistrationTests(_BuilderCase):
    """The sweep is a real import-time gate, not a dormant helper."""

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_module_import_runs_the_sweep_and_refuses_an_out_of_bounds_card(self):
        # The delta scenario: importing world.rules.starting_companions raises
        # from its registry sweep when a card declares more companions than
        # the party cap. Poison the real registry with one over-bound card and
        # reload the module: the module-bottom sweep must refuse the import.
        import importlib

        from world.rules import starting_companions as module
        from world.rules.party import PARTY_MAX_COMPANIONS

        bad = _probe_preset(
            key="reload_probe",
            starting_companions=tuple(
                StartingCompanion(key, 50, "夥伴")
                for key in list(PLAYER_PRESET_REGISTRY)[: PARTY_MAX_COMPANIONS + 1]
            ),
        )
        PLAYER_PRESET_REGISTRY["reload_probe"] = bad
        try:
            with self.assertRaises(ValueError) as caught:
                importlib.reload(module)
            self.assertRegex(str(caught.exception), "more than the party cap")
            self.assertRegex(str(caught.exception), "reload_probe")
        finally:
            PLAYER_PRESET_REGISTRY.pop("reload_probe", None)
            # Repair reload: re-executes the sweep clean over the shipped
            # registry and restores every public name.
            importlib.reload(module)
            # A reload re-executes every statement, so even the freshly
            # repaired module now carries NEW function and exception class
            # objects. Rebind this test module's exception name to the live
            # class so later assertRaises checks match what the reloaded
            # builder actually raises.
            globals()["StartingCompanionError"] = module.StartingCompanionError
        self.assertIs(module.PLAYER_PRESET_REGISTRY, PLAYER_PRESET_REGISTRY)
        self.assertTrue(callable(module.build_starting_companion))


def _reply_text(speech="我願意與妳同行。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


class CompanionActivationBindingTests(QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """Preset activation builds, seeds, and binds declared companions.

    Uses EvenniaTest (not EvenniaTestCase) because the invite re-binding
    scenario drives the real ``CmdInvite`` through the command mixin.
    """

    def setUp(self):
        super().setUp()
        # The affinity config validates its cap-breaks against the quest
        # registry; register the shipped catalog before loading it. The
        # isolation mixin restores the process-global registries after.
        register_catalog()
        validators_before = dict(guardrail._semantic_validators)
        fallbacks_before = dict(guardrail._degrade_fallbacks)
        self.addCleanup(lambda: guardrail._semantic_validators.update(validators_before))
        self.addCleanup(lambda: guardrail._degrade_fallbacks.update(fallbacks_before))
        guardrail._semantic_validators.clear()
        guardrail._degrade_fallbacks.clear()
        _OUTPUT_SCHEMAS.clear()
        self.addCleanup(_OUTPUT_SCHEMAS.clear)
        register_npc_dialogue()
        self.account = create_account(
            "twin-maker", "twin-maker@example.test", "testpassword", typeclass=Account
        )
        self.threshold = get_config().invite_threshold

    def _shell(self, key: str) -> PlayerCharacter:
        """A fresh pending shell placed in a room, as production leaves it."""
        shell = create_object(PlayerCharacter, key=key)
        self.account.at_post_create_character(shell)
        shell.location = self.room1
        return shell

    def _activate(self, shell: PlayerCharacter, preset_key: str):
        return activate_player_character(
            self.account, shell,
            CharacterCreationRequest(mode="preset", preset_key=preset_key),
        )

    def _companion_of(self, player: PlayerCharacter) -> LLMNPC:
        from world.rules.party import live_companions

        bound = live_companions(player)
        self.assertEqual(len(bound), 1)
        return bound[0]

    def _declared_affinity(self, preset_key: str) -> int:
        """The affinity value the preset's own card declares for its twin."""
        declaration = PLAYER_PRESET_REGISTRY[preset_key].starting_companions[0]
        return declaration.affinity

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_activating_yuna_binds_a_live_yuka_at_declared_affinity(self):
        shell = self._shell("maker-shell-a")
        self._activate(shell, _YUNA)
        self.assertFalse(shell.creation_pending)
        companion = self._companion_of(shell)
        # Built from the partner card, at the player's location.
        self.assertIsInstance(companion, LLMNPC)
        self.assertEqual(companion.key, "悠花")
        self.assertEqual(companion.location, shell.location)
        # Bound both ways through the sole writers.
        self.assertEqual(shell.db.party, [companion.pk])
        self.assertEqual(int(companion.db.party_member), int(shell.pk))
        self.assertTrue(is_companion(companion, shell))
        # Seeded at the declared value via the affinity surface.
        declared = self._declared_affinity(_YUNA)
        self.assertEqual(companion.relations.affinity_for(shell), declared)
        self.assertGreater(declared, self.threshold)

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_activating_yuka_binds_a_live_yuna_under_the_same_rules(self):
        shell = self._shell("maker-shell-yuka")
        self._activate(shell, _YUKA)
        companion = self._companion_of(shell)
        self.assertEqual(companion.key, "悠奈")
        self.assertEqual(companion.location, shell.location)
        self.assertEqual(shell.db.party, [companion.pk])
        self.assertEqual(int(companion.db.party_member), int(shell.pk))
        self.assertEqual(
            companion.relations.affinity_for(shell), self._declared_affinity(_YUKA)
        )

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_companionless_preset_activation_binds_nothing(self):
        shell = self._shell("maker-shell-wanderer")
        self._activate(shell, "elysa_snow")
        self.assertFalse(shell.creation_pending)
        self.assertFalse(shell.attributes.has("party"))
        self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())
        self.assertFalse(ObjectDB.objects.filter(db_key="悠奈").exists())

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_failure_in_build_seed_or_join_rolls_the_activation_back(self):
        # One scenario per injected step: build, seed, join. Each must raise,
        # leave the shell pending with no mechanical state, persist no
        # companion, and leave party membership unset.
        injections = (
            ("build", "world.rules.starting_companions.build_starting_companion"),
            ("seed", "world.rules.starting_companions.seed_affinity"),
            ("join", "world.rules.starting_companions.join_party"),
        )
        for step, target in injections:
            with self.subTest(step=step):
                shell = self._shell(f"maker-shell-{step}")
                before_objects = ObjectDB.objects.count()
                with patch(target, side_effect=RuntimeError(f"boom in {step}")):
                    with self.assertRaises(CharacterCreationError):
                        self._activate(shell, _YUNA)
                self.assertTrue(shell.creation_pending)
                self.assertEqual(shell.traits.all(), [])
                self.assertFalse(shell.attributes.has("party"))
                self.assertIsNone(shell.db.party)
                self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())
                # The rolled-back activation persists nothing at all.
                self.assertEqual(ObjectDB.objects.count(), before_objects)
                # A DB read (not the cache) confirms the pending flag survived.
                shell.attributes.reset_cache()
                self.assertTrue(shell.attributes.has("creation_pending"))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_the_starting_companion_consumes_one_party_slot(self):
        shell = self._shell("maker-shell-bound")
        self._activate(shell, _YUNA)
        self.assertEqual(party_size(shell), 1)
        fillers = [
            create_object(LLMNPC, key=f"填充夥伴{i}", location=self.room1)
            for i in range(PARTY_MAX_COMPANIONS - 1)
        ]
        for filler in fillers:
            join_party(filler, shell)
        self.assertEqual(party_size(shell), PARTY_MAX_COMPANIONS)
        fifth = create_object(LLMNPC, key="第五夥伴", location=self.room1)
        with self.assertRaises(PartyJoinError) as context:
            join_party(fifth, shell)
        self.assertEqual(context.exception.reason, REASON_PARTY_FULL)

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_dismissed_starting_companion_rejoins_via_invite(self):
        shell = self._shell("maker-shell-dismiss")
        self._activate(shell, _YUNA)
        companion = self._companion_of(shell)
        leave_party(companion, shell, reason="dismissed")
        # Dismissed, not deleted: still in the room at the seeded affinity.
        self.assertFalse(is_companion(companion, shell))
        self.assertEqual(companion.location, self.room1)
        self.assertEqual(
            companion.relations.affinity_for(shell), self._declared_affinity(_YUNA)
        )
        # The ordinary invite command re-binds through the degraded terminal
        # (declared seed > invite threshold), exactly like any other NPC.
        raw = default_profiles()
        raw["npc_dialogue"]["enabled"] = False
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=raw):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                output = self.call(CmdInvite(), "悠花", caller=shell, msg=None)
        self.assertIn(JOINED_MESSAGE, output)
        self.assertEqual(len(client.calls), 0)
        self.assertTrue(is_companion(companion, shell))
        self.assertEqual(int(companion.db.party_member), int(shell.pk))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_failure_after_a_completed_bind_evicts_the_built_npc(self):
        # Portrait finalization fails AFTER the binding "succeeded"
        # in-transaction: the rollback removes the companion row, but the
        # idmapper and the departure room's contents cache still hold the
        # created NPC unless activation's except branch evicts it.
        shell = self._shell("maker-shell-post-bind")
        captured: dict = {}

        def _portrait_boom(*args, **kwargs):
            captured["pk"] = shell.db.party[0] if shell.db.party else None
            raise RuntimeError("portrait boom")

        with patch(
            "world.rules.character_creation.finalize_player_portrait",
            side_effect=_portrait_boom,
        ):
            with self.assertRaises(RuntimeError):
                self._activate(shell, _YUNA)
        self.assertIsNotNone(captured["pk"], "the bind completed before the failure")
        # Gone from the database, from the room's contents, and from the
        # process-global idmapper — no phantom companion survives.
        self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())
        self.assertNotIn(
            "悠花", [obj.key for obj in self.room1.contents]
        )
        self.assertNotIn(captured["pk"], LLMNPC.__dbclass__.__instance_cache__)
        self.assertFalse(shell.attributes.has("party"))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_later_declaration_failing_deletes_the_already_joined_twin(self):
        # No shipped preset declares two companions, so exercise the
        # multi-companion compensation with a synthetic card: the first twin
        # builds, seeds, AND joins; the second twin's join fails — every NPC
        # built during the activation must be deleted, including the one that
        # already holds a party binding, and party left unset.
        from dataclasses import replace

        synthetic = replace(
            PLAYER_PRESET_REGISTRY["elysa_snow"],
            key="twin_pair",
            display_name="雙生者",
            starting_companions=(
                StartingCompanion(_YUKA, 95, "雙胞胎姊姊"),
                StartingCompanion(_YUNA, 90, "雙胞胎妹妹"),
            ),
        )
        PLAYER_PRESET_REGISTRY["twin_pair"] = synthetic
        self.addCleanup(PLAYER_PRESET_REGISTRY.pop, "twin_pair", None)
        shell = self._shell("maker-shell-pair")
        before_objects = ObjectDB.objects.count()
        # First join lands for real (the twin genuinely holds a binding);
        # the second join raises.
        from world.rules import party as party_module

        real_join = party_module.join_party

        def join_then_boom(npc, player):
            if party_size(player) == 0:
                return real_join(npc, player)
            raise RuntimeError("second join fails")

        with patch(
            "world.rules.starting_companions.join_party",
            side_effect=join_then_boom,
        ):
            with self.assertRaises(CharacterCreationError):
                self._activate(shell, "twin_pair")
        self.assertTrue(shell.creation_pending)
        self.assertFalse(shell.attributes.has("party"))
        self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())
        self.assertFalse(ObjectDB.objects.filter(db_key="悠奈").exists())
        self.assertEqual(ObjectDB.objects.count(), before_objects)

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_the_auto_leave_recheck_keeps_the_seeded_companion(self):
        from world.rules.affinity import run_auto_leave_recheck

        shell = self._shell("maker-shell-recheck")
        self._activate(shell, _YUNA)
        companion = self._companion_of(shell)
        # The wired auto-leave rule on arrival: 95 is above the threshold.
        self.assertIsNone(run_auto_leave_recheck(companion, shell))
        self.assertTrue(is_companion(companion, shell))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_name_clash_takes_the_pk_suffix_and_binds_the_right_entity(self):
        # The same-account design case: a player literally named 悠奈 owns
        # the twin's display name, so the companion's key takes the -{pk}
        # suffix while the party binding still names the real companion.
        first = self._shell("悠奈")
        self._activate(first, _YUNA)
        second = self._shell("maker-shell-second")
        self._activate(second, _YUKA)
        own_companion = self._companion_of(first)
        clash_companion = self._companion_of(second)
        # Player 悠奈's own twin (悠花) keeps its key untouched.
        self.assertEqual(own_companion.key, "悠花")
        # The second activation's twin wants 悠奈, which the *player* holds.
        self.assertNotEqual(clash_companion.key, "悠奈")
        self.assertEqual(clash_companion.key, f"悠奈-{clash_companion.pk}")
        # Both entities coexist; each player's list names its own twin.
        self.assertNotEqual(int(own_companion.pk), int(clash_companion.pk))
        self.assertEqual(second.db.party, [clash_companion.pk])
        self.assertEqual(first.db.party, [own_companion.pk])
        self.assertTrue(is_companion(clash_companion, second))
        self.assertFalse(is_companion(own_companion, second))
        # CmdLeave dismissal resolves the suffixed key through targeting.
        self.call(
            CmdLeave(), clash_companion.key, caller=second, msg=None
        )
        self.assertFalse(is_companion(clash_companion, second))
        self.assertTrue(is_companion(own_companion, first))
