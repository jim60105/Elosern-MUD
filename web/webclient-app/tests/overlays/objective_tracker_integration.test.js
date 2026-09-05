import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { h } from "vue";
import AppShell from "../../components/AppShell.vue";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import { OBJECTIVES_PANEL_SAMPLE } from "../../stories/fixtures.js";

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
      objectives: () => (rows.length > 0 && mode !== "creation" ? h(ObjectiveTracker, { rows }) : null),
    };

    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode, openSurfaces },
      slots,
    });
    return wrapper;
  }

  it("mounts the objective tracker in exploration mode when rows are present", () => {
    const w = mountShellWithTracker({ mode: "exploration" });
    const tracker = w.find('[data-testid="objective-tracker"]');
    expect(tracker.exists()).toBe(true);
    expect(tracker.get('[data-testid="objective-tracker__count"]').text()).toBe("3 追蹤");
  });

  it("mounts the objective tracker in combat mode when rows are present", () => {
    const w = mountShellWithTracker({ mode: "combat" });
    const tracker = w.find('[data-testid="objective-tracker"]');
    expect(tracker.exists()).toBe(true);
  });

  it("does not render the tracker in creation mode even if rows are present", () => {
    const w = mountShellWithTracker({ mode: "creation" });
    expect(w.find('[data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("does not render the tracker when rows is empty", () => {
    const w = mountShellWithTracker({ mode: "exploration", rows: [] });
    expect(w.find('[data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("HudFrame applies recession filter to .obj when data-menu-open is true", () => {
    const style = styleBlock("components/HudFrame.vue");
    expect(style).toContain(".elosern-stage[data-menu-open=\"true\"] .obj");
    expect(style).toContain("filter: var(--menu-open-filter)");
  });
});
