"""Gallery actions through real records/dispatch, with deterministic offline settlement."""

from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from django.test import override_settings
from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from PIL import Image

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from web.webclient.actions import gallery_actions as actions
from web.webclient.actions.dispatcher import handle_ui_action, _sequence_state
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.gallery_selection import gallery_selection_snapshot
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.protocol import validate_ui_action_result
from web.webclient.presentation.registry import build_production_registry
from world.art import gallery as api
from world.art import official, official_refs
from world.art import queue
from world.art.official import current_catalog, load_catalog, reset_catalog
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.rules.clock import get_world_clock

ROOT = Path(__file__).resolve().parents[4]
SUBJECT = "portrait:character:t_gallery_actor"
IMAGE = "12345678-1234-1234-1234-123456789abc"
OFFICIAL_IDENTITY = "preset/t_gallery_preset/a.png"
PAYLOADS = {
    "gallery.subject.select": {"subject_key": SUBJECT},
    "gallery.generate": {"subject_key": SUBJECT, "fields": ["appearance", "armor"], "custom_prompt": "  測試光影  "},
    "gallery.default.set": {"subject_key": SUBJECT, "image_id": IMAGE},
    "gallery.card.delete": {"subject_key": SUBJECT, "image_id": IMAGE},
    "gallery.face_rect.update": {"subject_key": SUBJECT, "image_id": IMAGE, "face_rect": {"x": 0.125, "y": 0.25, "w": 0.5, "h": 0.5}},
    "gallery.stage.update": {"subject_key": SUBJECT, "image_id": IMAGE, "stage": {"scale": 0.6, "x": -0.2, "y": 0.1}},
    "gallery.binding.save": {"subject_key": SUBJECT, "image_id": IMAGE, "slots": ["accessories", "weapon_off"]},
    "gallery.official.select": {"subject_key": SUBJECT, "identity": OFFICIAL_IDENTITY},
    "gallery.official.clear_selection": {"subject_key": SUBJECT},
    "gallery.official.geometry.set": {
        "subject_key": SUBJECT,
        "identity": OFFICIAL_IDENTITY,
        "face_rect": {"x": 0.125, "y": 0.25, "w": 0.5, "h": 0.5},
    },
    "gallery.official.geometry.clear": {
        "subject_key": SUBJECT,
        "identity": OFFICIAL_IDENTITY,
    },
}


def wire_cases():
    """Boundary corpus shared with Node; outputs must preserve accepted payloads."""
    cases = []
    def add(action, name, changes=None, accepted=False):
        value = deepcopy(PAYLOADS[action])
        if changes:
            changes(value)
        cases.append((name, action, value, accepted))
    for action in PAYLOADS:
        add(action, action, accepted=True)
        add(action, action + " extra", lambda p: p.update(item_key="t_smuggled"))
        add(action, action + " missing", lambda p: p.pop("subject_key"))
        for key in (None, 7, "scene:t_room", "portrait:character:", "portrait:character:a/b", "portrait:character:" + "a" * 65, "portrait:character:" + "𠮷" * 51, "portrait:character:a\u200db"):
            add(action, action + " bad subject " + repr(key), lambda p, key=key: p.update(subject_key=key))
        add(action, action + " key cap", lambda p: p.update(subject_key="portrait:character:" + "𠮷" * 50), True)
        if "image_id" in PAYLOADS[action]:
            for value in (None, True, IMAGE.upper(), IMAGE.replace("-", ""), IMAGE + "\n"):
                add(action, action + " UUID " + repr(value), lambda p, value=value: p.update(image_id=value))
    gen = "gallery.generate"
    for fields in (None, "armor", ["unknown"], ["armor", "armor"], [False], [[]], ["appearance"] * 6):
        add(gen, "fields " + repr(fields), lambda p, fields=fields: p.update(fields=fields))
    add(gen, "empty fields", lambda p: p.update(fields=[]), True)
    add(gen, "all fields reversed", lambda p: p.update(fields=list(reversed(actions.GALLERY_PROMPT_FIELDS))), True)
    for text in (None, 2, "x" * 513, "𠮷" * 513, "a\nb", "a\tb", "a\x00b", "a\u200db", "a\u2028b", "a\u2029b", "a\u00a0b", "a\u3000b", "a\ue000b", "a\u0378b", "\ud800"):
        add(gen, "prompt " + repr(text), lambda p, text=text: p.update(custom_prompt=text))
    for text in ("", "   ", "𠮷" * 512):
        add(gen, "accepted prompt " + repr(text), lambda p, text=text: p.update(custom_prompt=text), True)
    add(gen, "monster capabilities are not schema", lambda p: p.update(subject_key="portrait:monster:t_beast"), True)
    bind = "gallery.binding.save"
    for slots in (None, "armor", [], ["unknown"], ["armor", "armor"], [True], [{}], list(api.SLOT_ORDER) + ["armor"]):
        add(bind, "slots " + repr(slots), lambda p, slots=slots: p.update(slots=slots))
    rect = "gallery.face_rect.update"
    for value in (None, {}, {"x": 0, "y": 0, "w": 1, "h": 1, "z": 0}, {"x": True, "y": 0, "w": 1, "h": 1}, {"x": 0, "y": 0, "w": 0, "h": 1}, {"x": 0.75, "y": 0, "w": 0.5, "h": 1}, {"x": 0, "y": 0.75, "w": 1, "h": 0.5}, {"x": -0.1, "y": 0, "w": 1, "h": 1}):
        add(rect, "rect " + repr(value), lambda p, value=value: p.update(face_rect=value))
    add(rect, "full image", lambda p: p.update(face_rect={"x": 0, "y": 0, "w": 1, "h": 1}), True)
    stage = "gallery.stage.update"
    for value in (None, {}, {"scale": 1, "x": 0, "y": 0, "z": 0}, {"scale": 1, "x": 0}, {"scale": True, "x": 0, "y": 0}, {"scale": "nan", "x": 0, "y": 0}, {"scale": 0.1, "x": 0, "y": 0}, {"scale": 2.5, "x": 0, "y": 0}, {"scale": 1, "x": -0.6, "y": 0}, {"scale": 1, "x": 0, "y": 0.51}):
        add(stage, "stage " + repr(value), lambda p, value=value: p.update(stage=value))
    add(stage, "stage bounds", lambda p: p.update(stage={"scale": 0.2, "x": -0.5, "y": 0.5}), True)
    # The card-reference union: an admitted official identity reaches the
    # adapter (which refuses it with `official_read_only`), while anything
    # neither a uuid nor a valid identity stays an admission failure.
    for action in (
        "gallery.default.set",
        "gallery.card.delete",
        "gallery.face_rect.update",
        "gallery.stage.update",
        "gallery.binding.save",
    ):
        add(action, action + " official identity", lambda p: p.update(image_id=OFFICIAL_IDENTITY), True)
        add(action, action + " bad reference", lambda p: p.update(image_id="preset/bare"))
        add(action, action + " null reference", lambda p: p.update(image_id=None))
    select = "gallery.official.select"
    for identity in (
        None,
        7,
        "",
        "preset/bare",
        "preset/t_gallery_preset",
        "preset/t_gallery_preset/deep/a.png",
        "preset/t_gallery_preset/a.bmp",
        "preset/t_gallery_preset/a",
        "preset/../a.png",
        "preset/t_gallery_preset/a\u200b.png",
        "preset/t_gallery_preset/a\u00a0.png",
        "preset/t_gallery_preset/" + "k" * 200 + ".png",
    ):
        add(select, "identity " + repr(identity), lambda p, identity=identity: p.update(identity=identity))
    add(
        select,
        "identity at cap",
        lambda p: p.update(
            identity="preset/" + "k" * (192 - len("preset/") - len("/a.png")) + "/a.png"
        ),
        True,
    )
    clear = "gallery.official.geometry.clear"
    add(clear, "identity missing", lambda p: p.pop("identity"))
    geometry = "gallery.official.geometry.set"
    def stage_only(payload):
        payload.pop("face_rect", None)
        payload["stage"] = {"scale": 1, "x": 0, "y": 0}
    def neither(payload):
        payload.pop("face_rect", None)
    add(geometry, "geometry stage only", stage_only, True)
    add(geometry, "geometry both", lambda p: p.update(stage={"scale": 1, "x": 0, "y": 0}), True)
    add(geometry, "geometry neither", neither)
    for value in (None, {}, {"x": 0, "y": 0, "w": 0, "h": 1}, {"x": 0.75, "y": 0, "w": 0.5, "h": 1}, {"x": True, "y": 0, "w": 1, "h": 1}, {"x": -0.1, "y": 0, "w": 1, "h": 1}):
        add(geometry, "geometry rect " + repr(value), lambda p, value=value: p.update(face_rect=value))
    for value in (None, {}, {"scale": 3, "x": 0, "y": 0}, {"scale": 1, "x": 0}, {"scale": True, "x": 0, "y": 0}):
        add(geometry, "geometry stage " + repr(value), lambda p, value=value: p.update(stage=value))
    return cases


class GalleryActionWireTests(unittest.TestCase):
    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    def test_python_node_bidirectional_boundaries(self):
        registry = build_production_action_registry()
        cases = wire_cases()
        script = """
const fs = require('node:fs');
const p = require('./web/static/webclient/js/elosern/protocol.js');
const results = JSON.parse(fs.readFileSync(0, 'utf8')).map(([name, action, payload]) => {
  try { return [true, p.validateGalleryActionPayload(action, payload)]; }
  catch (_) { return [false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.run(["node", "-e", script], input=json.dumps(cases), text=True, capture_output=True, cwd=ROOT, check=True)
        for (name, action, payload, expected), (accepted, echoed) in zip(cases, json.loads(output.stdout), strict=True):
            with self.subTest(case=name):
                validator = registry.spec(action).validate_payload
                if expected:
                    self.assertEqual(validator(payload), payload)
                    self.assertTrue(accepted)
                    self.assertEqual(validator(echoed), payload)
                else:
                    with self.assertRaises(ValueError):
                        validator(payload)
                    self.assertFalse(accepted)

    def test_nonfinite_rectangles_reject_without_json_coercion(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            payload = deepcopy(PAYLOADS["gallery.face_rect.update"])
            payload["face_rect"]["x"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                actions.validate_gallery_face_rect_update_payload(payload)
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
const p = require('./web/static/webclient/js/elosern/protocol.js');
for (const x of [NaN, Infinity, -Infinity]) assert.throws(() => p.validateGalleryActionPayload(
  'gallery.face_rect.update', {subject_key: 'portrait:character:t_test',
  image_id: '12345678-1234-1234-1234-123456789abc', face_rect: {x, y: 0, w: 1, h: 1}}));
"""], cwd=ROOT, check=True)

class GalleryActionIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        get_world_clock()
        self.actor = self.character(PlayerCharacter, "t_gallery_actor")
        self.companion = self.character(NPC, "t_gallery_companion")
        self.companion.db.party_member = self.actor.pk
        self.actor.db.party = [self.companion.pk]
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_actor")
        self.companion_subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_companion")
        self.monster_subject = ArtSubject(ArtSubjectKind.MONSTER, "t_beast")
        tiers = {"t_beast": SimpleNamespace(display_name_zh="測試魔物", description="測試用魔物", example_monsters_zh=("測試獸",))}
        for target in ("web.webclient.presentation.gallery.MONSTER_TIER_REGISTRY", "world.art.subjects.MONSTER_TIER_REGISTRY"):
            patcher = patch(target, tiers)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        self.sent = []
        self.transport = SimpleNamespace(ndb=SimpleNamespace(), puppet=self.actor, protocol_key="websocket", msg=lambda **kwargs: self.sent.append(kwargs))
        self.coordinator = attach_coordinator(self.transport, self.registry)
        self.serial = 0

    def character(self, cls, stable_key):
        entity = create_object(cls, key="測試角色", location=self.room1)
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        entity.db.age = entity.db.apparent_age = 25
        return entity

    def card(self, number=1, subject=None):
        subject = subject or self.subject
        image_id = str(uuid.UUID(int=number))
        directory = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        identity = f"gallery/{directory}/{subject.key}/{image_id}.png"
        path = self.root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic-image")
        return api.append_card(subject, image_id=image_id, stored_identity=identity,
            prompt={"positive": "test prompt", "negative": "test negative"}, seed=7,
            checkpoint="test-checkpoint", requested_fields=[], binding=None,
            image_size={"width": 768, "height": 1024},
            source="generated", created_at=100 + number)

    def envelope(self, action, payload, request_id=None):
        self.serial += 1
        return {"protocol_version": 1, "presentation_epoch": self.coordinator.epoch,
            "request_id": request_id or f"g{self.serial}", "base_revision": self.coordinator.revision,
            "action_id": action, "payload": payload}

    def dispatch(self, action, payload, *, envelope=None):
        self.sent.clear()
        handle_ui_action(self.transport, self.actor, envelope or self.envelope(action, payload), self.action_registry, self.registry)
        result = self.sent[-1]["ui_action_result"][0][0]
        validate_ui_action_result(result)
        return result

    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    def test_all_seven_actions_declare_uniform_affected_panels_registered_in_production(self):
        self.assertEqual(actions.AFFECTED_GALLERY_PANELS, ("gallery", "art", "roster"))
        registry = build_production_registry()
        for name in actions.AFFECTED_GALLERY_PANELS:
            self.assertIn(name, registry.panel_names)
        card = self.card()
        pair = {"subject_key": SUBJECT, "image_id": card["image_id"]}
        operations = [
            ("gallery.subject.select", {"subject_key": SUBJECT}),
            ("gallery.generate", {"subject_key": SUBJECT, "fields": [], "custom_prompt": ""}),
            ("gallery.default.set", pair),
            ("gallery.face_rect.update", dict(pair, face_rect={"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.3})),
            ("gallery.stage.update", dict(pair, stage={"scale": 0.6, "x": -0.2, "y": 0})),
            ("gallery.binding.save", dict(pair, slots=["armor"])),
            ("gallery.card.delete", pair),
        ]
        for action, payload in operations:
            with self.subTest(action=action):
                spec = self.action_registry.spec(action)
                adapter = spec.adapter
                res = adapter(self.actor, payload, self.transport)
                self.assertEqual(res["affected_panels"], actions.AFFECTED_GALLERY_PANELS)
                self.assertEqual(res["outcome"], "success")
                rej = adapter(self.actor, dict(payload, subject_key="portrait:character:t_absent"), self.transport)
                self.assertEqual(rej["affected_panels"], actions.AFFECTED_GALLERY_PANELS)
                self.assertEqual(rej["outcome"], "rejected")

    def panel(self):
        updates = [call["ui_update"][0][0] for call in self.sent if "ui_update" in call]
        self.assertEqual(len(updates), 1)
        self.assertNotIn("ui_snapshot", self.sent[0])
        self.assertEqual(set(updates[0]["panels"]), {"gallery", "art", "roster"})
        self.assertEqual(updates[0]["revision"], self.sent[-1]["ui_action_result"][0][0]["presentation_revision"])
        return updates[0]["panels"]["gallery"]

    def generate(self, subject=None, **changes):
        payload = {"subject_key": (subject or self.subject).full(), "fields": [], "custom_prompt": ""}
        payload.update(changes)
        return self.dispatch("gallery.generate", payload)

    def settle(self, subject, image_id):
        jobs = queue.claim(10)
        job = next(job for job in jobs if job.db.gallery_image_id == image_id)
        directory = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        identity = f"gallery/{directory}/{subject.key}/{image_id}.png"
        path = self.root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(b"fake-offline-worker-image")
        # decoded size 768x1024
        return queue.settle_gallery_generated(job.key, generation_token=job.db.generation_token,
            output_identity=identity, tmp_path=str(tmp),
            prompt={"positive": "settled", "negative": "negative"},
            seed=42, checkpoint=None,
            image_size={"width": 768, "height": 1024})

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer",
        "webclient-gallery-management-actions::subject-selection-writes-only-session-presentation-state",
    )
    def test_selection_publishes_once_without_art_mutation_and_retires_on_unpuppet(self):
        self.card()
        self.generate(self.companion_subject)
        def art_state():
            return [
                [(record.pk, {attribute.key: deepcopy(attribute.value) for attribute in record.attributes.all()})
                 for record in model.objects.order_by("pk")]
                for model in (api.GalleryRecord, ArtAssetRecord)
            ]
        before = art_state()
        with patch.object(actions, "log_info") as info, patch.object(actions, "log_warn") as warn:
            result = self.dispatch("gallery.subject.select", {"subject_key": self.companion_subject.full()})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(self.panel()["selected"], self.companion_subject.full())
        self.assertEqual(before, art_state())
        self.assertIsNone(api.record_for(self.companion_subject))
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args, ("gallery_action",))
        warn.assert_not_called()
        SIGNAL_OBJECT_POST_UNPUPPET.send(sender=self.actor, session=self.transport, account=self.account)
        self.assertIsNone(gallery_selection_snapshot(self.transport, self.actor))
        self.assertIsNone(self.transport.ndb.gallery_selection)

    def test_unknown_selection_preserves_store_and_reports_unknown_subject(self):
        self.dispatch("gallery.subject.select", {"subject_key": self.companion_subject.full()})
        result = self.dispatch("gallery.subject.select", {"subject_key": "portrait:character:t_absent"})
        self.assertEqual(result["code"], "unknown_subject")
        self.assertEqual(self.panel()["selected"], self.companion_subject.full())

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache",
        "webclient-gallery-management-actions::generation-routes-one-request-through-the-service-seam",
    )
    def test_generation_pending_and_completed_request_dedupe(self):
        payload = dict(PAYLOADS["gallery.generate"])
        envelope = self.envelope("gallery.generate", payload)
        with patch.object(actions, "request_gallery_image", wraps=actions.request_gallery_image) as request:
            first = self.dispatch("gallery.generate", payload, envelope=envelope)
            self.assertEqual(first["outcome"], "success")
            image = first["data"]["image_id"]
            self.assertEqual([(row["image_id"], row["status"]) for row in self.panel()["cards"]], [(image, "pending")])
            duplicate = self.dispatch("gallery.generate", payload, envelope=envelope)
            self.assertEqual(duplicate, first)
            self.assertEqual(len(self.sent), 1)
            request.assert_called_once()
        second = self.generate()
        self.assertNotEqual(image, second["data"]["image_id"])
        self.assertEqual(len(queue.pending_gallery_jobs(self.subject)), 2)

    @covers_requirement("art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity")
    def test_companion_generation_reaches_age_gate_and_settles_real_card(self):
        self.companion.attributes.remove("age")
        self.assertEqual(self.generate(self.companion_subject)["code"], "subject_ineligible")
        self.assertEqual(queue.pending_gallery_jobs(self.companion_subject), [])
        self.companion.db.age = 25
        result = self.generate(self.companion_subject, fields=["armor", "appearance"], custom_prompt="   光影   ")
        self.assertEqual(result["outcome"], "success")
        stored = self.settle(self.companion_subject, result["data"]["image_id"])
        self.assertEqual(stored["requested_fields"], ["appearance", "armor"])
        self.assertEqual(stored["image_id"], result["data"]["image_id"])
        self.assertEqual(stored["seed"], 42)
        self.assertEqual(queue.pending_gallery_jobs(self.companion_subject), [])
        self.assertIsNone(api.record_for(self.subject))

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer",
        "webclient-gallery-management-actions::face-rect-save-stores-the-validated-rect-verbatim",
    )
    def test_face_rect_changes_only_placement_and_never_file_or_provenance(self):
        first = self.card()
        second = self.card(2)
        # On 768x1024: w=0.4 => h=0.3
        rect = {"x": 0.1, "y": 0.2, "w": 0.4, "h": 0.3}
        image_path = self.root / first["stored_identity"]
        before_stat = image_path.stat()
        result = self.dispatch("gallery.face_rect.update", {"subject_key": SUBJECT, "image_id": first["image_id"], "face_rect": rect})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(api.cards_for(self.subject), [dict(first, face_rect=rect), second])
        self.assertEqual(image_path.stat(), before_stat)
        self.assertEqual(image_path.read_bytes(), b"synthetic-image")
        self.assertEqual(len(list(self.root.rglob("*.png"))), 2)
        self.assertEqual(next(row for row in self.panel()["cards"] if row["image_id"] == first["image_id"])["face_rect"], rect)

    @covers_requirement(
        "art-gallery-model::a-face-rect-update-is-checked-against-the-card-s-recorded-image-size"
    )
    def test_non_square_face_rect_update_is_rejected(self):
        first = self.card()
        non_square = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
        result = self.dispatch("gallery.face_rect.update", {"subject_key": SUBJECT, "image_id": first["image_id"], "face_rect": non_square})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "gallery_rejected")
        self.assertEqual(result["message"], "無法更新這張肖像。")

    @covers_requirement(
        "webclient-gallery-management-actions::stage-save-accepts-one-exact-triple-and-preserves-gallery-publication-discipline"
    )
    def test_stage_save_stores_verbatim_publishes_and_replays_idempotently(self):
        first = self.card()
        second = self.card(2)
        triple = {"scale": 0.6, "x": 0.1, "y": -0.2}
        payload = {"subject_key": SUBJECT, "image_id": first["image_id"], "stage": triple}
        envelope = self.envelope("gallery.stage.update", payload)
        with patch.object(actions, "log_info") as info, patch("world.art.gallery.log_info") as service_info:
            result = self.dispatch("gallery.stage.update", payload, envelope=envelope)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "gallery_stage_updated")
        # Stored verbatim: the triple lands unchanged and siblings, default,
        # provenance and order survive the atomic replacement.
        self.assertEqual(
            api.cards_for(self.subject),
            [dict(first, stage=triple), second],
        )
        # The committed fact reaches the gallery presentation for the editor's
        # revision-correlated close gate.
        row = next(r for r in self.panel()["cards"] if r["image_id"] == first["image_id"])
        self.assertEqual(row["stage"], triple)
        self.assertIn(
            "gallery_stage_set",
            [call.args[0] for call in service_info.call_args_list if call.args],
        )
        # Replaying the same envelope is idempotent: one send, no re-write.
        self.assertEqual(self.dispatch("gallery.stage.update", payload, envelope=envelope), result)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(api.cards_for(self.subject), [dict(first, stage=triple), second])
        # An unknown card never mutates anything and speaks the ladder message.
        with patch.object(actions, "log_warn") as warn:
            missing = self.dispatch("gallery.stage.update", {"subject_key": SUBJECT, "image_id": IMAGE, "stage": {"scale": 1, "x": 0, "y": 0}})
        self.assertEqual(missing["outcome"], "rejected")
        self.assertEqual(missing["code"], "unknown_card")
        self.assertEqual(api.cards_for(self.subject), [dict(first, stage=triple), second])
        warn.assert_called_once()

    @covers_requirement(
        "art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots",
        "webclient-gallery-management-actions::binding-save-captures-the-current-snapshot-and-never-accepts-item-keys",
    )
    def test_binding_uses_companion_current_equipment_and_declared_order(self):
        card = self.card(subject=self.companion_subject)
        self.actor.db.equipment = {"armor": "t_actor_coat"}
        self.companion.db.equipment = {"armor": "t_old_coat"}
        payload = {"subject_key": self.companion_subject.full(), "image_id": card["image_id"], "slots": ["accessories", "armor", "weapon_off"]}
        self.companion.db.equipment = {"armor": "t_current_coat", "accessories": ["t_ring_z", "t_ring_a"]}
        result = self.dispatch("gallery.binding.save", payload)
        self.assertEqual(result["outcome"], "success")
        expected = {"mask": ["weapon_off", "armor", "accessories"], "snapshot": {"weapon_off": None, "armor": "t_current_coat", "accessories": ["t_ring_a", "t_ring_z"]}}
        self.assertEqual(api.cards_for(self.companion_subject), [dict(card, binding=expected)])
        self.companion.attributes.remove("equipment")
        self.assertEqual(self.dispatch("gallery.binding.save", payload)["outcome"], "success")
        self.assertEqual(api.cards_for(self.companion_subject)[0]["binding"]["snapshot"], {"weapon_off": None, "armor": None, "accessories": []})
        self.assertFalse(self.companion.attributes.has("equipment"))

    @covers_requirement(
        "art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles",
        "webclient-gallery-management-actions::default-set-and-card-delete-follow-the-shipped-delete-never-dangles-contract",
    )
    def test_default_delete_never_dangles_and_fresh_delete_refuses(self):
        first, second = self.card(), self.card(2)
        pair = {"subject_key": SUBJECT, "image_id": second["image_id"]}
        with patch.object(actions, "log_info") as info, patch("world.art.gallery.log_info") as service_info:
            self.assertEqual(self.dispatch("gallery.default.set", pair)["outcome"], "success")
        self.assertEqual(api.record_for(self.subject).db.default_image_id, second["image_id"])
        info.assert_called_once_with("gallery_action", context={"subject": SUBJECT, "action_id": "gallery.default.set", "image_id": second["image_id"], "kind": "portrait:character"})
        self.assertIn("gallery_default_set", [call.args[0] for call in service_info.call_args_list])
        envelope = self.envelope("gallery.card.delete", pair)
        deleted = self.dispatch("gallery.card.delete", pair, envelope=envelope)
        self.assertEqual(deleted["outcome"], "success")
        self.assertIsNone(api.record_for(self.subject).db.default_image_id)
        self.assertEqual(api.cards_for(self.subject), [first])
        self.assertFalse((self.root / second["stored_identity"]).exists())
        self.assertTrue((self.root / first["stored_identity"]).exists())
        self.assertFalse(any(row["is_default"] for row in self.panel()["cards"]))
        self.assertEqual(self.dispatch("gallery.card.delete", pair, envelope=envelope), deleted)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.dispatch("gallery.card.delete", pair)["code"], "unknown_card")
        self.panel()
        self.assertEqual(self.dispatch("gallery.card.delete", {"subject_key": SUBJECT, "image_id": first["image_id"]})["outcome"], "success")
        self.assertEqual(self.panel()["cards"], [])
        self.assertIsNone(api.record_for(self.subject).db.default_image_id)

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_monster_capability_refusals_and_offline_replacement(self):
        old = self.card(subject=self.monster_subject)
        self.dispatch("gallery.subject.select", {"subject_key": self.monster_subject.full()})
        self.assertEqual(self.generate(self.monster_subject, fields=["appearance"])["code"], "field_selection_unsupported")
        self.assertEqual(self.generate(self.monster_subject, custom_prompt="光影")["code"], "free_text_unsupported")
        for image in (old["image_id"], IMAGE):
            self.assertEqual(self.dispatch("gallery.binding.save", {"subject_key": self.monster_subject.full(), "image_id": image, "slots": ["armor"]})["code"], "binding_unsupported")
        self.assertEqual(queue.pending_gallery_jobs(self.monster_subject), [])
        result = self.generate(self.monster_subject, custom_prompt="   ")
        self.assertEqual(result["outcome"], "success")
        new = self.settle(self.monster_subject, result["data"]["image_id"])
        self.assertEqual(api.cards_for(self.monster_subject), [new])
        self.assertFalse((self.root / old["stored_identity"]).exists())
        self.assertEqual(self.dispatch("gallery.subject.select", {"subject_key": self.monster_subject.full()})["outcome"], "success")
        panel = self.panel()
        self.assertEqual([(row["image_id"], row["status"]) for row in panel["cards"]], [(new["image_id"], "card")])
        self.assertFalse(panel["capabilities"]["supports_bindings"])
        self.assertEqual(panel["filters"]["pending"], 0)
        pair = {"subject_key": self.monster_subject.full(), "image_id": new["image_id"]}
        self.assertEqual(self.dispatch("gallery.default.set", pair)["outcome"], "success")
        self.assertEqual(api.record_for(self.monster_subject).db.default_image_id, new["image_id"])
        self.assertEqual(self.dispatch("gallery.card.delete", pair)["outcome"], "success")
        self.assertEqual(self.panel()["cards"], [])
        self.assertIsNone(api.record_for(self.monster_subject).db.default_image_id)

    def test_missing_and_deleted_subjects_never_mutate_cards(self):
        card = self.card(subject=self.companion_subject)
        self.companion.delete()
        for key in (self.companion_subject.full(), "portrait:character:t_unknown", "portrait:monster:t_unknown"):
            with self.subTest(subject=key):
                self.assertEqual(self.dispatch("gallery.default.set", {"subject_key": key, "image_id": card["image_id"]})["code"], "unknown_subject")
        self.assertEqual(api.cards_for(self.companion_subject), [card])

    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    def test_malformed_payloads_never_reach_adapter_or_create_state(self):
        before = (api.GalleryRecord.objects.count(), ArtAssetRecord.objects.count())
        for name, action, payload, accepted in wire_cases():
            if accepted or "\\ud800" in repr(payload):
                continue  # lone surrogate is an envelope rejection, tested by wire parity
            with self.subTest(case=name), patch.object(actions, "_mutate") as mutate, patch.object(actions, "select_gallery_subject") as select:
                result = self.dispatch(action, payload)
                self.assertEqual(result["code"], "malformed_payload")
                mutate.assert_not_called()
                select.assert_not_called()
                self.assertEqual(len(self.sent), 1)
        self.assertEqual(before, (api.GalleryRecord.objects.count(), ArtAssetRecord.objects.count()))

    def test_defensive_domain_error_mapping_is_bounded_and_logs_once(self):
        card = self.card()
        cases = [
            (actions._gallery_generate_adapter, {"subject_key": SUBJECT, "fields": ["unknown"], "custom_prompt": ""}, "unknown_field"),
            (actions._gallery_generate_adapter, {"subject_key": SUBJECT, "fields": [], "custom_prompt": "x" * 513}, "prompt_too_long"),
            (actions._gallery_generate_adapter, {"subject_key": SUBJECT, "fields": [], "custom_prompt": "bad\nline"}, "invalid_prompt"),
            (actions._gallery_face_rect_update_adapter, {"subject_key": SUBJECT, "image_id": card["image_id"], "face_rect": {"x": 0, "y": 0, "w": 0, "h": 1}}, "gallery_rejected"),
        ]
        for adapter, payload, code in cases:
            with self.subTest(code=code), patch.object(actions, "log_warn") as warn, patch.object(actions, "log_info") as info:
                result = adapter(self.actor, payload, self.transport)
                self.assertEqual(result["code"], code)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["affected_panels"], ("gallery", "art", "roster"))
                self.assertLessEqual(len(result["message"]), 64)
                self.assertNotIn("bad", result["message"])
                warn.assert_called_once()
                self.assertEqual(warn.call_args.args, ("gallery_action",))
                self.assertIn("exc", warn.call_args.kwargs)
                info.assert_not_called()
        self.assertEqual(api.cards_for(self.subject), [card])
        self.assertEqual(queue.pending_gallery_jobs(self.subject), [])

    def test_busy_and_stale_requests_do_not_generate(self):
        payload = {"subject_key": SUBJECT, "fields": [], "custom_prompt": ""}
        stale = self.envelope("gallery.generate", payload)
        stale["base_revision"] += 1
        self.assertEqual(self.dispatch("gallery.generate", payload, envelope=stale)["outcome"], "stale")
        state = _sequence_state(self.transport)
        state.in_flight = True
        try:
            self.assertEqual(self.dispatch("gallery.generate", payload)["code"], "busy")
        finally:
            state.in_flight = False
        self.assertEqual(queue.pending_gallery_jobs(self.subject), [])

    @covers_requirement(
        "webclient-gallery-management-actions::every-management-mutation-emits-one-facade-event"
    )
    def test_each_completed_adapter_emits_one_gallery_event(self):
        card = self.card()
        pair = {"subject_key": SUBJECT, "image_id": card["image_id"]}
        operations = [
            ("gallery.subject.select", {"subject_key": SUBJECT}),
            ("gallery.generate", {"subject_key": SUBJECT, "fields": [], "custom_prompt": ""}),
            ("gallery.default.set", pair),
            ("gallery.face_rect.update", dict(pair, face_rect={"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.3})),
            ("gallery.binding.save", dict(pair, slots=["armor"])),
            ("gallery.card.delete", pair),
        ]
        for action, payload in operations:
            with self.subTest(action=action), patch.object(actions, "log_info") as info, patch.object(actions, "log_warn") as warn:
                result = self.dispatch(action, payload)
                self.assertEqual(result["outcome"], "success")
                updates = [call["ui_update"][0][0] for call in self.sent if "ui_update" in call]
                self.assertEqual(len(updates), 1)
                self.assertNotIn("ui_snapshot", self.sent[0])
                self.assertEqual(set(updates[0]["panels"].keys()), {"gallery", "art", "roster"})
                self.assertEqual(updates[0]["revision"], result["presentation_revision"])
                self.assertEqual(info.call_count, 1)
                self.assertEqual(info.call_args.args, ("gallery_action",))
                context = info.call_args.kwargs["context"]
                self.assertEqual(context["subject"], SUBJECT)
                self.assertEqual(context["action_id"], action)
                self.assertEqual(context["kind"], "portrait:character")
                self.assertEqual(context["image_id"], result.get("data", {}).get("image_id", payload.get("image_id")))
                warn.assert_not_called()
            with self.subTest(rejection=action), patch.object(actions, "log_info") as info, patch.object(actions, "log_warn") as warn:
                result = self.dispatch(action, dict(payload, subject_key="portrait:character:t_absent"))
                self.assertEqual(result["code"], "unknown_subject")
                self.assertEqual(warn.call_count, 1)
                self.assertEqual(warn.call_args.args, ("gallery_action",))
                self.assertEqual(warn.call_args.kwargs["context"]["action_id"], action)
                info.assert_not_called()


_PRESET_KEY = "t_gallery_preset"
_OTHER_PRESET_KEY = "t_gallery_other"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class OfficialPreferenceActionTests(EvenniaTest):
    """The four personal official-art preference adapters (tasks 3.2, 3.3).

    The actor is preset-born, so its content reference is the indexed
    ``preset/t_gallery_preset/`` directory; every request goes through the real
    dispatcher, so the refusal, publication, and idempotency contracts are
    exercised end to end.
    """

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / "store"
        self.store.mkdir()
        self.official_root = Path(self.tmp.name).resolve() / "official"
        settings = override_settings(
            ART_STORE_ROOT=str(self.store), ART_OFFICIAL_ROOT=str(self.official_root)
        )
        settings.enable()
        self.addCleanup(settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        for patcher in (
            patch.object(
                official_refs,
                "PLAYER_PRESET_REGISTRY",
                {_PRESET_KEY: object(), _OTHER_PRESET_KEY: object()},
            ),
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY, _OTHER_PRESET_KEY}),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        get_world_clock()
        self.actor = self._character("t_gallery_actor", _PRESET_KEY)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_actor")
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        self.sent = []
        self.transport = SimpleNamespace(
            ndb=SimpleNamespace(),
            puppet=self.actor,
            protocol_key="websocket",
            msg=lambda **kwargs: self.sent.append(kwargs),
        )
        self.coordinator = attach_coordinator(self.transport, self.registry)
        self.serial = 0

    # -- harness ----------------------------------------------------------
    def _character(self, stable_key, preset_key=None):
        entity = create_object(PlayerCharacter, key="測試角色", location=self.room1)
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        entity.db.age = entity.db.apparent_age = 25
        if preset_key is not None:
            entity.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, preset_key)
        return entity

    def _index(self, name="a.png", key=_PRESET_KEY, **manifest) -> str:
        folder = self.official_root / "preset" / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png())
        manifest_path = folder / "manifest.json"
        if manifest:
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        elif manifest_path.exists():
            manifest_path.unlink()
        load_catalog()
        return f"preset/{key}/{name}"

    def _card(self, number=1):
        image_id = str(uuid.UUID(int=number))
        identity = f"gallery/character/{self.subject.key}/{image_id}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"runtime-image")
        return api.append_card(
            self.subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
            created_at=100,
            image_size={"width": 768, "height": 1024},
        )

    def _envelope(self, action, payload, request_id=None):
        self.serial += 1
        return {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": request_id or f"o{self.serial}",
            "base_revision": self.coordinator.revision,
            "action_id": action,
            "payload": payload,
        }

    def _dispatch(self, action, payload, *, envelope=None):
        self.sent.clear()
        handle_ui_action(
            self.transport,
            self.actor,
            envelope or self._envelope(action, payload),
            self.action_registry,
            self.registry,
        )
        result = self.sent[-1]["ui_action_result"][0][0]
        validate_ui_action_result(result)
        return result

    def _panel(self):
        updates = [call["ui_update"][0][0] for call in self.sent if "ui_update" in call]
        self.assertEqual(len(updates), 1)
        self.assertNotIn("ui_snapshot", self.sent[0])
        self.assertEqual(set(updates[0]["panels"]), {"gallery", "art", "roster"})
        return updates[0]["panels"]["gallery"]

    def _world(self):
        """Every byte and every record the refusal must leave untouched."""
        return (
            {
                path.relative_to(self.official_root).as_posix(): path.read_bytes()
                for path in self.official_root.rglob("*")
                if path.is_file()
            },
            {
                path.relative_to(self.store).as_posix(): path.read_bytes()
                for path in self.store.rglob("*")
                if path.is_file()
            },
            [
                (record.pk, repr(record.attributes.all()))
                for record in api.GalleryRecord.objects.order_by("pk")
            ],
            [
                (record.pk, record.db.status)
                for record in ArtAssetRecord.objects.order_by("pk")
            ],
        )

    # -- the four preference adapters -------------------------------------
    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    @covers_requirement(
        "webclient-gallery-management-actions::personal-official-selection-and-override-adapters-reject-official-file-mutation-authoritatively"
    )
    def test_each_preference_adapter_writes_only_the_preference_and_publishes_once(self):
        identity = self._index("a.png")
        rect = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
        stage = {"scale": 0.6, "x": 0.0, "y": -0.2}
        operations = (
            (
                "gallery.official.select",
                {"subject_key": SUBJECT, "identity": identity},
                "gallery_official_selected",
            ),
            (
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "stage": dict(stage)},
                "gallery_official_geometry_set",
            ),
            (
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "face_rect": dict(rect)},
                "gallery_official_geometry_set",
            ),
            (
                "gallery.official.geometry.clear",
                {"subject_key": SUBJECT, "identity": identity},
                "gallery_official_geometry_cleared",
            ),
            (
                "gallery.official.clear_selection",
                {"subject_key": SUBJECT},
                "gallery_official_selection_cleared",
            ),
        )
        card = self._card()
        official_before = {
            path: path.read_bytes()
            for path in (self.official_root / "preset" / _PRESET_KEY).iterdir()
        }
        for action, payload, code in operations:
            with self.subTest(action=action), patch.object(
                actions, "log_info"
            ) as info, patch.object(actions, "log_warn") as warn:
                result = self._dispatch(action, payload)
                self.assertEqual(result["outcome"], "success")
                self.assertEqual(result["code"], code)
                # The adapter published its three declared panels before the
                # result (the wire envelope carries no affected-panel list).
                panel = self._panel()
                self.assertEqual(panel["selected"], SUBJECT)
                self.assertEqual(
                    [row["image_id"] for row in panel["cards"]], [card["image_id"]]
                )
                self.assertEqual(len(panel["official_entries"]), 1)
                self.assertEqual(
                    panel["official_entries"][0]["identity"], identity
                )
                self.assertEqual(info.call_count, 1)
                self.assertEqual(info.call_args.args, ("gallery_action",))
                self.assertEqual(info.call_args.kwargs["context"]["action_id"], action)
                # The event names the identity whenever the payload carries one.
                if "identity" in payload:
                    self.assertEqual(
                        info.call_args.kwargs["context"]["identity"],
                        payload["identity"],
                    )
                else:
                    self.assertNotIn("identity", info.call_args.kwargs["context"])
                warn.assert_not_called()
        # The writes landed exactly as the payloads declared: the face edit kept
        # the stored stage, and the stage edit kept the stored rectangle.
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry, {}
        )
        self.assertIsNone(api.official_preferences_for(self.subject).selection)
        self.assertEqual(
            {
                path: path.read_bytes()
                for path in (self.official_root / "preset" / _PRESET_KEY).iterdir()
            },
            official_before,
        )
        self.assertEqual(
            [row["image_id"] for row in api.cards_for(self.subject)],
            [card["image_id"]],
        )

    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    def test_a_geometry_edit_keeps_the_component_it_did_not_send(self):
        identity = self._index("a.png")
        rect = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
        stage = {"scale": 0.6, "x": 0.0, "y": -0.2}
        self.assertEqual(
            self._dispatch(
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "stage": dict(stage)},
            )["outcome"],
            "success",
        )
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry,
            {identity: {"stage": stage}},
        )
        self.assertEqual(
            self._dispatch(
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "face_rect": dict(rect)},
            )["outcome"],
            "success",
        )
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry,
            {identity: {"face_rect": rect, "stage": stage}},
        )
        self.assertEqual(
            self._dispatch(
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "stage": dict(stage)},
            )["outcome"],
            "success",
        )
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry,
            {identity: {"face_rect": rect, "stage": stage}},
        )
        # A rectangle that is not pixel-square on the image's current decoded
        # size is refused before the write, with no partial write.
        with patch.object(actions, "log_warn") as warn:
            refused = self._dispatch(
                "gallery.official.geometry.set",
                {
                    "subject_key": SUBJECT,
                    "identity": identity,
                    "face_rect": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.1},
                },
            )
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "gallery_rejected")
        self.assertEqual(warn.call_count, 1)
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry,
            {identity: {"face_rect": rect, "stage": stage}},
        )

    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    @covers_requirement(
        "webclient-gallery-management-actions::personal-official-selection-and-override-adapters-reject-official-file-mutation-authoritatively"
    )
    def test_an_out_of_reference_or_unindexed_identity_is_refused_with_no_write(self):
        mine = self._index("a.png")
        theirs = self._index("a.png", key=_OTHER_PRESET_KEY)
        before = self._world()
        api.set_official_selection(self.subject, mine)
        api.set_official_geometry(self.subject, mine, stage={"scale": 0.6, "x": 0.0, "y": 0.0})
        before = self._world()
        for identity in (theirs, "preset/t_gallery_absent/a.png", "preset/t_gallery_preset/absent.png"):
            for action in (
                "gallery.official.select",
                "gallery.official.geometry.set",
                "gallery.official.geometry.clear",
            ):
                payload = {"subject_key": SUBJECT, "identity": identity}
                if action == "gallery.official.geometry.set":
                    payload["stage"] = {"scale": 0.6, "x": 0.0, "y": 0.0}
                with self.subTest(identity=identity, action=action), patch.object(
                    actions, "log_warn"
                ) as warn:
                    result = self._dispatch(action, payload)
                    self.assertEqual(
                        (result["outcome"], result["code"]),
                        ("rejected", "unknown_official_image"),
                    )
                    self._panel()
                    self.assertEqual(warn.call_count, 1)
                    self.assertEqual(
                        warn.call_args.kwargs["context"]["identity"], identity
                    )
        self.assertEqual(self._world(), before)
        # A malformed geometry payload never reaches the adapter at all.
        for payload in (
            {"subject_key": SUBJECT, "identity": mine},
            {"subject_key": SUBJECT, "identity": mine, "face_rect": None},
            {"subject_key": SUBJECT, "identity": "preset/bare", "stage": {"scale": 1, "x": 0, "y": 0}},
            {"subject_key": SUBJECT, "identity": mine, "stage": {"scale": 1, "x": 0, "y": 0}, "extra": 1},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    self._dispatch("gallery.official.geometry.set", payload)["code"],
                    "malformed_payload",
                )
        self.assertEqual(self._world(), before)

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_a_replayed_preference_request_writes_once(self):
        identity = self._index("a.png")
        payload = {"subject_key": SUBJECT, "identity": identity}
        envelope = self._envelope("gallery.official.select", payload)
        with patch.object(
            api, "set_official_selection", wraps=api.set_official_selection
        ) as write:
            first = self._dispatch("gallery.official.select", payload, envelope=envelope)
            second = self._dispatch("gallery.official.select", payload, envelope=envelope)
        self.assertEqual(first, second)
        self.assertEqual(write.call_count, 1)
        self.assertEqual(api.official_preferences_for(self.subject).selection, identity)

    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    def test_a_stale_stored_rectangle_never_blocks_a_later_stage_edit(self):
        """An artwork update invalidates the stored rect, not the stage editor."""
        identity = self._index("a.png", width=4, height=4)
        rect = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
        self.assertEqual(
            self._dispatch(
                "gallery.official.geometry.set",
                {"subject_key": SUBJECT, "identity": identity, "face_rect": dict(rect)},
            )["outcome"],
            "success",
        )
        # A maintenance update replaces the bytes at other dimensions, so the
        # stored square no longer validates against the image's decoded size.
        (self.official_root / "preset" / _PRESET_KEY / "a.png").write_bytes(
            _png(768, 1024)
        )
        load_catalog()
        stage = {"scale": 0.6, "x": 0.0, "y": -0.2}
        result = self._dispatch(
            "gallery.official.geometry.set",
            {"subject_key": SUBJECT, "identity": identity, "stage": dict(stage)},
        )
        self.assertEqual(result["outcome"], "success")
        # The omitted (stale) rectangle is carried through verbatim and the sent
        # stage landed: only a SENT component is validated against the image.
        self.assertEqual(
            api.official_preferences_for(self.subject).geometry,
            {identity: {"face_rect": rect, "stage": stage}},
        )

    def test_clearing_an_absent_preference_reports_the_state_it_leaves(self):
        identity = self._index("a.png")

        def message(action, payload):
            return self.action_registry.spec(action).adapter(self.actor, payload)["message"]

        self.assertEqual(
            message("gallery.official.clear_selection", {"subject_key": SUBJECT}),
            "目前沒有官方圖片選取。",
        )
        self.assertEqual(
            message(
                "gallery.official.geometry.clear",
                {"subject_key": SUBJECT, "identity": identity},
            ),
            "這張官方圖片沒有個人調整。",
        )
        # A real write makes the very same clear claim its change.
        api.set_official_selection(self.subject, identity)
        api.set_official_geometry(
            self.subject, identity, stage={"scale": 1, "x": 0, "y": 0}
        )
        self.assertEqual(
            message("gallery.official.clear_selection", {"subject_key": SUBJECT}),
            "已清除官方圖片選取。",
        )
        self.assertEqual(
            message(
                "gallery.official.geometry.clear",
                {"subject_key": SUBJECT, "identity": identity},
            ),
            "已清除官方圖片的個人調整。",
        )

    # -- the read-only guarantee ------------------------------------------
    @covers_requirement(
        "webclient-gallery-management-actions::seven-gallery-management-actions-are-registered-with-exact-payload-validators"
    )
    @covers_requirement(
        "webclient-gallery-management-actions::personal-official-selection-and-override-adapters-reject-official-file-mutation-authoritatively"
    )
    @covers_requirement(
        "official-art-personalization::official-mutation-attempts-fail-named-with-no-file-or-shared-change"
    )
    def test_existing_mutation_adapters_refuse_an_official_identity_with_no_side_effects(self):
        identity = self._index("a.png")
        card = self._card()
        api.set_official_selection(self.subject, identity)
        before = self._world()
        operations = (
            ("gallery.default.set", {}),
            ("gallery.card.delete", {}),
            ("gallery.face_rect.update", {"face_rect": {"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.3}}),
            ("gallery.stage.update", {"stage": {"scale": 0.6, "x": 0.0, "y": 0.0}}),
            ("gallery.binding.save", {"slots": ["armor"]}),
        )
        for action, extra in operations:
            with self.subTest(action=action), patch.object(
                actions, "log_warn"
            ) as warn:
                result = self._dispatch(
                    action, {"subject_key": SUBJECT, "image_id": identity, **extra}
                )
                self.assertEqual(
                    (result["outcome"], result["code"]),
                    ("rejected", "official_read_only"),
                )
                self.assertEqual(warn.call_count, 1)
                self.assertEqual(warn.call_args.args, ("gallery_action",))
                self.assertEqual(warn.call_args.kwargs["context"]["image_id"], identity)
                # The three declared panels refresh before the rejected result.
                self._panel()
            self.assertEqual(self._world(), before)
        # The runtime card and the stored selection are exactly as they were.
        self.assertEqual(
            [row["image_id"] for row in api.cards_for(self.subject)],
            [card["image_id"]],
        )
        self.assertEqual(api.official_preferences_for(self.subject).selection, identity)

    @covers_requirement(
        "official-art-personalization::official-mutation-attempts-fail-named-with-no-file-or-shared-change"
    )
    def test_manual_generation_writes_only_the_runtime_store(self):
        self._index("a.png")
        official_before = self._world()[0]
        result = self._dispatch(
            "gallery.generate",
            {"subject_key": SUBJECT, "fields": [], "custom_prompt": ""},
        )
        self.assertEqual(result["outcome"], "success")
        image_id = result["data"]["image_id"]
        jobs = queue.claim(10)
        job = next(job for job in jobs if job.db.gallery_image_id == image_id)
        identity = f"gallery/character/{self.subject.key}/{image_id}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(b"settled-runtime-image")
        stored = queue.settle_gallery_generated(
            job.key,
            generation_token=job.db.generation_token,
            output_identity=identity,
            tmp_path=str(tmp),
            prompt=None,
            seed=None,
            checkpoint=None,
            image_size={"width": 768, "height": 1024},
        )
        self.assertEqual(stored["stored_identity"], identity)
        self.assertEqual(self._world()[0], official_before)
        self.assertTrue(target.exists())
