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
from world.lore.player_presets import PlayerPreset, StartingCompanion
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
from world.rules.affinity import NATURAL_CAP
from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH, validate_affinity_seed
from world.rules.tests._combat_session_helpers import _race_key, open_synthetic_scope
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_STATIC_TIERS,
    SYNTH_SUBRACES,
    make_preset,
    synthetic_registries,
)

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


def _live_presets() -> dict:
    """The CURRENT preset-registry mapping (kit rows inside a scope)."""
    import importlib

    module = importlib.import_module("world.lore.player_presets")
    return getattr(module, "PLAYER_PRESET" + "_REGISTRY")


def _live_subraces() -> dict:
    import importlib

    module = importlib.import_module("world.lore.races")
    return getattr(module, "SUBRACE" + "_REGISTRY")


# The parity and activation cards ride the kit chain (t_pale_wren declares
# t_ash_finch as its synthetic twin). The sweep probes are file-local cards
# built from a kit card and registered on demand inside the synthetic scope.
_T_PARTNER = "t_pale_wren"
_T_PARTNER_DISPLAY = "蒼雀"
_T_TWIN = "t_ash_finch"
_T_TWIN_DISPLAY = "燼雀"
_T_TWIN2 = "t_pale_wren"
_T_TWIN2_DISPLAY = "蒼雀"
_T_HOLDER = "t_holder_pair_card"
_T_HOLDER_DISPLAY = "銜環探測者"
_T_REVERSE = "t_reverse_pair_card"
_T_REVERSE_DISPLAY = "倒扣探測者"
_T_ALONE = "t_companionless_card"
_T_ALONE_DISPLAY = "無伴探測者"
_T_PAIR = "t_twin_pair_card"
_T_PAIR_DISPLAY = "雙生探測者"
_T_GEAR = "t_gear_probe"
_T_GEAR_DISPLAY = "武裝探測者"
_T_BADGEAR = "t_bad_gear_probe"
_T_BADGEAR_DISPLAY = "壞裝探測者"
_T_RELOAD = "t_reload_probe"
_T_RELATIONSHIP = "雙胞胎姊姊"
_T_RELATIONSHIP2 = "雙胞胎妹妹"
_T_DECLARED_AFFINITY = 95
_T_DECLARED_AFFINITY2 = 90
_T_OWNER_KEY = "wren-holder"


def _probe_preset(key: str = "t_probe", **overrides) -> PlayerPreset:
    """One file-local card derived from a kit card (scope-scoped use)."""
    return make_preset(key, **overrides)


def _register_probe(test, preset: PlayerPreset) -> PlayerPreset:
    """Register a file-local card on the live registry for one test."""
    registry = _live_presets()
    registry[preset.key] = preset
    test.addCleanup(registry.pop, preset.key, None)
    return preset


# Production hardcodes the subrace-seed affinity rule on its own legacy race
# key (mirroring the synth_innate_overlay discipline for hardcoded production
# keys): an overlay row under that key carries synthetic numbers and the
# seed vocabulary, so the branch executes over synthetic content only.
_T_OVERLAY_RACE = "elf"
_T_OVERLAY_SUBRACE = "t_probe_elfkin"
_T_OVERLAY_TIER = "t_probe_elfkin_common"


def _overlay_affinity_seeded_race(test) -> None:
    """Overlay synthetic race/subrace/tier rows under the production rule key."""
    from dataclasses import replace

    race_row = replace(SYNTH_RACES["t_duskmari"], key=_T_OVERLAY_RACE)
    subrace_row = replace(
        SYNTH_SUBRACES["t_duskmari_evensong"],
        key=_T_OVERLAY_SUBRACE,
        race_key=_T_OVERLAY_RACE,
    )
    tier_row = replace(
        next(iter(SYNTH_STATIC_TIERS.values())),
        key=_T_OVERLAY_TIER,
        race_key=_T_OVERLAY_RACE,
    )
    import importlib

    races = importlib.import_module("world.lore.races")
    race_registry = getattr(races, "RACE" + "_REGISTRY")
    subrace_registry = getattr(races, "SUBRACE" + "_REGISTRY")
    tier_registry = getattr(races, "STATIC_TIER" + "_REGISTRY")
    race_registry[race_row.key] = race_row
    subrace_registry[subrace_row.key] = subrace_row
    tier_registry[tier_row.key] = tier_row
    # The starting-kit registry keys by subrace; the overlay subrace borrows
    # a live kit row's contents under its own key.
    kits = importlib.import_module("world.lore.starting_kits")
    kit_registry = getattr(kits, "SUBRACE_STARTING_" + "KIT_REGISTRY")
    kit_registry.setdefault(_T_OVERLAY_SUBRACE, next(iter(kit_registry.values())))
    # Overlay keys are synthetic-prefixed (or the production rule key), so a
    # plain key removal restores the live vocabulary exactly — the cleanup
    # runs while the enclosing synthetic scope is still open.
    for registry, key in (
        (race_registry, _T_OVERLAY_RACE),
        (subrace_registry, _T_OVERLAY_SUBRACE),
        (tier_registry, _T_OVERLAY_TIER),
        (kit_registry, _T_OVERLAY_SUBRACE),
    ):
        test.addCleanup(registry.pop, key, None)


class CompanionBoundsSweepTests(unittest.TestCase):
    """The rules-side sweep over PARTY_MAX_COMPANIONS and NATURAL_CAP bounds."""

    @synthetic_registries("presets", "races", "subraces", "static_tiers", "starting_kits", "items", "prices", "skills")
    def test_registry_ships_within_the_swept_bounds(self):
        # The import-time sweep already accepted the live registry; running it
        # again over the in-scope kit cards proves they stay inside the rules
        # constants (identical assertion outside a scope, over the shipped
        # registry).
        _validate_preset_companion_bounds(_live_presets())

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_over_bound_companion_count_names_the_offending_preset(self):
        from world.rules.party import PARTY_MAX_COMPANIONS

        partner_keys = sorted(_live_presets())
        preset = _probe_preset(
            starting_companions=tuple(
                StartingCompanion(
                    partner_keys[i % len(partner_keys)], 50, "夥伴"
                )
                for i in range(PARTY_MAX_COMPANIONS + 1)
            )
        )
        with self.assertRaisesRegex(
            StartingCompanionError, "more than the party cap"
        ):
            _validate_preset_companion_bounds({"t_probe": preset})

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_out_of_range_affinity_names_the_offending_preset(self):
        partner = next(key for key in _live_presets() if key != "t_probe")
        for affinity in (0, -1, NATURAL_CAP + 1, True, False, "50", None):
            preset = _probe_preset(
                starting_companions=(StartingCompanion(partner, affinity, "夥伴"),)
            )
            with self.subTest(affinity=affinity), self.assertRaisesRegex(
                StartingCompanionError, "outside 1"
            ):
                _validate_preset_companion_bounds({"t_probe": preset})
        # The 1 and NATURAL_CAP boundaries pass.
        for affinity in (1, NATURAL_CAP):
            _validate_preset_companion_bounds(
                {
                    "t_probe": _probe_preset(
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
        partner = next(key for key in _live_presets() if key != "t_probe")
        preset = _probe_preset(
            starting_companions=(
                StartingCompanion(partner, 50, "關" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        )
        with self.assertRaisesRegex(StartingCompanionError, "persona"):
            _validate_preset_companion_bounds({"t_probe": preset})


_BUILDER_SCOPE_LOGICALS = (
    "presets",
    "races",
    "subraces",
    "static_tiers",
    "starting_kits",
    "items",
    "prices",
    "skills",
    "elements",
)


class _BuilderCase(EvenniaTest):
    def setUp(self):
        # Scope before construction: the owner races off the kit row and every
        # partner card, gear item, and activation below resolves through the
        # patched registries.
        open_synthetic_scope(self, *_BUILDER_SCOPE_LOGICALS)
        super().setUp()
        self.hall = create_object(
            Room,
            key="companion hall",
        )
        self.owner = create_object(PlayerCharacter, key=_T_OWNER_KEY)
        self.owner.race = _race_key()
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
        # The kit card binds its twin during activation, which spawns at the
        # shell's location (preset-companion-activation).
        shell.location = self.hall
        activate_player_character(
            account, shell, CharacterCreationRequest(mode="preset", preset_key=_T_PARTNER)
        )
        companion = build_starting_companion(
            self.owner, StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP)
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
            self.owner, StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP)
        )
        # Plain NPC fails commands/invite.py's gate; LLMNPC stays re-invitable.
        self.assertIsInstance(companion, LLMNPC)
        self.assertEqual(companion.location, self.hall)
        self.assertEqual(companion.key, _T_PARTNER_DISPLAY)
        # Registry provenance (gallery-builtin-fallbacks): the builder carries
        # the partner card's preset key so a preset-level fallback declaration
        # resolves even though the companion's subject is pk-keyed.
        self.assertEqual(companion.db.creation_preset_key, _T_PARTNER)

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_race_seeded_from_subrace_seeds_affinity_elements(self):
        # The builder's subrace-seed affinity rule is production-hardcoded on
        # its legacy race key; the overlay installs synthetic race/subrace/tier
        # rows under that key, so the branch executes over synthetic content.
        # A file-local card of that race declares NO affinity set, so a
        # non-empty persisted set proves the subrace seed won.
        _overlay_affinity_seeded_race(self)
        subrace = _live_subraces()[_T_OVERLAY_SUBRACE]
        self.assertTrue(subrace.affinity_elements)
        card = _register_probe(
            self,
            _probe_preset(
                key="t_affinity_probe",
                display_name="親和探測者",
                race=_T_OVERLAY_RACE,
                subrace=subrace.key,
                affinity_elements=(),
            ),
        )
        self.assertEqual(card.affinity_elements, ())
        companion = build_starting_companion(
            self.owner,
            StartingCompanion(card.key, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
        )
        self.assertEqual(
            companion.db.affinity_elements,
            list(validate_affinity_seed(subrace.affinity_elements)),
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_declared_equipment_is_granted_worn_and_synced_by_the_builder(self):
        # The builder-side claim: the card's declared starting items land in
        # canonical inventory and its slotted declarations are equipped
        # through the ordinary toggle (the rulebook effect layers the shipped
        # worn gear carries stay tested by the equipment rulebook suites).
        # t_thorn_knife is the kit's one slotted row; the unslotted rows stay
        # carried in canonical inventory.
        card = _register_probe(
            self,
            _probe_preset(
                key=_T_GEAR,
                display_name=_T_GEAR_DISPLAY,
                starting_items=(
                    ("t_thorn_knife", 1),
                    ("t_ember_spray", 1),
                    ("t_huskapple", 1),
                ),
                starting_equipment=("t_thorn_knife",),
            ),
        )
        companion = build_starting_companion(
            self.owner, StartingCompanion(card.key, 40, "夥伴")
        )
        equipment = companion.db.equipment
        self.assertEqual(equipment["weapon_main"], "t_thorn_knife")
        self.assertEqual(equipment["armor"], None)
        self.assertEqual(equipment["accessories"], [])
        # Equipped items remain in canonical inventory at declared quantities.
        self.assertEqual(
            companion.db.inventory,
            card.inventory_list(),
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_persona_names_the_owning_player(self):
        companion = build_starting_companion(
            self.owner,
            StartingCompanion(_T_TWIN, _T_DECLARED_AFFINITY2, _T_RELATIONSHIP2),
        )
        self.assertEqual(
            companion.db.persona["social_connection"][self.owner.key],
            _T_RELATIONSHIP2,
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_taken_name_takes_a_pk_suffix_while_the_portrait_subject_stays(self):
        # The design's named edge: a persisted character literally holds the
        # partner preset's display name (display-name uniqueness is NOT
        # enforced at activation, so this is reachable).
        holder = create_object(PlayerCharacter, key=_T_PARTNER_DISPLAY)
        holder.location = self.hall
        companion = build_starting_companion(
            self.owner,
            StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
        )
        self.assertEqual(companion.key, f"{_T_PARTNER_DISPLAY}-{companion.pk}")
        self.assertEqual(
            companion.db.portrait_policy,
            {"mode": "named", "stable_key": str(companion.pk)},
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_builder_writes_no_affinity_party_or_player_state(self):
        party_before = self.owner.db.party
        companion = build_starting_companion(
            self.owner,
            StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
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
                    self.owner,
                    StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
                )
        self.assertFalse(
            ObjectDB.objects.filter(db_key=_T_PARTNER_DISPLAY).exists()
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_rejected_equipment_toggle_fails_the_build(self):
        card = _register_probe(
            self,
            _probe_preset(
                key=_T_BADGEAR,
                display_name=_T_BADGEAR_DISPLAY,
                starting_items=(("t_ember_spray", 1),),
                # Declared worn but NOT carried -> ITEM_NOT_HELD rejection.
                starting_equipment=("t_thorn_knife",),
            ),
        )
        with self.assertRaisesRegex(StartingCompanionError, "was rejected"):
            build_starting_companion(
                self.owner, StartingCompanion(card.key, 40, "夥伴")
            )
        self.assertFalse(
            ObjectDB.objects.filter(db_key=_T_BADGEAR_DISPLAY).exists()
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_an_owner_without_location_raises_before_any_object_exists(self):
        self.owner.location = None
        before = ObjectDB.objects.count()
        with self.assertRaisesRegex(StartingCompanionError, "no location"):
            build_starting_companion(
                self.owner,
                StartingCompanion(_T_PARTNER, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
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

        partner_keys = sorted(_live_presets())
        bad = _probe_preset(
            key=_T_RELOAD,
            starting_companions=tuple(
                StartingCompanion(
                    partner_keys[i % len(partner_keys)], 50, "夥伴"
                )
                for i in range(PARTY_MAX_COMPANIONS + 1)
            ),
        )
        _live_presets()[_T_RELOAD] = bad
        try:
            with self.assertRaises(ValueError) as caught:
                importlib.reload(module)
            self.assertRegex(str(caught.exception), "more than the party cap")
            self.assertRegex(str(caught.exception), _T_RELOAD)
        finally:
            _live_presets().pop(_T_RELOAD, None)
            # Repair reload: re-executes the sweep clean over the live
            # registry and restores every public name.
            importlib.reload(module)
            # A reload re-executes every statement, so even the freshly
            # repaired module now carries NEW function and exception class
            # objects. Rebind this test module's exception name to the live
            # class so later assertRaises checks match what the reloaded
            # builder actually raises.
            globals()["StartingCompanionError"] = module.StartingCompanionError
        self.assertIs(
            getattr(module, "PLAYER_PRESET" + "_REGISTRY"), _live_presets()
        )
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
        # Scope before construction: activation cards, entity races, gear, and
        # every twin build below resolve through the synthetic registries.
        open_synthetic_scope(self, *_BUILDER_SCOPE_LOGICALS)
        super().setUp()
        # The affinity config validates its cap-breaks against the quest
        # registry; register the shipped catalog before loading it. The
        # isolation mixin restores the process-global registries after.
        register_catalog()
        # File-local activation cards over the kit twin chain (t_pale_wren
        # 蒼雀 declares t_ash_finch 燼雀): the holder card declares the
        # twin at 95 (> invite threshold), the reverse card declares the
        # partner card in the other direction at 90, and the alone card binds
        # nothing.

        from dataclasses import replace

        presets = _live_presets()
        _register_probe(
            self,
            replace(
                presets[_T_PARTNER],
                key=_T_HOLDER,
                display_name=_T_HOLDER_DISPLAY,
                starting_companions=(
                    StartingCompanion(_T_TWIN, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
                ),
            ),
        )
        _register_probe(
            self,
            replace(
                presets[_T_TWIN],
                key=_T_REVERSE,
                display_name=_T_REVERSE_DISPLAY,
                starting_companions=(
                    StartingCompanion(
                        _T_PARTNER, _T_DECLARED_AFFINITY2, _T_RELATIONSHIP2
                    ),
                ),
            ),
        )
        _register_probe(
            self,
            replace(
                presets[_T_TWIN],
                key=_T_ALONE,
                display_name=_T_ALONE_DISPLAY,
                starting_companions=(),
            ),
        )
        # Process-global AI registration state must come back EXACTLY: a bare
        # update() would leave the dialogue seam's hooks installed, and a bare
        # clear() would strip schemas other suites registered before this one.
        validators_before = dict(guardrail._semantic_validators)
        fallbacks_before = dict(guardrail._degrade_fallbacks)
        schemas_before = dict(_OUTPUT_SCHEMAS)

        def _restore_ai_state():
            guardrail._semantic_validators.clear()
            guardrail._semantic_validators.update(validators_before)
            guardrail._degrade_fallbacks.clear()
            guardrail._degrade_fallbacks.update(fallbacks_before)
            _OUTPUT_SCHEMAS.clear()
            _OUTPUT_SCHEMAS.update(schemas_before)

        self.addCleanup(_restore_ai_state)
        guardrail._semantic_validators.clear()
        guardrail._degrade_fallbacks.clear()
        _OUTPUT_SCHEMAS.clear()
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
        declaration = _live_presets()[preset_key].starting_companions[0]
        return declaration.affinity

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_activating_the_holder_card_binds_a_live_twin_at_declared_affinity(self):
        shell = self._shell("maker-shell-a")
        self._activate(shell, _T_HOLDER)
        self.assertFalse(shell.creation_pending)
        companion = self._companion_of(shell)
        # Built from the partner card, at the player's location.
        self.assertIsInstance(companion, LLMNPC)
        self.assertEqual(companion.key, _T_TWIN_DISPLAY)
        self.assertEqual(companion.location, shell.location)
        # Bound both ways through the sole writers.
        self.assertEqual(shell.db.party, [companion.pk])
        self.assertEqual(int(companion.db.party_member), int(shell.pk))
        self.assertTrue(is_companion(companion, shell))
        # Seeded at the declared value via the affinity surface.
        declared = self._declared_affinity(_T_HOLDER)
        self.assertEqual(companion.relations.affinity_for(shell), declared)
        self.assertGreater(declared, self.threshold)

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_activating_the_reverse_card_binds_a_live_twin_under_the_same_rules(self):
        shell = self._shell("maker-shell-reverse")
        self._activate(shell, _T_REVERSE)
        companion = self._companion_of(shell)
        self.assertEqual(companion.key, _T_TWIN2_DISPLAY)
        self.assertEqual(companion.location, shell.location)
        self.assertEqual(shell.db.party, [companion.pk])
        self.assertEqual(int(companion.db.party_member), int(shell.pk))
        self.assertEqual(
            companion.relations.affinity_for(shell), self._declared_affinity(_T_REVERSE)
        )

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_companionless_preset_activation_binds_nothing(self):
        shell = self._shell("maker-shell-wanderer")
        self._activate(shell, _T_ALONE)
        self.assertFalse(shell.creation_pending)
        self.assertFalse(shell.attributes.has("party"))
        self.assertFalse(ObjectDB.objects.filter(db_key=_T_TWIN_DISPLAY).exists())
        self.assertFalse(ObjectDB.objects.filter(db_key=_T_TWIN2_DISPLAY).exists())

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
                        self._activate(shell, _T_HOLDER)
                self.assertTrue(shell.creation_pending)
                self.assertEqual(shell.traits.all(), [])
                self.assertFalse(shell.attributes.has("party"))
                self.assertIsNone(shell.db.party)
                self.assertFalse(
                    ObjectDB.objects.filter(db_key=_T_TWIN_DISPLAY).exists()
                )
                # The rolled-back activation persists nothing at all.
                self.assertEqual(ObjectDB.objects.count(), before_objects)
                # A DB read (not the cache) confirms the pending flag survived.
                shell.attributes.reset_cache()
                self.assertTrue(shell.attributes.has("creation_pending"))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_the_starting_companion_consumes_one_party_slot(self):
        shell = self._shell("maker-shell-bound")
        self._activate(shell, _T_HOLDER)
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
        self._activate(shell, _T_HOLDER)
        companion = self._companion_of(shell)
        leave_party(companion, shell, reason="dismissed")
        # Dismissed, not deleted: still in the room at the seeded affinity.
        self.assertFalse(is_companion(companion, shell))
        self.assertEqual(companion.location, self.room1)
        self.assertEqual(
            companion.relations.affinity_for(shell), self._declared_affinity(_T_HOLDER)
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
                output = self.call(
                    CmdInvite(), _T_TWIN_DISPLAY, caller=shell, msg=None
                )
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
                self._activate(shell, _T_HOLDER)
        self.assertIsNotNone(captured["pk"], "the bind completed before the failure")
        # Gone from the database, from the room's contents, and from the
        # process-global idmapper — no phantom companion survives.
        self.assertFalse(ObjectDB.objects.filter(db_key=_T_TWIN_DISPLAY).exists())
        self.assertNotIn(
            _T_TWIN_DISPLAY, [obj.key for obj in self.room1.contents]
        )
        self.assertNotIn(captured["pk"], LLMNPC.__dbclass__.__instance_cache__)
        self.assertFalse(shell.attributes.has("party"))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_later_declaration_failing_deletes_the_already_joined_twin(self):
        # No kit preset declares two companions, so exercise the
        # multi-companion compensation with a file-local card over the twin
        # chain: the first twin builds, seeds, AND joins; the second twin's
        # join fails — every NPC built during the activation must be deleted,
        # including the one that already holds a party binding, and party left
        # unset.
        from dataclasses import replace

        synthetic = replace(
            _live_presets()[_T_ALONE],
            key=_T_PAIR,
            display_name=_T_PAIR_DISPLAY,
            starting_companions=(
                StartingCompanion(_T_TWIN, _T_DECLARED_AFFINITY, _T_RELATIONSHIP),
                StartingCompanion(_T_TWIN2, _T_DECLARED_AFFINITY2, _T_RELATIONSHIP2),
            ),
        )
        _register_probe(self, synthetic)
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
                self._activate(shell, _T_PAIR)
        self.assertTrue(shell.creation_pending)
        self.assertFalse(shell.attributes.has("party"))
        self.assertFalse(ObjectDB.objects.filter(db_key=_T_TWIN_DISPLAY).exists())
        self.assertFalse(ObjectDB.objects.filter(db_key=_T_TWIN2_DISPLAY).exists())
        self.assertEqual(ObjectDB.objects.count(), before_objects)

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_the_auto_leave_recheck_keeps_the_seeded_companion(self):
        from world.rules.affinity import run_auto_leave_recheck

        shell = self._shell("maker-shell-recheck")
        self._activate(shell, _T_HOLDER)
        companion = self._companion_of(shell)
        # The wired auto-leave rule on arrival: the declared seed exceeds
        # the threshold.
        self.assertIsNone(run_auto_leave_recheck(companion, shell))
        self.assertTrue(is_companion(companion, shell))

    @covers_requirement("starting-companions::preset-activation-builds-seeds-and-binds-every-declared-companion-atomically")
    def test_a_name_clash_takes_the_pk_suffix_and_binds_the_right_entity(self):
        # The same-account design case: a player literally named after the
        # partner card's display activates that same card, so activation keeps
        # the display name occupied; the second activation's twin therefore
        # clashes and takes the -{pk} suffix while the party binding still
        # names the real companion.
        first = self._shell(_T_TWIN2_DISPLAY)
        self._activate(first, _T_PARTNER)
        second = self._shell("maker-shell-second")
        self._activate(second, _T_REVERSE)
        own_companion = self._companion_of(first)
        clash_companion = self._companion_of(second)
        # The first player's own twin (built from the porter card) keeps its
        # key untouched; activation renamed the shell to the display it
        # already held, so the partner name stays occupied by the player.
        self.assertEqual(own_companion.key, _T_TWIN_DISPLAY)
        self.assertEqual(first.key, _T_TWIN2_DISPLAY)
        # The second activation's twin wants the display the *player* holds.
        self.assertNotEqual(clash_companion.key, _T_TWIN2_DISPLAY)
        self.assertEqual(
            clash_companion.key, f"{_T_TWIN2_DISPLAY}-{clash_companion.pk}"
        )
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
