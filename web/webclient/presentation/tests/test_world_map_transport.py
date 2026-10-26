"""The scoped world-map frame allowance (transport-world-map-panel).

An intact ``world_map`` above one generic 64 KB frame travels as one
``ui_update``: both validators exempt only the world map from the generic
frame budget, keep every sibling (``local_map`` and ``area_map`` included)
inside the 65,536-byte envelope, and bound the world map by its own logical
ceiling. Fixtures are the synthetic ones in
``web/static/webclient/js/tests/map_panel_fixtures.js``; the real-geography
measurement lives in ``test_world_map_measurement``.
"""

import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tools.spec_traceability import covers_requirement

from web.webclient.presentation import map_panels
from web.webclient.presentation.map_panels import (
    WORLD_MAP_FRAME_MAX_BYTES,
    carries_intact_world_map,
    check_world_map_envelope,
    validate_world_map,
)
from web.webclient.presentation.map_parts import decode_map_parts
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.registry import PresenterSpec
from web.webclient.presentation.tests._support import (
    publication_failure,
    publication_receipt,
)
from web.webclient.presentation.tests.test_map_panel_protocol import (
    _Session,
    _context,
    _coordinator,
    _dense_grid,
    _registry,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = "./web/static/webclient/js/tests/map_panel_fixtures.js"
NODE_TEST = "web/static/webclient/js/tests/protocol_world_map_transport.test.js"


SERVER_TIME = {
    "year": 1, "season_index": 0, "season_label": "春",
    "day_in_season": 1, "hour": 0, "minute": 0, "second": 0,
}


def _node(script: str, stdin: str = "") -> str:
    return subprocess.run(
        ["node", "-e", script], input=stdin, text=True, capture_output=True, cwd=ROOT, check=True
    ).stdout


def _fixtures() -> dict:
    over = map_panels.WORLD_MAX_BYTES + 1
    return json.loads(
        _node(
            f"const F=require('{FIXTURES}');"
            "const S=require('./web/static/webclient/js/tests/protocol_support.js');"
            "process.stdout.write(JSON.stringify({small:F.worldMap(),status:S.validStatusPanel(),"
            f"large:F.largeWorldMap(200000),over:F.largeWorldMap({over}),grid:F.gridArea(),"
            f"at:F.worldMapOfBytes({over - 1}),just_over:F.worldMapOfBytes({over})}}));"
        )
    )


FIX = _fixtures()


def _copy(name: str) -> dict:
    return json.loads(json.dumps(FIX[name]))


def _frame(panels: dict, revision: int = 2) -> dict:
    return {
        "protocol_version": 1,
        "presentation_epoch": "w" * 22,
        "revision": revision,
        # Every ui_update is one exact-base delta; the parity baseline is the
        # browser store's revision 1 snapshot.
        "base_revision": revision - 1,
        "removed_panels": [],
        "mode": "exploration",
        "panels": panels,
        "layout_version": 1,
        "server_time": dict(SERVER_TIME),
    }


def _padded(panel: dict, minimum: int) -> dict:
    """``panel`` plus 2,000-character fields until it alone exceeds ``minimum``."""
    panel = dict(panel)
    index = 0
    while json_byte_size(panel) <= minimum:
        panel[f"t_pad_{index}"] = "x" * 2000
        index += 1
    return panel


def _status() -> dict:
    """A browser-valid ``status`` panel (the Node suite's shared fixture)."""
    return _copy("status")


def _browser_accepts(frames: list[dict]) -> list[bool]:
    """Each frame's adoption by a fresh production browser store."""
    script = """
const fs = require('node:fs');
const P = require('./web/static/webclient/js/elosern/protocol.js');
const { validStatusPanel, serverTime } = require('./web/static/webclient/js/tests/protocol_support.js');
const frames = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(frames.map((frame) => {
  const store = P.createStore();
  store.beginTransport(1);
  store.receive(1, 'ui_snapshot', [{protocol_version: 1, presentation_epoch: frame.presentation_epoch,
    revision: 1, mode: 'exploration', panels: {status: validStatusPanel()}, layout_version: 1,
    server_time: serverTime()}], {});
  return store.receive(1, 'ui_update', [frame], {}).accepted === true;
})));
"""
    return json.loads(_node(script, json.dumps(frames, ensure_ascii=False)))


def _server_accepts(frame: dict) -> bool:
    try:
        if carries_intact_world_map(frame):
            check_world_map_envelope(frame)
        else:
            check_envelope(frame)
    except ProtocolValidationError:
        return False
    return True


class WorldMapFrameParityTests(unittest.TestCase):
    """Both validators decide identically on the same frames."""

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_world_map_allowance_parity(self):
        large = _copy("large")
        self.assertGreater(json_byte_size(large), MAX_CANONICAL_JSON_BYTES)
        long_world = _copy("large")
        long_world["districts"][1]["name"] = "名" * 3000
        unknown_world = _copy("large")
        unknown_world["secret"] = 1
        cases = [
            ("large intact world map", _frame({"world_map": large}), True),
            ("small world map", _frame({"world_map": _copy("small")}), True),
            ("world map with a companion", _frame({"world_map": _copy("large"), "status": _status()}), True),
            ("over-bound world map", _frame({"world_map": _copy("over")}), False),
            ("world map of exactly the ceiling", _frame({"world_map": _copy("at")}), True),
            ("world map one byte over the ceiling", _frame({"world_map": _copy("just_over")}), False),
            ("oversized companion", _frame({"world_map": _copy("small"), "status": _padded(_status(), 70_000)}), False),
            ("oversized local_map beside the world map", _frame({"world_map": _copy("small"), "local_map": _padded({"schema_version": 1}, 70_000)}), False),
            ("unsafe integer in a sibling", _frame({"world_map": _copy("large"), "status": {**_status(), "t": 2**60}}), False),
            ("unknown world field", _frame({"world_map": unknown_world}), False),
            ("long world string", _frame({"world_map": long_world}), False),
            ("oversized area_map alone", _frame({"area_map": _padded(_copy("grid"), 70_000)}), False),
        ]
        # Exact envelope fields are the browser's to enforce (the server builds
        # its own envelopes); the allowance must not relax them.
        field_cases = [
            ("boolean revision", {**_frame({"world_map": _copy("large")}), "revision": True}),
            ("unknown envelope field", {**_frame({"world_map": _copy("large")}), "extra": 1}),
        ]
        js = _browser_accepts([frame for _, frame, _ in cases] + [frame for _, frame in field_cases])
        for (name, frame, expected), browser in zip(cases, js[: len(cases)], strict=True):
            with self.subTest(case=name):
                self.assertEqual(_server_accepts(frame), expected)
                self.assertEqual(browser, expected)
        for (name, _), browser in zip(field_cases, js[len(cases) :], strict=True):
            with self.subTest(case=name):
                self.assertFalse(browser)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_the_ceiling_fixtures_sit_exactly_on_the_boundary(self):
        self.assertEqual(json_byte_size(validate_world_map(_copy("at"))), map_panels.WORLD_MAX_BYTES)
        self.assertEqual(json_byte_size(_copy("just_over")), map_panels.WORLD_MAX_BYTES + 1)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_allowance_predicate_and_frame_ceiling(self):
        big = _copy("large")
        self.assertTrue(carries_intact_world_map(_frame({"world_map": big})))
        for panels in ({"world_map": {**big, "part": {}}}, {"world_map": None}, {"world_map": []}, {"area_map": _copy("grid")}):
            with self.subTest(panels=list(panels)):
                self.assertFalse(carries_intact_world_map(_frame(panels)))
        for panels in ([], None):
            self.assertFalse(carries_intact_world_map({**_frame({}), "panels": panels}))
        self.assertEqual(WORLD_MAP_FRAME_MAX_BYTES, MAX_CANONICAL_JSON_BYTES + map_panels.WORLD_MAX_BYTES)
        self.assertEqual(map_panels.WORLD_MAX_BYTES, 2_097_152)
        # The generic envelope itself is unchanged: the same large frame fails it.
        with self.assertRaises(ProtocolValidationError):
            check_envelope(_frame({"world_map": big}))
        js = json.loads(
            _node(
                "const P=require('./web/static/webclient/js/elosern/protocol.js');"
                "process.stdout.write(JSON.stringify([P.WORLD_MAP_FRAME_MAX_BYTES,P.MAP_MAX_BYTES.world_map]));"
            )
        )
        self.assertEqual(js, [WORLD_MAP_FRAME_MAX_BYTES, map_panels.WORLD_MAX_BYTES])


def _world_registry(world_body, *, dialogue=False, area=None, state=None):
    registry = _registry(
        area or (lambda: _copy("grid")), [], dialogue=dialogue, state=state
    )
    registry.register(
        PresenterSpec("world_map", 1, ("map_unavailable", "世界地圖"), lambda ctx: world_body(), on_demand=True)
    )
    return registry


class WorldMapCoordinatorTests(unittest.TestCase):
    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_a_large_world_map_ships_as_one_intact_frame(self):
        session = _Session()
        coordinator = _coordinator(session, _world_registry(lambda: _copy("large")))
        coordinator.full_snapshot(_context())
        with mock.patch("web.webclient.presentation.coordinator.log_debug") as log_debug:
            receipt = publication_receipt(
                coordinator.enqueue_publication(
                    lambda: _context(), affected_panels={"world_map"}
                )
            )
        (name, frame), = session.frames()[1:]
        self.assertEqual(name, "ui_update")
        self.assertEqual(frame["revision"], receipt.revision)
        self.assertNotIn("part", frame["panels"]["world_map"])
        self.assertEqual(frame["panels"]["world_map"], validate_world_map(_copy("large")))
        self.assertGreater(json_byte_size(frame), MAX_CANONICAL_JSON_BYTES)
        check_world_map_envelope(frame)
        log_debug.assert_called_once()
        self.assertEqual(log_debug.call_args.args[0], "world_map_frame_sent")
        self.assertEqual(log_debug.call_args.kwargs["context"]["bytes"], json_byte_size(frame["panels"]["world_map"]))

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_a_dialogue_companion_rides_in_the_same_frame(self):
        session = _Session()
        state = {"status": 0, "dialogue": 0}
        coordinator = _coordinator(
            session,
            _world_registry(lambda: _copy("large"), dialogue=True, state=state),
            mode="dialogue",
        )
        coordinator.full_snapshot(_context())
        # The conversation changed, so the dialogue companion is a real
        # difference carried by the same frame.
        state["dialogue"] = 1
        coordinator.enqueue_publication(lambda: _context(), affected_panels={"world_map"})
        (_, frame), = session.frames()[1:]
        self.assertEqual(set(frame["panels"]), {"world_map", "dialogue"})

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_an_oversized_companion_aborts_before_anything_is_sent(self):
        session = _Session()
        registry = _world_registry(lambda: _copy("large"))
        coordinator = _coordinator(session, registry)
        coordinator.full_snapshot(_context())
        padded = _padded(_status(), 70_000)
        before = coordinator.revision
        with mock.patch.object(registry, "render", side_effect=lambda name, ctx: padded if name == "status" else _copy("large")):
            # The companion alone is over the generic frame: nothing is sent.
            publication_failure(
                coordinator.enqueue_publication(
                    lambda: _context(), affected_panels={"status", "world_map"}
                )
            ).trap(ProtocolValidationError)
        self.assertEqual(coordinator.revision, before)
        self.assertEqual(len(session.frames()), 1)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_a_dense_area_map_uses_parts_while_the_world_map_stays_intact(self):
        session = _Session()
        coordinator = _coordinator(session, _world_registry(lambda: _copy("large"), area=_dense_grid))
        coordinator.full_snapshot(_context())
        coordinator.enqueue_publication(
            lambda: _context(), affected_panels={"area_map", "world_map"}
        )
        frames = [frame for _, frame in session.frames()[1:]]
        area = [frame for frame in frames if "area_map" in frame["panels"]]
        world = [frame for frame in frames if "world_map" in frame["panels"]]
        self.assertGreater(len(area), 1)
        self.assertEqual(len(world), 1)
        self.assertEqual(list(world[0]["panels"]), ["world_map"])
        self.assertGreater(world[0]["revision"], area[0]["revision"])
        self.assertEqual(
            decode_map_parts("area_map", [frame["panels"]["area_map"] for frame in area]),
            map_panels.validate_area_map(_dense_grid()),
        )
        self.assertEqual(world[0]["panels"]["world_map"], validate_world_map(_copy("large")))

    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_an_over_bound_world_map_degrades_to_unavailable(self):
        session = _Session()
        coordinator = _coordinator(session, _world_registry(lambda: _copy("over")))
        coordinator.full_snapshot(_context())
        with mock.patch("web.webclient.presentation.coordinator.log_error") as log_error:
            coordinator.enqueue_publication(lambda: _context(), affected_panels={"world_map"})
        (_, frame), = session.frames()[1:]
        self.assertIs(frame["panels"]["world_map"]["available"], False)
        self.assertEqual(log_error.call_args.args[0], "map_panel_invalid")
        check_envelope(frame)


class WorldMapBrowserStoreEvidenceTests(unittest.TestCase):
    """Executed evidence: the production browser store's world-map frame suite."""

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_browser_world_map_transport_suite_passes(self):
        result = subprocess.run(
            ["node", "--test", "--test-reporter=tap", NODE_TEST], capture_output=True, text=True, cwd=ROOT
        )
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
        self.assertIn("# fail 0", result.stdout)
