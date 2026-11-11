"""Tests for the lore_codex presentation panel, presenter, and push seam.

Covers the exact schema-version-2 tile wall: all eight CODE_CATEGORIES in
mapping order with registry totals, one slot per registry entry in registry
order, identity-free placeholders, monster tier groups, stage-gated monster
cards, art descriptors built read-only from the existing pipelines, the
placeholder-then-art envelope trimming with its fail-closed path, omission of
vanished keys without record rewrite, corrupt-record degradation, host
independence, and push on a new reveal versus none on a repeat reveal.

Every registry entry is a synthetic kit row or a factory-built row.
"""

import json
import unittest
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from web.webclient.presentation import lore_codex as lore_codex_module
from web.webclient.presentation import watchers
from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.lore_codex import (
    LORE_CODEX_CATEGORIES,
    LORE_CODEX_MAX_CARD_FIELDS,
    LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS,
    LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
    LORE_CODEX_MAX_GROUPS_PER_CATEGORY,
    LORE_CODEX_MAX_KEY_CODE_POINTS,
    LORE_CODEX_MAX_LABEL_CODE_POINTS,
    LORE_CODEX_MAX_SLOTS_PER_CATEGORY,
    LORE_CODEX_MAX_TITLE_CODE_POINTS,
    LORE_CODEX_MAX_TOTAL_SLOTS,
    LORE_CODEX_MAX_VARIANT_LINES,
    LORE_CODEX_SCHEMA_VERSION,
    LoreCodexPanelError,
    _trim_to_envelope,
    lore_codex_presenter,
    validate_lore_codex,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    check_json_safety,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.art.store import ArtAssetRecord
from world.art.subjects import monster_subject_for
from world.rules.lore_knowledge import (
    CATEGORY_LABELS,
    CODE_CATEGORIES,
    lore_card,
    record_lore_reveal,
    species_card,
)
from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_RACES,
    make_guild_rank,
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    make_region,
    synthetic_registries,
)

# Kit-authored lore rows: every disclosed entry resolves through these.
T_RACE = "t_duskmari"
T_NATION = "t_miremoth"
T_ANCHOR = "t_hollow_tarn"
T_ANCHOR_TITLE = SYNTH_ANCHORS[T_ANCHOR].display_name_zh

# Monster rows: the kit species (first tier) plus two factory species, one of
# the second tier between two of the first, and one tier no species uses.
T_SPECIES = "t_whisper_quail"
T_FAINT, T_RIVEN = tuple(SYNTH_MONSTER_TIERS)
T_RIVEN_SPECIES = "t_codex_riven_species"
T_FAINT_SPECIES = "t_codex_faint_species"
T_EMPTY_TIER = "t_codex_empty_tier"
T_ART_REGION = "t_codex_art_region"
T_ART_ARCHETYPE = "t_synth_bazaar"
AUTHOR_MARKERS = tuple(
    getattr(SYNTH_MONSTER_SPECIES[T_SPECIES], field)
    for field in ("author_hidden_truth_zh", "author_explanation_zh", "author_conjecture_zh")
)


def _species_rows(key: str, tier: str, name: str) -> tuple[object, object]:
    variant_key = f"{key}_v"
    return (
        make_monster_species(key, display_name_zh=name, default_variant_key=variant_key),
        make_monster_variant(
            variant_key,
            species_key=key,
            threat_tier=tier,
            ordinary_variant=True,
            danger_grade=None,
        ),
    )


_RIVEN = _species_rows(T_RIVEN_SPECIES, T_RIVEN, "裂測獸")
_FAINT = _species_rows(T_FAINT_SPECIES, T_FAINT, "微測獸")

PRESENTER_TARGETS = (
    "races",
    "nations",
    "regions",
    "anchors",
    "elements",
    "magic_tiers",
    "guild_ranks",
    "monster_species",
    "monster_variants",
    "monster_tiers",
    "archetypes",
)
PRESENTER_EXTRA = {
    "monster_species": {T_RIVEN_SPECIES: _RIVEN[0], T_FAINT_SPECIES: _FAINT[0]},
    "monster_variants": {_RIVEN[1].key: _RIVEN[1], _FAINT[1].key: _FAINT[1]},
    "monster_tiers": {T_EMPTY_TIER: make_monster_tier(T_EMPTY_TIER, display_name_zh="空測級")},
    "regions": {
        T_ART_REGION: make_region(
            T_ART_REGION, display_name_zh="測圖地", scene_archetype=T_ART_ARCHETYPE
        )
    },
}


# ---------------------------------------------------------------------------
# Hand-built payloads for the validator
# ---------------------------------------------------------------------------


def _entry(key: str, title: str, *, stage=None, card=None, locked=None, art=None) -> dict:
    return {
        "key": key,
        "title": title,
        "stage": stage,
        "art": art,
        "card": card
        if card is not None
        else [{"name": "display_name_zh", "value": title}, {"name": "description", "value": "合成描述"}],
        "locked_fields": locked if locked is not None else [],
    }


def _placeholder() -> dict:
    return {"placeholder": True}


def _category(key: str, slots: list, *, groups=None, total=None) -> dict:
    if groups is None:
        groups = [{"key": key, "label": None, "slots": slots}]
    all_slots = [slot for group in groups for slot in group["slots"]]
    return {
        "key": key,
        "label": CATEGORY_LABELS[key],
        "discovered": sum(1 for slot in all_slots if "key" in slot),
        "total": len(all_slots) if total is None else total,
        "groups": groups,
    }


def _monster_entry(stage: str = "sighted") -> dict:
    locked = ["published_description_zh", "variants"] if stage == "sighted" else []
    return _entry(
        "t_beast",
        "合成獸",
        stage=stage,
        card=[
            {"name": "display_name_zh", "value": "合成獸"},
            {"name": "threat_tier", "value": "合成級"},
        ],
        locked=locked,
    )


def _valid_payload(**overrides) -> dict:
    categories = [
        _category("race", [_entry(T_RACE, "暮色族裔"), _placeholder()]),
        _category("nation", [_placeholder()]),
        _category("region", [_placeholder(), _placeholder()]),
        _category(
            "monster",
            [],
            groups=[
                {"key": "t_tier_a", "label": "甲級", "slots": [_monster_entry(), _placeholder()]},
                {"key": "t_tier_b", "label": "乙級", "slots": [_placeholder()]},
            ],
        ),
        _category("element", [_placeholder()]),
        _category("magic", []),
        _category("anchor", [_entry(T_ANCHOR, T_ANCHOR_TITLE)]),
        _category("guild", [_placeholder()]),
    ]
    payload = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "discovered_total": sum(c["discovered"] for c in categories),
        "total": sum(c["total"] for c in categories),
        "categories": categories,
    }
    payload.update(overrides)
    return payload


def _race_entry(payload: dict) -> dict:
    return payload["categories"][0]["groups"][0]["slots"][0]


def _monster(payload: dict) -> dict:
    return payload["categories"][LORE_CODEX_CATEGORIES.index("monster")]


def _rebalance(payload: dict) -> dict:
    """Recompute every count after a test edited slots."""
    for category in payload["categories"]:
        slots = [slot for group in category["groups"] for slot in group["slots"]]
        category["discovered"] = sum(1 for slot in slots if "key" in slot)
        category["total"] = max(category["total"], len(slots))
    payload["discovered_total"] = sum(c["discovered"] for c in payload["categories"])
    payload["total"] = sum(c["total"] for c in payload["categories"])
    return payload


class LoreCodexValidatorTests(unittest.TestCase):
    """Exact-shape and bounds validation tests for validate_lore_codex."""

    def test_valid_payload_passes_and_preserves_structure(self):
        validated = validate_lore_codex(_valid_payload())
        self.assertEqual(validated["schema_version"], 2)
        self.assertIs(validated["available"], True)
        self.assertEqual(validated["discovered_total"], 3)
        self.assertEqual(validated["total"], 11)
        self.assertEqual(
            tuple(c["key"] for c in validated["categories"]), LORE_CODEX_CATEGORIES
        )
        self.assertEqual(_race_entry(validated)["key"], T_RACE)
        self.assertEqual(validated["categories"][0]["groups"][0]["slots"][1], {"placeholder": True})

    def test_monster_category_with_zero_groups_and_empty_groups_are_valid(self):
        payload = _valid_payload()
        payload["categories"][3] = _category("monster", [], groups=[])
        validated = validate_lore_codex(_rebalance(payload))
        self.assertEqual(_monster(validated)["groups"], [])
        # A group trimmed down to no slots stays legal (placeholder trimming).
        payload = _valid_payload()
        payload["categories"][1]["groups"][0]["slots"] = []
        validate_lore_codex(payload)

    def test_schema_version_and_availability_are_exact(self):
        for overrides in ({"schema_version": 1}, {"schema_version": 3}, {"available": False}):
            with self.subTest(overrides=overrides), self.assertRaises(LoreCodexPanelError):
                validate_lore_codex(_valid_payload(**overrides))

    def test_category_list_must_be_the_eight_in_mapping_order(self):
        payload = _valid_payload()
        payload["categories"] = payload["categories"][:7]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"].append(_category("race", []))
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"][0], payload["categories"][1] = (
            payload["categories"][1],
            payload["categories"][0],
        )
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_extra_fields_at_every_level_raise(self):
        edits = (
            lambda p: p.update(extra=1),
            lambda p: p["categories"][0].update(extra=1),
            lambda p: p["categories"][0]["groups"][0].update(extra=1),
            lambda p: _race_entry(p).update(extra=1),
            lambda p: _race_entry(p)["card"][0].update(extra=1),
            lambda p: p["categories"][0].update(count=1),
            lambda p: p["categories"][0].update(entries=[]),
        )
        for index, edit in enumerate(edits):
            payload = _valid_payload()
            edit(payload)
            with self.subTest(edit=index), self.assertRaises(ProtocolValidationError):
                validate_lore_codex(payload)

    def test_an_identifying_placeholder_is_rejected(self):
        for extra in ({"key": "t_hidden"}, {"title": "隱藏"}, {"art": None}, {"stage": None}):
            payload = _valid_payload()
            payload["categories"][0]["groups"][0]["slots"][1].update(extra)
            with self.subTest(extra=extra), self.assertRaises(ProtocolValidationError):
                validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"][0]["groups"][0]["slots"][1]["placeholder"] = 1
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_counts_must_match_the_slots(self):
        payload = _valid_payload()
        payload["categories"][0]["discovered"] = 2
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"][0]["total"] = 1
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(discovered_total=99))
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_valid_payload(total=99))
        # A total above the shipped slots (a trimmed view) stays legal.
        payload = _valid_payload()
        payload["categories"][0]["total"] += 3
        payload["total"] += 3
        validate_lore_codex(payload)

    def test_group_rules_per_category(self):
        payload = _valid_payload()
        payload["categories"][0]["groups"].append({"key": "t_more", "label": None, "slots": []})
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"][0]["groups"][0]["label"] = "標籤"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][0]["label"] = None
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][1]["key"] = "t_tier_a"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        for key in ("", "t:tier", "k" * (LORE_CODEX_MAX_KEY_CODE_POINTS + 1)):
            payload = _valid_payload()
            _monster(payload)["groups"][0]["key"] = key
            with self.subTest(key=key), self.assertRaises(ProtocolValidationError):
                validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"] = [
            {"key": f"t_tier_{i}", "label": "級", "slots": []}
            for i in range(LORE_CODEX_MAX_GROUPS_PER_CATEGORY + 1)
        ]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_rebalance(payload))

    def test_stage_rules(self):
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0]["stage"] = None
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _race_entry(payload)["stage"] = "sighted"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0] = _monster_entry("defeated")
        validate_lore_codex(payload)

    def test_locked_field_rules(self):
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0]["stage"] = "defeated"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0]["locked_fields"] = ["threat_tier"]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0]["locked_fields"] = ["variants", "variants"]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _monster(payload)["groups"][0]["slots"][0]["locked_fields"] = [
            f"t_locked_{i}" for i in range(LORE_CODEX_MAX_CARD_FIELDS + 1)
        ]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _race_entry(payload)["locked_fields"] = ["description_more"]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_variant_lines_are_bounded(self):
        payload = _valid_payload()
        entry = _monster(payload)["groups"][0]["slots"][0]
        entry["stage"], entry["locked_fields"] = "defeated", []
        entry["card"].append(
            {"name": "variants", "value": "\n".join(["型"] * LORE_CODEX_MAX_VARIANT_LINES)}
        )
        validate_lore_codex(payload)
        entry["card"][-1]["value"] += "\n型"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_card_rules(self):
        payload = _valid_payload()
        _race_entry(payload)["card"] = [
            {"name": f"f_{i}", "value": "v"} for i in range(LORE_CODEX_MAX_CARD_FIELDS + 1)
        ]
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)
        payload = _valid_payload()
        _race_entry(payload)["card"][1]["name"] = "display_name_zh"
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)

    def test_entry_keys_are_opaque_unique_and_well_formed(self):
        for key in (None, 42, "", ":entry", "entry:other", "entry:", "bad\ud800key"):
            payload = _valid_payload()
            _race_entry(payload)["key"] = key
            with self.subTest(key=key), self.assertRaises(ProtocolValidationError):
                validate_lore_codex(payload)
        payload = _valid_payload()
        payload["categories"][0]["groups"][0]["slots"][1] = _entry(T_RACE, "重複")
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_rebalance(payload))

    def test_art_must_be_null_or_a_valid_descriptor(self):
        payload = _valid_payload()
        _race_entry(payload)["art"] = {"subject_id": "t"}
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(payload)

    def test_empty_and_surrogate_strings_raise(self):
        edits = (
            lambda p: _race_entry(p).update(title="   "),
            lambda p: _race_entry(p).update(title="bad\ud800title"),
            lambda p: _race_entry(p)["card"][0].update(name=""),
            lambda p: _race_entry(p)["card"][0].update(name="bad\ud800name"),
            lambda p: _race_entry(p)["card"][0].update(value="bad\ud800value"),
            lambda p: p["categories"][0].update(label=""),
            lambda p: p["categories"][0].update(label="bad\ud800label"),
        )
        for index, edit in enumerate(edits):
            payload = _valid_payload()
            edit(payload)
            with self.subTest(edit=index), self.assertRaises(LoreCodexPanelError):
                validate_lore_codex(payload)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_string_field_code_point_bounds_breach_raises(self):
        edits = (
            lambda p: _race_entry(p).update(key="k" * (LORE_CODEX_MAX_KEY_CODE_POINTS + 1)),
            lambda p: _race_entry(p).update(title="字" * (LORE_CODEX_MAX_TITLE_CODE_POINTS + 1)),
            lambda p: p["categories"][0].update(label="字" * (LORE_CODEX_MAX_LABEL_CODE_POINTS + 1)),
            lambda p: _race_entry(p)["card"][0].update(
                name="n" * (LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS + 1)
            ),
            lambda p: _race_entry(p)["card"][0].update(
                value="v" * (LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS + 1)
            ),
        )
        for index, edit in enumerate(edits):
            payload = _valid_payload()
            edit(payload)
            with self.subTest(edit=index), self.assertRaises(ProtocolValidationError):
                validate_lore_codex(payload)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_slot_bounds_per_category_and_in_total(self):
        payload = _valid_payload()
        payload["categories"][0]["groups"][0]["slots"] = [
            _placeholder() for _ in range(LORE_CODEX_MAX_SLOTS_PER_CATEGORY + 1)
        ]
        payload["categories"][0]["total"] = LORE_CODEX_MAX_SLOTS_PER_CATEGORY + 1
        with self.assertRaises(ProtocolValidationError):
            validate_lore_codex(_rebalance(payload))
        # 512 shipped slots pass; a top-level total of 513 does not, even
        # though no more than 512 slots ship.
        payload = _valid_payload()
        for category in payload["categories"]:
            category["groups"] = category["groups"][:1] or [
                {"key": "t_tier_a", "label": "甲級", "slots": []}
            ]
            category["groups"][0]["slots"] = [_placeholder() for _ in range(64)]
            category["total"] = 64
        validate_lore_codex(_rebalance(payload))
        payload["categories"][0]["total"] = 65
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(_rebalance(payload))

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_envelope_byte_size_overflow_fails_closed(self):
        payload = _valid_payload()
        payload["categories"][0]["groups"][0]["slots"] = [
            _entry(
                f"k_{i}",
                f"T_{i}",
                card=[{"name": f"f_{j}", "value": "x" * 1000} for j in range(LORE_CODEX_MAX_CARD_FIELDS)],
            )
            for i in range(25)
        ]
        payload = _rebalance(payload)
        self.assertGreater(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(LoreCodexPanelError):
            validate_lore_codex(payload)


class LoreCodexTrimTests(unittest.TestCase):
    """The incremental trim drops exactly as much as the limit demands."""

    ART = {"t_art": "像" * 40}

    def _payload(self) -> dict:
        # Groups that empty completely when their placeholders go, a
        # single-element list, and art on several entry slots.
        def entry(key):
            slot = _entry(key, "合成")
            slot["art"] = dict(self.ART)
            return slot

        return {
            "categories": [
                {"groups": [{"slots": [entry("t_a"), _placeholder(), _placeholder()]}]},
                {"groups": [{"slots": [_placeholder()]}, {"slots": [entry("t_b")]}]},
                {"groups": [{"slots": [entry("t_c"), _placeholder()]}, {"slots": [_placeholder()]}]},
            ]
        }

    @staticmethod
    def _drop_trailing_placeholders(payload: dict, count: int) -> dict:
        expected = deepcopy(payload)
        for category in reversed(expected["categories"]):
            for group in reversed(category["groups"]):
                for index in reversed(range(len(group["slots"]))):
                    if count and "placeholder" in group["slots"][index]:
                        del group["slots"][index]
                        count -= 1
        return expected

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed",
    )
    def test_placeholders_drop_exactly_until_the_payload_fits(self):
        payload = self._payload()
        for count in range(1, 6):
            expected = self._drop_trailing_placeholders(payload, count)
            trimmed = deepcopy(payload)
            with self.subTest(count=count), patch.object(
                lore_codex_module, "MAX_CANONICAL_JSON_BYTES", json_byte_size(expected)
            ):
                _trim_to_envelope(trimmed)
                self.assertEqual(trimmed, expected)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed",
    )
    def test_art_drops_from_the_last_entry_after_every_placeholder(self):
        payload = self._payload()
        no_placeholders = self._drop_trailing_placeholders(payload, 5)
        entries = [
            slot
            for category in no_placeholders["categories"]
            for group in category["groups"]
            for slot in group["slots"]
        ]
        for count in range(1, 4):
            expected = deepcopy(no_placeholders)
            expected_entries = [
                slot
                for category in expected["categories"]
                for group in category["groups"]
                for slot in group["slots"]
            ]
            for slot in expected_entries[len(entries) - count :]:
                slot["art"] = None
            trimmed = deepcopy(payload)
            with self.subTest(count=count), patch.object(
                lore_codex_module, "MAX_CANONICAL_JSON_BYTES", json_byte_size(expected)
            ):
                _trim_to_envelope(trimmed)
                self.assertEqual(trimmed, expected)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed",
    )
    def test_nothing_left_to_trim_fails_closed(self):
        with patch.object(lore_codex_module, "MAX_CANONICAL_JSON_BYTES", 10):
            with self.assertRaises(LoreCodexPanelError):
                _trim_to_envelope(self._payload())


def _mock_player(lore_discovered=None, lore_species_defeated=None):
    return SimpleNamespace(
        pk="42",
        db=SimpleNamespace(
            lore_discovered=lore_discovered, lore_species_defeated=lore_species_defeated
        ),
    )


def _slots(category: dict) -> list:
    return [slot for group in category["groups"] for slot in group["slots"]]


def _by_key(payload: dict, key: str) -> dict:
    return payload["categories"][LORE_CODEX_CATEGORIES.index(key)]


def _entry_slot(payload: dict, category: str, key: str) -> dict:
    return next(slot for slot in _slots(_by_key(payload, category)) if slot.get("key") == key)


@synthetic_registries(*PRESENTER_TARGETS, extra=PRESENTER_EXTRA)
class LoreCodexPresenterTests(EvenniaTestCase):
    """Presenter behavior, degradation, non-disclosure, art, and read-only tests."""

    def _render(self, player):
        return lore_codex_presenter(PresentationContext(actor=player, protocol_version=1))

    def test_no_actor_raises_panel_unavailable(self):
        with self.assertRaises(PanelUnavailableError):
            lore_codex_presenter(PresentationContext(actor=None, protocol_version=1))

    def test_empty_record_returns_available_all_placeholder_codex(self):
        payload = self._render(_mock_player())
        self.assertTrue(payload["available"])
        self.assertEqual(payload["discovered_total"], 0)
        for category in payload["categories"]:
            self.assertEqual(category["discovered"], 0)
            self.assertTrue(all(slot == {"placeholder": True} for slot in _slots(category)))

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-2-presentation-panel",
        "webclient-lore-codex-panel::codex-entry-titles-are-the-registry-s-display-names",
    )
    def test_two_discoveries_serialize_exactly(self):
        payload = self._render(
            _mock_player(lore_discovered={f"race:{T_RACE}", f"anchor:{T_ANCHOR}"})
        )
        self.assertEqual(
            set(payload), {"schema_version", "available", "discovered_total", "total", "categories"}
        )
        self.assertEqual(payload["discovered_total"], 2)
        self.assertEqual(tuple(c["key"] for c in payload["categories"]), LORE_CODEX_CATEGORIES)
        for category in payload["categories"]:
            self.assertEqual(set(category), {"key", "label", "discovered", "total", "groups"})
            self.assertEqual(category["label"], CATEGORY_LABELS[category["key"]])
            for group in category["groups"]:
                self.assertEqual(set(group), {"key", "label", "slots"})
            registry = CODE_CATEGORIES[category["key"]].registry
            if category["key"] != "monster":
                # One slot per registry entry in registry order.
                keys = [
                    slot.get("key") for slot in _slots(category)
                ]
                expected = [
                    key if (category["key"], key) in (("race", T_RACE), ("anchor", T_ANCHOR)) else None
                    for key in registry
                ]
                self.assertEqual(keys, expected)
        race = _entry_slot(payload, "race", T_RACE)
        self.assertEqual(set(race), {"key", "title", "stage", "art", "card", "locked_fields"})
        # The title is the registry's display name; the key stays opaque.
        self.assertEqual(race["title"], SYNTH_RACES[T_RACE].display_name_zh)
        self.assertNotIn(T_RACE, [field["value"] for field in race["card"]])
        self.assertEqual(_entry_slot(payload, "anchor", T_ANCHOR)["title"], T_ANCHOR_TITLE)

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-2-presentation-panel",
    )
    def test_totals_count_the_registry_and_non_monster_categories_have_one_unlabeled_group(self):
        payload = self._render(_mock_player(lore_discovered={f"race:{T_RACE}"}))
        for category in payload["categories"]:
            registry = CODE_CATEGORIES[category["key"]].registry
            self.assertEqual(category["total"], len(registry))
            self.assertEqual(len(_slots(category)), len(registry))
            self.assertEqual(
                category["discovered"], sum(1 for slot in _slots(category) if "key" in slot)
            )
            if category["key"] != "monster":
                self.assertEqual(len(category["groups"]), 1)
                self.assertIsNone(category["groups"][0]["label"])
        self.assertEqual(payload["total"], sum(c["total"] for c in payload["categories"]))
        self.assertEqual(
            payload["discovered_total"], sum(c["discovered"] for c in payload["categories"])
        )

    @covers_requirement(
        "webclient-lore-codex-panel::the-monster-category-groups-species-by-threat-tier",
    )
    def test_monster_species_group_by_tier_in_tier_order(self):
        payload = self._render(_mock_player(lore_discovered={f"monster:{T_RIVEN_SPECIES}"}))
        monster = _by_key(payload, "monster")
        self.assertEqual([g["key"] for g in monster["groups"]], [T_FAINT, T_RIVEN])
        self.assertEqual(
            [g["label"] for g in monster["groups"]],
            [SYNTH_MONSTER_TIERS[T_FAINT].display_name_zh, SYNTH_MONSTER_TIERS[T_RIVEN].display_name_zh],
        )
        self.assertNotIn(T_EMPTY_TIER, [g["key"] for g in monster["groups"]])
        faint, riven = monster["groups"]
        # Species registry order within each tier: two placeholders in faint.
        self.assertEqual(faint["slots"], [{"placeholder": True}, {"placeholder": True}])
        self.assertEqual([slot["key"] for slot in riven["slots"]], [T_RIVEN_SPECIES])

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-discloses-only-the-count-and-ordinal-position-of-undiscovered-entries"
    )
    def test_placeholders_carry_no_identity(self):
        payload = self._render(_mock_player(lore_discovered={f"race:{T_RACE}"}))
        race_slots = _slots(_by_key(payload, "race"))
        self.assertEqual(sum(1 for slot in race_slots if "key" in slot), 1)
        self.assertTrue(len(race_slots) >= 2)
        for slot in race_slots:
            if "key" not in slot:
                self.assertEqual(slot, {"placeholder": True})
        dumped = json.dumps(payload, ensure_ascii=False)
        for category, codex in CODE_CATEGORIES.items():
            for key, entry in codex.registry.items():
                if (category, key) == ("race", T_RACE):
                    continue
                with self.subTest(category=category, key=key):
                    self.assertNotIn(f'"{key}"', dumped)
                    self.assertNotIn(entry.display_name_zh, dumped)

    @covers_requirement(
        "webclient-lore-codex-panel::monster-entries-carry-stage-gated-cards",
    )
    def test_sighted_and_defeated_monster_cards(self):
        sighted = self._render(_mock_player(lore_discovered={f"monster:{T_SPECIES}"}))
        slot = _entry_slot(sighted, "monster", T_SPECIES)
        self.assertEqual(slot["stage"], "sighted")
        self.assertEqual(
            [f["name"] for f in slot["card"]],
            ["display_name_zh", "published_appearance_zh", "threat_tier"],
        )
        self.assertEqual(
            slot["locked_fields"],
            ["published_description_zh", "published_ecology_zh", "habitat_tags", "variants"],
        )
        species = SYNTH_MONSTER_SPECIES[T_SPECIES]
        dumped = json.dumps(sighted, ensure_ascii=False)
        self.assertNotIn(species.published_description_zh, dumped)
        self.assertNotIn(species.published_ecology_zh, dumped)

        defeated = self._render(
            _mock_player(
                lore_discovered={f"monster:{T_SPECIES}"}, lore_species_defeated={T_SPECIES}
            )
        )
        slot = _entry_slot(defeated, "monster", T_SPECIES)
        self.assertEqual(slot["stage"], "defeated")
        self.assertEqual(len(slot["card"]), 7)
        self.assertEqual(slot["locked_fields"], [])

    @covers_requirement(
        "webclient-lore-codex-panel::cards-are-rendered-by-the-canonical-renderer-never-composed-by-the-presenter"
    )
    def test_cards_match_the_canonical_renderers(self):
        payload = self._render(
            _mock_player(
                lore_discovered={f"nation:{T_NATION}", f"monster:{T_SPECIES}"},
                lore_species_defeated={T_SPECIES},
            )
        )
        nation = _entry_slot(payload, "nation", T_NATION)
        self.assertEqual(
            [(f["name"], f["value"]) for f in nation["card"]],
            list(lore_card("nation", T_NATION).items()),
        )
        monster = _entry_slot(payload, "monster", T_SPECIES)
        card, locked = species_card(T_SPECIES, "defeated")
        self.assertEqual([(f["name"], f["value"]) for f in monster["card"]], list(card.items()))
        self.assertEqual(monster["locked_fields"], list(locked))

    @covers_requirement(
        "webclient-lore-codex-panel::monster-entries-carry-stage-gated-cards",
    )
    def test_author_private_text_never_ships(self):
        for defeated in (None, {T_SPECIES}):
            payload = self._render(
                _mock_player(
                    lore_discovered={f"monster:{T_SPECIES}"}, lore_species_defeated=defeated
                )
            )
            dumped = json.dumps(payload, ensure_ascii=False)
            for marker in AUTHOR_MARKERS:
                with self.subTest(defeated=defeated, marker=marker):
                    self.assertNotIn(marker, dumped)

    @covers_requirement(
        "webclient-lore-codex-panel::monster-entries-carry-stage-gated-cards",
        "webclient-lore-codex-panel::codex-entries-carry-an-existing-art-descriptor-or-none",
    )
    def test_non_monster_entries_carry_no_stage_and_no_art_outside_regions_and_anchors(self):
        payload = self._render(
            _mock_player(lore_discovered={f"race:{T_RACE}", f"nation:{T_NATION}"})
        )
        for category, key in (("race", T_RACE), ("nation", T_NATION)):
            slot = _entry_slot(payload, category, key)
            self.assertIsNone(slot["stage"])
            self.assertEqual(slot["locked_fields"], [])
            self.assertIsNone(slot["art"])

    @covers_requirement(
        "webclient-lore-codex-panel::codex-entries-carry-an-existing-art-descriptor-or-none",
    )
    def test_monster_and_region_entries_carry_existing_art(self):
        payload = self._render(
            _mock_player(lore_discovered={f"monster:{T_SPECIES}", f"region:{T_ART_REGION}"})
        )
        monster_art = _entry_slot(payload, "monster", T_SPECIES)["art"]
        validate_artwork(monster_art)
        self.assertEqual(monster_art["subject_id"], monster_subject_for(T_SPECIES).full())
        region_art = _entry_slot(payload, "region", T_ART_REGION)["art"]
        validate_artwork(region_art)
        self.assertEqual(region_art["subject_id"], f"codex:region:{T_ART_REGION}")
        self.assertIn(T_ART_ARCHETYPE, json.dumps(region_art))

    @covers_requirement(
        "webclient-lore-codex-panel::codex-entries-carry-an-existing-art-descriptor-or-none",
    )
    def test_entry_art_fits_the_global_depth_bound_inside_an_envelope(self):
        # A codex slot nests its artwork descriptor under categories, groups
        # and slots, so a resource's geometry leaf sits far below the envelope
        # root; the whole snapshot must still pass the global bounds.
        geometry = {
            "image_size": {"width": 832, "height": 1216},
            "face_rect": {"x": 0.3, "y": 0.1, "w": 0.4, "h": 0.4},
            "stage": {"scale": 1.0, "x": 0.0, "y": 0.0},
            "aspect_ratio": "3:4",
        }

        def resource(name: str) -> dict:
            return {
                "resource_id": f"codex/{name}.png",
                "version": "a" * 64,
                "url": f"/art/codex/{name}.png",
                "origin": "runtime",
                "geometry": deepcopy(geometry),
            }

        descriptor = {
            "subject_id": f"codex:region:{T_ART_REGION}",
            "revision": "b" * 64,
            "generation_subject": f"codex:region:{T_ART_REGION}",
            "generation_state": "done",
            "attempts": [
                {"type": "image", "source_id": "codex.generated", "rank": 40, "resource": resource("attempt")}
            ],
            "terminal": {"kind": "alpha_mask", "source_id": "codex.mask", "rank": 100, "resource": resource("terminal")},
            "retention_sources": [],
        }
        with patch.object(lore_codex_module, "_build_art", return_value=descriptor):
            payload = self._render(_mock_player(lore_discovered={f"region:{T_ART_REGION}"}))
        self.assertEqual(
            _entry_slot(payload, "region", T_ART_REGION)["art"], validate_artwork(descriptor)
        )
        check_json_safety({"panels": {"lore_codex": payload}})

    @covers_requirement(
        "webclient-lore-codex-panel::codex-entries-carry-an-existing-art-descriptor-or-none",
    )
    def test_building_art_is_read_only_and_idempotent(self):
        record = {f"monster:{T_SPECIES}", f"region:{T_ART_REGION}", f"race:{T_RACE}"}
        defeated = {T_SPECIES}
        player = _mock_player(lore_discovered=set(record), lore_species_defeated=set(defeated))
        before = ArtAssetRecord.objects.count()
        with patch("world.art.queue.enqueue_gallery_job") as enqueued:
            first = self._render(player)
            second = self._render(player)
        enqueued.assert_not_called()
        self.assertEqual(ArtAssetRecord.objects.count(), before)
        self.assertEqual(first, second)
        self.assertEqual(player.db.lore_discovered, record)
        self.assertEqual(player.db.lore_species_defeated, defeated)

    @covers_requirement(
        "webclient-lore-codex-panel::codex-entries-carry-an-existing-art-descriptor-or-none",
    )
    def test_an_art_failure_nulls_only_that_slot(self):
        player = _mock_player(
            lore_discovered={f"monster:{T_SPECIES}", f"monster:{T_RIVEN_SPECIES}", f"region:{T_ART_REGION}"}
        )
        baseline = self._render(player)
        for failure in (
            {"side_effect": RuntimeError("art builder fault")},
            {"return_value": {"subject_id": "malformed"}},
        ):
            with self.subTest(failure=failure), patch.object(
                lore_codex_module, "describe_portrait", **failure
            ), patch.object(lore_codex_module, "log_warn") as warned:
                payload = self._render(player)
            self.assertTrue(payload["available"])
            for key in (T_SPECIES, T_RIVEN_SPECIES):
                self.assertIsNone(_entry_slot(payload, "monster", key)["art"])
            self.assertEqual(
                _entry_slot(payload, "region", T_ART_REGION),
                _entry_slot(baseline, "region", T_ART_REGION),
            )
            self.assertEqual(
                [call.args[0] for call in warned.call_args_list], ["lore_codex_art_failed"] * 2
            )

    def test_an_empty_species_registry_gives_a_monster_category_without_groups(self):
        with patch("world.rules.lore_knowledge.MONSTER_SPECIES_REGISTRY", MappingProxyType({})):
            payload = self._render(_mock_player())
        monster = _by_key(payload, "monster")
        self.assertEqual(monster["groups"], [])
        self.assertEqual((monster["discovered"], monster["total"]), (0, 0))

    @covers_requirement(
        "webclient-lore-codex-panel::cards-are-rendered-by-the-canonical-renderer-never-composed-by-the-presenter"
    )
    def test_vanished_registry_key_omitted_without_failing_or_rewriting_record(self):
        initial = {f"race:{T_RACE}", "race:t_vanished_key", "monster:t_vanished_species"}
        defeated = {"t_vanished_species"}
        player = _mock_player(lore_discovered=set(initial), lore_species_defeated=set(defeated))
        payload = self._render(player)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["discovered_total"], 1)
        race = _by_key(payload, "race")
        self.assertEqual(len(_slots(race)), len(CODE_CATEGORIES["race"].registry))
        self.assertNotIn("t_vanished", json.dumps(payload))
        self.assertEqual(player.db.lore_discovered, initial)
        self.assertEqual(player.db.lore_species_defeated, defeated)

    @covers_requirement(
        "webclient-lore-codex-panel::the-lore-codex-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_read_only_isolation_building_twice_leaves_record_unchanged(self):
        record = {f"race:{T_RACE}", f"anchor:{T_ANCHOR}"}
        player = _mock_player(lore_discovered=set(record))
        first = self._render(player)
        second = self._render(player)
        self.assertEqual(player.db.lore_discovered, record)
        self.assertEqual(first, second)

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
                    self._render(player)
                self.assertEqual(player.db.lore_discovered, corrupt_copy)

    def test_corrupt_defeated_record_degrades_whole_panel(self):
        for corrupt in ("not-a-set", {42}, {"t:bad"}, {""}):
            with self.subTest(corrupt=corrupt):
                corrupt_copy = deepcopy(corrupt)
                player = _mock_player(
                    lore_discovered={f"monster:{T_SPECIES}"}, lore_species_defeated=corrupt
                )
                with self.assertRaises(PanelUnavailableError):
                    self._render(player)
                self.assertEqual(player.db.lore_species_defeated, corrupt_copy)

    def _untrimmed(self):
        player = _mock_player(
            lore_discovered={f"race:{T_RACE}", f"monster:{T_SPECIES}", f"region:{T_ART_REGION}"}
        )
        return player, self._render(player)

    @staticmethod
    def _placeholder_count(payload):
        return sum(
            1 for category in payload["categories"] for slot in _slots(category) if "key" not in slot
        )

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_trailing_placeholders_drop_first(self):
        player, untrimmed = self._untrimmed()
        limit = json_byte_size(untrimmed) - 30
        with patch.object(lore_codex_module, "MAX_CANONICAL_JSON_BYTES", limit):
            trimmed = self._render(player)
        self.assertLessEqual(json_byte_size(trimmed), limit)
        dropped = self._placeholder_count(untrimmed) - self._placeholder_count(trimmed)
        self.assertGreaterEqual(dropped, 1)
        self.assertLess(dropped, self._placeholder_count(untrimmed))
        # Only the trailing placeholders went: the last category loses first.
        expected = deepcopy(untrimmed)
        remaining = dropped
        for category in reversed(expected["categories"]):
            for group in reversed(category["groups"]):
                for index in reversed(range(len(group["slots"]))):
                    if remaining and "key" not in group["slots"][index]:
                        del group["slots"][index]
                        remaining -= 1
        self.assertEqual(trimmed, expected)
        self.assertEqual(
            [c["total"] for c in trimmed["categories"]], [c["total"] for c in untrimmed["categories"]]
        )

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_art_drops_after_every_placeholder(self):
        player, untrimmed = self._untrimmed()
        without_placeholders = deepcopy(untrimmed)
        for category in without_placeholders["categories"]:
            for group in category["groups"]:
                group["slots"] = [slot for slot in group["slots"] if "key" in slot]
        monster = _entry_slot(without_placeholders, "monster", T_SPECIES)
        self.assertIsNotNone(monster["art"])
        # Fits once the last entry with art (the monster, whose category
        # follows the region's) loses it.
        monster["art"] = None
        limit = json_byte_size(without_placeholders)
        with patch.object(lore_codex_module, "MAX_CANONICAL_JSON_BYTES", limit):
            trimmed = self._render(player)
        self.assertEqual(trimmed, without_placeholders)
        self.assertIsNotNone(_entry_slot(trimmed, "region", T_ART_REGION)["art"])
        self.assertEqual(trimmed["discovered_total"], 3)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed"
    )
    def test_oversize_cards_without_placeholders_or_art_fail_closed(self):
        player, _ = self._untrimmed()
        with patch.object(lore_codex_module, "MAX_CANONICAL_JSON_BYTES", 200):
            with self.assertRaises(LoreCodexPanelError):
                self._render(player)

    @covers_requirement(
        "webclient-lore-codex-panel::the-panel-is-bounded-trims-placeholders-then-art-and-fails-closed",
    )
    def test_a_category_above_the_slot_bound_raises(self):
        ranks = {
            f"t_codex_rank_{i:03d}": make_guild_rank(f"t_codex_rank_{i:03d}")
            for i in range(LORE_CODEX_MAX_SLOTS_PER_CATEGORY + 1)
        }
        with synthetic_registries("guild_ranks", extra={"guild_ranks": ranks}):
            with self.assertRaises(LoreCodexPanelError):
                self._render(_mock_player())

    def test_registry_build_unavailable_matches_registered_reason(self):
        registry = build_production_registry()
        spec = registry.spec("lore_codex")
        self.assertEqual(spec.schema_version, LORE_CODEX_SCHEMA_VERSION)
        self.assertEqual(
            spec.unavailable_reason,
            ("lore_codex_unavailable", "知識圖鑑目前無法顯示"),
        )
        unavailable = registry.build_unavailable("lore_codex")
        self.assertEqual(unavailable["schema_version"], LORE_CODEX_SCHEMA_VERSION)
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
        self.assertEqual(_entry_slot(payload, "race", T_RACE)["key"], T_RACE)

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
            self.assertEqual(_entry_slot(pushed_panel, "race", T_RACE)["key"], T_RACE)

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
