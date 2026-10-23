"""World-map transport over the real socket (transport-world-map-panel).

The measured continental ``world_map`` (``tools.world_map_payload``, built
from the shipped geography) is published by the live server's coordinator
through the managed Evennia server, AMP, the portal and the WebSocket, and
adopted by the production browser store. Each journey asserts that:

- exactly one ``ui_update`` WebSocket frame carried the world map, intact
  (no bounded part), and that frame is larger than the generic 64 KB
  envelope;
- the store committed the map into ``state.maps`` and its canonical UTF-8
  bytes have the same length and SHA-256 as the server's validated body.

One server boots per class with the shipped catalogs, so the payload is the
real geography. The world map is published through the superuser ``@py``
command (see ``world_map_transport_fixture``) because the world presenter and
the ``map.view`` world scope belong to ``publish-world-map-panel``.
"""

from __future__ import annotations

import json
import re

from tools.spec_traceability import covers_requirement

from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import login_and_open, narrative_log_text, wait_for_store_state
from .harness import ManagedServer

GENERIC_FRAME_BYTES = 65_536
_RESULT_RE = re.compile(r"WORLD_MAP (\w+) (\d+) (\d+) ([0-9a-f]{64})")

_CAPTURE_SCRIPT = """() => {
  const store = window.__elosernBridge.store;
  window.__worldMapAdopted = null;
  store.subscribe((state) => {
    if (state && state.maps && state.maps.world_map) {
      window.__worldMapAdopted = { revision: state.revision, map: state.maps.world_map };
    }
  });
  return true;
}"""

# Canonical JSON (sorted keys, no whitespace) of the adopted map, measured
# as UTF-8 and hashed in the page.
_DIGEST_SCRIPT = """async () => {
  const adopted = window.__worldMapAdopted;
  if (!adopted) return null;
  const canonical = (value) => {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
  };
  const bytes = new TextEncoder().encode(canonical(adopted.map));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  return { revision: adopted.revision, bytes: bytes.length, sha256: hex };
}"""


def _store_active(state: dict) -> bool:
    return bool(state.get("connected")) and state.get("phase") == "active" and state.get("mutationsLocked") is not True


class WorldMapTransportTests(BrowserAcceptanceTest):
    """The measured world map crosses the real socket intact."""

    @classmethod
    def setUpClass(cls) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-world-map-")
        # Shipped catalogs: the payload is the real continental geography.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    def _round_trip(self, case: str) -> None:
        page = self.new_page()
        frames: list[str] = []

        def on_socket(socket) -> None:
            def on_frame(payload) -> None:
                text = payload if isinstance(payload, str) else payload.decode("utf-8")
                if '"world_map"' not in text:
                    return
                try:
                    name, args, _ = json.loads(text)
                    panels = args[0]["panels"]
                except (ValueError, TypeError, KeyError, IndexError):
                    return
                if name == "ui_update" and isinstance(panels.get("world_map"), dict):
                    frames.append(text)

            socket.on("framereceived", on_frame)

        page.on("websocket", on_socket)
        login_and_open(page, self.webclient_url, self.base_url)
        wait_for_store_state(page, _store_active, timeout=45000)
        page.evaluate(_CAPTURE_SCRIPT)
        command = (
            "@py __import__('web.tests.browser.world_map_transport_fixture', fromlist=['publish'])"
            f".publish(me, '{case}')"
        )
        page.evaluate("(text) => window.__elosernBridge.store.sendText(text)", command)

        def published(_state: dict) -> bool:
            return _RESULT_RE.search(narrative_log_text(page)) is not None

        try:
            wait_for_store_state(page, published, timeout=60000)
        except AssertionError as error:
            raise AssertionError(f"no fixture result; narrative tail: {narrative_log_text(page)[-1500:]!r}") from error
        match = _RESULT_RE.search(narrative_log_text(page))
        self.assertEqual(match.group(1), case)
        revision, size, digest = int(match.group(2)), int(match.group(3)), match.group(4)

        def adopted(_state: dict) -> bool:
            return bool(page.evaluate("() => !!window.__worldMapAdopted"))

        wait_for_store_state(page, adopted, timeout=60000)
        browser = page.evaluate(_DIGEST_SCRIPT)
        self.assertEqual(browser["bytes"], size)
        self.assertEqual(browser["sha256"], digest)
        self.assertGreaterEqual(browser["revision"], revision)

        self.assertEqual(len(frames), 1, "the world map must travel in exactly one WebSocket frame")
        self.assertGreater(len(frames[0].encode("utf-8")), GENERIC_FRAME_BYTES)
        name, args, _ = json.loads(frames[0])
        self.assertEqual(name, "ui_update")
        envelope = args[0]
        self.assertEqual(envelope["revision"], revision)
        self.assertNotIn("part", envelope["panels"]["world_map"])
        self.assertIs(envelope["panels"]["world_map"]["available"], True)

    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_representative_world_map_round_trips_intact(self):
        self._round_trip("representative")

    @covers_requirement("webclient-oob-protocol::continental-map-transport-is-measured-end-to-end")
    def test_supported_worst_case_world_map_round_trips_intact(self):
        self._round_trip("worst")
