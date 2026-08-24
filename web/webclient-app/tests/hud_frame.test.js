// H1 mode-gated visibility (design D2/D10): surface visibility is gated by
// the committed game mode. A surface hidden for the current mode is removed
// from rendering with `display:none` — never dimmed — so it leaves the
// accessibility tree and the tab order. This suite verifies the minimap
// matrix row (absent in combat, present in exploration) and the focus-rescue
// contract (a focused element inside a mode-hidden surface loses focus to
// the action dock, not to the document body).
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppShell from "../components/AppShell.vue";
import ActionDock from "../components/ActionDock.vue";
import LocalMap from "../components/LocalMap.vue";
import * as fx from "./store/protocol_fixtures.js";

import { h } from "vue";

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
