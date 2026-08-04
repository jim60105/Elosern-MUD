"""Evennia-backed tests for the deterministic creation-wizard draft service."""

from unittest.mock import patch
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
    resolve_starting_profile,
)
from world.rules.creation_messages import FALLBACK_CODE, rejection_code
from world.rules.creation_wizard import (
    CUSTOM_STAGE,
    PRESET_STAGE,
    activate_draft,
    clear_draft,
    read_creation_view,
    read_draft,
    save_custom_draft,
    save_preset_draft,
)


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result: dict[str, int] = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds allocatable spans")
    return result


class CreationWizardTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def custom_request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": None,
            "allocations": balanced_allocations("human"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    # -- read model ----------------------------------------------------------

    def test_read_view_derives_presets_and_custom_descriptor_from_registries(self):
        view = read_creation_view(self.character)
        keys = {card.key for card in view.presets}
        self.assertIn("human_wanderer", keys)
        self.assertIn("elf_guardian", keys)
        self.assertEqual(view.custom.name.max_length, 80)
        self.assertEqual(view.custom.adult.age_minimum, 18)
        self.assertEqual(view.custom.adult.apparent_age_minimum, 18)
        race_keys = {race.key for race in view.custom.races}
        self.assertEqual(race_keys, {"human", "beastfolk", "elf"})
        elf = next(race for race in view.custom.races if race.key == "elf")
        self.assertEqual(set(elf.subraces), {"fionnen", "ciaran", "eolas"})
        elf_profile = next(
            profile
            for profile in view.custom.profiles
            if profile.race == "elf" and profile.subrace == "fionnen"
        )
        axes = {axis.axis for axis in elf_profile.axes}
        self.assertEqual(axes, set(ALLOCATABLE_AXES))
        self.assertEqual(elf_profile.budget, resolve_starting_profile("elf", "fionnen").budget)
        self.assertIsNone(view.draft)

    def test_side_effect_free_read_model_including_no_materialized_traits(self):
        from world.rules.clock import get_world_clock, read_world_clock

        save_custom_draft(self.account, self.character, self.custom_request())
        before_pending = self.character.creation_pending
        before_draft = dict(read_draft(self.character))
        before_identity = {
            key: self.character.attributes.get(key)
            for key in ("age", "apparent_age", "race", "subrace")
        }
        before_traits = self.character.traits.all()
        clock_before = read_world_clock()
        tick_before = int(clock_before.tick) if clock_before is not None else None

        view = read_creation_view(self.character)

        self.assertEqual(self.character.creation_pending, before_pending)
        self.assertEqual(read_draft(self.character), before_draft)
        for key, value in before_identity.items():
            self.assertEqual(self.character.attributes.get(key), value)
        self.assertEqual(self.character.traits.all(), before_traits)
        clock_after = read_world_clock()
        self.assertIs(clock_after, clock_before, "the read model must not create the clock")
        if tick_before is not None:
            self.assertEqual(int(clock_after.tick), tick_before)
        self.assertEqual(view.draft["mode"], "custom")
        self.assertEqual(view.draft["display_name"], "新角色")
        for card in view.presets:
            self.assertTrue(card.background.strip())

    # -- preset draft --------------------------------------------------------

    def test_preset_draft_persists_and_survives_reload(self):
        draft = save_preset_draft(self.account, self.character, "human_wanderer")
        self.assertEqual(draft["mode"], "preset")
        self.assertEqual(draft["stage"], PRESET_STAGE)
        self.assertEqual(draft["preset_key"], "human_wanderer")
        self.assertTrue(self.character.creation_pending)
        # The draft is a stored attribute and survives a reload of the object.
        reloaded = PlayerCharacter.objects.get(id=self.character.id)
        self.assertEqual(read_draft(reloaded)["preset_key"], "human_wanderer")
        self.assertEqual(reloaded.creation_pending, True)
        self.assertEqual(reloaded.age, None)

    def test_invalid_preset_rejected_leaving_prior_draft_unchanged(self):
        save_preset_draft(self.account, self.character, "human_wanderer")
        with self.assertRaises(CharacterCreationError) as ctx:
            save_preset_draft(self.account, self.character, "nope")
        self.assertEqual(rejection_code(ctx.exception), "unknown_preset")
        self.assertEqual(read_draft(self.character)["preset_key"], "human_wanderer")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    # -- custom draft --------------------------------------------------------

    @covers_requirement(
        "webclient-character-creation-ui::the-server-owns-the-persisted-creation-wizard-draft",
        "player-character-creation::character-creation-offers-preset-and-custom-modes",
    )
    def test_custom_draft_uses_server_accepted_trimmed_name(self):
        draft = save_custom_draft(self.account, self.character, self.custom_request())
        self.assertEqual(draft["mode"], "custom")
        self.assertEqual(draft["stage"], CUSTOM_STAGE)
        self.assertEqual(draft["display_name"], "新角色")
        self.assertEqual(draft["allocations"], balanced_allocations("human"))
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.traits.all(), [])

    def test_invalid_custom_draft_rejected_without_mutation(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        cases = {
            "underage age": dict(age=17),
            "underage apparent age": dict(apparent_age=17),
            "markup delimiter": dict(display_name="|rbad|n"),
            "unknown race": dict(race="dragon"),
            "incompatible subrace": dict(race="human", subrace="foxkin"),
            "off budget": dict(allocations={
                key: 0 for key in ALLOCATABLE_AXES
            }),
        }
        for label, overrides in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(CharacterCreationError):
                    save_custom_draft(
                        self.account, self.character, self.custom_request(**overrides)
                    )
                self.assertEqual(
                    read_draft(self.character)["display_name"], "新角色",
                    "prior draft must be preserved on a rejected save",
                )
                self.assertEqual(self.character.age, None)
                self.assertTrue(self.character.creation_pending)

    # -- activation ----------------------------------------------------------

    @covers_requirement(
        "webclient-character-creation-ui::the-server-owns-the-persisted-creation-wizard-draft",
        "player-character-creation::character-creation-offers-preset-and-custom-modes",
    )
    def test_activation_clears_draft_atomically(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        result = activate_draft(self.account, self.character, sampler=lambda low, high: low)
        self.assertEqual(result.display_name, "新角色")
        self.assertFalse(self.character.creation_pending)
        self.assertIsNone(read_draft(self.character))
        self.assertFalse(self.character.attributes.has("creation_draft"))
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual(self.character.age, 20)

    def test_activate_without_draft_is_rejected(self):
        with self.assertRaises(CharacterCreationError) as ctx:
            activate_draft(self.account, self.character)
        self.assertEqual(rejection_code(ctx.exception), "no_draft")
        self.assertTrue(self.character.creation_pending)

    def test_draft_clear_failure_rolls_back_the_whole_activation(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        draft_before = dict(read_draft(self.character))

        def fail(stage):
            if stage == "creation_draft":
                raise RuntimeError("injected clear failure")

        with self.assertRaisesRegex(RuntimeError, "injected clear failure"):
            activate_draft(
                self.account, self.character,
                sampler=lambda low, high: low, write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(read_draft(self.character), draft_before)
        self.assertEqual(self.character.key, "creator-shell")
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(self.character.age, None)

    def test_concurrent_activations_apply_exactly_once(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        first = activate_draft(self.account, self.character, sampler=lambda low, high: low)
        self.assertFalse(self.character.creation_pending)
        # A second activation attempt for the same shell must fail its re-check
        # rather than double-applying: the first commit already cleared the
        # draft and flipped pending, so the second has nothing to activate.
        with self.assertRaises(CharacterCreationError) as ctx:
            activate_draft(self.account, self.character)
        self.assertNotEqual(rejection_code(ctx.exception), FALLBACK_CODE)
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.key, first.display_name)
        self.assertEqual(self.character.age, 20)

    def test_activated_elsewhere_with_draft_present_rejects_already_complete(self):
        # A character activated outside the wizard (e.g. the Telnet command)
        # leaves any earlier browser draft behind; a later activate must reject
        # as already complete rather than open a second activation.
        save_custom_draft(self.account, self.character, self.custom_request())
        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )

        activate_player_character(
            self.account, self.character, self.custom_request(),
            sampler=lambda low, high: low,
        )
        self.assertFalse(self.character.creation_pending)
        with self.assertRaises(CharacterCreationError) as ctx:
            activate_draft(self.account, self.character)
        self.assertEqual(rejection_code(ctx.exception), "already_complete")

    def test_activation_rollback_preserves_prior_draft_and_traits(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        draft_before = dict(read_draft(self.character))

        def fail(stage):
            if stage == "traits":
                raise RuntimeError("injected trait failure")

        with self.assertRaisesRegex(RuntimeError, "injected trait failure"):
            activate_draft(
                self.account, self.character,
                sampler=lambda low, high: low, write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(read_draft(self.character), draft_before)
        self.assertEqual(self.character.traits.all(), [])

    def test_preset_activation_uses_the_stored_preset_key(self):
        save_preset_draft(self.account, self.character, "elf_guardian")
        result = activate_draft(self.account, self.character, sampler=lambda low, high: high)
        self.assertEqual(result.race, "elf")
        self.assertEqual(result.display_name, "瑟芮雅")
        self.assertFalse(self.character.creation_pending)
        self.assertIsNone(read_draft(self.character))

    def test_non_wizard_activation_clears_a_stale_draft_atomically(self):
        # The Telnet command activates through ``activate_player_character``
        # directly; a leftover browser draft must be cleared by the SAME atomic
        # activation so no completed character ever retains a draft.
        save_custom_draft(self.account, self.character, self.custom_request())
        from world.rules.character_creation import activate_player_character

        activate_player_character(
            self.account, self.character, self.custom_request(),
            sampler=lambda low, high: low,
        )
        self.assertFalse(self.character.creation_pending)
        self.assertIsNone(read_draft(self.character))
        self.assertFalse(self.character.attributes.has("creation_draft"))

    # -- reset ---------------------------------------------------------------

    def test_reset_is_idempotent(self):
        save_custom_draft(self.account, self.character, self.custom_request())
        clear_draft(self.character)
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        clear_draft(self.character)
        self.assertIsNone(read_draft(self.character))
        # A reset never touches canonical identity or traits.
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.traits.all(), [])

    def test_semantically_invalid_stored_drafts_read_as_none(self):
        # A tampered or corrupt stored draft degrades only the draft slot: the
        # wizard would never persist these, but a hostile DB edit must not take
        # the creation panel unavailable.
        bases = {
            "unknown preset": {
                "version": 1,
                "mode": "preset",
                "stage": "preset_selected",
                "preset_key": "nope",
            },
            "underage age": {
                "version": 1,
                "mode": "custom",
                "stage": "custom_filled",
                "display_name": "角色",
                "age": 17,
                "apparent_age": 20,
                "race": "human",
                "subrace": None,
                "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            },
            "unknown race": {
                "version": 1,
                "mode": "custom",
                "stage": "custom_filled",
                "display_name": "角色",
                "age": 20,
                "apparent_age": 20,
                "race": "dragon",
                "subrace": None,
                "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            },
            "incompatible subrace": {
                "version": 1,
                "mode": "custom",
                "stage": "custom_filled",
                "display_name": "角色",
                "age": 20,
                "apparent_age": 20,
                "race": "human",
                "subrace": "foxkin",
                "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            },
            "wrong axes": {
                "version": 1,
                "mode": "custom",
                "stage": "custom_filled",
                "display_name": "角色",
                "age": 20,
                "apparent_age": 20,
                "race": "human",
                "subrace": None,
                "allocations": {"hp": 0},
            },
            "out of range allocation": {
                "version": 1,
                "mode": "custom",
                "stage": "custom_filled",
                "display_name": "角色",
                "age": 20,
                "apparent_age": 20,
                "race": "human",
                "subrace": None,
                "allocations": {**{axis: 0 for axis in ALLOCATABLE_AXES}, "hp": 20000},
            },
        }
        for label, storage in bases.items():
            with self.subTest(label=label):
                self.character.creation_draft = storage
                self.assertIsNone(read_draft(self.character), label)
                # The canonical surface stays untouched by a corrupt read.
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])


if __name__ == "__main__":
    unittest.main()
