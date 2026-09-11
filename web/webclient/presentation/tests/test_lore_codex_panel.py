"""Tests for the lore_codex presentation panel, presenter, and push seam.

Covers exact schema version 1, all eight CODE_CATEGORIES in mapping order,
non-disclosure of undiscovered entries, card fidelity from lore_card,
omission of vanished keys without record rewrite, read-only isolation,
host independence, corrupt record degradation to the common unavailable form,
strict bounds and envelope fail-closed enforcement, and push on new reveal
versus no push on repeat reveal.
"""

from copy import deepcopy
import unittest
from types import SimpleNamespace

from django.db import transaction
from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from web.webclient.presentation import watchers
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.lore_codex import (
    LORE_CODEX_CATEGORIES,
    LORE_CODEX_MAX_CARD_FIELDS,
    LORE_CODEX_MAX_ENTRIES_PER_CATEGORY,
    LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS,
    LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
    LORE_CODEX_MAX_KEY_CODE_POINTS,
    LORE_CODEX_MAX_LABEL_CODE_POINTS,
    LORE_CODEX_MAX_TITLE_CODE_POINTS,
    LORE_CODEX_MAX_TOTAL_ENTRIES,
    LORE_CODEX_SCHEMA_VERSION,
    LoreCodexPanelError,
    lore_codex_presenter,
    validate_lore_codex,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.rules.lore_knowledge import (
    CATEGORY_LABELS,
    LoreKeyError,
    lore_card,
    record_lore_reveal,
)
from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_NATIONS,
    SYNTH_RACES,
    synthetic_registries,
)

# Kit-authored lore rows: every disclosed entry resolves through these.
T_RACE = "t_duskmari"
T_NATION = "t_miremoth"
T_ANCHOR = "t_hollow_tarn"
T_ANCHOR_TITLE = SYNTH_ANCHORS[T_ANCHOR].display_name_zh


def _valid_category_group(key: str, label: str, entries: list[dict] | None = None) -> dict:
    entries = entries or []
    return {
        "key": key,
        "label": label,
        "count": len(entries),
        "entries": entries,
    }


def _valid_entry(key: str = "elf", title: str = "精靈", card: list[dict] | None = None) -> dict:
    card = card or [
        {"name": "key", "value": "elf"},
        {"name": "description", "value": "長壽種族"},
    ]
    return {
        "key": key,
        "title": title,
        "card": card,
    }


def _valid_payload(**overrides) -> dict:
    categories = [
        _valid_category_group("race", "種族", [_valid_entry(T_RACE, "暮色族裔")]),
        _valid_category_group("nation", "國家", []),
        _valid_category_group("region", "地域", []),
        _valid_category_group("monster", "魔物", []),
        _valid_category_group("element", "元素", []),
        _valid_category_group("magic", "魔法", []),
        _valid_category_group(
            "anchor",
            "地點",
            [
                _valid_entry(
                    T_ANCHOR,
                    T_ANCHOR_TITLE,
                    [
                        {"name": "display_name_zh", "value": T_ANCHOR_TITLE},
                        {"name": "description", "value": "帝國首都"},
                    ],
                )
            ],
        ),
        _valid_category_group("guild", "公會", []),
    ]
    payload = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "categories": categories,
        "discovered_total": 2,
    }
    payload.update(overrides)
    return payload


def _mock_player(lore_discovered=None):
    return SimpleNamespace(
        pk="42",
        db=SimpleNamespace(lore_discovered=lore_discovered),
    )


class LoreCodexValidatorTests(unittest.TestCase):
    """Exact-shape and bounds validation tests for validate_lore_codex."""

    def test_valid_payload_passes_and_preserves_structure(self):
        payload = _valid_payload()
        validated = validate_lore_codex(payload)
        self.assertEqual(validated["schema_version"], 1)
        self.assertIs(validated["available"], True)
        self.assertEqual(validated["discovered_total"], 2)
        self.assertEqual(len(validated["categories"]), len(LORE_CODEX_CATEGORIES))
        self.assertEqual(validated["categories"][0]["entries"][0]["key"], T_RACE)

    def test_empty_codex_payload_is_valid(self):
        categories = [
            _valid_category_group(cat, CATEGORY_LABELS[cat], [])
            for cat in LORE_CODEX_CATEGORIES
        ]
        payload = {
            "schema_version": 1,
            "available": True,
            "categories": categories,
            "discovered_total": 0,
        }
        validated = validate_lore_codex(payload)
        self.assertEqual(validated["discovered_total"], 0)
        self.assertTrue(all(g["count"] == 0 for g in validated["categories"]))
        self.assertTrue(all(g["entries"] == [] for g in validated["categories"]))

    def test_schema_version_mismatch_raises(self):
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(schema_version=2))

    def test_unavailable_discriminator_raises(self):
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(available=False))

    def test_categories_count_not_eight_raises(self):
        # 7 categories
        categories_7 = [
            _valid_category_group(cat, CATEGORY_LABELS[cat], [])
            for cat in LORE_CODEX_CATEGORIES[:7]
        ]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(categories=categories_7, discovered_total=0))

        # 9 categories
        categories_9 = categories_7 + [
            _valid_category_group("extra1", "額外1", []),
            _valid_category_group("extra2", "額外2", []),
        ]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(categories=categories_9, discovered_total=0))

    def test_reordered_categories_raise(self):
        payload = _valid_payload()
        # Swap race and nation
        payload["categories"][0], payload["categories"][1] = (
            payload["categories"][1],
            payload["categories"][0],
        )
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_count_mismatch_raises(self):
        payload = _valid_payload()
        payload["categories"][0]["count"] = 99
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_discovered_total_mismatch_raises(self):
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(discovered_total=99))

    def test_discovered_total_over_bound_raises(self):
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(discovered_total=LORE_CODEX_MAX_TOTAL_ENTRIES + 1))

    def test_extra_top_level_fields_raise(self):
        payload = _valid_payload(extra="unexpected")
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

    def test_extra_category_group_fields_raise(self):
        payload = _valid_payload()
        payload["categories"][0]["extra"] = "bad"
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

    def test_extra_entry_fields_raise(self):
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["extra"] = "bad"
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

    def test_extra_card_field_keys_raise(self):
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["extra"] = "bad"
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

    def test_empty_string_fields_raise(self):
        # Empty title
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["title"] = "   "
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

        # Empty card field name
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["name"] = ""
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

        # Empty category label
        payload = _valid_payload()
        payload["categories"][0]["label"] = ""
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_lone_surrogates_in_string_fields_raise(self):
        # Surrogate in entry key
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["key"] = "bad\ud800key"
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

        # Surrogate in title
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["title"] = "bad\ud800title"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

        # Surrogate in label
        payload = _valid_payload()
        payload["categories"][0]["label"] = "bad\ud800label"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

        # Surrogate in card field name
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["name"] = "bad\ud800name"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

        # Surrogate in card field value
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["value"] = "bad\ud800value"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_per_category_entry_bound_breach_raises(self):
        payload = _valid_payload()
        entries = [
            _valid_entry(f"entry_{i}", f"Title {i}")
            for i in range(LORE_CODEX_MAX_ENTRIES_PER_CATEGORY + 1)
        ]
        payload["categories"][0]["entries"] = entries
        payload["categories"][0]["count"] = len(entries)
        payload["discovered_total"] = len(entries) + 1
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_card_fields_bound_breach_raises(self):
        payload = _valid_payload()
        card_fields = [
            {"name": f"f_{i}", "value": f"v_{i}"}
            for i in range(LORE_CODEX_MAX_CARD_FIELDS + 1)
        ]
        payload["categories"][0]["entries"][0]["card"] = card_fields
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-and-fails-closed-on-registry-growth"
    )
    def test_envelope_byte_size_overflow_fails_closed(self):
        payload = _valid_payload()
        # Large payload exceeding MAX_CANONICAL_JSON_BYTES
        big_val = "x" * 1000
        entries = [
            _valid_entry(
                f"k_{i}",
                f"T_{i}",
                [{"name": f"f_{j}", "value": big_val} for j in range(LORE_CODEX_MAX_CARD_FIELDS)],
            )
            for i in range(25)
        ]
        payload["categories"][0]["entries"] = entries
        payload["categories"][0]["count"] = len(entries)
        payload["discovered_total"] = len(entries) + 1
        self.assertGreater(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-and-fails-closed-on-registry-growth"
    )
    def test_string_field_code_point_bounds_breach_raises(self):
        # Title: exactly one code point over the bound is rejected.
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["title"] = "字" * (
            LORE_CODEX_MAX_TITLE_CODE_POINTS + 1
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

        # Category label: exactly one code point over the bound is rejected.
        payload = _valid_payload()
        payload["categories"][0]["label"] = "字" * (
            LORE_CODEX_MAX_LABEL_CODE_POINTS + 1
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

        # Card field name: exactly one code point over the bound is rejected.
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["name"] = "n" * (
            LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS + 1
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

        # Card field value: exactly one code point over the bound is rejected.
        payload = _valid_payload()
        payload["categories"][0]["entries"][0]["card"][0]["value"] = "v" * (
            LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS + 1
        )
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)


@synthetic_registries("races", "nations", "anchors")
class LoreCodexPresenterTests(unittest.TestCase):
    """Presenter behavior, degradation, non-disclosure, and read-only tests."""

    def _context(self, actor):
        return PresentationContext(actor=actor, protocol_version=1)

    def test_no_actor_raises_panel_unavailable(self):
        context = self._context(None)
        with self.assertRaises(PanelUnavailableError):
            lore_codex_presenter(context)

    def test_empty_record_returns_available_empty_codex(self):
        player = _mock_player(lore_discovered=None)
        payload = lore_codex_presenter(self._context(player))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["discovered_total"], 0)
        self.assertEqual(len(payload["categories"]), len(LORE_CODEX_CATEGORIES))
        for cat in payload["categories"]:
            self.assertEqual(cat["count"], 0)
            self.assertEqual(cat["entries"], [])

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-1-presentation-panel"
    )
    def test_two_discoveries_serialize_exactly(self):
        player = _mock_player(lore_discovered={f"race:{T_RACE}", f"anchor:{T_ANCHOR}"})
        payload = lore_codex_presenter(self._context(player))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["discovered_total"], 2)

        # Check mapping order of categories
        category_keys = [c["key"] for c in payload["categories"]]
        self.assertEqual(tuple(category_keys), LORE_CODEX_CATEGORIES)

        # Race group has 1 entry
        race_group = payload["categories"][0]
        self.assertEqual(race_group["key"], "race")
        self.assertEqual(race_group["label"], "種族")
        self.assertEqual(race_group["count"], 1)
        self.assertEqual(len(race_group["entries"]), 1)
        elf_entry = race_group["entries"][0]
        self.assertEqual(elf_entry["key"], T_RACE)
        # The races card defines no display_name_zh: the title falls back to
        # the key, whatever the synthetic row is.
        self.assertEqual(elf_entry["title"], T_RACE)

        # Anchor group has 1 entry
        anchor_group = next(c for c in payload["categories"] if c["key"] == "anchor")
        self.assertEqual(anchor_group["count"], 1)
        anchor_entry = anchor_group["entries"][0]
        self.assertEqual(anchor_entry["key"], T_ANCHOR)
        self.assertEqual(anchor_entry["title"], T_ANCHOR_TITLE)

        # Every other group is empty
        for cat in payload["categories"]:
            if cat["key"] not in ("race", "anchor"):
                self.assertEqual(cat["count"], 0)
                self.assertEqual(cat["entries"], [])

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-discloses-only-what-the-holder-discovered"
    )
    def test_non_disclosure_undiscovered_entries_absent_and_no_denominators(self):
        player = _mock_player(lore_discovered={f"race:{T_RACE}"})
        payload = lore_codex_presenter(self._context(player))
        race_entries = payload["categories"][0]["entries"]
        self.assertEqual(len(race_entries), 1)
        self.assertEqual(race_entries[0]["key"], T_RACE)

        # Ensure no other race keys are disclosed
        disclosed = [e["key"] for e in race_entries]
        # A single reveal discloses exactly that entry: no other kit row
        # leaks into the group.
        self.assertEqual(disclosed, [T_RACE])
        for other in (*SYNTH_RACES, *SYNTH_NATIONS):
            if other != T_RACE:
                self.assertNotIn(other, disclosed)

        # Ensure no denominators, completion ratios, or capacity placeholders exist
        raw_repr = repr(payload)
        self.assertNotIn("denominator", raw_repr)
        self.assertNotIn("ratio", raw_repr)
        self.assertNotIn("total_possible", raw_repr)
        self.assertNotIn("capacity", raw_repr)
        self.assertNotIn("placeholder", raw_repr)

    def test_card_fidelity_matches_lore_card_field_for_field(self):
        player = _mock_player(lore_discovered={f"nation:{T_NATION}"})
        payload = lore_codex_presenter(self._context(player))
        nation_group = next(c for c in payload["categories"] if c["key"] == "nation")
        entry = nation_group["entries"][0]

        expected_card = lore_card("nation", T_NATION)
        rendered_card = {f["name"]: f["value"] for f in entry["card"]}
        self.assertEqual(rendered_card, expected_card)

        # Field order in card list matches lore_card keys
        card_field_names = [f["name"] for f in entry["card"]]
        self.assertEqual(card_field_names, list(expected_card.keys()))

    @covers_requirement(
        "webclient-lore-codex-panel::cards-are-rendered-by-the-canonical-renderer-never-composed-by-the-presenter"
    )
    def test_vanished_registry_key_omitted_without_failing_or_rewriting_record(self):
        # A stored entry whose registry key no longer exists
        initial_record = {f"race:{T_RACE}", "race:vanished_key_xyz"}
        player = _mock_player(lore_discovered=set(initial_record))

        payload = lore_codex_presenter(self._context(player))
        self.assertTrue(payload["available"])
        race_group = payload["categories"][0]
        self.assertEqual(race_group["count"], 1)
        self.assertEqual(race_group["entries"][0]["key"], T_RACE)
        self.assertEqual(payload["discovered_total"], 1)

        # Stored record is byte-for-byte / value unchanged
        self.assertEqual(player.db.lore_discovered, initial_record)

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-1-presentation-panel"
    )
    def test_read_only_isolation_building_twice_leaves_record_unchanged(self):
        record = {f"race:{T_RACE}", f"anchor:{T_ANCHOR}"}
        player = _mock_player(lore_discovered=set(record))

        first_payload = lore_codex_presenter(self._context(player))
        first_record_state = deepcopy(player.db.lore_discovered)

        second_payload = lore_codex_presenter(self._context(player))
        second_record_state = deepcopy(player.db.lore_discovered)

        self.assertEqual(first_record_state, set(record))
        self.assertEqual(second_record_state, set(record))
        self.assertEqual(first_payload, second_payload)

    @covers_requirement(
        "webclient-lore-codex-panel::a-corrupt-codex-record-degrades-the-whole-panel-and-repairs-nothing"
    )
    def test_corrupt_record_degrades_whole_panel_without_repairing_stored_record(self):
        for corrupt in (
            "not-a-set",
            {f"race:{T_RACE}", 42},
            {"elf_not_namespaced"},
            {"bogus_category:race"},
            {"race:"},
            {"race:extra:extra"},
        ):
            with self.subTest(corrupt=corrupt):
                corrupt_copy = deepcopy(corrupt)
                player = _mock_player(lore_discovered=corrupt)
                with self.assertRaises(PanelUnavailableError):
                    lore_codex_presenter(self._context(player))
                # Stored record was not reset, deleted, or repaired
                self.assertEqual(player.db.lore_discovered, corrupt_copy)

    def test_registry_build_unavailable_matches_registered_reason(self):
        registry = build_production_registry()
        spec = registry.spec("lore_codex")
        self.assertEqual(spec.schema_version, 1)
        self.assertEqual(
            spec.unavailable_reason,
            ("lore_codex_unavailable", "知識圖鑑目前無法顯示"),
        )
        unavailable = registry.build_unavailable("lore_codex")
        self.assertEqual(unavailable["schema_version"], 1)
        self.assertIs(unavailable["available"], False)
        self.assertEqual(unavailable["reason"]["code"], "lore_codex_unavailable")
        self.assertEqual(unavailable["reason"]["message"], "知識圖鑑目前無法顯示")


@synthetic_registries("races", "nations", "anchors")
class LoreCodexIntegrationTests(EvenniaTest):
    """Evennia integration tests: host independence, push triggers, and coordinator snapshots."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.registry = build_production_registry()

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-host-independent"
    )
    def test_host_independence_codex_readable_in_empty_room(self):
        # Room with no NPC or host present; the reveal targets a kit row.
        empty_room = create_object(Room, key="荒野孤地")
        self.char1.location = empty_room
        record_lore_reveal(self.char1, "race", T_RACE)

        context = PresentationContext(actor=self.char1, protocol_version=1)
        payload = self.registry.render("lore_codex", context)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["discovered_total"], 1)
        self.assertEqual(payload["categories"][0]["entries"][0]["key"], T_RACE)

    def _open_watched_session(self, recorded: list):
        """A live session with a coordinator, full snapshot, and watcher registration."""
        session = ServerSession()
        session.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        session.sessid = 942
        self.sessionhandler[session.sessid] = session
        session.protocol_key = "webclient/websocket"
        session.puppet = self.char1
        self.char1.sessions.add(session)

        session.msg = lambda **kwargs: recorded.append(kwargs)

        coordinator = PresentationCoordinator(session, self.registry)
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.char1, protocol_version=1)
        )
        watchers.register_watcher(session)
        return session

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-pushed-when-a-discovery-lands"
    )
    def test_push_on_new_reveal_and_no_push_on_repeat_reveal(self):
        # Set up a live session with coordinator and watcher
        recorded: list = []
        session = self._open_watched_session(recorded)

        try:
            # 1. New reveal: must push update
            recorded.clear()
            with self.captureOnCommitCallbacks(execute=True):
                record_lore_reveal(self.char1, "race", T_RACE)

            updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
            self.assertTrue(updates, "new lore reveal must push ui_update")
            pushed_panel = updates[-1]["panels"]["lore_codex"]
            self.assertTrue(pushed_panel["available"])
            self.assertEqual(pushed_panel["discovered_total"], 1)
            self.assertEqual(pushed_panel["categories"][0]["entries"][0]["key"], T_RACE)

            # 2. Repeat reveal: must NOT push
            recorded.clear()
            with self.captureOnCommitCallbacks(execute=True):
                record_lore_reveal(self.char1, "race", T_RACE)

            updates_repeat = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
            self.assertFalse(updates_repeat, "repeat reveal of existing entry must NOT push")

        finally:
            del self.sessionhandler[session.sessid]

    def test_rolled_back_reveal_pushes_nothing(self):
        # A reveal inside an outer transaction that rolls back must never reach a
        # live client: on_commit callbacks are discarded on rollback, and there is
        # no inline-push fallback.
        recorded: list = []
        session = self._open_watched_session(recorded)

        try:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError), transaction.atomic():
                    record_lore_reveal(self.char1, "race", T_RACE)
                    raise RuntimeError("injected caller failure")

            updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
            self.assertFalse(updates, "rolled-back reveal must never push to a live client")
        finally:
            del self.sessionhandler[session.sessid]
