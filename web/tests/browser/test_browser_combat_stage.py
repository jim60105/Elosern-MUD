"""The foe line-up on the combat stage (webclient-combat-foes-on-stage, C13a).

Every journey injects committed combat snapshots with its own participants
and art catalog into the live client and reads the stage in the frame after
the commit. Geometry is measured from rendered boxes; motion is read from
computed styles and polled end states, never from elapsed time, so a slow
runner can only lengthen an in-flight window, never skip it.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import snapshot_envelope, wait_for_store_state
from ._journey_support import (
    _SCENE_PNG_BYTES,
    _art_panel,
    _combat_panel,
    _exploration_context_actions_panel,
    _exploration_panel,
    _interact_target,
    _participant,
)
from .test_browser_mode_transitions import _START_SCROLL_SAMPLER, _STOP_SCROLL_SAMPLER

REFERENCE = (1920, 1080)
VIEWPORTS = ((1920, 1080), (1440, 900), (1280, 720))

# Heights, front to back, as fractions of the player's stage actor
# (components/foe-lineup.js FOE_SCALES).
SCALES = {1: (1.0,), 2: (0.9, 0.78), 3: (0.8, 0.7, 0.61)}

_FOE_NAMES = ("哥布林", "史萊姆", "狼人", "骷髏兵", "蝙蝠")


def _foes(count: int, defeated: tuple[int, ...] = ()) -> list:
    """``count`` foes in presenter order, identities 11.., each with a catalog ref."""
    return [
        _participant(
            11 + i,
            "e%d" % (i + 1),
            _FOE_NAMES[i],
            "foes",
            "defeated" if (11 + i) in defeated else "active",
            0 if (11 + i) in defeated else 20 + 10 * i,
            60,
            str(11 + i),
        )
        for i in range(count)
    ]


def _combat_panels(count: int, defeated: tuple[int, ...] = ()) -> dict:
    panel = _combat_panel()
    party = [p for p in panel["participants"] if p["team"] == "party"]
    panel["participants"] = party + _foes(count, defeated)
    # The shared skills target the fixture's own foe identities; this stage
    # needs no skill frame.
    panel["skills"] = []
    refs = [p["portrait_ref"] for p in panel["participants"] if p["portrait_ref"] is not None]
    return {"context_actions": panel, "art": _art_panel(refs)}


def _exploration_panels() -> dict:
    return {
        "exploration": _exploration_panel([_interact_target(11, "小販")]),
        "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
        "art": _art_panel([]),
    }


# Commits one snapshot (or, with `reset`, a transport reset and its resync
# snapshot) and reads the stage in the next animation frame.
_COMMIT_AND_READ = """async ([env, reset]) => {
  const store = window.__elosernBridge.store;
  const view = store.view;
  if (reset) {
    const generation = view.generation + 1;
    store.beginTransport(generation);
    store.setConnected(true);
    await new Promise((resolve) => requestAnimationFrame(() => resolve()));
    window.__c13aResets = (window.__c13aResets || 0) + 1;
    env.presentation_epoch = 'browserTestEpoch_c13a' + String.fromCharCode(96 + window.__c13aResets);
    env.revision = 1;
    const result = store.receive(generation, 'ui_snapshot', [env], {});
    if (!result.accepted) throw new Error('resync rejected: ' + JSON.stringify(result));
  } else {
    env.presentation_epoch = view.epoch;
    env.revision = view.revision + 1;
    const result = store.receive(view.generation, 'ui_snapshot', [env], {});
    if (!result.accepted) throw new Error('snapshot rejected: ' + JSON.stringify(result));
  }
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));
  return window.__c13aRead();
}"""

_INSTALL_READER = """() => {
  window.__c13aRead = () => {
    const q = (sel) => document.querySelector(sel);
    const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; };
    const right = q('[data-anchor="actor-right"]');
    const rows = [...right.querySelectorAll(':scope > [data-testid="foe-lineup"]')];
    const frame = q('[data-testid="participant-frame"]');
    return {
      width: innerWidth,
      band: box(q('[data-testid="stage-band"]')),
      player: box(q('[data-anchor="actor-left"] [data-testid="stage-actor"]')),
      frame: box(frame),
      frameText: frame ? frame.innerText : '',
      commandLine: box(q('[data-anchor="command-line"]')),
      plate: box(q('.scene-backdrop__plate')),
      rows: rows.map((row) => ({
        inert: row.inert,
        count: row.getAttribute('data-count'),
        hidden: row.getAttribute('aria-hidden'),
        entering: row.classList.contains('foes-enter-enter-active'),
        leaving: row.classList.contains('foes-enter-leave-active'),
        opacity: Number(getComputedStyle(row).opacity),
        duration: getComputedStyle(row).transitionDuration,
        focusable: row.querySelectorAll('button, a, input, textarea, select, [tabindex]').length,
        slots: [...row.querySelectorAll('[data-testid="foe-slot"]')].map((slot) => ({
          ref: slot.getAttribute('data-portrait-ref'),
          inert: slot.inert,
          leaving: slot.classList.contains('foe-leave-active'),
          box: box(slot),
          z: Number(getComputedStyle(slot).zIndex),
          transform: getComputedStyle(slot).transform,
          duration: getComputedStyle(slot).transitionDuration,
          gauge: box(slot.querySelector('[data-testid="foe-gauge"]')),
          dimmed: slot.querySelector('[data-testid="stage-actor"]').getAttribute('data-speaking') !== 'true',
          img: !!slot.querySelector('img'),
        })),
      })),
    };
  };
}"""


def _identity(transform: str) -> bool:
    return transform in ("none", "matrix(1, 0, 0, 1, 0, 0)")


class CombatStageBrowserTest(BrowserAcceptanceTest):
    """Design D2-D6 of the foe line-up at the supported viewports and levels."""

    def _page(self, viewport=REFERENCE, motion_level="off"):
        page = self.logged_in_page(viewport, motion_level=motion_level)
        # The catalog's portraits and the scene are served, so every figure
        # renders its image deterministically.
        page.route(
            "**/art/*.png",
            lambda route: route.fulfill(status=200, content_type="image/png", body=_SCENE_PNG_BYTES),
        )
        page.wait_for_function(
            "() => !!(window.__elosernBridge && window.__elosernBridge.store.view.epoch)", timeout=15000
        )
        page.evaluate(_INSTALL_READER)
        self._commit(page, "exploration", _exploration_panels())
        wait_for_store_state(page, lambda s: s.get("mode") == "exploration")
        return page

    def _commit(self, page, mode: str, panels: dict, reset: bool = False) -> dict:
        return page.evaluate(_COMMIT_AND_READ, [snapshot_envelope("", 0, panels, mode=mode), reset])

    def _read(self, page) -> dict:
        return page.evaluate("() => window.__c13aRead()")

    def _wait(self, page, predicate_js: str, timeout: int = 15000) -> None:
        page.wait_for_function(f"() => {{ const s = window.__c13aRead(); return {predicate_js}; }}", timeout=timeout)

    @covers_requirement(
        "webclient-contextual-hud::foes-stand-opposite-the-player-during-combat",
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
        "webclient-contextual-hud::the-combat-participant-frame-presents-the-session-s-participants-and-their-portraits",
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage",
    )
    def test_foes_stand_opposite_the_player(self):
        """One, two, and three foes stand in depth on the band, right of the
        stage centre and clear of the player; the front face clears the
        participant frame; each gauge stands above the command-line row; the
        caption plate stays centred between the player and the leftmost foe;
        nothing in the row is focusable; the frame lists everyone."""
        page = self._page(REFERENCE)
        page.evaluate("() => document.querySelector('[data-testid=\"command-line-toggle\"]').click()")
        for viewport in VIEWPORTS:
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            page.wait_for_function("([w, h]) => innerWidth === w && innerHeight === h", arg=list(viewport))
            for count in (1, 2, 3):
                with self.subTest(viewport=viewport, count=count):
                    self._commit(page, "combat", _combat_panels(count))
                    self._wait(page, f"s.rows.length === 1 && s.rows[0].slots.length === {count}")
                    s = self._read(page)
                    row = s["rows"][0]
                    slots = row["slots"]
                    size = "%dx%d/%d" % (viewport[0], viewport[1], count)
                    self.assertEqual(row["count"], str(count))
                    self.assertEqual(row["hidden"], "true")
                    self.assertEqual(row["focusable"], 0)
                    self.assertEqual([x["ref"] for x in slots], [str(11 + i) for i in range(count)])
                    self.assertTrue(all(x["img"] and not x["dimmed"] for x in slots), size)
                    player = s["player"]
                    centre = s["width"] / 2
                    lift = 0.035 * player["height"]
                    for i, slot in enumerate(slots):
                        b = slot["box"]
                        self.assertAlmostEqual(b["height"], SCALES[count][i] * player["height"], delta=1.0, msg=size)
                        self.assertAlmostEqual(b["bottom"], s["band"]["top"] - i * lift, delta=1.0, msg=size)
                        self.assertGreater(b["left"], centre, f"foe {i} crosses the stage centre at {size}")
                        self.assertGreater(b["left"], player["right"], f"foe {i} meets the player at {size}")
                        gauge = slot["gauge"]
                        self.assertLessEqual(gauge["bottom"], s["commandLine"]["top"], f"gauge {i} meets the command line at {size}")
                        self.assertAlmostEqual((gauge["left"] + gauge["right"]) / 2, (b["left"] + b["right"]) / 2, delta=1.0)
                        if i:
                            prev = slots[i - 1]
                            self.assertLess(b["left"], prev["box"]["left"], size)
                            self.assertLess(b["right"], prev["box"]["right"], size)
                            self.assertLess(slot["z"], prev["z"], size)
                            self.assertLessEqual(gauge["right"], prev["gauge"]["left"], f"gauges {i - 1}/{i} overlap at {size}")
                    front = slots[0]["box"]
                    self.assertLessEqual(
                        (front["left"] + front["right"]) / 2, s["frame"]["left"] - 24 + 1,
                        f"the front foe's face is under the participant frame at {size}",
                    )
                    # The caption plate stands between the player and the row.
                    plate = s["plate"]
                    leftmost = slots[-1]["box"]["left"]
                    self.assertIsNotNone(plate)
                    self.assertGreaterEqual(plate["left"], player["right"], size)
                    self.assertLessEqual(plate["right"], leftmost, f"the caption meets the foes at {size}")
                    self.assertAlmostEqual(
                        (plate["left"] + plate["right"]) / 2, (player["right"] + leftmost) / 2, delta=1.5, msg=size
                    )
                    # The frame lists every participant with numerals.
                    for name in _FOE_NAMES[:count]:
                        self.assertIn(name, s["frameText"])
                    self.assertIn("勇者", s["frameText"])
                    self.assertIn("100/100", s["frameText"])
        page.close()

    @covers_requirement("webclient-contextual-hud::foes-stand-opposite-the-player-during-combat")
    def test_foes_beyond_three_stay_in_the_frame(self):
        """Five active foes: three stand on the stage, the frame lists five."""
        page = self._page(REFERENCE)
        self._commit(page, "combat", _combat_panels(5))
        self._wait(page, "s.rows.length === 1")
        s = self._read(page)
        self.assertEqual([x["ref"] for x in s["rows"][0]["slots"]], ["11", "12", "13"])
        for name in _FOE_NAMES:
            self.assertIn(name, s["frameText"])
        self.assertEqual(page.locator('[data-testid="participant-frame"] .participant-frame__token--foe').count(), 5)
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::foes-stand-opposite-the-player-during-combat",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_foes_enter_and_leave_full(self):
        """A live entry fades the row in over 350ms while its foes slide in; a
        defeat leaves an inert slot while the other steps forward; leaving
        combat fades an inert row; no stage ancestor ever scrolls sideways."""
        page = self._page(REFERENCE, motion_level=None)
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "full")

        page.evaluate(_START_SCROLL_SAMPLER)
        s = self._commit(page, "combat", _combat_panels(2))
        self.assertEqual(len(s["rows"]), 1)
        row = s["rows"][0]
        self.assertTrue(row["entering"])
        self.assertIn("0.35s", row["duration"])
        self.assertLess(row["opacity"], 1)
        self.assertTrue(all(not _identity(x["transform"]) for x in row["slots"]))
        self._wait(page, "s.rows.length === 1 && !s.rows[0].entering && s.rows[0].opacity === 1")

        s = self._commit(page, "combat", _combat_panels(2, defeated=(11,)))
        slots = s["rows"][0]["slots"]
        leaving = [x for x in slots if x["leaving"]]
        self.assertEqual(len(leaving), 1)
        self.assertEqual(leaving[0]["ref"], "11")
        self.assertTrue(leaving[0]["inert"])
        self.assertIn("已敗退", s["frameText"])
        self._wait(page, "s.rows[0].slots.length === 1")

        s = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(len(s["rows"]), 1)
        self.assertTrue(s["rows"][0]["leaving"])
        self.assertTrue(s["rows"][0]["inert"])
        self._wait(page, "s.rows.length === 0")
        worst = page.evaluate(_STOP_SCROLL_SAMPLER)
        self.assertGreater(worst["frames"], 1)
        self.assertEqual(worst["scrollLeft"], 0, worst)
        self.assertLessEqual(worst["overflow"], 0, worst)
        page.close()

    @covers_requirement("webclient-contextual-hud::foes-stand-opposite-the-player-during-combat")
    def test_reload_in_combat_plays_no_entrance(self):
        """A reconnect into combat mounts the row at rest."""
        page = self._page(REFERENCE, motion_level=None)
        self._commit(page, "combat", _combat_panels(3))
        self._wait(page, "s.rows.length === 1 && !s.rows[0].entering")
        s = self._commit(page, "combat", _combat_panels(3), reset=True)
        self.assertEqual(len(s["rows"]), 1)
        self.assertFalse(s["rows"][0]["entering"])
        self.assertEqual(s["rows"][0]["opacity"], 1)
        self.assertTrue(all(_identity(x["transform"]) for x in s["rows"][0]["slots"]))
        page.close()

    @covers_requirement("webclient-contextual-hud::foes-stand-opposite-the-player-during-combat")
    def test_foes_reduced_only_fade(self):
        """At reduced the row fades within 150ms and nothing moves."""
        page = self._page(REFERENCE, motion_level="reduced")
        s = self._commit(page, "combat", _combat_panels(2))
        row = s["rows"][0]
        self.assertTrue(row["entering"])
        for duration in row["duration"].split(", "):
            self.assertLessEqual(float(duration.rstrip("s")), 0.15)
        self.assertTrue(all(_identity(x["transform"]) for x in row["slots"]))
        self._wait(page, "s.rows.length === 1 && !s.rows[0].entering")
        s = self._commit(page, "combat", _combat_panels(2, defeated=(11,)))
        for slot in s["rows"][0]["slots"]:
            for duration in slot["duration"].split(", "):
                self.assertLessEqual(float(duration.rstrip("s")), 0.15)
            self.assertTrue(_identity(slot["transform"]))
        page.close()

    @covers_requirement("webclient-contextual-hud::foes-stand-opposite-the-player-during-combat")
    def test_foes_off_is_instant(self):
        """At off the row and its foes are present or absent in the commit's frame."""
        page = self._page(REFERENCE)
        s = self._commit(page, "combat", _combat_panels(2))
        self.assertEqual(len(s["rows"]), 1)
        self.assertFalse(s["rows"][0]["entering"])
        self.assertEqual(s["rows"][0]["opacity"], 1)
        s = self._commit(page, "combat", _combat_panels(2, defeated=(11,)))
        self.assertEqual([x["ref"] for x in s["rows"][0]["slots"]], ["12"])
        s = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(s["rows"], [])
        page.close()
