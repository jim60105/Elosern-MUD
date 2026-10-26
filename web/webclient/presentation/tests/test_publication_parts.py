"""Bounded general publication codec (webclient-publication-codec).

Exact ``ui_publication_part`` wire bounds, the shared resource table, intact vs
fragmented delivery, UTF-8 boundary survival, panel-schema preflight and real
coordinator sends. Fixtures are synthetic or production panel schemas validated
by their own validators; no shipped lore content is named.
"""

import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tools.spec_traceability import covers_requirement

from web.webclient.presentation import publication_parts
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.lore_codex import (
    LORE_CODEX_CATEGORIES,
    validate_lore_codex,
)
from web.webclient.presentation.protocol import (
    CLIENT_MESSAGES,
    DIALOGUE_ENVELOPE_MAX_BYTES,
    DIALOGUE_PANEL_MAX_BYTES,
    MAX_CANONICAL_JSON_BYTES,
    SERVER_MESSAGES,
    UI_PUBLICATION_PART,
    VALIDATORS,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.publication import PublicationCompletion
from web.webclient.presentation.publication_parts import (
    PUBLICATION_ASSEMBLY_TIMEOUT_MS,
    PUBLICATION_CHUNK_BYTES,
    PUBLICATION_CHUNK_CHARS,
    PUBLICATION_MAX_ASSEMBLIES,
    PUBLICATION_MAX_BYTES,
    PUBLICATION_MAX_CHUNKS,
    PUBLICATION_MAX_PARTS,
    PUBLICATION_PART_BYTES,
    PublicationCodecError,
    canonical_bytes,
    encode_publication,
    encode_publication_parts,
    new_transfer_id,
    validate_publication_part,
)
from web.webclient.presentation.registry import (
    PresenterSpec,
    PresentationRegistry,
    build_production_registry,
)
from web.webclient.presentation.tests._support import (
    publication_failure,
    publication_receipt,
)

ROOT = Path(__file__).resolve().parents[4]
EPOCH = "e" * 22
SERVER_TIME = {
    "year": 1204,
    "season_index": 2,
    "season_label": "仲夏",
    "day_in_season": 17,
    "hour": 14,
    "minute": 30,
    "second": 5,
}


def _snapshot(panels, *, revision=1, mode="exploration"):
    return {
        "protocol_version": 1,
        "presentation_epoch": EPOCH,
        "revision": revision,
        "mode": mode,
        "panels": panels,
        "layout_version": 1,
        "server_time": dict(SERVER_TIME),
    }


def _delta(panels, *, revision=2, base_revision=1, mode="exploration", removed=()):
    return {
        **_snapshot(panels, revision=revision, mode=mode),
        "base_revision": base_revision,
        "removed_panels": list(removed),
    }


def _panel(filler: int = 24, width: int = 2_048) -> dict:
    """A structurally legal synthetic panel larger than one generic frame."""
    return {
        "schema_version": 1,
        "available": True,
        "rows": ["字" * width for _ in range(filler)],
    }


def _node(script: str, stdin: str = "") -> str:
    return subprocess.run(
        ["node", "-e", script],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    ).stdout


def _lore_codex_panel(width: int, last: int) -> dict:
    """One schema-valid lore_codex panel with tunable filler width."""

    def value(index: int) -> str:
        return "字" * (last if index == 0 else width)

    entries = [
        {
            "key": f"entry_{entry}",
            "title": "條目",
            "card": [
                {"name": f"field_{field}", "value": value(entry * 8 + field)}
                for field in range(8)
            ],
        }
        for entry in range(8)
    ]
    groups = [
        {
            "key": category,
            "label": f"類別{position}",
            "count": len(entries) if position == 0 else 0,
            "entries": entries if position == 0 else [],
        }
        for position, category in enumerate(LORE_CODEX_CATEGORIES)
    ]
    return {
        "schema_version": 1,
        "available": True,
        "categories": groups,
        "discovered_total": len(entries),
    }


def _near_cap_lore_codex() -> tuple[dict, int]:
    """The largest schema-valid lore_codex panel that still fits its own cap."""
    best = None
    low, high = 0, 1_024
    while low <= high:
        width = (low + high) // 2
        panel = _lore_codex_panel(width, width)
        try:
            validate_lore_codex(panel)
        except ProtocolValidationError:
            high = width - 1
            continue
        best = (panel, width)
        low = width + 1
    assert best is not None
    _, width = best
    chosen = _lore_codex_panel(width, width)
    low, high = 0, 1_024
    while low <= high:
        last = (low + high) // 2
        panel = _lore_codex_panel(width, last)
        try:
            validate_lore_codex(panel)
        except ProtocolValidationError:
            high = last - 1
            continue
        chosen = panel
        low = last + 1
    size = json_byte_size(validate_lore_codex(chosen))
    assert MAX_CANONICAL_JSON_BYTES - 8 <= size <= MAX_CANONICAL_JSON_BYTES, size
    return chosen, size


def _changed_codex(panel: dict) -> dict:
    """The same valid panel with a same-size content change."""
    changed = json.loads(json.dumps(panel))
    value = changed["categories"][0]["entries"][0]["card"][0]["value"]
    changed["categories"][0]["entries"][0]["card"][0]["value"] = "文" + value[1:]
    validate_lore_codex(changed)
    return changed


def _logical_at(canonical_size: int) -> dict:
    """A structurally legal snapshot of exactly ``canonical_size`` bytes.

    The final row absorbs the one-byte-granularity adjustment, so the fixture
    pins the generic envelope threshold with its metadata accounted for.
    """
    rows = ["x" * 2_048 for _ in range(32)]
    logical = _snapshot(
        {"status": {"schema_version": 1, "available": True, "rows": rows}}
    )
    adjustment = len(canonical_bytes(logical)) - canonical_size
    if not 0 <= adjustment <= 2_048:
        raise AssertionError(f"cannot tune the fixture by {adjustment} bytes")
    rows[-1] = rows[-1][: 2_048 - adjustment]
    logical = _snapshot(
        {"status": {"schema_version": 1, "available": True, "rows": rows}}
    )
    assert len(canonical_bytes(logical)) == canonical_size
    return logical


def _headers_and_raw(envelopes):
    """Validate every part envelope once; return its headers and the raw bytes."""
    decoded = [validate_publication_part(envelope) for envelope in envelopes]
    return [header for header, _ in decoded], b"".join(raw for _, raw in decoded)


class SharedConstantTableTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_the_finite_resource_table_is_exact_and_derived(self):
        self.assertEqual(PUBLICATION_MAX_BYTES, 16_777_216)
        self.assertEqual(PUBLICATION_PART_BYTES, 24_576)
        self.assertEqual(PUBLICATION_CHUNK_BYTES, 1_536)
        self.assertEqual(PUBLICATION_MAX_CHUNKS, 16)
        self.assertEqual(PUBLICATION_MAX_PARTS, 683)
        self.assertEqual(PUBLICATION_ASSEMBLY_TIMEOUT_MS, 30_000)
        self.assertEqual(PUBLICATION_MAX_ASSEMBLIES, 1)
        self.assertEqual(
            PUBLICATION_MAX_PARTS,
            -(-PUBLICATION_MAX_BYTES // PUBLICATION_PART_BYTES),
        )
        self.assertEqual(
            PUBLICATION_MAX_CHUNKS,
            PUBLICATION_PART_BYTES // PUBLICATION_CHUNK_BYTES,
        )
        self.assertEqual(PUBLICATION_CHUNK_CHARS, 2_048)
        # The maximum leaves exactly 16,384 raw bytes (11 chunks) for the last
        # part, and the base64 string cap is the generic string cap.
        remainder = PUBLICATION_MAX_BYTES - PUBLICATION_PART_BYTES * (
            PUBLICATION_MAX_PARTS - 1
        )
        self.assertEqual(remainder, 16_384)
        self.assertEqual(-(-remainder // PUBLICATION_CHUNK_BYTES), 11)

    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_the_browser_mirror_declares_the_same_constants(self):
        names = [
            "PUBLICATION_MAX_BYTES",
            "PUBLICATION_PART_BYTES",
            "PUBLICATION_CHUNK_BYTES",
            "PUBLICATION_MAX_CHUNKS",
            "PUBLICATION_MAX_PARTS",
            "PUBLICATION_ASSEMBLY_TIMEOUT_MS",
            "PUBLICATION_MAX_ASSEMBLIES",
        ]
        script = (
            "const P=require('./web/static/webclient/js/elosern/protocol.js');"
            f"process.stdout.write(JSON.stringify({json.dumps(names)}.map((n)=>P[n])));"
        )
        mirrored = json.loads(_node(script))
        for name, value in zip(names, mirrored, strict=True):
            with self.subTest(constant=name):
                self.assertEqual(value, getattr(publication_parts, name))

    def test_the_part_message_is_registered_exactly_once(self):
        self.assertIn(UI_PUBLICATION_PART, SERVER_MESSAGES)
        self.assertNotIn(UI_PUBLICATION_PART, CLIENT_MESSAGES)
        self.assertEqual(
            VALIDATORS[UI_PUBLICATION_PART].__module__,
            "web.webclient.presentation.protocol",
        )


class PartWireTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    def test_small_publication_travels_intact_under_its_original_command(self):
        logical = _snapshot({"status": {"schema_version": 1, "available": True}})
        frames = encode_publication("ui_snapshot", logical)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].command, "ui_snapshot")
        self.assertEqual(frames[0].envelope, logical)
        self.assertEqual(frames[0].canonical, canonical_bytes(logical))
        check_envelope(frames[0].envelope)

    def test_the_generic_envelope_threshold_accounts_for_metadata(self):
        at_bound = _logical_at(MAX_CANONICAL_JSON_BYTES)
        frames = encode_publication("ui_snapshot", at_bound)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].command, "ui_snapshot")

        over = _logical_at(MAX_CANONICAL_JSON_BYTES + 1)
        parts = encode_publication("ui_snapshot", over)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(frame.command == UI_PUBLICATION_PART for frame in parts))
        headers, raw = _headers_and_raw(frame.envelope for frame in parts)
        self.assertEqual(headers[0]["total_bytes"], MAX_CANONICAL_JSON_BYTES + 1)
        self.assertEqual(raw, canonical_bytes(over))

    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    @covers_requirement(
        "webclient-publication-delivery::general-publication-parts-use-exact-bounded-wire-fields"
    )
    def test_fragmented_snapshot_headers_match_the_logical_document(self):
        logical = _snapshot({"status": _panel()})
        frames = encode_publication("ui_snapshot", logical)
        self.assertGreater(len(frames), 1)
        self.assertTrue(all(frame.command == UI_PUBLICATION_PART for frame in frames))
        canonical = canonical_bytes(logical)
        raw = b""
        headers = []
        for index, frame in enumerate(frames):
            check_envelope(frame.envelope)
            header, chunk = validate_publication_part(frame.envelope)
            headers.append(header)
            raw += chunk
            self.assertEqual(header["part_index"], index)
            self.assertEqual(frame.envelope["publication_kind"], "snapshot")
            self.assertNotIn("base_revision", frame.envelope)
            self.assertEqual(frame.envelope["presentation_epoch"], EPOCH)
            self.assertEqual(frame.envelope["revision"], 1)
            self.assertEqual(frame.envelope["total_bytes"], len(canonical))
            self.assertEqual(frame.envelope["part_count"], len(frames))
            self.assertLessEqual(len(frame.envelope["chunks"]), PUBLICATION_MAX_CHUNKS)
            for chunk_text in frame.envelope["chunks"]:
                self.assertLessEqual(len(chunk_text), PUBLICATION_CHUNK_CHARS)
        self.assertEqual(raw, canonical)
        self.assertEqual(json.loads(raw.decode("utf-8")), logical)
        self.assertEqual(
            {header["transfer_id"] for header in headers}, {headers[0]["transfer_id"]}
        )
        self.assertRegex(headers[0]["transfer_id"], r"^[0-9a-f]{32}$")

    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    @covers_requirement(
        "webclient-publication-delivery::general-publication-parts-use-exact-bounded-wire-fields"
    )
    def test_fragmented_delta_repeats_its_exact_base(self):
        logical = _delta({"status": _panel()}, revision=9, base_revision=8)
        frames = encode_publication("ui_update", logical)
        self.assertGreater(len(frames), 1)
        for frame in frames:
            self.assertEqual(frame.envelope["publication_kind"], "delta")
            self.assertEqual(frame.envelope["base_revision"], 8)
            self.assertEqual(frame.envelope["revision"], 9)

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_part_boundaries_24576_and_24577(self):
        at_bound = encode_publication_parts(
            b"x" * PUBLICATION_PART_BYTES,
            presentation_epoch=EPOCH,
            revision=1,
            publication_kind="snapshot",
            transfer_id="0" * 32,
        )
        self.assertEqual(len(at_bound), 1)
        self.assertEqual(len(at_bound[0]["chunks"]), PUBLICATION_MAX_CHUNKS)

        over = encode_publication_parts(
            b"x" * (PUBLICATION_PART_BYTES + 1),
            presentation_epoch=EPOCH,
            revision=1,
            publication_kind="snapshot",
            transfer_id="0" * 32,
        )
        self.assertEqual(len(over), 2)
        self.assertEqual(len(over[1]["chunks"]), 1)
        header, raw = validate_publication_part(over[1])
        self.assertEqual(raw, b"x")
        self.assertEqual(header["part_index"], 1)

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_exact_maximum_derives_683_parts_and_overflow_rejects(self):
        canonical = b"x" * PUBLICATION_MAX_BYTES
        parts = encode_publication_parts(
            canonical,
            presentation_epoch=EPOCH,
            revision=1,
            publication_kind="snapshot",
            transfer_id="f" * 32,
        )
        self.assertEqual(len(parts), PUBLICATION_MAX_PARTS)
        self.assertEqual(parts[-1]["part_index"], PUBLICATION_MAX_PARTS - 1)
        self.assertEqual(len(parts[-1]["chunks"]), 11)
        header, raw = validate_publication_part(parts[-1])
        self.assertEqual(len(raw), 16_384)
        self.assertEqual(header["total_bytes"], PUBLICATION_MAX_BYTES)
        with self.assertRaises(PublicationCodecError):
            encode_publication_parts(
                canonical + b"x",
                presentation_epoch=EPOCH,
                revision=1,
                publication_kind="snapshot",
            )

    @covers_requirement(
        "webclient-publication-delivery::general-publication-parts-use-exact-bounded-wire-fields"
    )
    def test_part_shape_rejections(self):
        parts = encode_publication_parts(
            canonical_bytes(_delta({"status": _panel()})),
            presentation_epoch=EPOCH,
            revision=2,
            publication_kind="delta",
            base_revision=1,
            transfer_id="a" * 32,
        )
        valid = parts[0]

        def mutate(**changes):
            value = json.loads(json.dumps(valid))
            for key, replacement in changes.items():
                if replacement is None:
                    value.pop(key, None)
                else:
                    value[key] = replacement
            return value

        snapshot = mutate(publication_kind="snapshot")
        cases = [
            ("extra field", {**valid, "mode": "exploration"}),
            ("boolean index", mutate(part_index=True)),
            ("boolean revision", mutate(revision=True)),
            ("uppercase transfer", mutate(transfer_id="A" * 32)),
            ("short transfer", mutate(transfer_id="a" * 31)),
            ("count mismatch", mutate(part_count=valid["part_count"] + 1)),
            (
                "total changes part count",
                mutate(total_bytes=valid["total_bytes"] + PUBLICATION_PART_BYTES),
            ),
            ("index out of range", mutate(part_index=valid["part_count"])),
            ("missing base", mutate(base_revision=None)),
            ("snapshot with base", snapshot),
            ("delta base not older", mutate(base_revision=2)),
            ("unknown kind", mutate(publication_kind="repair")),
            ("missing field", mutate(chunks=None)),
        ]
        bad_alphabet = json.loads(json.dumps(valid))
        bad_alphabet["chunks"] = ["*" + chunk[1:] for chunk in bad_alphabet["chunks"]]
        cases.append(("bad alphabet", bad_alphabet))
        whitespace = json.loads(json.dumps(valid))
        whitespace["chunks"] = [" " + chunk for chunk in whitespace["chunks"]]
        cases.append(("whitespace", whitespace))
        short = json.loads(json.dumps(valid))
        short["chunks"] = short["chunks"][:-1]
        cases.append(("missing chunk", short))
        long_chunk = json.loads(json.dumps(valid))
        long_chunk["chunks"] = [chunk + "A" * 2_048 for chunk in long_chunk["chunks"]]
        cases.append(("oversized chunk", long_chunk))
        for name, value in cases:
            with self.subTest(case=name), self.assertRaises(ProtocolValidationError):
                validate_publication_part(value)

    @covers_requirement(
        "webclient-publication-delivery::general-publication-parts-use-exact-bounded-wire-fields"
    )
    def test_noncanonical_base64_padding_is_rejected(self):
        # Final parts with a one- and a two-byte remainder; each alternate
        # spelling decodes to the same raw bytes and is rejected only by the
        # canonical re-encoding rule.
        for total, canonical_chunk, variants in (
            (PUBLICATION_PART_BYTES + 1, "eA==", ("eB==", "eA===")),
            (PUBLICATION_PART_BYTES + 2, "eHg=", ("eHh=", "eHg==")),
        ):
            parts = encode_publication_parts(
                b"x" * total,
                presentation_epoch=EPOCH,
                revision=1,
                publication_kind="snapshot",
                transfer_id="b" * 32,
            )
            last = parts[-1]
            self.assertEqual(last["chunks"], [canonical_chunk])
            self.assertEqual(validate_publication_part(last)[1], b"x" * (total - PUBLICATION_PART_BYTES))
            for variant in variants:
                value = json.loads(json.dumps(last))
                value["chunks"] = [variant]
                with self.subTest(case=variant), self.assertRaises(
                    ProtocolValidationError
                ):
                    validate_publication_part(value)
            # The canonical spelling of the same bytes stays acceptable.
            canonical = json.loads(json.dumps(last))
            canonical["chunks"] = [canonical_chunk]
            validate_publication_part(canonical)

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_cjk_character_crossing_a_part_boundary_survives(self):
        def candidate(pad: int) -> dict:
            rows = ["😀" * 512 for _ in range(48)]
            rows[0] = "a" * pad + rows[0]
            return _snapshot(
                {"status": {"schema_version": 1, "available": True, "rows": rows}}
            )

        for pad in range(4):
            logical = candidate(pad)
            canonical = canonical_bytes(logical)
            if 0x80 <= canonical[PUBLICATION_PART_BYTES] <= 0xBF:
                break
        else:  # pragma: no cover - the shift is always reachable
            self.fail("no alignment splits a code point across the boundary")
        frames = encode_publication("ui_snapshot", logical)
        self.assertGreater(len(frames), 1)
        _headers, raw = _headers_and_raw(frame.envelope for frame in frames)
        self.assertEqual(raw, canonical)
        self.assertEqual(json.loads(raw.decode("utf-8")), logical)

    def test_dialogue_intact_allowance_is_preserved_and_never_a_logical_cap(self):
        # Dialogue stays inside its own 24,576-byte panel cap; the stripped
        # envelope just fits the generic ceiling, while the whole envelope
        # exceeds it. The scoped intact allowance must keep it intact.
        dialogue = {
            "schema_version": 3,
            "available": True,
            "kind": "dialogue",
            "lines": ["字" * 1_500 for _ in range(2)],
        }
        stripped_panel = _panel(filler=10)
        logical = _snapshot({"status": stripped_panel, "dialogue": dialogue})
        stripped = {**logical, "panels": {"status": stripped_panel}}
        self.assertGreater(json_byte_size(logical), MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(json_byte_size(stripped), MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(json_byte_size(logical), DIALOGUE_ENVELOPE_MAX_BYTES)
        check_envelope(logical)  # the allowance, not the generic cap, applies
        frames = encode_publication("ui_snapshot", logical)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].command, "ui_snapshot")

        # With the dialogue-removed envelope itself over the generic ceiling
        # the same shape fragments; the dialogue panel cap is still enforced.
        heavy = _snapshot({"status": _panel(filler=12), "dialogue": dialogue})
        heavy_stripped = {**heavy, "panels": {"status": heavy["panels"]["status"]}}
        self.assertGreater(json_byte_size(heavy_stripped), MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(json_byte_size(heavy), DIALOGUE_ENVELOPE_MAX_BYTES)
        with self.assertRaises(ProtocolValidationError):
            check_envelope(heavy)
        parts = encode_publication("ui_snapshot", heavy)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(frame.command == UI_PUBLICATION_PART for frame in parts))
        _headers, raw = _headers_and_raw(frame.envelope for frame in parts)
        self.assertEqual(json.loads(raw.decode("utf-8")), heavy)

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_over_bound_dialogue_panel_is_rejected_not_fragmented(self):
        logical = _snapshot(
            {
                "status": {"schema_version": 1, "available": True},
                "dialogue": {
                    "schema_version": 3,
                    "available": True,
                    "kind": "dialogue",
                    "lines": ["字" * 2_000 for _ in range(5)],
                },
            }
        )
        dialogue_size = json_byte_size(logical["panels"]["dialogue"])
        self.assertGreater(dialogue_size, DIALOGUE_PANEL_MAX_BYTES)
        self.assertLess(json_byte_size(logical), PUBLICATION_MAX_BYTES)
        with self.assertRaises(PublicationCodecError):
            encode_publication("ui_snapshot", logical)

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_registered_panel_validator_rejects_malformed_nested_content(self):
        def reject(payload):
            raise ProtocolValidationError("nested schema refused")

        logical = _snapshot({"lore_codex": {"schema_version": 1, "available": True}})
        with self.assertRaises(PublicationCodecError):
            encode_publication(
                "ui_snapshot", logical, panel_validators={"lore_codex": (reject, 1)}
            )

    def test_unavailable_form_is_validated_without_the_available_validator(self):
        def never(payload):  # pragma: no cover - asserted not to run
            raise AssertionError("the available validator must not see unavailable")

        logical = _snapshot(
            {
                "lore_codex": {
                    "schema_version": 1,
                    "available": False,
                    "reason": {"code": "missing_data", "message": "無法讀取"},
                }
            }
        )
        frames = encode_publication(
            "ui_snapshot", logical, panel_validators={"lore_codex": (never, 1)}
        )
        self.assertEqual(frames[0].command, "ui_snapshot")
        broken = _snapshot(
            {
                "lore_codex": {
                    "schema_version": 2,
                    "available": False,
                    "reason": {"code": "missing_data", "message": "無法讀取"},
                }
            }
        )
        with self.assertRaises(PublicationCodecError):
            encode_publication(
                "ui_snapshot", broken, panel_validators={"lore_codex": (never, 1)}
            )

    @covers_requirement(
        "webclient-publication-delivery::general-delivery-has-finite-shared-resource-limits"
    )
    def test_aggregate_overflow_and_foreign_commands_reject(self):
        with self.assertRaises(PublicationCodecError):
            encode_publication("ui_action_result", _snapshot({"status": {}}))
        # Structurally legal (320-item list, 64-field objects, 2,048-code-point
        # strings) but 17.7 MB, above the finite logical ceiling.
        logical = _snapshot(
            {
                "status": {
                    "schema_version": 1,
                    "available": True,
                    "blob": [
                        {f"k{index}": "字" * 2_048 for index in range(9)}
                        for _ in range(320)
                    ],
                }
            }
        )
        self.assertGreater(json_byte_size(logical), PUBLICATION_MAX_BYTES)
        with self.assertRaises(PublicationCodecError):
            encode_publication("ui_snapshot", logical)
        map_logical = _snapshot(
            {
                "area_map": {
                    "schema_version": 1,
                    "available": False,
                    "reason": {"code": "map_unavailable", "message": "無"},
                }
            }
        )
        with self.assertRaises(PublicationCodecError):
            encode_publication("ui_snapshot", map_logical)

    def test_production_registry_carries_panel_validators(self):
        registry = build_production_registry()
        validators = registry.panel_validators
        from web.webclient.presentation.character import validate_character
        from web.webclient.presentation.dialogue import (
            DIALOGUE_SCHEMA_VERSION,
            validate_dialogue,
        )
        from web.webclient.presentation.lore_codex import (
            validate_lore_codex as validate_codex,
        )

        self.assertEqual(
            validators["dialogue"], (validate_dialogue, DIALOGUE_SCHEMA_VERSION)
        )
        self.assertEqual(validators["character"][0], validate_character)
        self.assertEqual(validators["lore_codex"][0], validate_codex)
        # On-demand map panels keep their specialized transport validators.
        self.assertNotIn("area_map", validators)
        self.assertNotIn("world_map", validators)


# ---------------------------------------------------------------------------
# Coordinator integration.
# ---------------------------------------------------------------------------


class _Session:
    sessid = 7

    def __init__(self):
        self.sent = []
        self.on_send = None
        self._sends = 0

    def msg(self, **kwargs):
        ((name, payload),) = kwargs.items()
        envelope = payload[0][0]
        self._sends += 1
        if self.on_send is not None:
            self.on_send(name, envelope, self._sends)
        self.sent.append(kwargs)

    def frames(self):
        return [
            (name, payload[0][0])
            for kwargs in self.sent
            for name, payload in kwargs.items()
        ]

    def names(self):
        return [name for name, _ in self.frames()]


class _Calendar:
    year, season_index, season_name, day_in_season, hour, minute, second = (
        1204,
        2,
        "仲夏",
        17,
        14,
        30,
        5,
    )


def _coordinator(session, registry, mode="exploration"):
    return PresentationCoordinator(
        session,
        registry,
        calendar_provider=lambda: _Calendar(),
        mode_provider=lambda context: mode,
    )


def _context():
    return PresentationContext(actor=object(), protocol_version=1)


def _codex_registry(holder):
    """A registry whose sole eager panel is a validated production schema."""
    registry = PresentationRegistry("test")
    registry.register(
        PresenterSpec(
            name="lore_codex",
            schema_version=1,
            unavailable_reason=("missing_data", "無法讀取"),
            presenter=lambda context: holder["panel"],
        )
    )
    registry.attach_validator("lore_codex", validate_lore_codex)
    return registry


def _register_area_map(registry):
    registry.register(
        PresenterSpec(
            name="area_map",
            schema_version=1,
            unavailable_reason=("map_unavailable", "地圖目前無法顯示"),
            # An available body violating the map schema degrades to the
            # unavailable map form.
            presenter=lambda context: {"schema_version": 1, "available": True},
            on_demand=True,
        )
    )
    return registry


class CoordinatorCodecTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_oversized_snapshot_sends_parts_and_installs_the_baseline(self):
        panel, panel_size = _near_cap_lore_codex()
        session = _Session()
        coordinator = _coordinator(session, _codex_registry({"panel": panel}))
        receipt = publication_receipt(coordinator.full_snapshot(_context()))
        self.assertTrue(receipt.published)
        self.assertEqual(receipt.kind, "snapshot")
        frames = session.frames()
        self.assertGreater(len(frames), 1)
        self.assertEqual({name for name, _ in frames}, {UI_PUBLICATION_PART})
        for _, envelope in frames:
            check_envelope(envelope)
        headers, raw = _headers_and_raw(envelope for _, envelope in frames)
        logical = json.loads(raw.decode("utf-8"))
        self.assertEqual(logical["panels"]["lore_codex"], validate_lore_codex(panel))
        self.assertEqual(logical["presentation_epoch"], coordinator.epoch)
        self.assertEqual(logical["revision"], receipt.revision)
        self.assertEqual(logical["mode"], "exploration")
        self.assertEqual(logical["server_time"], SERVER_TIME)
        self.assertEqual(
            {header["transfer_id"] for header in headers}, {headers[0]["transfer_id"]}
        )
        self.assertEqual(headers[0]["total_bytes"], len(raw))
        # The intact envelope is over the generic ceiling while the logical
        # document is not: the panel itself fits its own panel cap.
        self.assertLessEqual(panel_size, MAX_CANONICAL_JSON_BYTES)
        self.assertGreater(len(raw), MAX_CANONICAL_JSON_BYTES)
        # The baseline is installed only after every part sent.
        self.assertEqual(coordinator.published_revision, receipt.revision)
        self.assertEqual(set(coordinator.committed_panels), {"lore_codex"})

    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_fragmented_delta_keeps_its_exact_base_and_orders_the_result(self):
        panel, _ = _near_cap_lore_codex()
        holder = {"panel": panel}
        session = _Session()
        coordinator = _coordinator(session, _codex_registry(holder))
        publication_receipt(coordinator.full_snapshot(_context()))
        base = coordinator.published_revision
        holder["panel"] = _changed_codex(panel)
        session.sent.clear()

        owned = {"outcome": "success", "code": "ok", "message": "完成"}

        def envelope(epoch, revision):
            return {
                "protocol_version": 1,
                "presentation_epoch": epoch,
                "request_id": "r1",
                "outcome": owned["outcome"],
                "code": owned["code"],
                "message": owned["message"],
                "presentation_revision": revision,
            }

        receipt = publication_receipt(
            coordinator.enqueue_publication(
                _context,
                affected_panels={"lore_codex"},
                completion=PublicationCompletion(
                    request_id="r1", result=owned, envelope=envelope
                ),
            )
        )
        names = session.names()
        self.assertEqual(names[-1], "ui_action_result")
        self.assertTrue(names)
        self.assertTrue(all(name == UI_PUBLICATION_PART for name in names[:-1]))
        headers, raw = _headers_and_raw(
            envelope for _, envelope in session.frames()[:-1]
        )
        self.assertGreater(len(headers), 1)
        self.assertEqual({header["publication_kind"] for header in headers}, {"delta"})
        self.assertEqual({header["base_revision"] for header in headers}, {base})
        self.assertEqual({header["revision"] for header in headers}, {receipt.revision})
        logical = json.loads(raw.decode("utf-8"))
        self.assertEqual(logical["base_revision"], base)
        self.assertEqual(logical["revision"], receipt.revision)
        self.assertEqual(logical["removed_panels"], [])
        self.assertEqual(
            logical["panels"]["lore_codex"], validate_lore_codex(holder["panel"])
        )

    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_invalid_supplied_panel_sends_nothing_and_consumes_no_revision(self):
        panel, _ = _near_cap_lore_codex()
        session = _Session()
        coordinator = _coordinator(session, _codex_registry({"panel": panel}))
        publication_receipt(coordinator.full_snapshot(_context()))
        session.sent.clear()
        before = coordinator.revision
        bad = {
            "schema_version": 1,
            "available": True,
            "categories": [],
            "discovered_total": 999,
        }
        publication_failure(
            coordinator.panel_update(_context(), {"lore_codex": bad})
        ).trap(ProtocolValidationError)
        self.assertEqual(session.sent, [])
        self.assertEqual(coordinator.revision, before)
        self.assertEqual(coordinator.published_revision, before)

    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_invalid_eager_candidate_blocks_a_combined_map_batch(self):
        panel, _ = _near_cap_lore_codex()
        holder = {"panel": panel}
        registry = _register_area_map(_codex_registry(holder))
        session = _Session()
        coordinator = _coordinator(session, registry)
        with mock.patch("web.webclient.presentation.coordinator.log_error"):
            publication_receipt(coordinator.full_snapshot(_context()))
            session.sent.clear()
            before = coordinator.revision
            holder["panel"] = {
                "schema_version": 1,
                "available": True,
                "categories": [],
            }
            publication_failure(
                coordinator.enqueue_publication(
                    _context, affected_panels={"lore_codex", "area_map"}
                )
            ).trap(ProtocolValidationError)
        self.assertEqual(session.sent, [])
        self.assertEqual(coordinator.revision, before)
        self.assertEqual(coordinator.published_revision, before)

    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_general_parts_never_wrap_a_specialized_map_body(self):
        panel, _ = _near_cap_lore_codex()
        holder = {"panel": panel}
        session = _Session()
        coordinator = _coordinator(session, _register_area_map(_codex_registry(holder)))
        with mock.patch("web.webclient.presentation.coordinator.log_error"):
            publication_receipt(coordinator.full_snapshot(_context()))
            holder["panel"] = _changed_codex(panel)
            session.sent.clear()
            publication_receipt(
                coordinator.enqueue_publication(
                    _context, affected_panels={"lore_codex", "area_map"}
                )
            )
        frames = session.frames()
        general = [
            (name, envelope) for name, envelope in frames if name == UI_PUBLICATION_PART
        ]
        maps = [(name, envelope) for name, envelope in frames if name == "ui_update"]
        self.assertTrue(general)
        self.assertEqual(len(maps), 1)
        self.assertEqual(list(maps[0][1]["panels"]), ["area_map"])
        # The map keeps its specialized part shape (22-character transfer id,
        # count/byte_length/chunk), never the general chunks wire.
        map_part = maps[0][1]["panels"]["area_map"]["part"]
        self.assertEqual(len(map_part["transfer_id"]), 22)
        self.assertNotIn("chunks", map_part)
        # Every general frame is a bare part header: no panels, no mode.
        for _, envelope in general:
            self.assertEqual(
                set(envelope),
                {
                    "protocol_version",
                    "presentation_epoch",
                    "revision",
                    "publication_kind",
                    "transfer_id",
                    "part_index",
                    "part_count",
                    "total_bytes",
                    "chunks",
                    "base_revision",
                },
            )

    @covers_requirement(
        "webclient-publication-delivery::all-delivery-frames-are-validated-before-publication"
    )
    def test_part_send_failure_invalidates_the_baseline_and_repairs(self):
        panel, _ = _near_cap_lore_codex()
        holder = {"panel": panel}
        session = _Session()
        coordinator = _coordinator(session, _codex_registry(holder))
        publication_receipt(coordinator.full_snapshot(_context()))
        holder["panel"] = _changed_codex(panel)
        session.sent.clear()

        def fail_second_part(name, envelope, index):
            if name == UI_PUBLICATION_PART and envelope["part_index"] == 1:
                raise RuntimeError("socket gone")

        session.on_send = fail_second_part
        publication_failure(coordinator.enqueue_publication(_context)).trap(RuntimeError)
        escaped = coordinator.revision
        self.assertGreater(escaped, 1)
        # The issued target escaped the transport; the incomplete publication
        # can never be a delta base, so the next publication repairs.
        self.assertEqual(coordinator.published_revision, escaped)
        self.assertEqual(coordinator.committed_panels, {})

        session.on_send = None
        session.sent.clear()
        receipt = publication_receipt(coordinator.enqueue_publication(_context))
        self.assertEqual(receipt.kind, "snapshot")
        self.assertEqual(receipt.revision, escaped + 1)
        self.assertTrue(all(name == UI_PUBLICATION_PART for name in session.names()))


class BrowserAssemblyFixtureTests(unittest.TestCase):
    """Production-encoder bytes drive the real browser reducer once."""

    def _parts(self, logical: dict, message: str, transfer: str) -> list[dict]:
        raw = canonical_bytes(logical)
        self.assertGreater(len(raw), MAX_CANONICAL_JSON_BYTES)
        kind = "delta" if message == "ui_update" else "snapshot"
        parts = encode_publication_parts(
            raw,
            presentation_epoch=logical["presentation_epoch"],
            revision=logical["revision"],
            publication_kind=kind,
            base_revision=logical.get("base_revision"),
            transfer_id=transfer,
        )
        self.assertGreater(len(parts), 1)
        _, reassembled = _headers_and_raw(parts)
        self.assertEqual(reassembled, raw)
        return parts

    def test_the_encoder_bytes_commit_one_atomic_browser_state(self):
        panel, _ = _near_cap_lore_codex()
        snapshot = _snapshot({"lore_codex": panel})
        changed = _changed_codex(panel)
        delta = _delta({"lore_codex": changed}, revision=2, base_revision=1, mode="combat")
        delta["server_time"]["hour"] = 15

        snapshot_parts = self._parts(snapshot, "ui_snapshot", "ab" * 16)
        delta_parts = self._parts(delta, "ui_update", "cd" * 16)
        script = """
const fs = require('node:fs');
const P = require('./web/static/webclient/js/elosern/protocol.js');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
function summary(state) {
  return {
    phase: state.phase,
    epoch: state.activeEpoch,
    revision: state.revision,
    mode: state.mode,
    hour: state.serverTime === null ? null : state.serverTime.hour,
    panelCount: Object.keys(state.panels).length,
    hasCodex: Object.prototype.hasOwnProperty.call(state.panels, 'lore_codex'),
  };
}
const store = P.createStore();
let notified = 0;
let notifiedAfterSnapshot = 0;
store.subscribe(() => { notified += 1; });
store.beginTransport(1);
const baseline = notified;
const initial = summary(store.getState());
const snapshotIntermediates = [];
const snapshotResults = input.snapshot.map((part) => {
  const result = store.receive(1, 'ui_publication_part', [part], {});
  snapshotIntermediates.push(summary(store.getState()));
  return result;
});
const afterSnapshot = store.getState();
notifiedAfterSnapshot = notified - baseline;
const beforeDelta = summary(afterSnapshot);
const deltaIntermediates = [];
const deltaResults = input.delta.map((part) => {
  const result = store.receive(1, 'ui_publication_part', [part], {});
  deltaIntermediates.push(summary(store.getState()));
  return result;
});
const afterDelta = store.getState();
process.stdout.write(JSON.stringify({
  initial: initial,
  snapshotResults: snapshotResults,
  snapshotIntermediates: snapshotIntermediates,
  deltaResults: deltaResults,
  deltaIntermediates: deltaIntermediates,
  beforeDelta: beforeDelta,
  notifiedAfterSnapshot: notifiedAfterSnapshot,
  notified: notified - baseline,
  snapshotState: {
    phase: afterSnapshot.phase,
    revision: afterSnapshot.revision,
    epoch: afterSnapshot.activeEpoch,
    mode: afterSnapshot.mode,
    panel: afterSnapshot.panels.lore_codex,
  },
  deltaState: {
    revision: afterDelta.revision,
    mode: afterDelta.mode,
    hour: afterDelta.serverTime.hour,
    panel: afterDelta.panels.lore_codex,
  },
}));
"""
        outcome = json.loads(
            _node(
                script,
                json.dumps({"snapshot": snapshot_parts, "delta": delta_parts}),
            )
        )

        # Nothing is adopted or notified before the final snapshot part.
        for result in outcome["snapshotResults"][:-1]:
            self.assertEqual(result, {"accepted": False, "pending": True, "revision": 1})
        # Every intermediate part leaves the committed state untouched.
        self.assertEqual(
            outcome["snapshotIntermediates"][:-1],
            [outcome["initial"]] * (len(outcome["snapshotIntermediates"]) - 1),
        )
        self.assertEqual(
            outcome["initial"],
            {
                "phase": "awaiting_initial_snapshot",
                "epoch": None,
                "revision": None,
                "mode": None,
                "hour": None,
                "panelCount": 0,
                "hasCodex": False,
            },
        )
        self.assertEqual(
            outcome["snapshotResults"][-1],
            {"accepted": True, "established": True, "revision": 1},
        )
        self.assertEqual(outcome["notifiedAfterSnapshot"], 1)
        self.assertEqual(outcome["snapshotState"]["phase"], "active")
        self.assertEqual(outcome["snapshotState"]["epoch"], EPOCH)
        self.assertEqual(outcome["snapshotState"]["revision"], 1)
        self.assertEqual(
            outcome["snapshotState"]["panel"], json.loads(json.dumps(validate_lore_codex(panel)))
        )

        # The fragmented delta commits exactly once, at its final part.
        for result in outcome["deltaResults"][:-1]:
            self.assertEqual(result, {"accepted": False, "pending": True, "revision": 2})
        self.assertEqual(
            outcome["deltaIntermediates"][:-1],
            [outcome["beforeDelta"]] * (len(outcome["deltaIntermediates"]) - 1),
        )
        self.assertEqual(outcome["deltaResults"][-1], {"accepted": True, "revision": 2})
        self.assertEqual(outcome["notified"], 2)
        self.assertEqual(outcome["deltaState"]["revision"], 2)
        self.assertEqual(outcome["deltaState"]["mode"], "combat")
        self.assertEqual(outcome["deltaState"]["hour"], 15)
        self.assertEqual(
            outcome["deltaState"]["panel"],
            json.loads(json.dumps(validate_lore_codex(changed))),
        )


class TransferIdTests(unittest.TestCase):
    def test_transfer_ids_are_128_random_bits_as_lowercase_hex(self):
        ids = {new_transfer_id() for _ in range(16)}
        self.assertEqual(len(ids), 16)
        for value in ids:
            self.assertRegex(value, r"^[0-9a-f]{32}$")
            self.assertEqual(len(value), publication_parts.TRANSFER_ID_LENGTH)


if __name__ == "__main__":
    unittest.main()
