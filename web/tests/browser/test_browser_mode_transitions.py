"""Mode transitions at the motion level (webclient-mode-transitions, C11c).

Every journey commits a mode change into the live client and reads, in the
frame after the commit and inside the same evaluation, the state the
transitions leave: the collapsed command region's reach and computed
transition, the host's entering or leaving copy, the flash's animation, the
veil's opacity transition, the command panel's flip, and the choice rows'
stagger delays. No assertion measures elapsed time: a journey reads computed
styles and polls for end states, so a slow runner can only make an in-flight
window longer, never skip it.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import open_dialogue_choices, snapshot_envelope, wait_for_store_state
from ._journey_support import (
    _combat_panel,
    _exploration_context_actions_panel,
    _exploration_panel,
    _interact_target,
)

REFERENCE = (1451, 790)



def _dialogue_panel() -> dict:
    return {
        "schema_version": 2,
        "available": True,
        "kind": "dialogue",
        "host": {"identity": 11, "display_name": "小販", "portrait_ref": None},
        "bond_stage": None,
        "line": "歡迎光臨，要看看今天的貨嗎？",
        "choices": [
            {"keyword_id": "goods", "label": "有什麼貨？"},
            {"keyword_id": "price", "label": "價錢怎麼算？"},
            {"keyword_id": "town", "label": "最近鎮上如何？"},
            {"keyword_id": "road", "label": "路上安全嗎？"},
        ],
    }


def _exploration_panels() -> dict:
    return {
        "exploration": _exploration_panel([_interact_target(11, "小販")]),
        "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
    }


_CLOSED_DIALOGUE = {
    "schema_version": 2,
    "available": False,
    "reason": {"code": "dialogue_unavailable", "message": "對話已結束"},
}


# Commits one snapshot and reads the stage in the next animation frame, in
# the same evaluation. `reset` first runs a transport reset and commits the
# snapshot as the resync (a new presentation epoch): the reconnect path.
_COMMIT_AND_READ = """async ([env, reset]) => {
  const store = window.__elosernBridge.store;
  const view = store.view;
  if (reset) {
    const generation = view.generation + 1;
    store.beginTransport(generation);
    store.setConnected(true);
    await new Promise((resolve) => requestAnimationFrame(() => resolve()));
    window.__c11cResets = (window.__c11cResets || 0) + 1;
    env.presentation_epoch = 'browserTestEpoch_c11c' + String.fromCharCode(96 + window.__c11cResets);
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
  return window.__c11cRead();
}"""

# The reader, installed once per page.
_INSTALL_READER = """() => {
  window.__c11cRead = () => {
    const q = (sel) => document.querySelector(sel);
    const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width }; };
    const stage = q('[data-testid="elosern-stage"]');
    const command = q('[data-anchor="band-command"]');
    const commandStyle = getComputedStyle(command);
    const dockChild = command.firstElementChild;
    const flash = q('[data-testid="stage-flash"]');
    const veil = q('[data-testid="stage-combat-veil"]');
    const anims = (el) => (el ? el.getAnimations().map((a) => ({ name: a.animationName || null, duration: a.effect.getTiming().duration })) : []);
    const hosts = [...document.querySelectorAll('[data-anchor="actor-right"] [data-testid="stage-actor"]')];
    const rows = [...document.querySelectorAll('[data-anchor="choices"] [role="menuitem"]')];
    const active = document.activeElement;
    return {
      mode: stage.getAttribute('data-elosern-mode'),
      modeChange: stage.getAttribute('data-mode-change'),
      band: box(q('[data-testid="stage-band"]')),
      message: box(q('[data-anchor="band-message"]')),
      command: {
        inert: command.inert,
        visibility: commandStyle.visibility,
        opacity: Number(commandStyle.opacity),
        position: commandStyle.position,
        transform: commandStyle.transform,
        duration: commandStyle.transitionDuration,
        property: commandStyle.transitionProperty,
      },
      dockAnimations: anims(dockChild),
      flash: {
        hidden: flash.getAttribute('aria-hidden'),
        pointer: getComputedStyle(flash).pointerEvents,
        opacity: Number(getComputedStyle(flash).opacity),
        animations: anims(flash),
      },
      veil: {
        hidden: veil.getAttribute('aria-hidden'),
        pointer: getComputedStyle(veil).pointerEvents,
        opacity: Number(getComputedStyle(veil).opacity),
        duration: getComputedStyle(veil).transitionDuration,
      },
      hosts: hosts.map((el) => ({
        inert: el.inert,
        entering: el.classList.contains('actor-enter-enter-active'),
        leaving: el.classList.contains('actor-enter-leave-active'),
        duration: getComputedStyle(el).transitionDuration,
        transform: getComputedStyle(el).transform,
      })),
      plates: [...document.querySelectorAll('[data-testid="message-name-plate"]')].map((el) => ({
        inert: el.inert,
        entering: el.classList.contains('plate-enter-active'),
        duration: getComputedStyle(el).transitionDuration,
      })),
      list: !!q('[data-anchor="choices"] [data-testid="dialogue-choices"]'),
      listFocused: active === q('[data-anchor="choices"] [data-testid="dialogue-choices"]'),
      dockFocused: !!active && active.id === 'action-dock',
      rows: rows.map((el) => ({ delay: getComputedStyle(el).animationDelay, name: getComputedStyle(el).animationName, opacity: Number(getComputedStyle(el).opacity) })),
      flashPeak: getComputedStyle(document.documentElement).getPropertyValue('--motion-flash-peak').trim(),
    };
  };
}"""


# Samples, every animation frame until stopped, the horizontal scroll state
# of the stage, each element that contains it, and the document's scrolling
# element: the largest scroll offset and the largest scrollable overflow
# (scrollWidth - clientWidth) seen, with the element that showed it.
_START_SCROLL_SAMPLER = """() => {
  const stage = document.querySelector('[data-testid="elosern-stage"]');
  const chain = [];
  for (let el = stage; el; el = el.parentElement) chain.push(el);
  chain.push(document.scrollingElement);
  const name = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.classList.length ? '.' + [...el.classList].join('.') : '');
  const worst = { frames: 0, scrollLeft: 0, overflow: 0, at: null };
  window.__c11cScroll = { worst, running: true };
  const tick = () => {
    worst.frames += 1;
    for (const el of chain) {
      if (el.scrollLeft > worst.scrollLeft) { worst.scrollLeft = el.scrollLeft; worst.at = name(el); }
      const overflow = el.scrollWidth - el.clientWidth;
      if (overflow > worst.overflow) { worst.overflow = overflow; worst.at = name(el); }
    }
    if (window.__c11cScroll.running) requestAnimationFrame(tick);
  };
  tick();
}"""

_STOP_SCROLL_SAMPLER = """() => { window.__c11cScroll.running = false; return window.__c11cScroll.worst; }"""


def _identity(transform: str) -> bool:
    return transform in ("none", "matrix(1, 0, 0, 1, 0, 0)")


class ModeTransitionsBrowserTest(BrowserAcceptanceTest):
    """The dialogue, combat, and choice rows of design §9.3."""

    def _page(self, motion_level):
        page = self.logged_in_page(REFERENCE, motion_level=motion_level)
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
        return page.evaluate("() => window.__c11cRead()")

    def _wait(self, page, predicate_js: str, timeout: int = 15000) -> None:
        page.wait_for_function(f"() => {{ const s = window.__c11cRead(); return {predicate_js}; }}", timeout=timeout)

    def _enter_dialogue(self, page) -> dict:
        return self._commit(page, "dialogue", {**_exploration_panels(), "dialogue": _dialogue_panel()})

    def _leave_dialogue(self, page) -> dict:
        return self._commit(page, "exploration", {**_exploration_panels(), "dialogue": _CLOSED_DIALOGUE})

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_dialogue_enter_and_leave_full(self):
        """Entering dialogue widens the window at once and slides the inert
        command region out; the host enters over 350ms with the plate. Leaving
        reverses it: the host leaves inert and the dock is focused, in reach."""
        page = self._page(None)
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "full")
        state = self._enter_dialogue(page)
        self.assertEqual(state["modeChange"], "exploration-dialogue")
        self.assertAlmostEqual(state["message"]["width"], state["band"]["width"], delta=1.0)
        self.assertTrue(state["command"]["inert"])
        self.assertEqual(state["command"]["position"], "absolute")
        self.assertIn("0.25s", state["command"]["duration"])
        self.assertIn("transform", state["command"]["property"])
        self.assertEqual(len(state["hosts"]), 1)
        self.assertTrue(state["hosts"][0]["entering"])
        self.assertIn("0.35s", state["hosts"][0]["duration"])
        self.assertEqual(len(state["plates"]), 1)
        self.assertTrue(state["plates"][0]["entering"])
        # The slide ends hidden, the host at rest.
        self._wait(page, "s.command.visibility === 'hidden' && s.hosts.length === 1 && !s.hosts[0].entering")
        # The list appears once the live line is read, and takes focus.
        open_dialogue_choices(page)
        self._wait(page, "s.list && s.listFocused")

        state = self._leave_dialogue(page)
        self.assertEqual(state["modeChange"], "dialogue-exploration")
        self.assertFalse(state["command"]["inert"])
        self.assertEqual(state["command"]["visibility"], "visible")
        self.assertAlmostEqual(state["message"]["width"], state["band"]["width"] * 2 / 3, delta=2.0)
        self.assertEqual(len(state["hosts"]), 1)
        self.assertTrue(state["hosts"][0]["leaving"])
        self.assertTrue(state["hosts"][0]["inert"])
        self.assertFalse(state["list"])
        self._wait(page, "s.dockFocused")
        self._wait(page, "s.hosts.length === 0 && s.command.opacity === 1 && s.plates.length === 0")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band",
    )
    def test_no_stage_ancestor_scrolls_horizontally_full(self):
        """The command region slides past the stage's right edge, yet in no
        frame of entering or leaving dialogue or combat does the stage, an
        ancestor, or the document gain a horizontal scroll offset or a
        scrollable width beyond its own: the stage clips instead of scrolling,
        so focusing the returning dock never drags the stage sideways."""
        page = self._page(None)
        page.evaluate("() => document.getElementById('action-dock').focus()")
        self._wait(page, "s.dockFocused")

        def sampled(commit, settled: str) -> dict:
            page.evaluate(_START_SCROLL_SAMPLER)
            commit()
            self._wait(page, settled)
            # A few frames past the settled state catch a late scroll.
            page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
            return page.evaluate(_STOP_SCROLL_SAMPLER)

        steps = {
            "enter dialogue": sampled(lambda: self._enter_dialogue(page), "s.command.visibility === 'hidden'"),
        }
        # Parked in dialogue, the stage is not a scroll container: a script
        # (or a focus or scrollIntoView) cannot move it either.
        forced = page.evaluate(
            """() => { const stage = document.querySelector('[data-testid="elosern-stage"]');
              stage.scrollLeft = 400; return { left: stage.scrollLeft, width: stage.scrollWidth, client: stage.clientWidth }; }"""
        )
        self.assertEqual(forced["left"], 0)
        self.assertLessEqual(forced["width"], forced["client"])
        open_dialogue_choices(page)
        self._wait(page, "s.list && s.listFocused")
        steps["leave dialogue"] = sampled(
            lambda: self._leave_dialogue(page), "s.dockFocused && s.command.opacity === 1 && s.hosts.length === 0"
        )
        steps["enter combat"] = sampled(
            lambda: self._commit(page, "combat", {"context_actions": _combat_panel()}),
            "s.veil.opacity === 1 && s.dockAnimations.length === 0",
        )
        steps["leave combat"] = sampled(
            lambda: self._commit(page, "exploration", _exploration_panels()),
            "s.veil.opacity === 0 && s.dockAnimations.length === 0",
        )
        for step, worst in steps.items():
            with self.subTest(step=step):
                self.assertGreater(worst["frames"], 1)
                self.assertEqual(worst["scrollLeft"], 0, worst)
                self.assertLessEqual(worst["overflow"], 0, worst)
        self.assertTrue(self._read(page)["dockFocused"])
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode",
    )
    def test_combat_enter_and_leave_full(self):
        """Entering combat flashes once (120ms), fades the veil in, and flips
        the panel in; leaving plays no flash and flips it back; a second entry
        flashes again. Every layer is decorative and pointer-transparent."""
        page = self._page(None)
        combat = {"context_actions": _combat_panel()}
        state = self._commit(page, "combat", combat)
        self.assertEqual(state["modeChange"], "exploration-combat")
        self.assertIn({"name": "elosern-stage-flash", "duration": 120}, state["flash"]["animations"])
        self.assertEqual(state["flash"]["hidden"], "true")
        self.assertEqual(state["flash"]["pointer"], "none")
        self.assertEqual(state["veil"]["hidden"], "true")
        self.assertEqual(state["veil"]["pointer"], "none")
        self.assertEqual(state["veil"]["duration"], "0.35s")
        self.assertLess(state["veil"]["opacity"], 1)
        self.assertIn("elosern-panel-flip-in", [a["name"] for a in state["dockAnimations"]])
        # Nothing decorative intercepts a click on the stage.
        hit = page.evaluate(
            "() => { const el = document.elementFromPoint(960, 400); return el ? (el.dataset.testid || el.className) : null; }"
        )
        self.assertNotIn(hit, ("stage-flash", "stage-combat-veil"))
        self._wait(page, "s.veil.opacity === 1 && s.flash.animations.length === 0")

        state = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(state["modeChange"], "combat-exploration")
        self.assertEqual(state["flash"]["animations"], [])
        self.assertIn("elosern-panel-flip-out", [a["name"] for a in state["dockAnimations"]])
        self._wait(page, "s.veil.opacity === 0")

        state = self._commit(page, "combat", combat)
        self.assertIn({"name": "elosern-stage-flash", "duration": 120}, state["flash"]["animations"])
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
    )
    def test_choices_stagger_full(self):
        """The rows stagger in 40ms apart; the list holds focus from its first
        frame and a digit activates at once."""
        page = self._page(None)
        self._enter_dialogue(page)
        open_dialogue_choices(page)
        self._wait(page, "s.list && s.rows.length === 7")
        state = self._read(page)
        self.assertEqual(
            [row["delay"] for row in state["rows"]],
            ["0s"] + [f"{0.04 * n:.2f}".rstrip("0") + "s" for n in range(1, len(state["rows"]))],
        )
        self.assertEqual({row["name"] for row in state["rows"]}, {"elosern-choice-row-in"})
        self._wait(page, "s.listFocused")
        page.keyboard.press("2")
        self.assertIsNotNone(page.evaluate("() => window.__elosernBridge.store.view.dispatch.inFlight"))
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
    )
    def test_reload_in_combat_plays_nothing(self):
        """A reconnect into combat or dialogue renders every final state: no
        mode change, no flash, the veil at rest, the host and the list at rest,
        and the collapsed region hidden in the resync's frame."""
        page = self._page(None)
        combat = {"context_actions": _combat_panel()}
        self._commit(page, "combat", combat)
        self._wait(page, "s.veil.opacity === 1 && s.flash.animations.length === 0")
        state = self._commit(page, "combat", combat, reset=True)
        self.assertIsNone(state["modeChange"])
        self.assertEqual(state["flash"]["animations"], [])
        self.assertEqual(state["veil"]["opacity"], 1)
        self.assertEqual(state["dockAnimations"], [])

        self._commit(page, "exploration", _exploration_panels())
        self._enter_dialogue(page)
        open_dialogue_choices(page)
        self._wait(page, "s.list && s.command.visibility === 'hidden'")
        state = self._commit(page, "dialogue", {**_exploration_panels(), "dialogue": _dialogue_panel()}, reset=True)
        self.assertIsNone(state["modeChange"])
        self.assertEqual(state["command"]["visibility"], "hidden")
        self.assertEqual(len(state["hosts"]), 1)
        self.assertFalse(state["hosts"][0]["entering"])
        self.assertEqual([p["entering"] for p in state["plates"]], [False])
        # The list, whenever it shows after the resync, shows at rest.
        self._wait(page, "s.list")
        self.assertEqual({row["name"] for row in self._read(page)["rows"]}, {"none"})
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
    )
    def test_mode_transitions_reduced(self):
        """Reduced keeps only short fades: every duration is within 150ms,
        nothing moves, the flash is invisible, and the rows appear together."""
        page = self._page("reduced")
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "reduced")
        state = self._enter_dialogue(page)
        self.assertEqual(state["command"]["duration"].split(", ")[0], "0.15s")
        for duration in state["command"]["duration"].split(", "):
            self.assertLessEqual(float(duration.rstrip("s")), 0.15)
        self.assertTrue(_identity(state["command"]["transform"]))
        self.assertTrue(state["hosts"][0]["entering"])
        for duration in state["hosts"][0]["duration"].split(", "):
            self.assertLessEqual(float(duration.rstrip("s")), 0.15)
        self.assertTrue(_identity(state["hosts"][0]["transform"]))
        for duration in state["plates"][0]["duration"].split(", "):
            self.assertLessEqual(float(duration.rstrip("s")), 0.15)
        open_dialogue_choices(page)
        state = self._read(page)
        self.assertEqual({row["delay"] for row in state["rows"]}, {"0s"})

        state = self._leave_dialogue(page)
        self.assertTrue(state["hosts"][0]["leaving"])
        self.assertTrue(_identity(state["hosts"][0]["transform"]))

        state = self._commit(page, "combat", {"context_actions": _combat_panel()})
        self.assertEqual(state["flashPeak"], "0")
        self.assertTrue(all(a["duration"] == 0 for a in state["flash"]["animations"]))
        self.assertEqual(state["flash"]["opacity"], 0)
        self.assertEqual(state["veil"]["duration"], "0.15s")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::mode-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band",
    )
    def test_mode_transitions_off(self):
        """At off every mode change shows its final state in the frame after
        the commit: no leaving copy, the region hidden or shown, the veil at
        its final opacity, the flash invisible, and every row fully shown."""
        page = self._page("off")
        state = self._enter_dialogue(page)
        self.assertEqual(state["command"]["visibility"], "hidden")
        self.assertTrue(state["command"]["inert"])
        self.assertEqual(len(state["hosts"]), 1)
        self.assertFalse(state["hosts"][0]["entering"])
        # The list appears once the line is read, every row fully shown in
        # the frame it renders.
        rows = page.evaluate(
            """async () => {
              const page = document.querySelector('[data-testid="message-page"]');
              page.focus();
              for (let i = 0; i < 20 && !document.querySelector('[data-anchor="choices"] [role="menuitem"]'); i += 1) {
                page.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
                await new Promise((resolve) => requestAnimationFrame(() => resolve()));
              }
              return window.__c11cRead().rows;
            }"""
        )
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["opacity"] == 1 for row in rows))

        state = self._leave_dialogue(page)
        self.assertEqual(state["hosts"], [])
        self.assertEqual(state["plates"], [])
        self.assertEqual(state["command"]["visibility"], "visible")
        self.assertEqual(state["command"]["opacity"], 1)

        state = self._commit(page, "combat", {"context_actions": _combat_panel()})
        self.assertEqual(state["veil"]["opacity"], 1)
        self.assertEqual(state["flash"]["opacity"], 0)
        state = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(state["veil"]["opacity"], 0)
        page.close()
