"""Tests for NPC persona persistence, versioning, and parity with PersonaStore (D2/D3/D4)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.db import OperationalError, transaction
from django.test.utils import CaptureQueriesContext
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.lore.npc_card import (
    NPC_CARD_RENDER_ORDER,
    NpcCard,
    NpcCardError,
    normalize_card,
    render_card_block,
)
from world.rules.npc_persona import (
    NpcPersonaSnapshot,
    NpcPersonaStorageError,
    NpcPersonaUnavailable,
    UpdateOutcome,
    _raw_meta_value,
    current_persona_version,
    initialize_npc_persona,
    provenance_profile_key,
    read_npc_persona,
    update_npc_persona,
)
from world.rules.persona import PersonaStore
from world.tests.raw_attributes import raw_attribute_value

FIXTURES_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "lore"
    / "tests"
    / "fixtures"
    / "npc_card_boundary_cases.json"
)


class NpcPersonaParityTest(EvenniaTest):
    """Test rendering parity between PersonaStore.flatten and render_card_block (D2)."""

    @covers_requirement("npc-persona-card::validation-and-prompt-rendering-share-one-field-order-and-label-policy")
    @covers_requirement("persona-store::the-speech-style-field-renders-with-its-localized-label")
    def test_parity_across_valid_boundary_fixtures(self) -> None:
        """Every valid fixture card flattened through PersonaStore over NPC_CARD_RENDER_ORDER equals render_card_block."""
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)

        for case in cases:
            if not case.get("expected_valid"):
                continue

            with self.subTest(case=case["name"]):
                raw = dict(case["card"])
                if case.get("use_astral_600_field"):
                    field = case["use_astral_600_field"]
                    raw[field] = "😀" * 600

                card = normalize_card(raw)
                entity = SimpleNamespace(db=SimpleNamespace(persona=card.to_record()))
                store = PersonaStore(entity)

                flattened = store.flatten(NPC_CARD_RENDER_ORDER)
                direct = render_card_block(card)

                self.assertIsNotNone(flattened)
                self.assertEqual(flattened, direct)
                self.assertNotIn("…", flattened)

    @covers_requirement("persona-store::the-speech-style-field-renders-with-its-localized-label")
    def test_default_field_set_regression(self) -> None:
        """Default flatten() does not include speech_style and remains unchanged."""
        card_record = {
            "identity": {"public": "接待員", "hidden": ""},
            "appearance": "金髮碧眼。",
            "personality": "親切熱情。",
            "speech_style": "公事語氣。",
            "life_story": "在王都長大。",
            "habit": "整理文件。",
            "social_connection": "",
        }
        entity = SimpleNamespace(db=SimpleNamespace(persona=card_record))
        store = PersonaStore(entity)
        default_flattened = store.flatten()
        self.assertIsNotNone(default_flattened)
        self.assertNotIn("說話風格：", default_flattened)
        self.assertNotIn("公事語氣。", default_flattened)


class NpcPersonaServiceTest(EvenniaTest):
    """Test persistence, read, initialization, and update logic in world/rules/npc_persona.py (D3/D4)."""

    def setUp(self) -> None:
        super().setUp()
        self.npc = create_object(NPC, key="測試NPC")
        self.valid_card_raw = {
            "identity": {"public": "公會守衛", "hidden": "前刺客"},
            "appearance": "高大威猛，身披重鎧。",
            "personality": "沉默寡言，警惕心強。",
            "speech_style": "簡短低沉。",
            "life_story": "曾效力於暗影公會，後金盆洗手。",
            "habit": "擦拭配劍。",
            "social_connection": "酒館老闆是舊識。",
        }
        self.provenance = {"kind": "profile", "profile": "guard_01"}

    @covers_requirement("npc-persona-card::npc-persona-metadata-is-a-separate-record")
    @covers_requirement("npc-persona-card::initialization-never-overwrites-a-marked-npc")
    def test_first_initialization(self) -> None:
        """First initialization writes card and metadata at version 1 atomically."""
        snapshot = initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        self.assertIsInstance(snapshot, NpcPersonaSnapshot)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.generation, 1)
        self.assertEqual(snapshot.provenance, self.provenance)

        # Confirm persisted on entity
        self.assertEqual(self.npc.db.persona["identity"]["public"], "公會守衛")
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

    @covers_requirement("npc-persona-card::initialization-never-overwrites-a-marked-npc")
    def test_reinitialization_no_overwrite(self) -> None:
        """Initializing an NPC already having current generation metadata does not overwrite."""
        snapshot1 = initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        self.assertEqual(snapshot1.version, 1)

        # Update to version 2
        updated_card_raw = dict(self.valid_card_raw)
        updated_card_raw["appearance"] = "換上了輕甲。"
        res = update_npc_persona(self.npc, updated_card_raw, expected_version=1)
        self.assertEqual(res.status, "updated")
        self.assertEqual(res.version, 2)

        # Re-initialize
        snapshot2 = initialize_npc_persona(self.npc, self.valid_card_raw, {"kind": "profile", "profile": "other"})
        self.assertEqual(snapshot2.version, 2)
        self.assertEqual(self.npc.db.persona["appearance"], "換上了輕甲。")

    @covers_requirement("npc-persona-card::initialization-never-overwrites-a-marked-npc")
    def test_invalid_card_writes_nothing(self) -> None:
        """An invalid card raises NpcCardError and writes nothing."""
        bad_card = dict(self.valid_card_raw)
        bad_card["habit"] = 12345
        with self.assertRaises(NpcCardError):
            initialize_npc_persona(self.npc, bad_card, self.provenance)

        self.assertIsNone(self.npc.db.persona)
        self.assertIsNone(self.npc.db.npc_persona_meta)

    @covers_requirement("npc-persona-card::reading-an-npc-persona-never-initializes-or-repairs-it")
    def test_read_never_writes_or_repairs(self) -> None:
        """read_npc_persona never writes and returns NpcPersonaUnavailable on corrupt or missing records."""
        # Non-NPC
        res = read_npc_persona(self.char1)
        self.assertIsInstance(res, NpcPersonaUnavailable)
        self.assertEqual(res.reason, "not_npc")

        # Missing card
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaUnavailable)
        self.assertEqual(res.reason, "missing_card")

        # Missing meta
        self.npc.db.persona = normalize_card(self.valid_card_raw).to_record()
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaUnavailable)
        self.assertEqual(res.reason, "missing_meta")

        # Corrupt card
        self.npc.db.persona = {"unknown": "val"}
        self.npc.db.npc_persona_meta = {"format": 1, "generation": 1, "persona_version": 1, "provenance": self.provenance}
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaUnavailable)
        self.assertEqual(res.reason, "corrupt_card")
        self.assertEqual(self.npc.db.persona, {"unknown": "val"})  # No repair

        # Corrupt meta
        self.npc.db.persona = normalize_card(self.valid_card_raw).to_record()
        self.npc.db.npc_persona_meta = {"format": "bad"}
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaUnavailable)
        self.assertEqual(res.reason, "corrupt_meta")

        # Valid read
        self.npc.db.npc_persona_meta = {"format": 1, "generation": 1, "persona_version": 1, "provenance": self.provenance}
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaSnapshot)
        self.assertEqual(res.version, 1)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_boundary_only_and_crlf_card_and_greeting_resave_is_no_op(self) -> None:
        """Boundary-only whitespace and CRLF vs LF card/greeting resave succeeds unchanged with same version."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        update_npc_persona(
            self.npc,
            self.valid_card_raw,
            expected_version=1,
            offline_greeting="「歡迎光臨。」",
        )
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 2)

        # Resave with boundary whitespace (U+FEFF, U+0085, etc) and CRLF line endings
        crlf_boundary_card = dict(self.valid_card_raw)
        crlf_boundary_card["appearance"] = "\ufeff\u0085高大威猛，身披重鎧。\r\n\u0085\ufeff "
        boundary_greeting = "\ufeff\u0085「歡迎光臨。」\u0085\ufeff"

        res = update_npc_persona(
            self.npc,
            crlf_boundary_card,
            expected_version=2,
            offline_greeting=boundary_greeting,
        )
        self.assertEqual(res.status, "unchanged")
        self.assertEqual(res.version, 2)
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 2)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_optional_clear_advances_once_repeat_is_unchanged_and_stale_rejects(self) -> None:
        """Clearing optional content with boundary whitespace advances version once; repeat is unchanged; stale rejects."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        # Set initial greeting override
        update_npc_persona(
            self.npc,
            self.valid_card_raw,
            expected_version=1,
            offline_greeting="「初始問候。」",
        )
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 2)
        self.assertTrue(self.npc.attributes.has("npc_offline_greeting"))

        # First clear: identity.hidden and offline_greeting cleared using boundary whitespace
        card_cleared = dict(self.valid_card_raw)
        card_cleared["identity"] = {"public": "公會守衛", "hidden": "\ufeff\u0085 \t"}
        card_cleared["social_connection"] = "\ufeff\u0085 \t"
        res1 = update_npc_persona(self.npc, card_cleared, expected_version=2, offline_greeting="\ufeff\u0085 ")
        self.assertEqual(res1.status, "updated")
        self.assertEqual(res1.version, 3)
        self.assertEqual(self.npc.db.persona["identity"]["hidden"], "")
        self.assertEqual(self.npc.db.persona["social_connection"], "")
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

        # Repeated clear with expected_version=3: no-op, unchanged
        res2 = update_npc_persona(self.npc, card_cleared, expected_version=3, offline_greeting="")
        self.assertEqual(res2.status, "unchanged")
        self.assertEqual(res2.version, 3)

        # Stale repeat with expected_version=1: rejected as version_conflict without writing
        res3 = update_npc_persona(self.npc, card_cleared, expected_version=1, offline_greeting="")
        self.assertEqual(res3.status, "version_conflict")
        self.assertEqual(res3.version, 3)

    @covers_requirement("npc-persona-card::persona-updates-are-compare-and-set-on-persona-version")
    def test_no_op_success(self) -> None:
        """Submitting an identical card succeeds with unchanged status without advancing version."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        res = update_npc_persona(self.npc, self.valid_card_raw, expected_version=1)
        self.assertEqual(res.status, "unchanged")
        self.assertEqual(res.version, 1)
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

    @covers_requirement("npc-persona-card::persona-updates-are-compare-and-set-on-persona-version")
    def test_stale_no_op_conflict(self) -> None:
        """Submitting an identical card with a stale version is rejected as version_conflict."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        # Advance to version 2
        card2 = dict(self.valid_card_raw)
        card2["appearance"] = "新外觀。"
        res = update_npc_persona(self.npc, card2, expected_version=1)
        self.assertEqual(res.status, "updated")
        self.assertEqual(res.version, 2)

        # Submit current card2 with stale expected_version=1
        res = update_npc_persona(self.npc, card2, expected_version=1)
        self.assertEqual(res.status, "version_conflict")
        self.assertEqual(res.version, 2)

    @covers_requirement("npc-persona-card::persona-updates-are-compare-and-set-on-persona-version")
    def test_hidden_only_change_bumps_version(self) -> None:
        """Changing only identity.hidden advances the version."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        card2 = dict(self.valid_card_raw)
        card2["identity"] = {"public": "公會守衛", "hidden": "秘密探員"}
        res = update_npc_persona(self.npc, card2, expected_version=1)
        self.assertEqual(res.status, "updated")
        self.assertEqual(res.version, 2)
        self.assertEqual(self.npc.db.persona["identity"]["hidden"], "秘密探員")
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 2)

    @covers_requirement("npc-persona-card::persona-updates-are-compare-and-set-on-persona-version")
    def test_change_and_revert_bumps_twice(self) -> None:
        """Changing a card and then reverting it bumps version twice."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        card2 = dict(self.valid_card_raw)
        card2["habit"] = "新習慣。"
        res1 = update_npc_persona(self.npc, card2, expected_version=1)
        self.assertEqual(res1.status, "updated")
        self.assertEqual(res1.version, 2)

        res2 = update_npc_persona(self.npc, self.valid_card_raw, expected_version=2)
        self.assertEqual(res2.status, "updated")
        self.assertEqual(res2.version, 3)
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 3)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_card_and_greeting_share_one_version(self) -> None:
        """Greeting-only, both, stale, and clear submissions all ride persona_version."""
        from world.rules.npc_persona import current_persona_version, read_offline_greeting

        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        res = update_npc_persona(self.npc, self.valid_card_raw, expected_version=1, offline_greeting="「早安。」")
        self.assertEqual((res.status, res.version), ("updated", 2))
        self.assertEqual(read_offline_greeting(self.npc), "「早安。」")
        # The stale-persona completion gate reads this same version.
        self.assertEqual(current_persona_version(self.npc), 2)

        changed = dict(self.valid_card_raw)
        changed["habit"] = "晨間散步。"
        both = update_npc_persona(self.npc, changed, expected_version=2, offline_greeting="「晚安。」")
        self.assertEqual((both.status, both.version), ("updated", 3))

        stale = update_npc_persona(self.npc, self.valid_card_raw, expected_version=2, offline_greeting="")
        self.assertEqual((stale.status, stale.version), ("version_conflict", 3))
        self.assertEqual(read_offline_greeting(self.npc), "「晚安。」")
        self.assertEqual(read_npc_persona(self.npc).card.habit, "晨間散步。")

        cleared = update_npc_persona(self.npc, changed, expected_version=3, offline_greeting="")
        self.assertEqual((cleared.status, cleared.version), ("updated", 4))
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))
        self.assertEqual(read_offline_greeting(self.npc), "")

        invalid = update_npc_persona(self.npc, changed, expected_version=4, offline_greeting="甲\n乙")
        self.assertEqual((invalid.status, invalid.reason), ("invalid", "greeting_invalid"))
        self.assertEqual(current_persona_version(self.npc), 4)

    @covers_requirement("npc-persona-card::persona-updates-are-compare-and-set-on-persona-version")
    def test_boolean_or_non_integer_version_rejected(self) -> None:
        """Boolean or non-integer expected_version is rejected without writing."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        for bad_v in (True, False, "1", 1.0, None):
            with self.subTest(version=bad_v):
                res = update_npc_persona(self.npc, self.valid_card_raw, expected_version=bad_v)
                self.assertEqual(res.status, "invalid")
                self.assertEqual(res.reason, "invalid_version")
                self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

    def test_current_persona_version_valid_npc(self) -> None:
        """Valid NPC metadata returns its integer persona_version."""
        self.assertIsNone(current_persona_version(self.npc))
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        self.assertEqual(current_persona_version(self.npc), 1)

    def test_current_persona_version_non_npc(self) -> None:
        """Non-NPC or None returns None."""
        self.assertIsNone(current_persona_version(None))
        self.assertIsNone(current_persona_version(object()))

    def test_current_persona_version_malformed_metadata_returns_none_and_never_writes(self) -> None:
        """Malformed metadata yields None without writing or repairing."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        bad_metas = (
            "not a dict",
            123,
            {},
            {"persona_version": True},
            {"persona_version": False},
            {"persona_version": 0},
            {"persona_version": -5},
            {"persona_version": "1"},
            {"persona_version": None},
        )
        for bad in bad_metas:
            with self.subTest(meta=bad):
                self.npc.db.npc_persona_meta = bad
                self.assertIsNone(current_persona_version(self.npc))
                # Verify raw attribute is not repaired or overwritten
                self.assertEqual(self.npc.db.npc_persona_meta, bad)

    def test_provenance_profile_key_reads_profile_provenance_only(self) -> None:
        """provenance_profile_key returns profile key for kind 'profile' and None for others."""
        self.assertIsNone(provenance_profile_key(None))
        self.assertIsNone(provenance_profile_key(self.char1))
        self.assertIsNone(provenance_profile_key(self.npc))

        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        self.assertEqual(provenance_profile_key(self.npc), "guard_01")

        # Companion provenance returns None
        self.npc.db.npc_persona_meta = {
            "format": 1,
            "generation": 1,
            "persona_version": 1,
            "provenance": {"kind": "companion", "profile": "partner_scout", "owner": 1},
        }
        self.assertIsNone(provenance_profile_key(self.npc))

        # Malformed metadata yields None without writing or repairing
        bad_metas = (
            "corrupt",
            {"provenance": "corrupt"},
            {"provenance": {"kind": "profile", "profile": ""}},
            {"provenance": {"kind": "profile", "profile": True}},
            {"provenance": {"kind": "profile", "profile": None}},
        )
        for bad in bad_metas:
            with self.subTest(bad=bad):
                self.npc.db.npc_persona_meta = bad
                self.assertIsNone(provenance_profile_key(self.npc))
                self.assertEqual(self.npc.db.npc_persona_meta, bad)


class NpcPersonaConcurrencyAndFailureTest(EvenniaTest):
    """Concurrency, SQL statement ordering, and fault injection tests (D4)."""

    def setUp(self) -> None:
        super().setUp()
        self.npc = create_object(NPC, key="測試NPC2")
        self.valid_card_raw = {
            "identity": {"public": "接待員", "hidden": ""},
            "appearance": "金髮碧眼。",
            "personality": "親切熱情。",
            "speech_style": "公事語氣。",
            "life_story": "王都長大。",
            "habit": "整理文件。",
            "social_connection": "",
        }
        self.provenance = {"kind": "profile", "profile": "receptionist_01"}
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_meta_change_behind_cache_detected_as_conflict(self) -> None:
        """A meta change written directly to DB behind the idmapper cache is detected as a conflict."""
        from evennia.typeclasses.attributes import Attribute
        attr = self.npc.db_attributes.get(db_key="npc_persona_meta")
        new_meta = dict(attr.db_value)
        new_meta["persona_version"] = 99
        Attribute.objects.filter(id=attr.id).update(db_value=new_meta)

        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

        new_card = dict(self.valid_card_raw)
        new_card["appearance"] = "染了黑髮。"
        res = update_npc_persona(self.npc, new_card, expected_version=1)
        self.assertEqual(res.status, "version_conflict")
        self.assertEqual(res.version, 99)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_guarded_update_precedes_meta_select(self) -> None:
        """CaptureQueriesContext shows the guarded UPDATE precedes the meta SELECT."""
        from django.db import connection

        new_card = dict(self.valid_card_raw)
        new_card["appearance"] = "染了黑髮。"

        with CaptureQueriesContext(connection) as queries:
            update_npc_persona(self.npc, new_card, expected_version=1)

        sql_statements = [q["sql"].upper() for q in queries]
        update_idx = None
        for i, sql in enumerate(sql_statements):
            if "UPDATE" in sql and "OBJECTDB" in sql:
                update_idx = i
                break
        self.assertIsNotNone(update_idx, f"Guarded UPDATE not found in SQL queries: {sql_statements}")

        select_idx = None
        for i, sql in enumerate(sql_statements[update_idx + 1:], start=update_idx + 1):
            if "SELECT" in sql and ("NPC_PERSONA_META" in sql or "DB_ATTRIBUTES" in sql or "ATTRIBUTE" in sql):
                select_idx = i
                break
        self.assertIsNotNone(select_idx, f"Meta SELECT not found after guarded UPDATE: {sql_statements}")
        self.assertLess(update_idx, select_idx)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_operational_error_yields_storage_unavailable_and_restores_cache(self) -> None:
        """A patched OperationalError during update yields storage_unavailable and restores caches."""
        new_card = dict(self.valid_card_raw)
        new_card["appearance"] = "新外觀"

        with patch("world.rules.npc_persona._lock_npc_row", side_effect=OperationalError("database locked")):
            res = update_npc_persona(self.npc, new_card, expected_version=1)

        self.assertEqual(res.status, "storage_unavailable")
        self.assertEqual(res.reason, "storage_unavailable")
        self.assertEqual(self.npc.db.persona["appearance"], "金髮碧眼。")
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_failure_after_card_write_restores_db_rows_and_caches(self) -> None:
        """A failure injected after card write rolls back DB rows and restores attribute caches."""
        new_card = dict(self.valid_card_raw)
        new_card["appearance"] = "新外觀"

        raw_persona_before = raw_attribute_value(self.npc, "persona")
        raw_meta_before = raw_attribute_value(self.npc, "npc_persona_meta")

        original_add = self.npc.attributes.add

        def faulty_add(key, value, **kwargs):
            if key == "npc_persona_meta":
                raise RuntimeError("simulated write crash")
            return original_add(key, value, **kwargs)

        with patch.object(self.npc.attributes, "add", side_effect=faulty_add):
            with self.assertRaises(RuntimeError):
                update_npc_persona(self.npc, new_card, expected_version=1)

        self.assertEqual(raw_attribute_value(self.npc, "persona"), raw_persona_before)
        self.assertEqual(raw_attribute_value(self.npc, "npc_persona_meta"), raw_meta_before)

        self.assertEqual(self.npc.db.persona["appearance"], "金髮碧眼。")
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 1)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_failure_after_greeting_write_restores_the_field(self) -> None:
        """A crash after the greeting write rolls back both a set and a cleared field."""
        original_add = self.npc.attributes.add

        def faulty_add(key, value, **kwargs):
            if key == "npc_persona_meta":
                raise RuntimeError("simulated write crash")
            return original_add(key, value, **kwargs)

        # Setting a new override over an absent field.
        with patch.object(self.npc.attributes, "add", side_effect=faulty_add):
            with self.assertRaises(RuntimeError):
                update_npc_persona(self.npc, self.valid_card_raw, expected_version=1, offline_greeting="「新的問候。」")
        self.assertIsNone(raw_attribute_value(self.npc, "npc_offline_greeting"))
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

        # Clearing an existing override.
        self.assertEqual(
            update_npc_persona(self.npc, self.valid_card_raw, expected_version=1, offline_greeting="「舊的問候。」").status,
            "updated",
        )
        with patch.object(self.npc.attributes, "add", side_effect=faulty_add):
            with self.assertRaises(RuntimeError):
                update_npc_persona(self.npc, self.valid_card_raw, expected_version=2, offline_greeting="")
        self.assertEqual(raw_attribute_value(self.npc, "npc_offline_greeting"), "「舊的問候。」")
        self.assertEqual(self.npc.db.npc_offline_greeting, "「舊的問候。」")
        self.assertEqual(self.npc.db.npc_persona_meta["persona_version"], 2)

    @covers_requirement("npc-persona-card::persona-writes-are-atomic-serialized-and-restore-caches-on-rollback")
    def test_sequential_same_version_updates_exactly_one_wins(self) -> None:
        """Exactly one of two sequential same-version updates wins; the second gets a version conflict."""
        card_a = dict(self.valid_card_raw)
        card_a["appearance"] = "外觀A"

        card_b = dict(self.valid_card_raw)
        card_b["appearance"] = "外觀B"

        res1 = update_npc_persona(self.npc, card_a, expected_version=1)
        res2 = update_npc_persona(self.npc, card_b, expected_version=1)

        self.assertEqual(res1.status, "updated")
        self.assertEqual(res1.version, 2)

        self.assertEqual(res2.status, "version_conflict")
        self.assertEqual(res2.version, 2)
        self.assertEqual(self.npc.db.persona["appearance"], "外觀A")


class NpcPersonaObservabilityTest(EvenniaTest):
    """Observability events testing (D5)."""

    def setUp(self) -> None:
        super().setUp()
        self.npc = create_object(NPC, key="觀察NPC")
        self.valid_card_raw = {
            "identity": {"public": "偵探", "hidden": "秘密探員"},
            "appearance": "風衣與禮帽。",
            "personality": "敏銳冷靜。",
            "speech_style": "謹慎推演。",
            "life_story": "解決了許多疑難懸案。",
            "habit": "點燃菸斗。",
            "social_connection": "警局內部有線人。",
        }
        self.provenance = {"kind": "profile", "profile": "detective_01"}

    @covers_requirement("npc-persona-card::persona-writers-emit-commit-bound-events-without-persona-text")
    @patch("world.rules.npc_persona.log_info")
    def test_initialization_event_on_commit_no_prose(self, mock_log_info: MagicMock) -> None:
        """Initialization emits npc_persona_initialized on commit without card text."""
        with self.captureOnCommitCallbacks(execute=True):
            initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)

        init_calls = [
            c for c in mock_log_info.call_args_list if c.args and c.args[0] == "npc_persona_initialized"
        ]
        self.assertEqual(len(init_calls), 1)
        ctx = init_calls[0].kwargs.get("context", {})
        self.assertEqual(ctx.get("npc"), str(self.npc.pk))
        self.assertEqual(ctx.get("source"), "profile")
        self.assertEqual(ctx.get("profile"), "detective_01")
        self.assertEqual(ctx.get("version"), 1)

        # Assert no prose from valid_card_raw appears in any context value
        all_prose_fragments = [
            "偵探", "秘密探員", "風衣與禮帽", "敏銳冷靜", "謹慎推演",
            "解決了許多疑難懸案", "點燃菸斗", "警局內部有線人"
        ]
        for val in ctx.values():
            for fragment in all_prose_fragments:
                self.assertNotIn(fragment, str(val))

    @covers_requirement("npc-persona-card::persona-writers-emit-commit-bound-events-without-persona-text")
    @patch("world.rules.npc_persona.log_info")
    def test_update_event_on_commit_no_prose(self, mock_log_info: MagicMock) -> None:
        """Update emits npc_persona_updated carrying versions and IDs, no prose."""
        with self.captureOnCommitCallbacks(execute=True):
            initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        mock_log_info.reset_mock()

        new_card = dict(self.valid_card_raw)
        new_card["appearance"] = "換穿了便服。"
        with self.captureOnCommitCallbacks(execute=True):
            res = update_npc_persona(self.npc, new_card, expected_version=1, actor=self.char1)
        self.assertEqual(res.status, "updated")

        update_calls = [
            c for c in mock_log_info.call_args_list if c.args and c.args[0] == "npc_persona_updated"
        ]
        self.assertEqual(len(update_calls), 1)
        ctx = update_calls[0].kwargs.get("context", {})
        self.assertEqual(ctx.get("npc"), str(self.npc.pk))
        self.assertEqual(ctx.get("char"), str(self.char1.pk))
        self.assertEqual(ctx.get("version_from"), 1)
        self.assertEqual(ctx.get("version_to"), 2)
        self.assertIs(ctx.get("card_changed"), True)
        self.assertIs(ctx.get("greeting_changed"), False)

        # Assert no prose in context values
        self.assertNotIn("換穿了便服", str(ctx))

    @covers_requirement("npc-persona-card::persona-writers-emit-commit-bound-events-without-persona-text")
    @patch("world.rules.npc_persona.log_info")
    def test_update_rejected_event_no_prose(self, mock_log_info: MagicMock) -> None:
        """Rejected update emits npc_persona_update_rejected with reason."""
        initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
        mock_log_info.reset_mock()

        res = update_npc_persona(self.npc, self.valid_card_raw, expected_version=99, actor=self.char1)
        self.assertEqual(res.status, "version_conflict")

        reject_calls = [
            c for c in mock_log_info.call_args_list if c.args and c.args[0] == "npc_persona_update_rejected"
        ]
        self.assertEqual(len(reject_calls), 1)
        ctx = reject_calls[0].kwargs.get("context", {})
        self.assertEqual(ctx.get("npc"), str(self.npc.pk))
        self.assertEqual(ctx.get("char"), str(self.char1.pk))
        self.assertEqual(ctx.get("reason"), "version_conflict")
        self.assertEqual(ctx.get("expected_version"), 99)
        self.assertEqual(ctx.get("current_version"), 1)

    @covers_requirement("npc-persona-card::reading-an-npc-persona-never-initializes-or-repairs-it")
    @patch("world.rules.npc_persona.log_warn")
    def test_unavailable_event(self, mock_log_warn: MagicMock) -> None:
        """read_npc_persona emits npc_persona_unavailable warn event."""
        res = read_npc_persona(self.npc)
        self.assertIsInstance(res, NpcPersonaUnavailable)

        unavail_calls = [
            c for c in mock_log_warn.call_args_list if c.args and c.args[0] == "npc_persona_unavailable"
        ]
        self.assertEqual(len(unavail_calls), 1)
        ctx = unavail_calls[0].kwargs.get("context", {})
        self.assertEqual(ctx.get("npc"), str(self.npc.pk))
        self.assertEqual(ctx.get("reason"), "missing_card")

    @covers_requirement("npc-persona-card::persona-writers-emit-commit-bound-events-without-persona-text")
    @patch("world.rules.npc_persona.log_info")
    def test_rolled_back_write_logs_no_success_event(self, mock_log_info: MagicMock) -> None:
        """A rolled-back write logs no success event."""
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    initialize_npc_persona(self.npc, self.valid_card_raw, self.provenance)
                    raise RuntimeError("simulated rollback")
            except RuntimeError:
                pass

        init_calls = [
            c for c in mock_log_info.call_args_list if c.args and c.args[0] == "npc_persona_initialized"
        ]
        self.assertEqual(len(init_calls), 0)
