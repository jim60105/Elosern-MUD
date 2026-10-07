"""Fixed-fixture reader tests: art records (task 2.4 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
art-asset kind: subject key, status, prompt summary, source hash, generated
time and failure reason, plus the existing ``/art/`` thumbnail offered only
when the stored identity resolves to a real file. Its ``gm-runtime-state``
requirement annotation was attached when the delta spec synced into the main
spec at archive.
"""

from __future__ import annotations

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from world.art.store import ArtAssetRecord, ArtAssetStatus

from tools.spec_traceability import covers_requirement
from web.gm.readers import art
from web.gm.readers._entities import stored_attribute_keys
from web.gm.tests._state_support import (
    failed_sections,
    row_value,
    section_keys,
    section_of,
)

EXPECTED_SECTIONS = ["identity", "prompt", "generation", "output", "gallery"]


class ArtReaderTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.record = create.create_script(
            ArtAssetRecord, key="art:t_reader_subject"
        )
        self.record.db.kind = "monster"
        self.record.db.subject_key = "t_reader_subject"
        self.record.db.status = ArtAssetStatus.FAILED
        self.record.db.source_description = "一頭在合成礁石上休息的合成禽鳥。"
        self.record.db.source_hash = "t_synthetichash"
        self.record.db.prompt_digest = "t_syntheticdigest"
        self.record.db.generation_token = "t_token"
        self.record.db.attempt_count = 3
        self.record.db.last_error_code = "art_sd_unavailable"
        self.record.db.output_identity = "t_missing_output.webp"
        self.record.db.enqueued_at = 1700000000.0
        self.record.db.completed_at = 1700000042.0

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_detail_exposes_every_curated_art_section(self):
        detail = art.detail(self.record)
        self.assertEqual(detail["kind"], "art")
        self.assertEqual(detail["id"], "art:t_reader_subject")
        self.assertEqual(self.record.db_key, detail["id"])
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_status_and_offers_no_thumbnail_without_a_file(self):
        identity = section_of(art.detail(self.record), "identity")
        self.assertEqual(row_value(identity, "主體"), "t_reader_subject")
        self.assertEqual(row_value(identity, "種類"), "monster")
        self.assertEqual(row_value(identity, "狀態"), ArtAssetStatus.FAILED)
        self.assertEqual(row_value(identity, "縮圖"), "沒有可用的檔案")
        thumbnail_row = next(row for row in identity["rows"] if row["label"] == "縮圖")
        self.assertNotIn("link", thumbnail_row)
        self.assertIsNone(art.thumbnail_url(self.record))

    def test_identity_offers_the_thumbnail_once_the_output_file_exists(self):
        # The positive half of the contract: the stored identity is offered
        # only because a real file resolves under ``ART_STORE_ROOT``.
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        identity = "gallery/monster/t_reader_subject/t_reader_image.png"
        with tempfile.TemporaryDirectory() as store:
            target = Path(store) / identity
            target.parent.mkdir(parents=True)
            target.write_bytes(b"t_syntheticimage")
            with override_settings(ART_STORE_ROOT=store):
                self.record.db.output_identity = identity
                self.assertEqual(art.thumbnail_url(self.record), f"/art/{identity}")
                thumbnail = next(
                    row
                    for row in section_of(art.detail(self.record), "identity")["rows"]
                    if row["label"] == "縮圖"
                )
                self.assertEqual(
                    thumbnail["link"], {"kind": "media", "id": f"/art/{identity}"}
                )

    def test_generation_and_output_report_stored_provenance(self):
        detail = art.detail(self.record)
        generation = section_of(detail, "generation")
        self.assertEqual(row_value(generation, "來源雜湊"), "t_synthetichash")
        self.assertEqual(row_value(generation, "提示摘要"), "t_syntheticdigest")
        self.assertEqual(row_value(generation, "嘗試次數"), 3)
        self.assertEqual(row_value(generation, "最後錯誤"), "art_sd_unavailable")
        self.assertEqual(row_value(generation, "完成時間"), 1700000042.0)
        output = section_of(detail, "output")
        self.assertEqual(row_value(output, "輸出識別"), "t_missing_output.webp")
        self.assertEqual(row_value(output, "雜湊已變更"), "否")

    def test_prompt_section_carries_the_source_description_as_text(self):
        prompt = section_of(art.detail(self.record), "prompt")
        self.assertEqual(prompt["type"], "text")
        self.assertIn("合成禽鳥", prompt["text"])

    def test_absent_prompt_and_non_gallery_records_report_honest_empty_states(self):
        plain = create.create_script(ArtAssetRecord, key="art:t_reader_plain")
        plain.db.subject_key = "t_reader_plain"
        detail = art.detail(plain)
        self.assertEqual(section_of(detail, "prompt")["type"], "empty")
        gallery = section_of(detail, "gallery")
        self.assertEqual(gallery["type"], "empty")
        self.assertIn("畫廊", gallery["note"])

    def test_a_gallery_record_reports_its_job_fields(self):
        job = create.create_script(
            ArtAssetRecord, key="art:t_reader_subject:gen:t_image"
        )
        job.db.subject_key = "t_reader_subject"
        job.db.gallery_image_id = "t_image"
        job.db.gallery_requested_fields = ["face", "pose"]
        gallery = section_of(art.detail(job), "gallery")
        self.assertEqual(row_value(gallery, "畫廊影像"), "t_image")
        self.assertEqual(row_value(gallery, "要求欄位"), "face、pose")

    def test_raw_record_tab_projects_the_stored_fields_not_evennia_metadata(self):
        detail = art.detail(self.record)
        self.assertEqual(set(detail["raw"]), {"record"})
        record = detail["raw"]["record"]
        self.assertEqual(set(record), set(art.RECORD_FIELDS))
        self.assertEqual(record["subject_key"], "t_reader_subject")

    def test_list_items_are_summary_only_and_filterable(self):
        items = art.list_items({})
        self.assertEqual([item["id"] for item in items], ["art:t_reader_subject"])
        item = items[0]
        self.assertEqual(
            [field["label"] for field in item["fields"]],
            ["種類", "狀態", "記錄鍵", "失敗代碼", "畫廊任務"],
        )
        self.assertEqual(art.list_items({"status": ArtAssetStatus.FAILED}), items)
        self.assertEqual(art.list_items({"status": "done"}), [])
        self.assertEqual(art.list_items({"kind": "monster"}), items)
        self.assertEqual(art.list_items({"kind": "character"}), [])

    def test_reading_an_art_record_creates_no_attributes(self):
        before = stored_attribute_keys(self.record)
        art.detail(self.record)
        art.list_items({})
        self.assertEqual(stored_attribute_keys(self.record), before)
