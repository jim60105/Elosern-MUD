"""Dream panel wire v4: the canonical scene descriptor and its actor binding.

Change ``unified-dream-rendering``. The dream stage's artwork is the SAME
canonical scene descriptor every other scene surface carries, so the panel's
read model, the shared Python validator (``web/webclient/presentation/
artwork.py``) and the client mirror must agree on one exact fact set at one
schema version. This module proves the production boundary of that agreement:
the presenter's published payload validates under the canonical validator, the
descriptor's field set is exactly the shared vocabulary, the descriptor is bound
to THIS actor's own logical dream subject, and the retired raw-URL shapes are
refused instead of adapted.

v4 publishes the two-stage wish with its working proposal and last change
report, so this module also proves the aggregate envelope: the largest legal
state the applier's budgets admit, carried with every per-field bound at its
own ceiling, still fits the protocol's canonical JSON limit and is accepted by
the shipped client validator.
"""

import json
import subprocess
import unittest
from pathlib import Path
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
from world.narrative import dream_proposal
from world.narrative import dream_session as lifecycle
from world.narrative import dream_surface as surface
from world.narrative.threads import create_thread

_UNSET = object()
REPO_ROOT = Path(__file__).resolve().parents[4]

# The shipped client validator decides acceptance for every payload below: the
# envelope proof is only complete if the client can render what the server
# publishes (same bridge as web/webclient/presentation/tests/test_area_map).
_JS_ACCEPTS = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
try { protocol.validatePanel('dream', 5, payload); process.stdout.write('ok'); }
catch (error) { process.stdout.write('no:' + error.message); }
"""


def _accepted_by_client(payload):
    """('ok' | 'no:<reason>', stderr) for one dream panel payload."""
    result = subprocess.run(
        ["node", "-e", _JS_ACCEPTS],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
        timeout=120,
    )
    return result.stdout.strip(), result.stderr.strip()


def _canonical_bytes(value):
    """The applier's own canonical JSON measure of a proposal or report."""
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _filler_item(index):
    """One bounded, distinct list item at the item bound (worst-case bytes)."""
    prefix = f"{index:02d}："
    return prefix + "念" * (dream_proposal.MAX_ITEM_CHARACTERS - len(prefix))


def _bounded_proposal():
    """The working proposal closest under ``MAX_PROPOSAL_BYTES``."""
    proposal = dream_proposal.empty_proposal()
    proposal["summary"] = "夢" * dream_proposal.MAX_SUMMARY_CHARACTERS
    proposal["requirements"] = [
        {
            "kind": dream_proposal.REQUIREMENT_KINDS[index % len(dream_proposal.REQUIREMENT_KINDS)],
            "text": f"{index:02d}：" + "約" * (dream_proposal.MAX_REQUIREMENT_TEXT - 3),
        }
        for index in range(dream_proposal.MAX_REQUIREMENTS)
    ]
    for field in dream_proposal.LIST_FIELDS:
        index = 0
        while len(proposal[field]) < dream_proposal.MAX_LIST_ITEMS:
            candidate = {**proposal, field: [*proposal[field], _filler_item(index)]}
            try:
                dream_proposal.normalize_proposal(candidate)
            except dream_proposal.ProposalEditError:
                break
            proposal = candidate
            index += 1
    return dream_proposal.normalize_proposal(proposal)


def _bounded_report():
    """The change report closest under ``MAX_CHANGES_BYTES``."""
    report = {
        "summary": "changed",
        "lists": {
            field: {"added": [], "removed": []} for field in dream_proposal.LIST_FIELDS
        },
        "requirements": {"added": [], "removed": []},
    }
    index = 0
    for field in dream_proposal.LIST_FIELDS:
        for half in ("added", "removed"):
            while len(report["lists"][field][half]) < dream_proposal.MAX_LIST_ITEMS:
                candidate = {
                    "summary": report["summary"],
                    "lists": {
                        name: {part: list(entry[part]) for part in ("added", "removed")}
                        for name, entry in report["lists"].items()
                    },
                    "requirements": {
                        part: [dict(row) for row in report["requirements"][part]]
                        for part in ("added", "removed")
                    },
                }
                candidate["lists"][field][half].append(_filler_item(index))
                if _canonical_bytes(candidate) > dream_proposal.MAX_CHANGES_BYTES:
                    break
                report = candidate
                index += 1
    return report


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
        """One real accepted sleeping receipt associated to its owner."""
        from world.rules.sleep_receipt import (
            KIND_VOLUNTARY,
            MODE_DURATION,
            STATE_SLEEPING,
            SleepReceipt,
            write_sleep_receipt,
        )

        sleep_id = "synthetic-artwork-sleep"
        write_sleep_receipt(
            actor,
            SleepReceipt(
                sleep_id=sleep_id,
                body_id=int(actor.pk),
                owner_id=int(actor.pk),
                kind=KIND_VOLUNTARY,
                mode=MODE_DURATION,
                entry_tick=100,
                target_tick=700,
                limit_tick=700,
                settled_through_tick=700,
                revision=0,
                state=STATE_SLEEPING,
                accepted_seconds=600,
                partial=False,
                entry_operation_id=sleep_id,
            ),
        )
        return surface.enter_for_owner(
            actor, sleep_id=sleep_id, revision=0, generation=0
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
    def test_the_dream_panel_ships_the_canonical_descriptor_at_schema_five(self):
        self.entered(self.actor)
        payload = self.render()
        self.assertEqual(payload["schema_version"], DREAM_SCHEMA_VERSION)
        self.assertEqual(DREAM_SCHEMA_VERSION, 5)
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

    def publish_largest_wish(self):
        """Write the largest legal wish and every offered thread label."""
        value = surface.association(self.actor)
        value["proposal"] = _bounded_proposal()
        value["changes"] = _bounded_report()
        value["scene"] = "雲" * 2048
        value["dialogue"] = "夢" * 2048
        self.actor.db.dream_surface = value
        for index in range(32):
            create_thread(
                thread_id=f"synthetic-envelope-thread-{index}",
                origin=f"synthetic-envelope-origin-{index}",
                participants=[str(self.actor.pk)],
                # The offered label ceiling, in the widest UTF-8 encoding.
                factual_summary=f"{index:02d}：" + "線" * 157,
            )

    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_the_largest_legal_wish_fits_the_envelope(self):
        # The aggregate proposal and report budgets are only useful if the
        # largest panel they admit still travels: one byte more in either
        # budget widens this payload past the protocol ceiling.
        self.entered(self.actor)
        self.publish_largest_wish()
        state = self.render()["state"]
        self.assertLessEqual(
            _canonical_bytes(state["proposal"]), dream_proposal.MAX_PROPOSAL_BYTES
        )
        self.assertLessEqual(
            _canonical_bytes(state["changes"]), dream_proposal.MAX_CHANGES_BYTES
        )
        self.assertEqual(len(state["thread_choices"]), 32)
        self.assertEqual(len(state["scene"]), 2048)
        self.assertEqual(len(state["dialogue"]), 2048)
        self.assertEqual(state["stage"], lifecycle.STAGE_CONVERSING)

        open_payload = self.render()
        self.assertLessEqual(json_byte_size(open_payload), MAX_CANONICAL_JSON_BYTES)
        # Schema 5 publishes the wish once (inside the proposal), so the
        # largest legal panel now leaves headroom under the ceiling; the
        # aggregate budgets themselves stay the applier's own bounds.
        verdict, stderr = _accepted_by_client(open_payload)
        self.assertEqual(verdict, "ok", stderr)

        # The same budgets with the conversation closed: the ending replaces the
        # thread choices, and that state still fits and validates.
        session = surface.associated_session(self.actor)
        session.completed_exchanges = lifecycle.MAX_EXCHANGES
        session.stage = lifecycle.STAGE_FINALIZED
        session.state = lifecycle.STATE_ENDED
        session.save(
            update_fields=["completed_exchanges", "stage", "state", "updated_at"]
        )
        closed_payload = self.render()
        closed_state = closed_payload["state"]
        self.assertEqual(closed_state["stage"], lifecycle.STAGE_FINALIZED)
        self.assertTrue(closed_state["ending"])
        self.assertEqual(closed_state["thread_choices"], [])
        self.assertLessEqual(json_byte_size(closed_payload), MAX_CANONICAL_JSON_BYTES)
        verdict, stderr = _accepted_by_client(closed_payload)
        self.assertEqual(verdict, "ok", stderr)

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
