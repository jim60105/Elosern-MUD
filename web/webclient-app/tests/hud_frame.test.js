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
import ActionDock from "../components/ActionDock.vue";
import LocalMap from "../components/LocalMap.vue";
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
});

describe("dock band ownership (webclient-align-01-dock-chrome)", () => {
  it("paints the full-width band on the dock anchor, not the content column", () => {
    // Source-level ownership guard (the z-index-scale precedent): the
    // painted band's declarations must live on the full-width anchor rule
    // in HudFrame.vue and be ABSENT from the centered `.action-dock` rule.
    // The real-browser gutter/paint proof lives in
    // web/tests/browser/test_browser_contextual_hud.py.
    const anchorRule = extractRule(
      styleBlock("components/HudFrame.vue"),
      ".elosern-stage [data-anchor=\"dock\"]",
    );
    expect(anchorRule, "the dock anchor rule exists").not.toBe("");
    expect(anchorRule).toContain("left: 0");
    expect(anchorRule).toContain("right: 0");
    // The draft's `.dockwrap` values, verbatim.
    expect(anchorRule).toContain("linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))");
    expect(anchorRule).toContain("border-top: var(--line)");
    expect(anchorRule).toContain("box-shadow: 0 -14px 34px -24px #000");
    expect(anchorRule).toContain("padding: 11px 18px 12px");

    const dockRule = extractRule(
      styleBlock("components/ActionDock.vue"),
      ".action-dock",
    );
    expect(dockRule, "the content column rule exists").not.toBe("");
    expect(dockRule).toContain("max-width: 1180px");
    expect(dockRule).toContain("margin: 0 auto");
    // The content column paints nothing: no background, border, or shadow.
    expect(dockRule).not.toContain("linear-gradient");
    expect(dockRule).not.toContain("box-shadow");
    expect(dockRule).not.toContain("border-top");
    expect(dockRule).not.toContain("background");
  });
});
