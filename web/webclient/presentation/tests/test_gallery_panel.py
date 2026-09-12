"""Gallery read-only projection, transport lifecycle, and executable wire parity."""

from copy import deepcopy
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
from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.gallery import gallery_presenter, gallery_subjects, validate_gallery
from web.webclient.presentation.gallery_selection import gallery_selection_snapshot, select_gallery_subject
from web.webclient.presentation.ingress import build_presentation_context, reset_client_sequence, _coordinator_for
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import build_production_registry
from world.art import gallery as api
from world.art.queue import enqueue_gallery_job, pending_gallery_jobs, settle_gallery_failed
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

ROOT = Path(__file__).resolve().parents[4]


def image_id(number):
    return str(uuid.UUID(int=number))


def payload():
    """File-local synthetic character wire fixture, independent of shipped content."""
    return {
        "schema_version": 1, "available": True, "kind": "gallery",
        "subjects": [{"subject_key": "portrait:character:t_gallery", "kind": "portrait:character", "display_name": "測試角色", "is_puppet": True}],
        "selected": "portrait:character:t_gallery",
        "filters": {"all": 1, "defaults": 1, "bound": 0, "pending": 0, "failed": 0},
        "cards": [{
            "image_id": image_id(1), "status": "card", "label": "測試肖像",
            "url": f"/art/gallery/character/t_gallery/{image_id(1)}.png",
            "face_rect": dict(api.DEFAULT_FACE_RECT), "is_default": True,
            "chips": ["預設臉框", "目前預設"], "requested_fields": ["appearance"],
            "binding_present": False, "created_at": 100,
        }],
        "equipment_summary": {
            "weapon_main": {"value": None, "display_name": "未裝備"},
            "weapon_off": {"value": None, "display_name": "未裝備"},
            "armor": {"value": None, "display_name": "未裝備"},
            "accessories": {"value": [], "display_names": [], "equipped_count": 0},
        },
        "capabilities": {"supports_bindings": True, "supports_field_selection": True, "supports_free_text": True, "max_cards": None},
        "binding_warnings": [], "error_state": None,
    }


class GalleryWireTests(unittest.TestCase):
    @covers_requirement(
        "webclient-gallery-panel::the-gallery-payload-is-exactly-version-mirrored-across-server-and-client"
    )
    def test_bidirectional_boundary_parity(self):
        cases = [("valid", payload(), True)]
        def add(name, modify, accepted=False):
            value = payload()
            modify(value)
            cases.append((name, value, accepted))
        add("unknown top key", lambda p: p.update(extra=1))
        add("unknown nested key", lambda p: p["cards"][0].update(extra=1))
        add("wrong schema boolean", lambda p: p.update(schema_version=True))
        add("integral numeric schema", lambda p: p.update(schema_version=1.0), True)
        add("unknown selection", lambda p: p.update(selected="portrait:character:absent"))
        add("surrogate", lambda p: p["subjects"][0].update(display_name="\ud800"))
        add("name at cap", lambda p: p["subjects"][0].update(display_name="𠮷" * 64), True)
        add("name over cap", lambda p: p["subjects"][0].update(display_name="𠮷" * 65))
        add("label at cap", lambda p: p["cards"][0].update(label="畫" * 128), True)
        add("label over cap", lambda p: p["cards"][0].update(label="畫" * 129))
        add("rect zero", lambda p: p["cards"][0]["face_rect"].update(w=0))
        add("rect overflow", lambda p: p["cards"][0]["face_rect"].update(x=0.9))
        add("rect boolean", lambda p: p["cards"][0]["face_rect"].update(x=True))
        add("fractional timestamp", lambda p: p["cards"][0].update(created_at=100.125), True)
        add("timestamp boolean", lambda p: p["cards"][0].update(created_at=True))
        add("unsafe timestamp", lambda p: p["cards"][0].update(created_at=2**53))
        add("wrong count", lambda p: p["filters"].update(all=2))
        add("boolean count", lambda p: p["filters"].update(all=True))
        add("integral numeric count", lambda p: p["filters"].update(all=1.0), True)
        add("foreign URL", lambda p: p["cards"][0].update(url=f"/art/gallery/character/other/{image_id(1)}.png"))
        add("unsupported extension", lambda p: p["cards"][0].update(url=p["cards"][0]["url"] + ".svg"))
        add("jpg extension", lambda p: p["cards"][0].update(url=p["cards"][0]["url"][:-4] + ".jpg"), True)
        add("duplicate card", lambda p: p["cards"].append(deepcopy(p["cards"][0])))
        add("pending with URL", lambda p: p["cards"][0].update(status="pending"))
        add("unknown field", lambda p: p["cards"][0].update(requested_fields=["unknown"]))
        add("duplicate field", lambda p: p["cards"][0].update(requested_fields=["appearance", "appearance"]))
        add("chip mismatch", lambda p: p["cards"][0].update(chips=["自訂臉框", "目前預設"]))
        add("unsupported equipment", lambda p: p["capabilities"].update(supports_bindings=False))
        add("warning missing card", lambda p: p["binding_warnings"].append({"image_id": image_id(99), "label": "不存在", "conditions": ["防具：未裝備"]}))
        def subjects(p, count):
            p["subjects"].extend({"subject_key": f"portrait:character:t_{i}", "kind": "portrait:character", "display_name": "其他角色", "is_puppet": False} for i in range(count - 1))
        add("rail at cap", lambda p: subjects(p, 24), True)
        add("rail over cap", lambda p: subjects(p, 25))
        def subject_key(p, key):
            p["selected"] = p["subjects"][0]["subject_key"] = f"portrait:character:{key}"
            p["cards"][0]["url"] = f"/art/gallery/character/{key}/{image_id(1)}.avif"
        add("URL 129", lambda p: subject_key(p, "a" * 64), True)
        add("key byte cap", lambda p: subject_key(p, "𠮷" * 50), True)
        add("key byte overflow", lambda p: subject_key(p, "𠮷" * 51))
        add("key codepoint overflow", lambda p: subject_key(p, "a" * 65))
        add("key control", lambda p: subject_key(p, "x\u200dy"))
        add("key separator", lambda p: subject_key(p, "x/y"))
        add("permitted key whitespace", lambda p: subject_key(p, "key "), True)
        def accessories(p, values):
            p["equipment_summary"]["accessories"] = {"value": values, "display_names": ["測試飾品"] * len(values), "equipped_count": len(values)}
        add("accessories at cap", lambda p: accessories(p, [f"t_{i}" for i in range(5)]), True)
        add("accessories over cap", lambda p: accessories(p, [f"t_{i}" for i in range(6)]))
        add("accessories unsorted", lambda p: accessories(p, ["t_z", "t_a"]))
        add("Unicode sort", lambda p: accessories(p, ["\ue000", "𠮷"]), True)
        def failed(p):
            p["cards"] = [{"image_id": image_id(2), "status": "failed", "label": "暫時無法生成，稍後再試", "url": None, "face_rect": None, "is_default": False, "chips": [], "requested_fields": [], "binding_present": False, "created_at": 200}]
            p["filters"] = {"all": 1, "defaults": 0, "bound": 0, "pending": 0, "failed": 1}
            p["error_state"] = {"code": "sd_connection_error", "at": 200}
        add("failed row", failed, True)
        def pending_rows(p, count):
            failed(p)
            p["error_state"] = None
            first = p["cards"][0]
            first.update(status="pending", label="肖像（生成中）")
            p["cards"] = [dict(first, image_id=image_id(i + 1)) for i in range(count)]
            p["filters"].update(all=count, pending=count, failed=0)
        add("pending at cap", lambda p: pending_rows(p, 8), True)
        add("pending over cap", lambda p: pending_rows(p, 9))
        def warning_rows(p, count, condition_length=12):
            first = p["cards"][0]
            first.update(is_default=False, binding_present=True, chips=["防具", "預設臉框"])
            p["cards"] = []
            for i in range(count):
                row = dict(first, image_id=image_id(i + 1), url=f"/art/gallery/character/t_gallery/{image_id(i + 1)}.png")
                p["cards"].append(row)
            p["filters"].update(all=count, defaults=0, bound=count)
            p["binding_warnings"] = [{"image_id": row["image_id"], "label": row["label"], "conditions": ["條" * condition_length]} for row in p["cards"]]
        add("warnings at cap", lambda p: warning_rows(p, 5), True)
        add("warnings over cap", lambda p: warning_rows(p, 6))
        add("condition at cap", lambda p: warning_rows(p, 1, 512), True)
        add("condition over cap", lambda p: warning_rows(p, 1, 513))
        def over_bytes(p):
            first = p["cards"][0]
            first.update(is_default=False, chips=["預設臉框"], label="𠮷" * 128)
            p["cards"] = []
            for i in range(110):
                row = deepcopy(first)
                row.update(image_id=image_id(i + 1), url=f"/art/gallery/character/t_gallery/{image_id(i + 1)}.png")
                p["cards"].append(row)
            p["filters"].update(all=110, defaults=0)
        add("envelope byte overflow", over_bytes)
        script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validateGalleryPanel(value)]; }
  catch (_) { return [name, false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.run(["node", "-e", script], input=json.dumps(cases), text=True, capture_output=True, cwd=ROOT, check=True)
        js_results = json.loads(output.stdout)
        for (name, value, expected), (_, js_accepts, echoed) in zip(cases, js_results, strict=True):
            with self.subTest(case=name):
                try:
                    validate_gallery(value)
                    python_accepts = True
                except ProtocolValidationError:
                    python_accepts = False
                self.assertEqual(python_accepts, expected)
                self.assertEqual(js_accepts, expected)
                if js_accepts:
                    self.assertEqual(validate_gallery(echoed), value)


class GalleryPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.actor = create_object(PlayerCharacter, key="測試主角", location=self.room1)
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "t_gallery_actor"}
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_actor")
        self.context = PresentationContext(self.actor, 1)
        self.registry = build_production_registry()
        tiers = {"t_beast": SimpleNamespace(display_name_zh="測試魔物")}
        for target in ("web.webclient.presentation.gallery.MONSTER_TIER_REGISTRY", "world.art.subjects.MONSTER_TIER_REGISTRY"):
            patcher = patch(target, tiers)
            patcher.start()
            self.addCleanup(patcher.stop)

    def card(self, number, *, timestamp=100, binding=None, face=None, subject=None, extension=".png"):
        subject = subject or self.subject
        directory = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        identity = f"gallery/{directory}/{subject.key}/{image_id(number)}{extension}"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        return api.append_card(subject, image_id=image_id(number), stored_identity=identity,
            prompt=None, seed=None, checkpoint=None, requested_fields=[], binding=binding,
            source="seed", created_at=timestamp, face_rect=face or dict(api.DEFAULT_FACE_RECT))

    def make_session(self):
        session = SimpleNamespace(ndb=SimpleNamespace(), puppet=self.actor, protocol_key="websocket", msg=lambda **kwargs: None)
        attach_coordinator(session, self.registry)
        return session

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-1-presentation-panel"
    )
    def test_empty_available_and_mode_gate(self):
        before = api.GalleryRecord.objects.count()
        value = gallery_presenter(self.context)
        self.assertEqual(value["cards"], [])
        self.assertEqual(value["filters"], dict.fromkeys(("all", "defaults", "bound", "pending", "failed"), 0))
        self.assertEqual(value["selected"], self.subject.full())
        self.assertEqual(api.GalleryRecord.objects.count(), before)
        self.actor.creation_pending = True
        self.assertEqual(self.registry.render("gallery", self.context)["reason"]["code"], "gallery_unavailable")

    @covers_requirement(
        "webclient-gallery-panel::the-subject-rail-names-every-gallery-bearing-subject-with-companion-first-ordering"
    )
    def test_rail_prioritizes_companions_reserves_monsters_and_skips_corruption(self):
        other = create_object(NPC, key="其他角色")
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_other"}
        companion = create_object(NPC, key="同行角色")
        companion.db.portrait_policy = {"mode": "named", "stable_key": "t_companion"}
        companion.db.party_member = self.actor.pk
        self.actor.db.party = [companion.pk]
        corrupt = create_object(NPC, key="損壞資料")
        corrupt.db.portrait_policy = {"mode": "named", "stable_key": "bad/key"}
        rail = gallery_subjects(self.actor)
        self.assertEqual([entry[0]["subject_key"] for entry in rail], [self.subject.full(), "portrait:character:t_companion", "portrait:character:t_other", "portrait:monster:t_beast"])
        with patch("web.webclient.presentation.gallery.GALLERY_MAX_SUBJECTS", 3):
            self.assertEqual([row[0]["subject_key"] for row in gallery_subjects(self.actor)], [self.subject.full(), "portrait:character:t_companion", "portrait:monster:t_beast"])

    @covers_requirement(
        "webclient-gallery-panel::card-rows-are-server-authored-with-chips-crown-and-validated-media",
        "webclient-gallery-panel::filter-counts-and-the-equipment-summary-are-server-computed",
    )
    def test_card_chips_order_counts_and_overlap_are_server_facts(self):
        self.actor.db.equipment = {"weapon_main": "t_sword", "armor": "t_coat", "accessories": ["t_ring_b", "t_ring_a"]}
        bound = {"mask": ["weapon_main", "armor"], "snapshot": {"weapon_main": "t_sword", "armor": "t_coat"}}
        self.card(1, binding=bound, face={"x": 0, "y": 0, "w": 1, "h": 1})
        self.card(2, timestamp=200, binding={"mask": ["armor"], "snapshot": {"armor": "t_coat"}})
        self.card(3, timestamp=200, binding={"mask": ["weapon_main"], "snapshot": {"weapon_main": "t_other"}})
        with patch("web.webclient.presentation.gallery.ITEM_REGISTRY", {"t_sword": SimpleNamespace(display_name_zh="測試長劍"), "t_coat": SimpleNamespace(display_name_zh="測試外套")}):
            value = gallery_presenter(self.context)
        self.assertEqual([row["image_id"] for row in value["cards"]], [image_id(2), image_id(3), image_id(1)])
        self.assertEqual(value["cards"][-1]["chips"], ["主手", "防具", "自訂臉框", "目前預設"])
        self.assertEqual([row["image_id"] for row in value["binding_warnings"]], [image_id(2), image_id(1)])
        self.assertEqual(value["binding_warnings"][-1]["conditions"], ["主手：測試長劍", "防具：測試外套"])
        self.assertEqual(value["equipment_summary"]["accessories"]["value"], ["t_ring_a", "t_ring_b"])
        self.assertEqual(value["filters"], {"all": 3, "defaults": 1, "bound": 3, "pending": 0, "failed": 0})

    @covers_requirement("webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only")
    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-1-presentation-panel"
    )
    def test_repeated_render_preserves_duplicate_records_cards_jobs_and_files(self):
        self.card(1)
        duplicate = create_script(api.GalleryRecord, key=api.record_key(self.subject), persistent=True, interval=0)
        duplicate.db.cards = []
        job = self.job(2)
        before_records = [(row.pk, repr(row.attributes.all())) for row in api.GalleryRecord.objects.all()]
        before_jobs = [(row.pk, row.db.status, row.db.enqueued_at) for row in ArtAssetRecord.objects.all()]
        before_files = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first = gallery_presenter(self.context)
        self.assertEqual(gallery_presenter(self.context), first)
        self.assertEqual([(row.pk, repr(row.attributes.all())) for row in api.GalleryRecord.objects.all()], before_records)
        self.assertEqual([(row.pk, row.db.status, row.db.enqueued_at) for row in ArtAssetRecord.objects.all()], before_jobs)
        self.assertEqual({path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}, before_files)
        self.assertEqual(job.db.status, "pending")

    @covers_requirement(
        "webclient-gallery-panel::binding-overlap-warnings-are-computed-only-in-the-presenter"
    )
    def test_accessory_match_requires_exact_equipment_and_warnings_keep_newest_five(self):
        self.actor.db.equipment = {"accessories": ["t_ring_b", "t_ring_a"]}
        binding = {"mask": ["accessories"], "snapshot": {"accessories": ["t_ring_a", "t_ring_b"]}}
        for number in range(1, 8):
            self.card(number, timestamp=number, binding=binding)
        self.card(8, timestamp=8, binding={"mask": ["accessories"], "snapshot": {"accessories": ["t_ring_a"]}})
        value = gallery_presenter(self.context)
        self.assertEqual([row["image_id"] for row in value["binding_warnings"]], [image_id(number) for number in range(7, 2, -1)])
        self.assertEqual(value["binding_warnings"][0]["conditions"], ["飾品：t_ring_a、t_ring_b（任一）"])
        self.assertEqual(value["filters"]["bound"], 8)

    def job(self, number):
        with patch("world.art.queue._prompt_digest_or_empty", return_value=""), patch("world.art.queue.time.time", return_value=300 + number):
            return enqueue_gallery_job(self.subject, "synthetic portrait", image_id=image_id(number), binding=None, face_rect=None, requested_fields=[])

    @covers_requirement(
        "webclient-gallery-panel::pending-jobs-and-the-recorded-error-render-as-truthful-synthetic-rows"
    )
    def test_pending_bound_dedupe_and_offline_failed_settlement(self):
        for number in range(1, 11):
            self.job(number)
        self.assertEqual([row["image_id"] for row in pending_gallery_jobs(self.subject)], [image_id(number) for number in range(10, 2, -1)])
        self.card(10, timestamp=400)
        value = gallery_presenter(self.context)
        self.assertEqual(sum(row["image_id"] == image_id(10) for row in value["cards"]), 1)
        self.assertEqual(value["filters"]["pending"], 7)
        job = ArtAssetRecord.objects.get(db_key=f"art:{self.subject.full()}:gen:{image_id(9)}")
        job.db.status = "in_progress"
        job.db.generation_token = "t_token"
        with patch("world.art.gallery.time.time", return_value=500):
            settle_gallery_failed(job.key, generation_token="t_token", error="sd_connection_error")
        value = gallery_presenter(self.context)
        failed = [row for row in value["cards"] if row["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertIn("暫時無法生成，稍後再試", failed[0]["label"])
        self.assertIn("sd_connection_error", failed[0]["label"])
        self.assertIsNone(failed[0]["url"])
        self.assertEqual(value, gallery_presenter(self.context))
        self.assertEqual(len(api.cards_for(self.subject)), 1)

    @covers_requirement(
        "webclient-gallery-panel::card-rows-are-server-authored-with-chips-crown-and-validated-media"
    )
    def test_missing_and_symlink_files_are_omitted(self):
        first = self.card(1)
        second = self.card(2)
        (self.root / first["stored_identity"]).unlink()
        target = self.root / second["stored_identity"]
        target.unlink()
        target.symlink_to(__file__)
        value = gallery_presenter(self.context)
        self.assertEqual(value["cards"], [])
        self.assertEqual(value["filters"]["all"], 0)

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_selection_is_transport_owned_and_retired_by_real_unpuppet_signal(self):
        a, b = self.make_session(), self.make_session()
        selected = "portrait:monster:t_beast"
        with patch("web.webclient.presentation.gallery_selection.log_info") as event:
            self.assertEqual(select_gallery_subject(a, self.actor, selected)["outcome"], "success")
            select_gallery_subject(a, self.actor, selected)
            event.assert_called_once_with("gallery_panel_selected", context={"subject": selected, "kind": "portrait:monster"})
        self.assertIsNone(gallery_selection_snapshot(b, self.actor))
        self.assertEqual(select_gallery_subject(a, self.actor, "scene:t_scene")["code"], "unknown_subject")
        self.assertEqual(gallery_selection_snapshot(a, self.actor), selected)
        value = gallery_presenter(build_presentation_context(a, self.actor))
        self.assertEqual(value["selected"], selected)
        self.assertIsNone(value["equipment_summary"])
        self.assertFalse(value["capabilities"]["supports_bindings"])
        SIGNAL_OBJECT_POST_UNPUPPET.send(sender=self.actor, session=a, account=self.account)
        self.assertIsNone(a.ndb.gallery_selection)
        self.assertIsNone(gallery_selection_snapshot(a, self.actor))
        select_gallery_subject(a, self.actor, selected)
        reset_client_sequence(a)
        self.assertIsNone(gallery_selection_snapshot(a, self.actor))
        select_gallery_subject(a, self.actor, selected)
        a.ndb.elosern_actor_id = str(self.actor.pk)
        other = create_object(PlayerCharacter, key="新角色")
        a.puppet = other
        _coordinator_for(a, other)
        self.assertIsNone(a.ndb.gallery_selection)

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_deleted_selected_character_falls_back_without_writing(self):
        other = create_object(NPC, key="待刪角色")
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_deleted"}
        session = self.make_session()
        select_gallery_subject(session, self.actor, "portrait:character:t_deleted")
        frozen = build_presentation_context(session, self.actor)
        other.delete()
        self.assertEqual(gallery_presenter(frozen)["selected"], self.subject.full())
        self.assertEqual(session.ndb.gallery_selection.subject_key, "portrait:character:t_deleted")
