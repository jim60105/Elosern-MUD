"""On-demand map panel protocol (define-map-panel-protocol).

Exact ``area_map``/``world_map`` schemas with Python/JavaScript parity, the
bounded part codec, on-demand registry/coordinator semantics, and an
executed-evidence wrapper that runs the browser decoder/store Node tests.
Fixtures are the synthetic schema-valid ones in
``web/static/webclient/js/tests/map_panel_fixtures.js`` (one source for both
languages); no production lore is named.
"""

import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tools.spec_traceability import covers_requirement

from web.webclient.presentation import map_panels, map_parts
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.map_panels import (
    MAP_NODE_ID_RE,
    MapPanelError,
    validate_area_map,
    validate_map_panel,
    validate_world_map,
)
from web.webclient.presentation.map_parts import (
    MAP_PART_RAW_BYTES,
    decode_map_parts,
    encode_map_parts,
    max_parts,
    validate_map_part,
)
from web.webclient.presentation.protocol import (
    MAX_STRING_CODE_POINTS,
    ProtocolValidationError,
    check_envelope,
)
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from world.rules.map_knowledge import encode_grid, encode_room, encode_wild

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = "./web/static/webclient/js/tests/map_panel_fixtures.js"
NODE_TEST = "web/static/webclient/js/tests/protocol_map_panels.test.js"



def _node(script: str, stdin: str = "") -> str:
    return subprocess.run(
        ["node", "-e", script], input=stdin, text=True, capture_output=True, cwd=ROOT, check=True
    ).stdout


def _fixtures() -> dict:
    return json.loads(
        _node(
            f"const F=require('{FIXTURES}');"
            "process.stdout.write(JSON.stringify({grid:F.gridArea(),interior:F.interiorArea(),"
            "wild:F.wildernessArea(),world:F.worldMap()}));"
        )
    )


FIX = _fixtures()


def _copy(name: str) -> dict:
    return json.loads(json.dumps(FIX[name]))


def _js_decisions(cases: list[tuple[str, str, str]]) -> list[bool]:
    """Feed each case's exact JSON text to the browser validator."""
    script = """
const fs = require('node:fs');
const P = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(([panel, text]) => {
  try { P.validateMapPanel(panel, JSON.parse(text)); return true; } catch (_) { return false; }
})));
"""
    return json.loads(_node(script, json.dumps([[panel, text] for _, panel, text in cases])))


class MapSchemaParityTests(unittest.TestCase):
    """Both validators decide identically on the same wire text."""

    @covers_requirement(
        "webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators"
    )
    def test_bidirectional_schema_parity(self):
        def text(value):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        grid, interior, wild, world = (_copy(k) for k in ("grid", "interior", "wild", "world"))

        def variant(base, mutate):
            value = json.loads(json.dumps(base))
            mutate(value)
            return text(value)

        accept = [
            ("grid valid", "area_map", text(grid)),
            ("interior valid", "area_map", text(interior)),
            ("wilderness valid", "area_map", text(wild)),
            ("world valid", "world_map", text(world)),
            ("approximate integral float", "world_map", text(world).replace('"x":650,', '"x":650.0,', 1)),
        ]
        # Integral number spellings JSON cannot tell from integers: the browser
        # reads them as integers, so the server normalizes and accepts too.
        for spelling in ("3.0", "-0.0", "1e2", "1E1"):
            accept.append((f"integral spelling {spelling}", "area_map", text(grid).replace('"x":10,', f'"x":{spelling},', 1)))
        reject = [
            ("grid extra node field", "area_map", variant(grid, lambda v: v["nodes"][1].update(secret=1))),
            ("grid km frame", "area_map", variant(grid, lambda v: v["frame"].update(unit="km"))),
            ("interior with xy", "area_map", variant(interior, lambda v: v["nodes"][0].update(x=0, y=0))),
            ("foreign grid node", "area_map", variant(grid, lambda v: v["nodes"][2].update(id="grid:t_other:2:1"))),
            ("boolean coordinate", "area_map", variant(grid, lambda v: v["nodes"][1].update(x=True))),
            ("fractional metre", "area_map", variant(grid, lambda v: v["nodes"][1].update(x=10.5))),
            ("leading-zero node id", "area_map", variant(grid, lambda v: v.update(current_node="grid:t_map:01:1"))),
            ("current not visited", "area_map", variant(wild, lambda v: v["nodes"][112].update(visited=False))),
            ("bearing 360", "area_map", variant(grid, lambda v: v["quest_markers"][1]["destination"].update(bearing_deg=360))),
            ("tagged both", "area_map", variant(grid, lambda v: v["quest_markers"][0]["destination"].update(bearing_deg=1))),
            ("unlit enriched", "world_map", variant(world, lambda v: v["districts"][0].update(name="秘"))),
            ("landmark node id", "world_map", variant(world, lambda v: v["districts"][1]["landmark"].update(node_id="room:1"))),
            ("approximate off grid", "world_map", variant(world, lambda v: v["quest_markers"][1].update(x=651))),
            ("approximate exact id", "world_map", variant(world, lambda v: v["quest_markers"][1].update(node_id="room:1"))),
            ("open coastline", "world_map", variant(world, lambda v: v["common"]["coastline"].pop())),
            ("trail overlap", "world_map", variant(world, lambda v: v.update(trail={"resolution_km": 1, "rows": [[1, [[0, 3], [2, 1]]]]}))),
            ("trail resolution 2", "world_map", variant(world, lambda v: v.update(trail={"resolution_km": 2, "rows": []}))),
            ("unknown place kind", "world_map", variant(world, lambda v: v["visited_places"][0].update(kind="dungeon"))),
        ]
        for name, _, payload_text in accept[4:]:
            self.assertNotEqual(payload_text, text(world) if "approximate" in name else text(grid), name)
        cases = [(name, panel, body, True) for name, panel, body in accept] + [
            (name, panel, body, False) for name, panel, body in reject
        ]
        js = _js_decisions([(name, panel, body) for name, panel, body, _ in cases])
        for (name, panel, payload_text, expected), js_accepts in zip(cases, js, strict=True):
            with self.subTest(case=name):
                try:
                    validate_map_panel(panel, json.loads(payload_text))
                    py_accepts = True
                except ProtocolValidationError:
                    py_accepts = False
                self.assertEqual(py_accepts, expected)
                self.assertEqual(js_accepts, expected)

    @covers_requirement(
        "webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators"
    )
    def test_mirrored_constants_are_equal(self):
        js = json.loads(
            _node(
                "const P=require('./web/static/webclient/js/elosern/protocol.js');"
                "process.stdout.write(JSON.stringify({c:P.MAP_CONSTANTS,s:P.MAP_PANEL_SCHEMAS,"
                "b:P.MAP_MAX_BYTES,raw:P.MAP_PART_RAW_BYTES,chars:P.MAP_PART_CHUNK_CHARS,"
                "parts:[P.maxMapParts('area_map'),P.maxMapParts('world_map')]}));"
            )
        )
        for name, value in js["c"].items():
            with self.subTest(constant=name):
                expected = MAP_NODE_ID_RE.pattern if name == "MAP_NODE_ID_RE" else getattr(map_panels, name)
                if isinstance(expected, tuple):
                    expected = list(expected)
                if name == "MAP_NODE_ID_RE":
                    # Same grammar, spelled with JS escaping of the literal.
                    self.assertEqual(value.replace("\\/", "/"), expected)
                else:
                    self.assertEqual(value, expected)
        self.assertEqual(js["s"], map_panels.MAP_PANEL_SCHEMAS)
        self.assertEqual(js["b"], map_panels.MAP_MAX_BYTES)
        self.assertEqual(js["raw"], MAP_PART_RAW_BYTES)
        self.assertEqual(js["chars"], map_parts.MAP_PART_CHUNK_CHARS)
        self.assertEqual(js["chars"], MAX_STRING_CODE_POINTS)
        self.assertEqual(js["parts"], [max_parts("area_map"), max_parts("world_map")])

    @covers_requirement(
        "webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators"
    )
    def test_canonical_encoders_match_the_node_grammar(self):
        # Publishers own existence checks; the wire grammar accepts exactly
        # the canonical encoder output and nothing looser.
        for node_id in (encode_grid("t_map", 0, 12), encode_wild("elosern", 2699, 0), encode_room(42)):
            with self.subTest(node_id=node_id):
                self.assertRegex(node_id, MAP_NODE_ID_RE)
        for bad in ("grid:t_map:-1:0", "room:0", "wild:t_other:1:1", "grid:a:b:1:2"):
            with self.subTest(bad=bad):
                self.assertIsNone(MAP_NODE_ID_RE.fullmatch(bad))

    @covers_requirement(
        "webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators"
    )
    def test_layer_frames_carry_their_own_units(self):
        grid, interior, wild = (validate_area_map(_copy(k)) for k in ("grid", "interior", "wild"))
        self.assertEqual(grid["frame"], {"key": grid["map_id"], "unit": "m"})
        self.assertEqual(interior["frame"], {"key": interior["map_id"], "unit": "none"})
        self.assertEqual(wild["frame"], {"key": "elosern", "unit": "km"})
        self.assertNotIn("x", interior["nodes"][0])
        self.assertIsInstance(wild["nodes"][0]["x"], float)
        world = validate_world_map(_copy("world"))
        self.assertEqual(set(world["districts"][0]), {"id", "lit", "outline"})


class MapPartCodecTests(unittest.TestCase):
    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    def test_round_trip_uses_fixed_bounded_parts(self):
        body = _copy("wild")
        parts = encode_map_parts("area_map", body)
        self.assertGreater(len(parts), 1)
        self.assertEqual(len({part["part"]["transfer_id"] for part in parts}), 1)
        for part in parts[:-1]:
            self.assertEqual(len(validate_map_part("area_map", part)[1]), MAP_PART_RAW_BYTES)
            self.assertEqual(len(part["part"]["chunk"]), MAX_STRING_CODE_POINTS)
        self.assertEqual(decode_map_parts("area_map", parts), validate_area_map(body))

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    def test_incomplete_duplicate_or_malformed_transfers_fail(self):
        parts = encode_map_parts("area_map", _copy("wild"))
        for name, broken in (
            ("missing", parts[:-1]),
            ("duplicate", parts[:1] + parts[:1] + parts[2:]),
            ("reordered", [parts[1], parts[0], *parts[2:]]),
        ):
            with self.subTest(case=name), self.assertRaises(MapPanelError):
                decode_map_parts("area_map", broken)
        part = json.loads(json.dumps(parts[0]))
        for name, mutate in (
            ("count", lambda p: p.update(count=p["count"] + 1)),
            ("index", lambda p: p.update(index=p["count"])),
            ("chunk", lambda p: p.update(chunk=p["chunk"][:-4])),
            ("alphabet", lambda p: p.update(chunk="*" + p["chunk"][1:])),
            ("bytes", lambda p: p.update(byte_length=map_panels.AREA_MAX_BYTES + 1)),
            ("extra", lambda p: p.update(extra=1)),
        ):
            value = json.loads(json.dumps(part))
            mutate(value["part"])
            with self.subTest(case=name), self.assertRaises(MapPanelError):
                validate_map_part("area_map", value)
        with self.assertRaises(MapPanelError):
            encode_map_parts("area_map", {**_copy("grid"), "secret": 1})

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    def test_python_parts_are_adopted_by_the_browser_store(self):
        body = _copy("wild")
        parts = encode_map_parts("area_map", body)
        frames = [
            {
                "protocol_version": 1,
                "presentation_epoch": "e" * 22,
                "revision": 2,
                "mode": "exploration",
                "panels": {"area_map": part},
                "layout_version": 1,
                "server_time": {
                    "year": 1, "season_index": 0, "season_label": "春",
                    "day_in_season": 1, "hour": 0, "minute": 0, "second": 0,
                },
            }
            for part in parts
        ]
        for frame in frames:
            check_envelope(frame)
        script = """
const fs = require('node:fs');
const P = require('./web/static/webclient/js/elosern/protocol.js');
const frames = JSON.parse(fs.readFileSync(0, 'utf8'));
const store = P.createStore();
store.beginTransport(1);
const snap = Object.assign({}, frames[0], {revision: 1, panels: {}});
snap.panels = {};
const first = store.receive(1, 'ui_snapshot', [Object.assign({}, snap, {panels: {status: {schema_version: 4, available: false, reason: {code: 'x', message: 'x'}}}})], {});
const results = frames.map((f) => store.receive(1, 'ui_update', [f], {}));
process.stdout.write(JSON.stringify({first, results, state: store.getState()}));
"""
        out = json.loads(_node(script, json.dumps(frames)))
        self.assertTrue(out["first"]["accepted"])
        self.assertTrue(all(result["accepted"] for result in out["results"]))
        self.assertTrue(all(result.get("partial") for result in out["results"][:-1]))
        self.assertEqual(out["state"]["maps"]["area_map"], validate_area_map(body))
        self.assertEqual(out["state"]["revision"], 2)


# ---------------------------------------------------------------------------
# Registry and coordinator.
# ---------------------------------------------------------------------------


class _Session:
    sessid = 7

    def __init__(self):
        self.sent = []

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def frames(self):
        return [(name, args[0][0]) for kwargs in self.sent for name, args in kwargs.items()]


class _Calendar:
    year, season_index, season_name, day_in_season, hour, minute, second = 1204, 2, "仲夏", 17, 14, 30, 5


def _registry(map_body, calls, *, dialogue=False):
    registry = PresentationRegistry("test")
    registry.register(
        PresenterSpec(
            name="status",
            schema_version=1,
            unavailable_reason=("missing_data", "無法讀取"),
            presenter=lambda ctx: {"schema_version": 1, "available": True},
        )
    )
    if dialogue:
        registry.register(
            PresenterSpec(
                name="dialogue",
                schema_version=2,
                unavailable_reason=("dialogue_unavailable", "對話"),
                presenter=lambda ctx: {"schema_version": 2, "available": True},
            )
        )

    def presenter(ctx):
        calls.append(ctx)
        return map_body()

    # Test-only on-demand presenter with schema-valid geometry: production
    # registers no map presenter until its owning change.
    registry.register(
        PresenterSpec(
            name="area_map",
            schema_version=1,
            unavailable_reason=("map_unavailable", "地圖目前無法顯示"),
            presenter=presenter,
            on_demand=True,
        )
    )
    return registry


def _coordinator(session, registry, mode="exploration"):
    return PresentationCoordinator(
        session, registry, calendar_provider=lambda: _Calendar(), mode_provider=lambda ctx: mode
    )


def _context():
    return PresentationContext(actor=object(), protocol_version=1)


def _dense_grid():
    """A small-byte grid area whose 400 edges exceed the 320-item frame list."""
    body = _copy("grid")
    body["nodes"] = [
        {"id": f"grid:t_map:{i}:0", "label": f"點{i}", "x": i, "y": 0,
         "visibility": "current" if i == 0 else "seen", "gateway": None, "action": None}
        for i in range(21)
    ]
    body["current_node"] = "grid:t_map:0:0"
    body["edges"] = [
        {"source": f"grid:t_map:{a}:0", "destination": f"grid:t_map:{b}:0"}
        for a in range(21) for b in range(21) if a != b
    ][:400]
    body["quest_markers"] = []
    return body


class OnDemandRegistryTests(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_only_map_panels_register_on_demand(self):
        registry = PresentationRegistry("test")
        for spec in (
            PresenterSpec("status", 1, ("x", "x"), lambda ctx: {}, on_demand=True),
            PresenterSpec("area_map", 1, ("x", "x"), lambda ctx: {}),
            PresenterSpec("world_map", 2, ("x", "x"), lambda ctx: {}, on_demand=True),
        ):
            with self.subTest(spec=spec.name), self.assertRaises(ProtocolValidationError):
                registry.register(spec)
        registry.register(PresenterSpec("world_map", 1, ("x", "x"), lambda ctx: {}, on_demand=True))
        self.assertEqual(registry.on_demand_panel_names, {"world_map"})
        self.assertEqual(registry.eager_panel_names, frozenset())

    def test_production_registers_no_map_presenter(self):
        from web.webclient.presentation.registry import build_production_registry

        names = build_production_registry().panel_names
        self.assertFalse(names & set(map_panels.MAP_PANEL_SCHEMAS))


class OnDemandCoordinatorTests(unittest.TestCase):
    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_eager_publication_never_runs_map_presenters(self):
        calls, session = [], _Session()
        coordinator = _coordinator(session, _registry(lambda: _copy("grid"), calls))
        coordinator.full_snapshot(_context())
        coordinator._publish_presentation(_context(), {"status"})
        self.assertEqual(calls, [])
        frames = session.frames()
        self.assertEqual([name for name, _ in frames], ["ui_snapshot", "ui_update"])
        for _, envelope in frames:
            self.assertNotIn("area_map", envelope["panels"])

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    def test_a_fitting_map_ships_in_one_frame(self):
        calls, session = [], _Session()
        coordinator = _coordinator(session, _registry(lambda: _copy("grid"), calls))
        coordinator.full_snapshot(_context())
        revision = coordinator._publish_presentation(_context(), {"area_map"})
        self.assertEqual(len(calls), 1)
        (name, frame), = session.frames()[1:]
        self.assertEqual(name, "ui_update")
        self.assertEqual(frame["panels"]["area_map"], validate_area_map(_copy("grid")))
        self.assertEqual(frame["revision"], revision)

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    @covers_requirement(
        "webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes"
    )
    def test_an_oversized_map_travels_as_one_bounded_transfer(self):
        session = _Session()
        coordinator = _coordinator(session, _registry(_dense_grid, []))
        coordinator.full_snapshot(_context())
        with mock.patch("web.webclient.presentation.coordinator.log_debug") as log_debug:
            coordinator._publish_presentation(_context(), {"area_map"})
        frames = [frame for _, frame in session.frames()[1:]]
        self.assertGreater(len(frames), 0)
        self.assertEqual({frame["revision"] for frame in frames}, {coordinator.revision})
        for frame in frames:
            check_envelope(frame)
            self.assertEqual(list(frame["panels"]), ["area_map"])
            self.assertEqual({k: v for k, v in frame.items() if k != "panels"},
                             {k: v for k, v in frames[0].items() if k != "panels"})
        self.assertEqual(
            decode_map_parts("area_map", [frame["panels"]["area_map"] for frame in frames]),
            validate_area_map(_dense_grid()),
        )
        log_debug.assert_called_once()
        self.assertEqual(log_debug.call_args.kwargs["context"]["parts"], len(frames))

    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    def test_dialogue_companion_precedes_the_transfer(self):
        session = _Session()
        coordinator = _coordinator(session, _registry(_dense_grid, [], dialogue=True), mode="dialogue")
        coordinator.full_snapshot(_context())
        coordinator._publish_presentation(_context(), {"area_map"})
        frames = [frame for _, frame in session.frames()[1:]]
        self.assertEqual(set(frames[0]["panels"]), {"dialogue"})
        self.assertTrue(all(list(frame["panels"]) == ["area_map"] for frame in frames[1:]))
        self.assertGreater(frames[1]["revision"], frames[0]["revision"])

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    def test_an_invalid_map_body_degrades_to_unavailable(self):
        session = _Session()
        coordinator = _coordinator(session, _registry(lambda: {**_copy("grid"), "secret": 1}, []))
        coordinator.full_snapshot(_context())
        with mock.patch("web.webclient.presentation.coordinator.log_error") as log_error:
            coordinator._publish_presentation(_context(), {"area_map"})
        _, frame = session.frames()[-1]
        self.assertIs(frame["panels"]["area_map"]["available"], False)
        self.assertEqual(frame["panels"]["area_map"]["reason"]["code"], "internal_presenter_error")
        self.assertEqual(log_error.call_args.args[0], "map_panel_invalid")


class BrowserStoreEvidenceTests(unittest.TestCase):
    """Executed evidence: the production browser decoder/store Node tests."""

    @covers_requirement(
        "webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels"
    )
    @covers_requirement(
        "webclient-oob-protocol::full-snapshots-and-updates-have-registered-replacement-semantics"
    )
    @covers_requirement(
        "webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators"
    )
    def test_browser_map_store_suite_passes(self):
        result = subprocess.run(["node", "--test", "--test-reporter=tap", NODE_TEST], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
        self.assertIn("# fail 0", result.stdout)
