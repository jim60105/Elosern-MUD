"""Creation panel presenter tests: form and preset-card envelope rendering."""
from dataclasses import replace
from pathlib import Path

from django.conf import settings
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.art import official
from world.art.fallback_keys import FALLBACK_EXTENSION
from world.art.gallery import GalleryRecord
from world.art.gallery_fallback import band_key_for
from world.art.official import OfficialCatalog, OfficialContent, OfficialImage
from world.art.store import GalleryJobRecord
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.creation import AFFINITY_ELEMENT_KEYS, CREATION_SCHEMA_VERSION, MAX_PROPOSAL_NAME_CODE_POINTS, validate_creation
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, json_byte_size
from web.webclient.presentation.registry import build_production_registry
from world.rules.creation_wizard import ALLOCATABLE_AXES, read_draft
from world.tests.synthetic_data import SYNTH_PRESETS
from ._support import _T_PRESET, _T_RACE, _T_SUBRACE, _live, _open_t_creation_scope, _shipped_race_affinity, _t_profile_pairs, _t_spend
import unittest
from world.tests.start_room_fixture import stub_start_room


class CreationPanelPresenterTests(EvenniaTest):

    def setUp(self):
        self.enterContext(stub_start_room())
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


    @covers_requirement("webclient-character-creation-ui::creation-resource-and-offense-labels-are-distinguishable")
    def test_creation_profile_axes_distinguish_resource_and_offense_labels(self):
        payload = self._render()
        for profile in payload["custom"]["profiles"]:
            axes_by_key = {ax["axis"]: ax for ax in profile["axes"]}
            if "mp" in axes_by_key and "magic_power" in axes_by_key:
                self.assertTrue(axes_by_key["mp"]["label"].strip())
                self.assertTrue(axes_by_key["magic_power"]["label"].strip())
                self.assertNotEqual(
                    axes_by_key["mp"]["label"],
                    axes_by_key["magic_power"]["label"],
                )
                self.assertNotEqual(
                    axes_by_key["mp"]["explanation"],
                    axes_by_key["magic_power"]["explanation"],
                )


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
            "engagement_id": "hostile:1:1:0",
            "mode": "hostile",
            "room_id": int(room.pk),
            "player_ids": [int(self.character.pk)],
            "enemy_ids": [int(monster.pk)],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "settled_rounds": 0,
            "exam_id": None,
            "started_tick": 0,
            "population_cell": None,
            # The strict record parse requires the draft fields: without them
            # the pending shell reads as out of session.
            "round_revision": 0,
            "draft_version": 0,
            "draft_entries": {},
            "confirmed_actors": [],
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


    # -- creation panel artwork (creation-panel-artwork) -------------------

    def _write_state(self):
        """The creation presenter's mutation surface: DB rows, policy, files."""
        store_root = Path(settings.ART_STORE_ROOT)
        files = (
            sorted(str(path) for path in store_root.rglob("*"))
            if store_root.exists()
            else []
        )
        return (
            GalleryRecord.objects.count(),
            GalleryJobRecord.objects.count(),
            self.character.db.portrait_policy,
            files,
        )

    def _catalog(self, elements):
        contents = {}
        images = {}
        for key, identity, fingerprint in elements:
            image = OfficialImage(
                identity=identity,
                kind="preset",
                key=key,
                fingerprint=fingerprint * 64,
                image_size={"width": 8, "height": 8},
                face_rect={"x": 0.2, "y": 0.1, "w": 0.4, "h": 0.5},
                stage={"scale": 1.25, "x": 0.1, "y": -0.1},
            )
            contents[("preset", key)] = OfficialContent(
                kind="preset",
                key=key,
                default_identity=identity,
                images=(identity,),
            )
            images[identity] = image
        return OfficialCatalog(contents, images)

    def _card(self, payload, key):
        return next(card for card in payload["presets"] if card["key"] == key)


    def test_a_preset_with_official_artwork_offers_only_its_own_default(self):
        identity = f"preset/{_T_PRESET}/hero.png"
        other_identity = "preset/t_ash_finch/other.png"
        catalog = self._catalog(
            [
                (_T_PRESET, identity, "a"),
                ("t_ash_finch", other_identity, "b"),
            ]
        )
        # A stored personal selection must never be consulted by a preview.
        self.character.db.official_selection = other_identity
        before = self._write_state()
        with patch.object(official, "_CATALOG", catalog):
            payload = self._render()
        card = self._card(payload, _T_PRESET)
        artwork = card["artwork"]
        self.assertEqual(artwork["subject_id"], f"creation:preset:{_T_PRESET}")
        self.assertEqual(len(artwork["attempts"]), 1)
        attempt = artwork["attempts"][0]
        resource = attempt["resource"]
        self.assertEqual(attempt["type"], "image")
        self.assertEqual(resource["origin"], "official")
        self.assertEqual(resource["url"], f"/art/official/{'a' * 64}/{identity}")
        self.assertEqual(resource["version"], "a" * 64)
        self.assertEqual(
            resource["geometry"]["face_rect"], {"x": 0.2, "y": 0.1, "w": 0.4, "h": 0.5}
        )
        self.assertEqual(
            resource["geometry"]["stage"], {"scale": 1.25, "x": 0.1, "y": -0.1}
        )
        self.assertNotIn(other_identity, str(artwork))
        self.assertIsNone(artwork["generation_subject"])
        self.assertIsNone(artwork["generation_state"])
        self.assertEqual(artwork["retention_sources"], [])
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        self.assertEqual(artwork["terminal"]["source_id"], "portrait.alpha:woman")
        self.assertEqual(self._write_state(), before)


    def test_a_preset_without_official_artwork_resolves_the_builtin_figure(self):
        before = self._write_state()
        with patch.object(official, "_CATALOG", OfficialCatalog({}, {})):
            payload = self._render()
        female = self._card(payload, _T_PRESET)["artwork"]
        male = self._card(payload, "t_ash_finch")["artwork"]
        self.assertEqual(female["attempts"], [])
        self.assertEqual(male["attempts"], [])
        self.assertEqual(female["terminal"]["source_id"], "portrait.alpha:woman")
        self.assertEqual(male["terminal"]["source_id"], "portrait.alpha:man")
        for artwork in (female, male):
            self.assertIsNone(artwork["generation_subject"])
            self.assertIsNone(artwork["generation_state"])
            self.assertEqual(artwork["retention_sources"], [])
        self.assertEqual(self._write_state(), before)


    def test_a_declared_preset_fallback_key_wins_over_the_band_rule(self):
        registry = _live("world.lore.player_presets", "PLAYER_PRESET_REGISTRY")
        preset = registry[_T_PRESET]
        with patch.dict(
            registry,
            {_T_PRESET: replace(preset, fallback_key="elder")},
            clear=False,
        ):
            with patch.object(official, "_CATALOG", OfficialCatalog({}, {})):
                payload = self._render()
        artwork = self._card(payload, _T_PRESET)["artwork"]
        self.assertEqual(artwork["terminal"]["source_id"], "portrait.alpha:elder")
        self.assertEqual(
            artwork["terminal"]["resource"]["resource_id"],
            f"defaults/elder{FALLBACK_EXTENSION}",
        )


    def test_silhouette_table_is_actor_specific_and_matches_later_resolution(self):
        payload = self._render()
        table = payload["custom"]["silhouettes"]
        self.assertEqual(len(table), 9)
        for entry in table:
            expected = band_key_for(
                f"portrait:character:{self.character.pk}",
                entry["sex"],
                entry["apparent_age_minimum"],
            )
            self.assertEqual(
                entry["artwork"]["terminal"]["source_id"],
                f"portrait.alpha:{expected}",
            )
            self.assertIn(
                f":{self.character.pk}:{entry['sex']}:", entry["artwork"]["subject_id"]
            )
            self.assertEqual(entry["artwork"]["attempts"], [])
        # A second pending character gets its own identity, never a shared
        # cached table.
        other = create_object(PlayerCharacter, key="pending-shell-2")
        self.account.at_post_create_character(other)
        other_payload = self.registry.render(
            "creation", PresentationContext(actor=other, protocol_version=1)
        )
        for entry in other_payload["custom"]["silhouettes"]:
            self.assertIn(f":{other.pk}:{entry['sex']}:", entry["artwork"]["subject_id"])


if __name__ == "__main__":
    unittest.main()
