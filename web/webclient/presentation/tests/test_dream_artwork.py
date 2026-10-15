"""Dream panel wire v3: the canonical scene descriptor and its actor binding.

Change ``unified-dream-rendering``. The dream stage's artwork is the SAME
canonical scene descriptor every other scene surface carries, so the panel's
read model, the shared Python validator (``web/webclient/presentation/
artwork.py``) and the client mirror must agree on one exact fact set at one
schema version. This module proves the production boundary of that agreement:
the presenter's published payload validates under the canonical validator, the
descriptor's field set is exactly the shared vocabulary, the descriptor is bound
to THIS actor's own logical dream subject, and the retired raw-URL shapes are
refused instead of adapted.
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from web.webclient.presentation import artwork as artwork_validator
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.dream import DREAM_SCHEMA_VERSION, dream_presenter
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.art import descriptors
from world.narrative import dream_surface as surface

_UNSET = object()


class DreamArtworkWireTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="synthetic dreamer",
            location=self.room1,
        )
        self.other = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="synthetic outsider",
            location=self.room1,
        )
        self.registry = build_production_registry()

    def entered(self, actor):
        """One real accepted zero-duration sleep associating an open session."""
        from server import dream_service as service

        return service.enter_after_sleep(
            actor, tick_from=100, tick_to=100, requested_seconds=0
        )

    def context(self, actor=_UNSET):
        return PresentationContext(
            actor=self.actor if actor is _UNSET else actor, protocol_version=1
        )

    def render(self, actor=_UNSET):
        return self.registry.render("dream", self.context(actor))

    def descriptor(self, actor=_UNSET):
        return self.render(actor)["state"]["scene_art"]

    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_the_dream_panel_ships_the_canonical_descriptor_at_schema_three(self):
        self.entered(self.actor)
        payload = self.render()
        self.assertEqual(payload["schema_version"], DREAM_SCHEMA_VERSION)
        self.assertEqual(DREAM_SCHEMA_VERSION, 3)
        descriptor = payload["state"]["scene_art"]
        # The published descriptor IS valid under the canonical validator: the
        # server read model and the active wire validator agree on one shape.
        self.assertEqual(artwork_validator.validate_artwork(descriptor), descriptor)
        # ...and its fact set is exactly the shared vocabulary every scene
        # surface (and the client's own mirror) accepts — no extra field, no
        # retired flat projection.
        self.assertEqual(set(descriptor), set(artwork_validator.DESCRIPTOR_FIELDS))
        for attempt in descriptor["attempts"]:
            if attempt["type"] == "image":
                self.assertEqual(set(attempt), set(artwork_validator.IMAGE_ATTEMPT_FIELDS))
                self.assertEqual(set(attempt["resource"]), set(artwork_validator.RESOURCE_FIELDS))
                self.assertEqual(
                    set(attempt["resource"]["geometry"]), set(artwork_validator.GEOMETRY_FIELDS)
                )
            else:
                self.assertEqual(set(attempt), set(artwork_validator.FAULT_ATTEMPT_FIELDS))
                self.assertNotIn("resource", attempt)
        if descriptor["terminal"] is not None:
            self.assertEqual(set(descriptor["terminal"]), set(artwork_validator.TERMINAL_FIELDS))
        for entry in descriptor["retention_sources"]:
            self.assertEqual(set(entry), set(artwork_validator.RETENTION_FIELDS))
        # The dream claims no generation and retains nothing: its chain is the
        # optional operator image, the required bundled dream and the terminal.
        self.assertIsNone(descriptor["generation_subject"])
        self.assertIsNone(descriptor["generation_state"])
        self.assertEqual(descriptor["retention_sources"], [])
        # The whole published panel still fits the shared envelope bound.
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)

    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_the_descriptor_is_bound_to_the_actors_own_dream_subject(self):
        self.entered(self.actor)
        self.entered(self.other)
        mine = self.descriptor(self.actor)
        theirs = self.descriptor(self.other)
        # Two owners (and two sessions) are two logical subjects, so a
        # descriptor can never describe more than the surface it belongs to.
        self.assertEqual(mine["subject_id"], surface.scene_subject_id(self.actor))
        self.assertEqual(theirs["subject_id"], surface.scene_subject_id(self.other))
        self.assertNotEqual(mine["subject_id"], theirs["subject_id"])
        self.assertLessEqual(len(mine["subject_id"]), descriptors.MAX_SUBJECT_ID)

        # A structurally valid descriptor naming ANOTHER subject is refused
        # rather than presented as this player's stage.
        with patch("server.dream_service.dream_state", return_value=self.render(self.other)["state"]):
            with self.assertRaises(ProtocolValidationError):
                dream_presenter(self.context(self.actor))
        # The registry degrades that refusal to its own unavailable form, so no
        # client ever receives the refused payload.
        with patch("server.dream_service.dream_state", return_value=self.render(self.other)["state"]):
            refused = self.render(self.actor)
        self.assertFalse(refused["available"])
        self.assertEqual(refused["reason"]["code"], "internal_presenter_error")

    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_the_retired_raw_url_shapes_are_refused(self):
        self.entered(self.actor)
        state = self.render()["state"]
        retired = [
            "/art/official/" + "0" * 64 + "/npc/dream_goddess/dream-throne.webp",
            "",
            None,
        ]
        for value in retired:
            with self.subTest(value=value):
                with patch(
                    "server.dream_service.dream_state",
                    return_value={**state, "scene_art": value},
                ):
                    with self.assertRaises(ProtocolValidationError):
                        dream_presenter(self.context())
        # A malformed fact set (an unbounded source identity, an unknown fault
        # reason) is refused by the same canonical validator.
        malformed = {
            **state,
            "scene_art": {
                **state["scene_art"],
                "attempts": [
                    {
                        "type": "fault",
                        "source_id": "scene.operator:" + "x" * 300,
                        "rank": 30,
                        "reason": "not_a_reason",
                    }
                ],
            },
        }
        with patch("server.dream_service.dream_state", return_value=malformed):
            with self.assertRaises(ProtocolValidationError):
                dream_presenter(self.context())

    def test_an_anonymous_context_is_unavailable(self):
        with self.assertRaises(PanelUnavailableError):
            dream_presenter(self.context(None))

    def test_a_missing_association_publishes_no_state(self):
        # A player who never slept has no dream panel state at all: the panel
        # stays available with a null state, exactly like before the artwork
        # moved onto the shared descriptor.
        payload = self.render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["state"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
