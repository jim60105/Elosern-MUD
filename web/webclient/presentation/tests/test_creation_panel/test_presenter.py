"""Creation panel presenter tests: form and preset-card envelope rendering."""
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.creation import AFFINITY_ELEMENT_KEYS, CREATION_SCHEMA_VERSION, MAX_PROPOSAL_NAME_CODE_POINTS, validate_creation
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, json_byte_size
from web.webclient.presentation.registry import build_production_registry
from world.rules.creation_wizard import ALLOCATABLE_AXES, read_draft
from world.tests.synthetic_data import SYNTH_PRESETS
from ._support import _T_RACE, _T_SUBRACE, _open_t_creation_scope, _shipped_race_affinity, _t_profile_pairs, _t_spend
import unittest


class CreationPanelPresenterTests(EvenniaTest):

    def setUp(self):
        # The wizard build, draft preflight, and activation all resolve
        # through the patched catalogs. Elements stay shipped: the panel
        # validator's affinity element set is captured at import time and
        # custom-mode affinity is an explicit empty set here, so the element
        # mirror claim keeps running against real lore.
        _open_t_creation_scope(self, "skills", "items", "prices")
        handle = patch(
            "web.webclient.presentation.creation._validate_affinity",
            _shipped_race_affinity,
        )
        handle.start()
        self.addCleanup(handle.stop)
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="pending-shell")
        self.account.at_post_create_character(self.character)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.character, protocol_version=1)


    def _render(self):
        return self.registry.render("creation", self.context)


    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_pending_character_receives_the_creation_panel(self):
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "creation")
        self.assertEqual(payload["schema_version"], CREATION_SCHEMA_VERSION)
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), len(SYNTH_PRESETS))
        self.assertEqual(len(payload["custom"]["profiles"]), len(_t_profile_pairs()))
        # The read model is side-effect free: canonical state is unchanged.
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])


    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_panel_sex_descriptor_ships_server_labels_in_vocabulary_order(self):
        payload = self._render()
        self.assertEqual(
            [(option["key"], option["label"]) for option in payload["custom"]["sex"]],
            [("female", "女性"), ("male", "男性"), ("other", "其他")],
        )
        for option in payload["custom"]["sex"]:
            self.assertEqual(set(option), {"key", "label"})


    @covers_requirement("webclient-character-creation-ui::the-server-owns-the-persisted-creation-wizard-draft")
    def test_saved_draft_sex_renders_in_the_panel(self):
        from world.rules.character_creation import CharacterCreationRequest
        from world.rules.creation_wizard import save_custom_draft

        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="性選角色",
                age=20,
                apparent_age=20,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
                sex="female",
            ),
        )
        payload = self._render()
        self.assertEqual(payload["draft"]["sex"], "female")
        # The read model stays side-effect free with the new channel.
        self.assertTrue(self.character.creation_pending)


    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_activated_character_receives_only_the_unavailable_form(self):
        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )
        from world.rules.creation_wizard import save_custom_draft

        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="已啟用角色",
                age=20,
                apparent_age=20,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
            ),
        )
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="已啟用角色",
                age=20,
                apparent_age=20,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
            ),
        )
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("presets", payload)
        self.assertNotIn("custom", payload)
        self.assertNotIn("draft", payload)
        self.assertEqual(payload["reason"]["code"], "creation_unavailable")


    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_combat_character_receives_only_the_unavailable_form(self):
        # A pending shell carries a valid active session record: creation must
        # be unavailable even though the character is still creation-pending.
        room = create_object(Room, key="creation arena")
        monster = create_object(Monster, key="creation goblin")
        self.character.location = room
        self.character.db.active_combat = {
            "session_id": "hostile:1:1",
            "mode": "hostile",
            "room_id": int(room.pk),
            "player_ids": [int(self.character.pk)],
            "enemy_ids": [int(monster.pk)],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("presets", payload)


    def test_corrupt_draft_degrades_only_the_draft_slot(self):
        self.character.creation_draft = {"version": 3, "garbage": True}
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), len(SYNTH_PRESETS))
        self.assertEqual(len(payload["custom"]["profiles"]), len(_t_profile_pairs()))
        # The whole panel remains schema-valid.
        validate_creation(payload)


    def test_semantically_broken_draft_degrades_only_the_draft_slot(self):
        # A draft that is structurally a custom draft but violates the
        # advertised age range (below the 0 minimum) must not take the whole
        # panel unavailable.
        self.character.creation_draft = {
            "version": 2,
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "年輕角色",
            "age": -1,
            "apparent_age": 20,
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "persona": None,
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), len(SYNTH_PRESETS))
        validate_creation(payload)


    def test_saved_draft_round_trips_through_the_presenter(self):
        from world.rules.creation_wizard import save_custom_draft
        from world.rules.character_creation import CharacterCreationRequest

        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="  新角色  ",
                age=20,
                apparent_age=20,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
            ),
        )
        payload = self._render()
        self.assertEqual(payload["draft"]["mode"], "custom")
        self.assertEqual(payload["draft"]["display_name"], "新角色")
        self.assertEqual(payload["draft"]["age"], 20)


    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_slotless_panel_omits_the_proposal_key(self):
        payload = self._render()
        # The key is absent entirely — never present as null.
        self.assertNotIn("proposal", payload)


    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_pending_proposal_renders_with_its_exact_shape(self):
        from web.webclient.presentation.context import ProposalSnapshot

        context = PresentationContext(
            actor=self.character,
            protocol_version=1,
            proposal=ProposalSnapshot(
                revision=3,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
                persona={
                    "personality": "沉穩",
                    "life_story": "來自邊境的小村，靠磨劍維生",
                    "habit": "清晨練劍",
                },
            ),
        )
        payload = self.registry.render("creation", context)
        proposal = payload["proposal"]
        self.assertEqual(
            set(proposal), {"revision", "race", "subrace", "allocations", "persona"}
        )
        self.assertEqual(proposal["revision"], 3)
        self.assertEqual(proposal["persona"]["personality"], "沉穩")
        # Rendering stays read-only: no draft appeared, nothing persisted.
        self.assertIsNone(payload["draft"])
        self.assertIsNone(read_draft(self.character))


    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_snapshot_transient_fill_keys_render_and_absent_ones_omit(self):
        from web.webclient.presentation.context import ProposalSnapshot

        def snapshot(**fill):
            return PresentationContext(
                actor=self.character,
                protocol_version=1,
                proposal=ProposalSnapshot(
                    revision=4,
                    race=_T_RACE,
                    subrace=_T_SUBRACE,
                    allocations=_t_spend(),
                    persona={
                        "personality": "好奇",
                        "life_story": "貓人少女",
                        "habit": "午後打盹",
                    },
                    **fill,
                ),
            )

        carried = self.registry.render("creation", snapshot(
            display_name="咪咪",
            age=20,
            apparent_age=18,
            background="貓婆婆收養的孤女",
            affinity_elements=("fire",),
        ))["proposal"]
        self.assertEqual(carried["display_name"], "咪咪")
        self.assertEqual(carried["age"], 20)
        self.assertEqual(carried["apparent_age"], 18)
        self.assertEqual(carried["background"], "貓婆婆收養的孤女")
        self.assertEqual(carried["affinity_elements"], ["fire"])

        absent = self.registry.render("creation", snapshot())["proposal"]
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, absent)


    def test_snapshot_affinity_is_a_copy_not_a_live_slot_reference(self):
        # The frozen snapshot must survive a later mutation of the source
        # slot: proposal_snapshot deep-copies the affinity list into a tuple.
        from types import SimpleNamespace

        from web.webclient.presentation.ingress import proposal_snapshot

        slot = {
            "owner_actor_id": "1",
            "revision": 1,
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": _t_spend(),
            "persona": {
                "personality": "沉穩",
                "life_story": "來自邊境的小村",
                "habit": "清晨練劍",
            },
            "affinity_elements": ["fire"],
        }
        session = SimpleNamespace(ndb=SimpleNamespace(concept_proposal=slot))
        snapshot = proposal_snapshot(session, SimpleNamespace(pk="1"))
        self.assertIsNotNone(snapshot)
        slot["affinity_elements"].append("water")
        self.assertEqual(snapshot.as_dict()["affinity_elements"], ["fire"])


    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_worst_case_proposal_fits_the_envelope_bound(self):
        # The v3 all-ceilings proposal — three maximum-length persona fields,
        # a maximum background, a maximum display name (four-byte scalars, the
        # true UTF-8 worst case), both ages, and an eight-element affinity
        # set — stays inside the canonical envelope with room to spare.
        from web.webclient.presentation.context import ProposalSnapshot
        from web.webclient.presentation.protocol import json_byte_size

        context = PresentationContext(
            actor=self.character,
            protocol_version=1,
            proposal=ProposalSnapshot(
                revision=9,
                race=_T_RACE,
                subrace=_T_SUBRACE,
                allocations=_t_spend(),
                persona={
                    "personality": "😀" * 600,
                    "life_story": "😀" * 600,
                    "habit": "😀" * 600,
                },
                display_name="😀" * MAX_PROPOSAL_NAME_CODE_POINTS,
                age=10000,
                apparent_age=10000,
                background="😀" * 600,
                affinity_elements=tuple(AFFINITY_ELEMENT_KEYS),
            ),
        )
        payload = self.registry.render("creation", context)
        self.assertEqual(len(payload["proposal"]["persona"]["personality"]), 600)
        # Four-byte scalars make the maximum name a true 256-UTF-8-byte value.
        self.assertEqual(
            json_byte_size("😀" * MAX_PROPOSAL_NAME_CODE_POINTS),
            4 * MAX_PROPOSAL_NAME_CODE_POINTS + 2,
        )
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)


if __name__ == "__main__":
    unittest.main()
