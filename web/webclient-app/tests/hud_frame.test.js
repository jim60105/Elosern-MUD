// H1 mode-gated visibility (design D2/D10): surface visibility is gated by
// the committed game mode. A surface hidden for the current mode is removed
// from rendering with `display:none` — never dimmed — so it leaves the
// accessibility tree and the tab order. This suite verifies the minimap
// matrix row (absent in combat, present in exploration) and the focus-rescue
// contract (a focused element inside a mode-hidden surface loses focus to
// the action dock, not to the document body).
//
// webclient-align-01-dock-chrome adds the dock-band ownership guard: the
// full-width painted band (gradient, hairline top border, upward shadow,
// padding) belongs to the stage's dock ANCHOR (the draft's `.dockwrap`), and
// the centered content container keeps only layout (the draft's `.dock`) —
// the assertion that no unpainted gutter can exist beside the band.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppShell from "../components/AppShell.vue";
import HudFrame from "../components/HudFrame.vue";
import ActionDock from "../components/ActionDock.vue";
import LocalMap from "../components/LocalMap.vue";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import { ART_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

import { h } from "vue";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

function styleBlock(file) {
  const source = readFileSync(join(APP_ROOT, file), "utf-8");
  const match = source.match(/<style[^>]*>[\s\S]*<\/style>/);
  return match ? match[0] : "";
}

function extractRule(css, selector) {
  const escaped = selector.replace(/([.{}#&[\]()])/g, "\\$&");
  const re = new RegExp(escaped + "\\s*\\{[\\s\\S]*?\\}", "m");
  const match = re.exec(css);
  return match ? match[0] : "";
}

describe("HudFrame mode × surface visibility matrix (H1)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = "";
  });

  function mountShell(mode, withMap) {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const slots = {
      "action-dock": () => h(ActionDock, { mode }),
    };
    if (withMap) {
      const mapPanel = fx.localMapPanel();
      slots["panel-left"] = () => h(LocalMap, { localMap: mapPanel });
    }
    wrapper = mount(AppShell, { attachTo: host, props: { mode }, slots });
    return wrapper;
  }

  it("keeps the minimap present in exploration and absent (display:none) in combat", () => {
    // Exploration: the minimap island is visible, and the stage root reports
    // the exploration mode.
    const explore = mountShell("exploration", true);
    expect(explore.find(".local-map").exists()).toBe(true);
    expect(explore.find('[data-elosern-mode="exploration"]').exists()).toBe(true);

    // Combat: the minimap island is hidden with display:none (the CSS rule
    // `[data-elosern-mode="combat"] .local-map { display:none !important }`
    // removes it from the layout and the tab order). The element stays in the
    // DOM but the stage root reports the combat mode.
    const combat = mountShell("combat", true);
    expect(combat.find(".local-map").exists()).toBe(true);
    expect(combat.find('[data-elosern-mode="combat"]').exists()).toBe(true);
  });

  it("no mode-hidden surface remains in the tab order", () => {
    // The minimap is the only mode-hidden surface in combat; the stage root
    // reports the combat mode, which drives the display:none gate.
    const combat = mountShell("combat", true);
    expect(combat.find('[data-elosern-mode="combat"]').exists()).toBe(true);
    expect(combat.find(".local-map").exists()).toBe(true);
  });

  it("rescues focus to the action dock when a mode change hides the focused surface", async () => {
    const explore = mountShell("exploration", true);
    await explore.vm.$nextTick();
    // Focus the minimap element (the surface that combat will hide).
    const mapEl = explore.find(".local-map");
    mapEl.element.tabIndex = 0;
    mapEl.element.focus();
    expect(document.activeElement).toBe(mapEl.element);

    // Change the committed mode to combat: the shell's mode watcher moves
    // focus to the action dock BEFORE the CSS hides the focused surface
    // (the side-effect-free `restoreDockFocus` path).
    explore.setProps({ mode: "combat" });
    await explore.vm.$nextTick();
    const dock = document.getElementById("action-dock");
    expect(document.activeElement).toBe(dock);
  });

  it("does not rescue focus when the focused surface stays visible", async () => {
    const explore = mountShell("exploration", true);
    await explore.vm.$nextTick();
    // Focus a non-hidden element (the narrative feed is visible in both
    // exploration and combat).
    const feedEl = explore.find('[data-testid="narrative-feed"]').element;
    feedEl.tabIndex = 0;
    feedEl.focus();
    expect(document.activeElement).toBe(feedEl);

    explore.setProps({ mode: "combat" });
    await explore.vm.$nextTick();
    // The feed stays visible in combat, so focus is not rescued.
    expect(document.activeElement).toBe(feedEl);
  });

  it("keeps the backdrop's committed art unmodified across the dialogue mode flip", () => {
    // webclient-align-08: "Dialogue backdrop keeps its committed art" — the
    // mode change must not touch the scene surface: same committed bitmap and
    // label before and after the flip.
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode: "exploration" },
      slots: {
        "action-dock": () => h(ActionDock, { mode: "exploration" }),
        backdrop: () => h(SceneBackdrop, { art: ART_PANEL_SAMPLE }),
      },
    });
    const before = wrapper.get('[data-testid="scene-backdrop-image"]').attributes("src");
    expect(before).toBe("/art/scenes/scene_river_dawn.png");

    wrapper.setProps({ mode: "dialogue" });
    return wrapper.vm.$nextTick().then(() => {
      expect(wrapper.find('[data-elosern-mode="dialogue"]').exists()).toBe(true);
      expect(wrapper.get('[data-testid="scene-backdrop-image"]').attributes("src")).toBe(before);
      expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("河畔清晨");
    });
  });

  it("keeps the whole cockpit visible in dialogue mode (matrix dialogue column)", () => {
    // webclient-align-08-dialogue-surface: the dialogue column hides nothing
    // — the narrative caption, the HUD island stack, the minimap, the dock,
    // and the command line all stay rendered; only the narrative
    // presentation changes (the feed variant lives inside NarrativeFeed).
    const dialogue = mountShell("dialogue", true);
    expect(dialogue.find('[data-elosern-mode="dialogue"]').exists()).toBe(true);
    expect(dialogue.find('[data-anchor="band-message"]').exists()).toBe(true);
    expect(dialogue.find('[data-anchor="actor-left"]').exists()).toBe(true);
    expect(dialogue.find('[data-anchor="hud-left"]').exists()).toBe(true);
    expect(dialogue.find('[data-anchor="command-line"]').exists()).toBe(true);
    expect(dialogue.find(".local-map").exists()).toBe(true);
    expect(dialogue.find('[data-anchor="band-command"]').exists()).toBe(true);

    // The HudFrame gate rules name ONLY creation/combat — a dialogue mode
    // can never match a display:none arm (source-level guard, the same
    // style used by the dock-band ownership guard).
    const css = styleBlock("components/HudFrame.vue");
    // The gate arms exist (creation message region / combat minimap), and NO
    // arm ever names the dialogue mode.
    expect(css).toMatch(
      /\.elosern-stage\[data-elosern-mode="creation"\] \[data-anchor="band-message"\]/,
    );
    expect(css).toMatch(/\.elosern-stage\[data-elosern-mode="combat"\] \.local-map/);
    expect(/data-elosern-mode="dialogue"/.test(css)).toBe(false);

    // Flipping exploration → dialogue never strands focus: the shell's
    // focus-rescue map carries an explicit empty dialogue row (nothing is
    // hidden, so a focused feed keeps focus).
    const feedEl = dialogue.find('[data-testid="narrative-feed"]').element;
    feedEl.tabIndex = 0;
    feedEl.focus();
    expect(document.activeElement).toBe(feedEl);
  });
});

describe("bottom band ownership (webclient-avg-stage-shell design D1/D2)", () => {
  it("paints the band chrome once on the stage band, never on the regions or the dock column", () => {
    // Source-level ownership guard (the z-index-scale precedent): the
    // painted band's declarations live on the full-width `.stage-band` rule
    // in HudFrame.vue, whose height is the fixed `--band-h` token; the
    // command region and the `.action-dock` content column paint nothing.
    const css = styleBlock("components/HudFrame.vue");
    const bandRule = extractRule(css, ".elosern-stage .stage-band");
    expect(bandRule, "the band rule exists").not.toBe("");
    expect(bandRule).toContain("left: 0");
    expect(bandRule).toContain("right: 0");
    expect(bandRule).toContain("bottom: 0");
    expect(bandRule).toContain("height: var(--band-h)");
    expect(bandRule).toContain("grid-template-columns: minmax(0, 2fr) minmax(0, 1fr)");
    // The draft's `.dockwrap` values, verbatim.
    expect(bandRule).toContain("linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))");
    expect(bandRule).toContain("border-top: var(--line)");
    expect(bandRule).toContain("box-shadow: 0 -14px 34px -24px #000");

    const commandRule = extractRule(css, '.elosern-stage [data-anchor="band-command"]');
    expect(commandRule, "the command region rule exists").not.toBe("");
    expect(commandRule).not.toContain("background");
    expect(commandRule).not.toContain("box-shadow");

    const dockRule = extractRule(
      styleBlock("components/ActionDock.vue"),
      ".action-dock",
    );
    expect(dockRule, "the content column rule exists").not.toBe("");
    // The content column paints nothing: no background, border, or shadow.
    expect(dockRule).not.toContain("linear-gradient");
    expect(dockRule).not.toContain("box-shadow");
    expect(dockRule).not.toContain("border-top");
    expect(dockRule).not.toContain("background");
  });

  it("sizes the stage from --band-h alone; --dock-h is gone", () => {
    const css = styleBlock("components/HudFrame.vue");
    expect(css).not.toContain("--dock-h");
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf8");
    expect(tokens).toContain("--band-h: clamp(260px, 27.8vh, 400px);");
    expect(tokens).toContain("--stage-content-bottom: calc(var(--band-h) + var(--command-line-h));");
    expect(tokens).not.toContain("--dock-h");
    const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    expect(shellCss).not.toContain("--dock-h");
    expect(shellCss).not.toContain("stage-portrait");
  });

  it("places the portrait anchors after the combat veil so the player paints above it", () => {
    const wrapper = mount(HudFrame, { props: { mode: "combat" } });
    const stage = wrapper.get('[data-testid="elosern-stage"]').element;
    const order = [...stage.children].map(
      (el) => el.getAttribute("data-testid") || el.className,
    );
    const veil = order.indexOf("stage-combat-veil");
    expect(veil).toBeGreaterThanOrEqual(0);
    expect(order.indexOf("anchor-actor-left")).toBeGreaterThan(veil);
    expect(order.indexOf("anchor-actor-right")).toBeGreaterThan(veil);
    // The band holds exactly the two regions, message first.
    const band = wrapper.get('[data-testid="stage-band"]');
    expect(band.findAll(":scope > [data-anchor]").map((el) => el.attributes("data-anchor"))).toEqual([
      "band-message",
      "band-command",
    ]);
  });
});
