// webclient-scene-overview-component (task 4.5): the verb popover renders
// the real `verbMenuFor` rows and closes on an outside press.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DockVerbPopover from "../../components/DockVerbPopover.vue";
import { explorationPanelFixture, verbArgs } from "../../stories/fixtures/scene_overview.js";

const PANEL = explorationPanelFixture({
  targets: [
    {
      identity: 11,
      name: "試驗守衛",
      affordances: [
        { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
        {
          kind: "action",
          action_id: "explore.engage",
          label: "戰鬥",
          enabled: false,
          disabled_reason: { code: "peaceful", message: "這裡禁止戰鬥。" },
        },
      ],
    },
  ],
});

describe("DockVerbPopover", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPopover(props = {}) {
    wrapper = mount(DockVerbPopover, {
      attachTo: document.body,
      props: { ...verbArgs(PANEL, 11), ...props },
    });
    return wrapper;
  }

  it("names its target and lists the verb rows, ending with 查看 then back", () => {
    const w = mountPopover();
    expect(w.get(".verb-popover__head").text()).toBe("試驗守衛");
    expect(w.get('[data-testid="verb-popover"]').attributes("aria-label")).toBe("試驗守衛 的行動");
    const rows = w.findAll('[data-testid="dock-item"]');
    expect(rows.map((row) => row.attributes("data-item-key"))).toEqual([
      "talk-open",
      "engage",
      "look-target",
      "back",
    ]);
    expect(rows.slice(-2).map((row) => row.get(".dock-menu-item__label").text())).toEqual([
      "查看",
      "返回上一層",
    ]);
    expect(w.get('[data-testid="dock-menu"]').attributes("role")).toBe("listbox");
  });

  it("emits activate for an enabled row and only focus-change for a disabled one", async () => {
    const w = mountPopover();
    await w.get('[data-item-key="look-target"]').trigger("click");
    const [[payload]] = w.emitted("activate");
    expect(payload.key).toBe("look-target");
    expect(payload.item.payload).toEqual({ target_id: 11 });
    await w.get('[data-item-key="engage"]').trigger("click");
    expect(w.emitted("focus-change")).toEqual([["look-target"], ["engage"]]);
    expect(w.emitted("activate")).toHaveLength(1);
    expect(w.get("#exploration-row-1-reason").text()).toBe("這裡禁止戰鬥。");
  });

  it("emits back once on an outside press and nothing on a press on the card", async () => {
    const w = mountPopover();
    await w.get('[data-testid="verb-popover"]').trigger("pointerdown");
    await w.get(".verb-popover__head").trigger("pointerdown");
    expect(w.emitted("back")).toBeUndefined();
    await w.get('[data-testid="verb-popover-layer"]').trigger("pointerdown");
    expect(w.emitted("back")).toHaveLength(1);
    expect(w.emitted("activate")).toBeUndefined();
  });
});
