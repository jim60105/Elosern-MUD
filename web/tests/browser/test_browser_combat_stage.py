"""The combat stage: the foe line-up (webclient-combat-foes-on-stage, C13a)
and the shared-scale formation (webclient-combat-formation).

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
from .test_browser_combat_choreography import _PLAY_ROUND, _SWALLOW_ACTIONS, _beat, _beats_panel
from .test_browser_mode_transitions import _START_SCROLL_SAMPLER, _STOP_SCROLL_SAMPLER

REFERENCE = (1451, 790)
VIEWPORTS = ((1451, 790), (1741, 948), (2560, 1440))
FORMATION_VIEWPORTS = ((1451, 790), (1600, 900))

# The dead-centre gap of webclient-combat-formation: the command card's
# columns are centre ± 132px·S; at rest the 16px·S gutter widens that to
# centre ± 148px·S.
CARD_HALF = 132
GAP_HALF = 148

_FOE_NAMES = (
    "哥布林", "史萊姆", "灰狼妖", "骷髏兵", "蝙蝠", "強盜", "弓手", "術士",
    "劍士", "槍兵", "惡犬", "巨蛛", "石像", "幽靈", "狂戰士",
)
_COMPANION_NAMES = ("蕾娜", "幽", "艾德蒙", "雪莉")


def _foe_state(identity: int, defeated: tuple[int, ...], fled: tuple[int, ...]) -> str:
    if identity in defeated:
        return "defeated"
    return "fled" if identity in fled else "active"


def _foes(
    count: int, defeated: tuple[int, ...] = (), names: tuple[str, ...] = _FOE_NAMES, fled: tuple[int, ...] = ()
) -> list:
    """``count`` foes in presenter order, identities 11.., each with a catalog ref."""
    return [
        _participant(
            11 + i,
            "e%d" % (i + 1),
            names[i],
            "foes",
            _foe_state(11 + i, defeated, fled),
            0 if (11 + i) in defeated else 20 + 10 * (i % 5),
            60,
            str(11 + i),
        )
        for i in range(count)
    ]


def _party_panel(companions: int) -> dict:
    """A committed party v2 panel with ``companions`` slots (no portraits)."""
    return {
        "schema_version": 2,
        "available": True,
        "general_quota": {"used": companions, "limit": 4},
        "slots": [
            {
                "identity": 101 + i,
                "display_name": _COMPANION_NAMES[i],
                "portrait_ref": None,
                "hp_current": 90 + i,
                "hp_maximum": 120,
                "bond_stage": "初識",
                "membership": {"general": True, "temporary_commissions": []},
            }
            for i in range(companions)
        ],
    }


def _combat_panels(
    count: int,
    defeated: tuple[int, ...] = (),
    companions: int = 0,
    names=_FOE_NAMES,
    fled: tuple[int, ...] = (),
    downed: tuple[int, ...] = (),
) -> dict:
    panel = _combat_panel()
    # The player alone from the shared fixture (its knocked-out ally is no
    # drawn figure), then the drawn companions: the session stays within its
    # 16-participant bound at the largest case.
    party = [p for p in panel["participants"] if p["team"] == "party" and p["state"] == "active"]
    party += [
        _participant(
            101 + i,
            "a%d" % (i + 3),
            _COMPANION_NAMES[i],
            "party",
            "knocked_out" if (101 + i) in downed else "active",
            0 if (101 + i) in downed else 90 + i,
            120,
            None,
        )
        for i in range(companions)
    ]
    panel["participants"] = party + _foes(count, defeated, names, fled)
    # The shared skills target the fixture's own foe identities; this stage
    # needs no skill frame.
    panel["skills"] = []
    refs = [p["portrait_ref"] for p in panel["participants"] if p["portrait_ref"] is not None]
    panels = {"context_actions": panel, "art": _art_panel(refs)}
    if companions:
        panels["party"] = _party_panel(companions)
    return panels


def _exploration_panels(companions: int = 0) -> dict:
    panels = {
        "exploration": _exploration_panel([_interact_target(11, "小販")]),
        "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
        "art": _art_panel([]),
    }
    if companions:
        panels["party"] = _party_panel(companions)
    return panels


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
    const stage = q('[data-testid="elosern-stage"]');
    const root = getComputedStyle(q('.elosern-root'));
    const right = q('[data-anchor="actor-right"]');
    const rows = [...right.querySelectorAll(':scope > [data-testid="foe-lineup"]')];
    const map = q('[data-anchor="map"]');
    const placeCard = q('[data-testid="place-card"]');
    // The beat step's resolved distance (the token is a calc() of --ui-scale).
    const probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;visibility:hidden;width:var(--motion-beat-lunge)';
    stage.appendChild(probe);
    const lunge = probe.getBoundingClientRect().width;
    probe.remove();
    return {
      width: innerWidth,
      stage: box(stage),
      scale: Number(getComputedStyle(document.documentElement).getPropertyValue('--ui-scale')) || 1,
      formation: stage.getAttribute('data-formation'),
      header: box(q('.stage-metrics > [data-metric="--header-h"]')).height,
      band: box(q('[data-testid="stage-band"]')),
      vitals: box(q('[data-anchor="vitals"]')),
      mapDisplay: map ? getComputedStyle(map).display : null,
      placeCardShown: !!(placeCard && placeCard.checkVisibility()),
      player: box(q('[data-anchor="actor-left"] [data-controlled="true"] [data-testid="stage-actor"]')),
      party: [...document.querySelectorAll('[data-anchor="actor-left"] [data-testid="companion-figure"]')].map((slot) => ({
        identity: slot.getAttribute('data-identity'),
        controlled: slot.getAttribute('data-controlled') === 'true',
        fallen: slot.getAttribute('data-fallen'),
        rank: slot.getAttribute('data-rank'),
        box: box(slot.querySelector('[data-testid="stage-actor"]')),
      })),
      plates: [...document.querySelectorAll('[data-anchor="plates"] [data-testid="figure-plate"]')]
        .filter((el) => !el.inert)
        .map((el) => ({
          box: box(el),
          identity: el.getAttribute('data-identity'),
          side: el.getAttribute('data-side'),
          form: el.getAttribute('data-form'),
          label: el.getAttribute('aria-label'),
          fallen: el.getAttribute('data-fallen'),
          fallenText: el.querySelector('[data-testid="figure-plate-fallen"]')?.textContent ?? null,
          token: el.querySelector('[data-testid="figure-plate-token"]')?.textContent ?? null,
        })),
      // Descendants in the tab order: the plates and their glyphs are
      // tabindex=-1 stops of the one group (webclient-combat-figure-plates).
      platesLayerFocusable: [...q('[data-anchor="plates"]').querySelectorAll('button, a, input, textarea, select, [tabindex]')]
        .filter((el) => el.tabIndex >= 0).length,
      platesZ: Number(getComputedStyle(q('[data-anchor="plates"]')).zIndex),
      actorsZ: Math.max(...['actor-left', 'actor-right'].map((a) => Number(getComputedStyle(q(`[data-anchor="${a}"]`)).zIndex))),
      captionLeft: root.getPropertyValue('--caption-left').trim(),
      captionRight: root.getPropertyValue('--caption-right').trim(),
      commandLine: box(q('[data-anchor="command-line"]')),
      plate: box(q('.scene-backdrop__plate')),
      lunge,
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
          rank: slot.getAttribute('data-rank'),
          inert: slot.inert,
          leaving: slot.classList.contains('foe-leave-active'),
          box: box(slot.querySelector('[data-testid="stage-actor"]')),
          z: Number(getComputedStyle(slot).zIndex),
          transform: getComputedStyle(slot).transform,
          duration: getComputedStyle(slot).transitionDuration,
          dimmed: slot.querySelector('[data-testid="stage-actor"]').getAttribute('data-speaking') !== 'true',
          fallen: slot.getAttribute('data-fallen'),
          seal: !!slot.querySelector('[data-testid="stage-actor-seal"]'),
          img: !!slot.querySelector('img'),
        })),
      })),
    };
  };
}"""

# Samples every standing figure's height (party and foes, leaving ones
# excluded) in each animation frame while `action` runs, for `frames` frames.
_SAMPLE_HEIGHTS = """async ([frames]) => {
  const heights = () => [...document.querySelectorAll(
      '[data-anchor="actor-left"] [data-testid="stage-actor"], [data-anchor="actor-right"] [data-testid="foe-slot"] [data-testid="stage-actor"]')]
    .filter((el) => !el.closest('.foe-leave-active, .foes-enter-leave-active'))
    .map((el) => el.getBoundingClientRect().height);
  const out = [];
  for (let i = 0; i < frames; i += 1) {
    out.push(heights());
    await new Promise((resolve) => requestAnimationFrame(() => resolve()));
  }
  return out;
}"""

# The farthest frame of every figure's beat step: each figure's beat wrapper
# plays the real lunge keyframes, paused at their peak (45% of the step).
_LUNGE_PEAK = """() => {
  const step = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-beat-step')) || 240;
  const actors = [...document.querySelectorAll(
      '[data-anchor="actor-left"] [data-testid="stage-actor"], [data-anchor="actor-right"] [data-testid="stage-actor"]')];
  const out = [];
  const rest = actors.map((actor) => {
    const r = actor.getBoundingClientRect();
    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
  });
  for (const actor of actors) {
    const beat = actor.querySelector(':scope > .stage-actor__fall > .stage-actor__beat');
    beat.setAttribute('data-beat', 'lunge');
    beat.style.animationDelay = `-${step * 0.45}ms`;
    beat.style.animationPlayState = 'paused';
  }
  actors.forEach((actor, index) => {
    const r = actor.querySelector(':scope > .stage-actor__fall > .stage-actor__beat').getBoundingClientRect();
    out.push({ side: actor.getAttribute('data-side'), left: r.left, right: r.right, rest: rest[index] });
  });
  for (const actor of actors) {
    const beat = actor.querySelector(':scope > .stage-actor__fall > .stage-actor__beat');
    beat.removeAttribute('data-beat');
    beat.style.animationDelay = '';
    beat.style.animationPlayState = '';
  }
  return out;
}"""


def _identity(transform: str) -> bool:
    return transform in ("none", "matrix(1, 0, 0, 1, 0, 0)")


def _intersects(a: dict, b: dict) -> bool:
    return a["left"] < b["right"] and b["left"] < a["right"] and a["top"] < b["bottom"] and b["top"] < a["bottom"]


class CombatStageBrowserTest(BrowserAcceptanceTest):
    """The combat stage: the foe line-up and the shared-scale formation."""

    def _page(self, viewport=REFERENCE, motion_level="off", companions=0):
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
        self._commit(page, "exploration", _exploration_panels(companions))
        wait_for_store_state(page, lambda s: s.get("mode") == "exploration")
        return page

    def _commit(self, page, mode: str, panels: dict, reset: bool = False) -> dict:
        return page.evaluate(_COMMIT_AND_READ, [snapshot_envelope("", 0, panels, mode=mode), reset])

    def _read(self, page) -> dict:
        return page.evaluate("() => window.__c13aRead()")

    def _wait(self, page, predicate_js: str, timeout: int = 15000) -> None:
        page.wait_for_function(f"() => {{ const s = window.__c13aRead(); return {predicate_js}; }}", timeout=timeout)

    def _resize(self, page, viewport) -> None:
        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        page.wait_for_function("([w, h]) => innerWidth === w && innerHeight === h", arg=list(viewport))
        # The formation re-measures in the resize's own frame; one more frame
        # lets the instant re-form paint.
        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")

    def _figures(self, s: dict) -> list:
        """Every standing figure box: the drawn party, then the standing foes."""
        foes = [x["box"] for row in s["rows"] if not row["leaving"] for x in row["slots"] if not x["leaving"]]
        return [x["box"] for x in s["party"]] + foes

    @covers_requirement(
        "webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation",
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
        "webclient-contextual-hud::combat-figures-carry-glance-plates",
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage",
    )
    def test_foes_stand_opposite_the_player(self):
        """One, two, and three foes stand in the formation at the player's
        scale, right of the dead-centre gap and clear of the player; each foe
        carries its plate; the caption plate stays centred between the party's
        innermost figure and the leftmost foe; nothing in the row is
        focusable; the map column is not rendered.

        Migrated by webclient-combat-formation: the depth table's 100/90/78
        heights, the lift and the participant-frame face clearance guarded the
        foes' placement against the player, the centre and the right column;
        the same defects are now detected by the formation's equal heights,
        the gap and the hidden map anchor."""
        page = self._page(REFERENCE)
        page.evaluate("() => document.querySelector('[data-testid=\"command-line-toggle\"]').click()")
        for viewport in VIEWPORTS:
            self._resize(page, viewport)
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
                    self.assertEqual(s["formation"], "true")
                    self.assertEqual(s["mapDisplay"], "none", size)
                    player = s["player"]
                    centre = s["stage"]["left"] + s["stage"]["width"] / 2
                    gap = GAP_HALF * s["scale"]
                    for i, slot in enumerate(slots):
                        b = slot["box"]
                        self.assertAlmostEqual(b["height"], player["height"], delta=1.0, msg=size)
                        self.assertGreaterEqual(b["left"], centre + gap - 1, f"foe {i} enters the gap at {size}")
                        self.assertFalse(_intersects(b, player), f"foe {i} meets the player at {size}")
                        if i:
                            # Later foes step toward the centre, behind the first.
                            self.assertLess(b["left"], slots[i - 1]["box"]["left"], size)
                            self.assertLess(slot["z"], slots[i - 1]["z"], size)
                    self.assertLessEqual(player["right"], centre - gap + 1, size)
                    # Every foe carries its plate; the controlled player none.
                    self.assertEqual([p["identity"] for p in s["plates"]], [str(11 + i) for i in range(count)])
                    # The caption plate stands between the party and the foes.
                    plate = s["plate"]
                    leftmost = min(x["box"]["left"] for x in slots)
                    self.assertIsNotNone(plate)
                    self.assertGreaterEqual(plate["left"], player["right"], size)
                    self.assertLessEqual(plate["right"], leftmost, f"the caption meets the foes at {size}")
                    self.assertAlmostEqual(
                        (plate["left"] + plate["right"]) / 2, (player["right"] + leftmost) / 2, delta=1.5, msg=size
                    )
        # Shrinking the window in combat re-seats the caption's foe edge at
        # once (no held room from the wider stage).
        self._resize(page, REFERENCE)
        s = self._read(page)
        leftmost = min(x["box"]["left"] for x in s["rows"][0]["slots"])
        self.assertAlmostEqual(
            float(s["captionRight"].rstrip("px")), s["stage"]["width"] - leftmost + 16 * s["scale"], delta=1.0
        )
        page.close()

    @covers_requirement("webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation")
    def test_every_active_foe_stands(self):
        """Five active foes all stand, each with its plate; no roster lists them.

        Migrated by webclient-combat-formation: this method guarded the three-foe
        cap and the frame's complete list; every active foe now stands and its
        plate carries what the frame listed."""
        page = self._page(REFERENCE)
        self._commit(page, "combat", _combat_panels(5))
        self._wait(page, "s.rows.length === 1 && s.plates.length === 5")
        s = self._read(page)
        self.assertEqual([x["ref"] for x in s["rows"][0]["slots"]], ["11", "12", "13", "14", "15"])
        for name, plate in zip(_FOE_NAMES, s["plates"]):
            self.assertTrue(plate["label"].startswith(name + " e"), plate["label"])
            self.assertIn("，敵方，生命 ", plate["label"])
        self.assertEqual(page.locator('[data-testid="participant-frame"]').count(), 0)
        page.close()

    @covers_requirement("webclient-contextual-hud::combat-figures-carry-glance-plates")
    @covers_requirement(
        "webclient-contextual-hud::figure-plates-show-conditions-at-a-glance-and-their-details-on-demand"
    )
    def test_figure_plates_show_conditions_and_alarm(self):
        """A poisoned foe's plate shows its glyph, whose tooltip opens on demand
        only and closes on every exit tried here; a companion at 20% carries
        危險 and the critical hue; the plates are one tab stop after the dock
        (webclient-combat-figure-plates)."""
        page = self._page(REFERENCE, companions=1)
        panels = _combat_panels(2, companions=1)
        for p in panels["context_actions"]["participants"]:
            if p["identity"] == 11:
                p["conditions"] = [{"code": "poison", "label": "中毒", "severity": "harmful"}]
            if p["identity"] == 101:
                p["hp_current"] = 24  # of 120: 20%
        self._commit(page, "combat", panels)
        self._wait(page, "s.plates.length === 3")
        plates = page.locator('[data-anchor="plates"] [data-testid="figure-plate"]')
        foe = page.locator('[data-anchor="plates"] [data-testid="figure-plate"][data-identity="11"]')
        ally = page.locator('[data-anchor="plates"] [data-testid="figure-plate"][data-identity="101"]')
        glyph = foe.locator('[data-testid="figure-plate__condition--poison"]')
        tooltip = page.locator('[data-testid="figure-plate__condition-tooltip"]')

        # The glyph stands inside its plate's slot, and nothing is open at rest.
        self.assertEqual(glyph.inner_text().strip(), "▼")
        self.assertEqual(glyph.get_attribute("aria-label"), "中毒")
        plate_box, glyph_box = foe.bounding_box(), glyph.bounding_box()
        self.assertGreaterEqual(glyph_box["x"], plate_box["x"] - 0.5)
        self.assertLessEqual(glyph_box["x"] + glyph_box["width"], plate_box["x"] + plate_box["width"] + 0.5)
        self.assertGreaterEqual(glyph_box["y"], plate_box["y"] - 0.5)
        self.assertLessEqual(glyph_box["y"] + glyph_box["height"], plate_box["y"] + plate_box["height"] + 0.5)
        self.assertNotIn("中毒", foe.inner_text())
        self.assertEqual(page.locator('[role="tooltip"]').count(), 0, "no tooltip at rest")

        # Hover opens it inside the viewport; leaving closes it.
        glyph.hover()
        tooltip.wait_for(state="visible", timeout=5000)
        self.assertEqual(tooltip.get_attribute("role"), "tooltip")
        self.assertIn("中毒", tooltip.inner_text())
        self.assertEqual(glyph.get_attribute("aria-describedby"), tooltip.get_attribute("id"))
        tip_box = tooltip.bounding_box()
        self.assertGreaterEqual(tip_box["x"], 4 - 0.5)
        self.assertLessEqual(tip_box["x"] + tip_box["width"], REFERENCE[0] - 4 + 0.5)
        self.assertGreaterEqual(tip_box["y"], 0)
        page.mouse.move(5, REFERENCE[1] // 2)
        tooltip.wait_for(state="detached", timeout=5000)
        # Hover again, then a round starts playing: it closes.
        glyph.hover()
        tooltip.wait_for(state="visible", timeout=5000)
        page.evaluate("() => { window.__elosernBridge.store.view.dispatch.beatLocked = true; }")
        tooltip.wait_for(state="detached", timeout=5000)
        page.evaluate("() => { window.__elosernBridge.store.view.dispatch.beatLocked = false; }")
        page.mouse.move(5, REFERENCE[1] // 2)

        # The companion at 20% carries 危險 and the critical hue.
        self.assertEqual(ally.get_attribute("data-low-hp"), "true")
        self.assertEqual(ally.locator('[data-testid="figure-plate-danger"]').inner_text(), "危險")
        crit = page.evaluate(
            "() => { const p = document.createElement('span'); p.style.color = 'var(--crit)';"
            " document.body.appendChild(p); const c = getComputedStyle(p).color; p.remove(); return c; }"
        )
        self.assertEqual(ally.locator(".figure-plate__current").evaluate("el => getComputedStyle(el).color"), crit)
        self.assertIn("，危險", ally.get_attribute("aria-label"))
        self.assertNotEqual(
            foe.locator(".figure-plate__current").evaluate("el => getComputedStyle(el).color"), crit
        )

        # One tab stop after the dock: Tab walks out of the dock and lands on
        # the leftmost plate, crossing no other stop inside the layer.
        page.evaluate("() => document.getElementById('action-dock').focus()")
        landed = None
        for _ in range(6):
            page.keyboard.press("Tab")
            landed = page.evaluate(
                "() => { const a = document.activeElement;"
                " return { inPlates: !!a.closest('[data-anchor=\"plates\"]'),"
                " inDock: !!a.closest('#action-dock'), identity: a.getAttribute('data-identity') }; }"
            )
            if not landed["inDock"]:
                break
        self.assertTrue(landed["inPlates"], f"Tab from the dock does not reach the plates group: {landed}")
        order = page.evaluate(
            "() => [...document.querySelectorAll('[data-anchor=\"plates\"] [data-testid=\"figure-plate\"]')]"
            ".sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left)"
            ".map((el) => el.getAttribute('data-identity'))"
        )
        self.assertEqual(landed["identity"], order[0])
        self.assertEqual(page.locator('[data-anchor="plates"]').get_attribute("tabindex"), "-1")
        page.keyboard.press("ArrowRight")
        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-identity')"), order[1])
        # Focus reaches the foe's glyph: its tooltip opens; Escape closes it,
        # and the next Escape returns to the dock.
        while page.evaluate("() => document.activeElement.getAttribute('data-identity')") != "11":
            page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowDown")
        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-code')"), "poison")
        tooltip.wait_for(state="visible", timeout=5000)
        page.keyboard.press("Escape")
        tooltip.wait_for(state="detached", timeout=5000)
        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-code')"), "poison")
        page.keyboard.press("Escape")
        self.assertEqual(page.evaluate("() => document.activeElement.id"), "action-dock")
        self.assertEqual(page.locator('[data-anchor="plates"]').get_attribute("tabindex"), "0")
        self.assertEqual(plates.count(), 3)
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation",
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode",
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
    )
    def test_combat_formation_shares_one_scale_and_keeps_the_centre_clear(self):
        """webclient-combat-formation task 3.1, at 1451x790 and 1600x900.

        For parties of 1, 3 and 5 figures against 1, 4, 8 and 16 − party foes:
        every figure box on both sides has one height, nothing stands in the
        dead-centre gap at rest or reaches into the card's columns at the beat
        step's peak, plates are pairwise disjoint and clear of the vitals dock
        and the top band, the place card and the map anchor are not rendered,
        leaving combat restores the exploration boxes, entering at `full`
        keeps one height in every sampled frame, and three same-named foes
        show their tokens; no head (front rank or back) is ever covered by a
        plate or by a figure in front of it, and no figure paints over a
        plate."""
        for viewport in FORMATION_VIEWPORTS:
            for companions in (0, 2, 4):
                party = 1 + companions
                page = self._page(viewport, companions=companions)
                explore = self._read(page)
                before = [x["box"] for x in explore["party"]]
                self.assertEqual(len(before), party)
                for foes in (1, 4, 8, 16 - party):
                    size = "%dx%d party %d foes %d" % (viewport[0], viewport[1], party, foes)
                    with self.subTest(case=size):
                        self._commit(page, "combat", _combat_panels(foes, companions=companions))
                        self._wait(page, f"s.rows.length === 1 && s.rows[0].slots.length === {foes} && s.party.length === {party}")
                        s = self._read(page)
                        figures = self._figures(s)
                        self.assertEqual(len(figures), party + foes, size)
                        heights = [b["height"] for b in figures]
                        self.assertLessEqual(max(heights) - min(heights), 1.0, f"two scales at {size}: {heights}")
                        S = s["scale"]
                        centre = s["stage"]["left"] + s["stage"]["width"] / 2
                        gap = {"left": centre - GAP_HALF * S, "right": centre + GAP_HALF * S}
                        for b in figures + [p["box"] for p in s["plates"]]:
                            self.assertTrue(
                                b["right"] <= gap["left"] + 1 or b["left"] >= gap["right"] - 1,
                                f"a box enters the dead-centre gap at {size}: {b}",
                            )
                        # One plate per drawn figure but the controlled one.
                        self.assertEqual(len(s["plates"]), party - 1 + foes, size)
                        top_band = s["stage"]["top"] + s["header"]
                        for a_index, a in enumerate(s["plates"]):
                            self.assertGreaterEqual(a["box"]["top"], top_band - 1, f"a plate enters the top band at {size}")
                            if s["vitals"] and s["vitals"]["width"] > 0:
                                self.assertFalse(_intersects(a["box"], s["vitals"]), f"a plate meets the vitals dock at {size}")
                            for b in s["plates"][a_index + 1:]:
                                self.assertFalse(_intersects(a["box"], b["box"]), f"two plates meet at {size}")
                        # No head is ever covered (webclient-combat-formation):
                        # a head is the central 30% of a figure's width and the
                        # top 22% of its height. No plate covers any head, front
                        # rank or back; no front-rank figure reaches a back-rank
                        # head; the heads of one rank stay apart. Lower bodies
                        # may be covered. The plates layer paints above every
                        # figure, so no figure covers a plate.
                        standing = [(x["rank"], x["box"]) for x in s["party"]] + [
                            (x["rank"], x["box"]) for row in s["rows"] for x in row["slots"] if not x["leaving"]
                        ]

                        def head(b):
                            return {
                                "left": b["left"] + 0.35 * b["width"], "right": b["left"] + 0.65 * b["width"],
                                "top": b["top"], "bottom": b["top"] + 0.22 * b["height"],
                            }

                        for rank, _ in standing:
                            self.assertIn(rank, ("0", "1"), f"a figure without a formation rank at {size}")
                        for rank, b in standing:
                            h = head(b)
                            for p in s["plates"]:
                                self.assertFalse(_intersects(p["box"], h), f"a plate covers a rank-{rank} head at {size}")
                            for other_rank, o in standing:
                                if o is b:
                                    continue
                                if (other_rank or "0") < (rank or "0"):
                                    self.assertFalse(_intersects(o, h), f"a front figure covers a back head at {size}")
                                elif other_rank == rank:
                                    self.assertFalse(_intersects(head(o), h), f"two heads of one rank overlap at {size}")
                        self.assertGreater(s["platesZ"], s["actorsZ"], "the plates layer must paint above the figures")
                        self.assertEqual(s["mapDisplay"], "none", size)
                        self.assertFalse(s["placeCardShown"], size)
                        # The layer itself is the one tab stop (webclient-combat-figure-plates).
                        self.assertEqual(s["platesLayerFocusable"], 0)
                        # The beat step's farthest frame stays out of the
                        # card's columns.
                        card = {"left": centre - CARD_HALF * S, "right": centre + CARD_HALF * S}
                        self.assertAlmostEqual(s["lunge"], 12 * S, delta=0.5)
                        peaks = page.evaluate(_LUNGE_PEAK)
                        for peak in peaks:
                            self.assertTrue(
                                peak["right"] <= card["left"] + 1 or peak["left"] >= card["right"] - 1,
                                f"a stepping figure enters the card's columns at {size}: {peak}",
                            )
                            # At the step's peak its head reaches no other head
                            # of its rank (same side, same top) at rest.
                            shift = peak["left"] - peak["rest"]["left"]
                            moved = head({**peak["rest"], "left": peak["rest"]["left"] + shift})
                            for other in peaks:
                                if other is peak or other["side"] != peak["side"]:
                                    continue
                                if abs(other["rest"]["top"] - peak["rest"]["top"]) > 1:
                                    continue
                                self.assertFalse(
                                    _intersects(moved, head(other["rest"])),
                                    f"a stepping figure leans its head over a neighbour's at {size}",
                                )
                # Leaving combat restores the exploration boxes.
                s = self._commit(page, "exploration", _exploration_panels(companions))
                self._wait(page, "s.rows.length === 0")
                after = [x["box"] for x in self._read(page)["party"]]
                for a, b in zip(before, after):
                    for key in ("left", "top", "width", "height"):
                        self.assertAlmostEqual(a[key], b[key], delta=1.0, msg=f"exploration box {key} at {viewport}")
                # Entering at full: one height in every sampled frame.
                page.evaluate("() => window.__elosernBridge.store.setMotionLevel('full')")
                page.evaluate(
                    "(env) => { const store = window.__elosernBridge.store; const view = store.view;"
                    " env.presentation_epoch = view.epoch; env.revision = view.revision + 1;"
                    " store.receive(view.generation, 'ui_snapshot', [env], {}); }",
                    snapshot_envelope("", 0, _combat_panels(4, companions=companions), mode="combat"),
                )
                samples = page.evaluate(_SAMPLE_HEIGHTS, [40])
                for frame in samples:
                    self.assertLessEqual(max(frame) - min(frame), 1.0, f"two heights in one entry frame at {viewport}: {frame}")
                self.assertGreater(len({round(frame[0]) for frame in samples}), 2, "the entry glided over several frames")
                page.close()
        # Three same-named foes show their session tokens; a fourth does not.
        page = self._page(REFERENCE)
        names = ("哥布林", "哥布林", "哥布林", "狼")
        s = self._commit(page, "combat", _combat_panels(4, names=names))
        self._wait(page, "s.plates.length === 4")
        s = self._read(page)
        self.assertEqual([p["token"] for p in s["plates"]], ["e1", "e2", "e3", None])
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation",
        "webclient-contextual-hud::combat-figures-carry-glance-plates",
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
    )
    def test_fallen_figures_keep_their_slot_and_read_as_fallen(self):
        """webclient-combat-defeated-foes task 2.1: with three foes and a
        knocked-out companion at `full`, a playing round defeats the middle
        foe. It collapses in its slot on its defeat beat (its untransformed box
        unchanged ±1px, the formation's scale unchanged), carries the seal and
        a 已擊破 plate; the companion kneels with a 倒地 plate; at `reduced`
        the fall wrapper's pose takes no transition time."""
        page = self._page(REFERENCE, motion_level=None, companions=1)
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "full")
        page.evaluate(_SWALLOW_ACTIONS)
        self._commit(page, "combat", _combat_panels(3, companions=1, downed=(101,)))
        self._wait(
            page, "s.rows.length === 1 && !s.rows[0].entering && s.rows[0].opacity === 1 && s.plates.length === 4"
        )
        wait_for_store_state(page, lambda st: st["dispatch"]["inFlight"] is None and not st["dispatch"]["beatLocked"])
        before = self._read(page)
        heights = {round(box["height"]) for box in self._figures(before)}
        self.assertEqual(len(heights), 1, heights)
        self.assertEqual([x["fallen"] for x in before["rows"][0]["slots"]], [None, None, None])
        companion = next(x for x in before["party"] if x["identity"] == "101")
        self.assertEqual(companion["fallen"], "down")
        ally_plate = next(p for p in before["plates"] if p["identity"] == "101")
        self.assertEqual(ally_plate["fallen"], "down")
        self.assertEqual(ally_plate["fallenText"], "▼倒地")
        self.assertTrue(ally_plate["label"].endswith("倒地"), ally_plate["label"])

        # The round: a hit, then the defeat of foe 12. The completing
        # publication already commits it defeated; it falls on its own beat.
        lines = ["勇者擊中了史萊姆，造成 30 點傷害。", "史萊姆倒下了。"]
        panels = {
            **_combat_panels(3, defeated=(12,), companions=1, downed=(101,)),
            "combat_beats": _beats_panel(
                "s-9/7",
                [
                    _beat(0, 0, "damage", "1", "12", 30, 0, lines[0]),
                    _beat(1, 0, "target_defeated", "1", "12", text=lines[1]),
                ],
            ),
        }
        page.evaluate(
            _PLAY_ROUND,
            [snapshot_envelope("", 0, panels, mode="combat"), "ui_update", [*lines, "行動完成，繼續戰鬥。"]],
        )
        self.assertIsNone(self._read(page)["rows"][0]["slots"][1]["fallen"], "it stands until its beat")
        # On its beat the collapse eases over the defeat token on the exit curve.
        fall = '[data-testid="foe-slot"][data-portrait-ref="12"] [data-testid="stage-actor-fall"]'
        page.wait_for_function(
            "(sel) => document.querySelector(sel)?.getAttribute('data-fallen') === 'defeated'",
            arg=fall,
            timeout=15000,
            polling="raf",
        )
        timing = page.evaluate(
            "(sel) => { const cs = getComputedStyle(document.querySelector(sel));"
            " return { property: cs.transitionProperty, duration: cs.transitionDuration,"
            " easing: cs.transitionTimingFunction }; }",
            fall,
        )
        self.assertEqual(timing["property"], "transform, filter, opacity")
        self.assertEqual(timing["duration"], "0.35s, 0.35s, 0.35s")
        self.assertIn("cubic-bezier(0.4, 0, 1, 1)", timing["easing"])
        wait_for_store_state(page, lambda st: (st.get("beatPlayback") or {}).get("phase") == "done")
        page.wait_for_function(
            "(sel) => getComputedStyle(document.querySelector(sel)).opacity === '0.8'", arg=fall, timeout=5000
        )

        after = self._read(page)
        slots = after["rows"][0]["slots"]
        self.assertEqual([x["ref"] for x in slots], ["11", "12", "13"])
        self.assertEqual([x["fallen"] for x in slots], [None, "defeated", None])
        self.assertTrue(slots[1]["seal"])
        self.assertFalse(slots[0]["seal"] or slots[2]["seal"])
        for was, now in zip(before["rows"][0]["slots"], slots):
            for edge in ("left", "top", "width", "height"):
                self.assertAlmostEqual(was["box"][edge], now["box"][edge], delta=1, msg=edge)
        self.assertEqual({round(box["height"]) for box in self._figures(after)}, heights)
        # The collapsed figure stays inside its slot, its feet on the floor.
        posed = page.evaluate(
            "(sel) => { const r = document.querySelector(sel).getBoundingClientRect();"
            " return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; }",
            fall,
        )
        slot_box = slots[1]["box"]
        self.assertAlmostEqual(posed["bottom"], slot_box["bottom"], delta=1)
        self.assertAlmostEqual(posed["top"], slot_box["top"] + 0.2 * slot_box["height"], delta=1)
        self.assertGreaterEqual(posed["left"], slot_box["left"] - 1)
        self.assertLessEqual(posed["right"], slot_box["right"] + 1)
        foe_plate = next(p for p in after["plates"] if p["identity"] == "12")
        self.assertEqual(foe_plate["fallen"], "defeated")
        self.assertEqual(foe_plate["fallenText"], "✕已擊破")
        self.assertTrue(foe_plate["label"].endswith("已擊破"), foe_plate["label"])
        self.assertEqual(next(x for x in after["party"] if x["identity"] == "101")["fallen"], "down")

        # Reduced: the pose takes no time; only the tone fades, within 150ms.
        page.evaluate("() => window.__elosernBridge.store.setMotionLevel('reduced')")
        page.wait_for_function("() => document.documentElement.dataset.motion === 'reduced'")
        reduced = page.evaluate("(sel) => getComputedStyle(document.querySelector(sel)).transitionDuration", fall)
        self.assertEqual(reduced, "0s, 0.15s, 0.15s")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_foes_enter_and_leave_full(self):
        """A live entry fades the row in over 350ms while its foes slide in; a
        flee leaves an inert slot while the other steps forward; leaving
        combat fades an inert row; no stage ancestor ever scrolls sideways.

        Migrated by webclient-combat-defeated-foes: a defeated foe now keeps its
        slot, so the leaving foe flees."""
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
        two_foe_edge = self._read(page)["captionRight"]
        self.assertNotEqual(two_foe_edge, "")

        s = self._commit(page, "combat", _combat_panels(2, fled=(11,)))
        slots = s["rows"][0]["slots"]
        leaving = [x for x in slots if x["leaving"]]
        self.assertEqual(len(leaving), 1)
        self.assertEqual(leaving[0]["ref"], "11")
        self.assertTrue(leaving[0]["inert"])
        # The caption keeps the two-foe room until the fled foe has faded.
        self.assertEqual(s["captionRight"], two_foe_edge)
        self._wait(page, "s.rows[0].slots.length === 1")
        self._wait(page, f"s.captionRight !== '{two_foe_edge}'")
        one_foe_edge = self._read(page)["captionRight"]

        s = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(len(s["rows"]), 1)
        self.assertTrue(s["rows"][0]["leaving"])
        self.assertTrue(s["rows"][0]["inert"])
        # The row keeps its room while it fades; releasing it is the fade's end.
        self.assertEqual(s["captionRight"], one_foe_edge)
        self._wait(page, "s.rows.length === 0")
        # The row's room is released once it has faded.
        self._wait(page, "s.captionRight === ''")
        worst = page.evaluate(_STOP_SCROLL_SAMPLER)
        self.assertGreater(worst["frames"], 1)
        self.assertEqual(worst["scrollLeft"], 0, worst)
        self.assertLessEqual(worst["overflow"], 0, worst)
        page.close()

    @covers_requirement("webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation")
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

    @covers_requirement("webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation")
    def test_foes_reduced_only_fade(self):
        """At reduced the row fades within 150ms and nothing moves (the leaving
        foe flees: a defeated one keeps its slot, webclient-combat-defeated-foes)."""
        page = self._page(REFERENCE, motion_level="reduced")
        s = self._commit(page, "combat", _combat_panels(2))
        row = s["rows"][0]
        self.assertTrue(row["entering"])
        for duration in row["duration"].split(", "):
            self.assertLessEqual(float(duration.rstrip("s")), 0.15)
        self.assertTrue(all(_identity(x["transform"]) for x in row["slots"]))
        self._wait(page, "s.rows.length === 1 && !s.rows[0].entering")
        s = self._commit(page, "combat", _combat_panels(2, fled=(11,)))
        for slot in s["rows"][0]["slots"]:
            for duration in slot["duration"].split(", "):
                self.assertLessEqual(float(duration.rstrip("s")), 0.15)
            self.assertTrue(_identity(slot["transform"]))
        self._wait(page, "s.rows[0].slots.length === 1")
        s = self._commit(page, "exploration", _exploration_panels())
        self.assertTrue(s["rows"][0]["leaving"])
        self._wait(page, "s.rows.length === 0 && s.captionRight === ''")
        page.close()

    @covers_requirement("webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation")
    def test_foes_off_is_instant(self):
        """At off the row and its foes are present or absent in the commit's
        frame: a fled foe is gone and a defeated one lies fallen in its slot at
        once (webclient-combat-defeated-foes)."""
        page = self._page(REFERENCE)
        s = self._commit(page, "combat", _combat_panels(2))
        self.assertEqual(len(s["rows"]), 1)
        self.assertFalse(s["rows"][0]["entering"])
        self.assertEqual(s["rows"][0]["opacity"], 1)
        s = self._commit(page, "combat", _combat_panels(2, fled=(11,)))
        self.assertEqual([x["ref"] for x in s["rows"][0]["slots"]], ["12"])
        s = self._commit(page, "combat", _combat_panels(2, defeated=(12,)))
        self.assertEqual([x["ref"] for x in s["rows"][0]["slots"]], ["11", "12"])
        self.assertEqual([x["fallen"] for x in s["rows"][0]["slots"]], [None, "defeated"])
        self.assertTrue(s["rows"][0]["slots"][1]["seal"])
        s = self._commit(page, "exploration", _exploration_panels())
        self.assertEqual(s["rows"], [])
        page.close()
