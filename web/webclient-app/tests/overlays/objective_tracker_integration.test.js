import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { h } from "vue";
import AppClient from "../../AppClient.vue";
import AppShell from "../../components/AppShell.vue";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { OBJECTIVES_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "../store/protocol_fixtures.js";

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

describe("ObjectiveTracker integration & stage recession (webclient-align-09-objective-tracker-ui)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountShellWithTracker({ mode = "exploration", rows = OBJECTIVES_PANEL_SAMPLE.rows, openSurfaces = [] } = {}) {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);

    const slots = {
      map: () => (rows.length > 0 && mode !== "creation" ? h(ObjectiveTracker, { rows }) : null),
    };

    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode, openSurfaces },
      slots,
    });
    return wrapper;
  }

  it("mounts the objective line inside the map anchor in exploration mode", () => {
    const w = mountShellWithTracker({ mode: "exploration" });
    const tracker = w.find('[data-anchor="map"] [data-testid="objective-tracker"]');
    expect(tracker.exists()).toBe(true);
    expect(tracker.get('[data-testid="objective-tracker__more"]').text()).toBe("+2");
  });

  it("keeps the objective line mounted in combat, where the stage CSS hides it", () => {
    // The data rule mounts it; the exploration-only gate is CSS on the
    // stage's mode attribute (asserted below), so the DOM stays stable.
    const w = mountShellWithTracker({ mode: "combat" });
    expect(w.find('[data-anchor="map"] [data-testid="objective-tracker"]').exists()).toBe(true);
    expect(w.find('[data-elosern-mode="combat"]').exists()).toBe(true);
  });

  it("does not render the tracker in creation mode even if rows are present", () => {
    const w = mountShellWithTracker({ mode: "creation" });
    expect(w.find('[data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("does not render the tracker when rows is empty", () => {
    const w = mountShellWithTracker({ mode: "exploration", rows: [] });
    expect(w.find('[data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("recedes the objective line through its anchor, not a rule of its own", () => {
    // The line lives inside the `map` anchor, which the menu-open filter
    // already covers; a second `.obj` filter would double the recession.
    const style = styleBlock("components/HudFrame.vue");
    expect(style).toContain('.elosern-stage[data-menu-open="true"] .stage-anchor:not(.stage-band > .stage-anchor)');
    expect(style).toContain("filter: var(--menu-open-filter)");
    expect(style).not.toMatch(/data-menu-open="true"\] \.obj/);
    const shell = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf-8");
    expect(shell).not.toMatch(/data-menu-open="true"\] \.obj/);
  });

  it("shows the objective line only in exploration and hides the whole map anchor in creation", () => {
    const style = styleBlock("components/HudFrame.vue");
    const gate = extractRule(
      style,
      '.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="map"] .obj',
    );
    expect(gate).toContain("display: none");
    expect(style).toMatch(
      /\.elosern-stage\[data-elosern-mode="creation"\] \[data-anchor="map"\][,\s]/,
    );
  });
});

describe("the map anchor's island order (webclient-avg-stage-hud-anchors design D1/D4)", () => {
  let wrapper;
  let store;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  async function mountClient(panels, mode = "exploration") {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot({ mode, panels })], {});
    expect(result.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    return wrapper;
  }

  function mapChildren(w) {
    return [...w.get('[data-anchor="map"]').element.children].map((el) => el.getAttribute("data-testid"));
  }

  it("stacks the minimap, the objective line, and the title ballot in that order", async () => {
    const w = await mountClient({
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      local_map: fx.localMapPanel(),
      objectives: OBJECTIVES_PANEL_SAMPLE,
      title_ballot: {
        schema_version: 1,
        available: true,
        kind: "title_ballot",
        candidates: [{ index: 1, display: "異名1", basis: "第1條事蹟引用。" }],
      },
    });
    expect(mapChildren(w)).toEqual(["local-map", "objective-tracker", "title-ballot-menu"]);
    expect(w.find('[data-anchor="vitals"] [data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("puts the combat participant frame in the map anchor, never on a portrait anchor", async () => {
    const w = await mountClient(
      {
        status: fx.statusPanel(),
        context_actions: fx.combatActions(),
      },
      "combat",
    );
    expect(w.find('[data-anchor="map"] [data-testid="participant-frame"]').exists()).toBe(true);
    expect(w.find('[data-anchor="actor-right"] [data-testid="participant-frame"]').exists()).toBe(false);
    expect(w.get('[data-anchor="actor-right"]').element.children.length).toBe(0);
  });
});
