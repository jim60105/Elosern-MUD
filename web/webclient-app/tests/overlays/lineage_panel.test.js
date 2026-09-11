// skill-lineage-panel (task 2.3): the big-window lineage ledger. Every
// rendered value is proven to come from the committed panel payload alone —
// header counts, per-node meters, 見頂 marks, prerequisite lines, and the
// collapsed-chain meter are serialized server truth; the client computes no
// growth rules and invents no placeholder chain when the payload omits one.
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import LineagePanel from "../../components/LineagePanel.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

// File-local synthetic lineage rows (test-data-independence): invented
// t_-keyed chains with invented element prose; every rendered value still
// proves it comes from the payload.
const T_ROOT = "t_ember_arrow";
const T_ROOT_LABEL = "燼羽箭";
const T_CHILD = "t_cinder_tide";
const T_CHILD_LABEL = "燼潮波";
const T_CHILD_PREREQ = "需「焰紋術 Lv.3」";
const T_EL_FIRE = "焰流";
const T_WIND = "t_gale_lance";
const T_WIND_LABEL = "巒槍";
const T_EL_WIND = "馜流";
const T_ABSENT = "t_tide_spear";

function node(overrides = {}) {
  return {
    skill_key: T_ROOT,
    display_name_zh: T_ROOT_LABEL,
    owned: true,
    usable: true,
    level: 1,
    xp_into_level: 23,
    xp_to_next_level: 27,
    capped: false,
    prereq_text_zh: "",
    ...overrides,
  };
}

const AVAILABLE_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "lineage",
  completed_count: 1,
  total_count: 2,
  chains: [
    {
      root_skill_key: T_ROOT,
      element_or_style_zh: T_EL_FIRE,
      consumed: true,
      meter: 1,
      nodes: [
        node({ skill_key: T_ROOT, xp_into_level: 0, xp_to_next_level: 0, capped: true, level: 10 }),
        node({
          skill_key: T_CHILD,
          display_name_zh: T_CHILD_LABEL,
          owned: false,
          usable: false,
          level: 0,
          xp_into_level: 0,
          xp_to_next_level: 50,
          prereq_text_zh: T_CHILD_PREREQ,
        }),
      ],
    },
    {
      root_skill_key: T_WIND,
      element_or_style_zh: T_EL_WIND,
      consumed: false,
      meter: 0.25,
      nodes: [node({ skill_key: T_WIND, display_name_zh: T_WIND_LABEL })],
    },
  ],
};

const UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "lineage_unavailable", message: "技能系譜目前無法顯示" },
};

describe("LineagePanel (skill-lineage-panel task 2.3)", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders the header counts verbatim from the payload", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-panel-header"]').text()).toBe("已完成 1 / 2 樹");
  });

  it("renders chains collapsed with the chain meter; no node rows", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    const toggle = w.get(`[data-testid="lineage-chain-toggle-${T_WIND}"]`);
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(w.find(`[data-testid="lineage-chain-nodes-${T_WIND}"]`).exists()).toBe(false);
    // Collapsed chain renders its aggregate meter (0.25 → 25%).
    expect(w.text()).toContain("25%");
    const fill = w
      .get(`[data-testid="lineage-chain-meter-${T_WIND}"]`)
      .get(".lineage-chain__meter-fill");
    expect(fill.attributes("style")).toContain("width: 25%");
  });

  it("a consumed chain renders the 已全數見頂 mark instead of a percent", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-chain-consumed"]').text()).toBe("已全數見頂");
  });

  it("expanding renders per-node meters, the 見頂 mark, and prereq lines", async () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    await w.get(`[data-testid="lineage-chain-toggle-${T_ROOT}"]`).trigger("click");
    expect(w.get(`[data-testid="lineage-chain-toggle-${T_ROOT}"]`).attributes("aria-expanded")).toBe("true");
    const nodes = w.get(`[data-testid="lineage-chain-nodes-${T_ROOT}"]`);
    expect(nodes.findAll(".lineage-node")).toHaveLength(2);
    // The capped node carries the 見頂 mark, not a meter.
    expect(w.get(`[data-testid="lineage-node-${T_ROOT}"]`).text()).toContain("（見頂）");
    // The locked node renders its payload prereq line verbatim.
    expect(w.get(`[data-testid="lineage-node-prereq-${T_CHILD}"]`).text()).toBe(T_CHILD_PREREQ);
    await w.get(`[data-testid="lineage-chain-toggle-${T_WIND}"]`).trigger("click");
    // The owned, uncapped node renders the payload meter pair 「23/50 → 下一階」.
    expect(w.get(`[data-testid="lineage-node-meter-${T_WIND}"]`).text()).toBe("23/50 → 下一階");
  });

  it("collapsing again removes the node rows", async () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    const toggle = w.get(`[data-testid="lineage-chain-toggle-${T_WIND}"]`);
    await toggle.trigger("click");
    expect(w.find(`[data-testid="lineage-chain-nodes-${T_WIND}"]`).exists()).toBe(true);
    await toggle.trigger("click");
    expect(w.find(`[data-testid="lineage-chain-nodes-${T_WIND}"]`).exists()).toBe(false);
  });

  it("an unavailable payload renders the registry reason and no ledger", () => {
    const w = mount(LineagePanel, { props: { lineage: UNAVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-panel-unavailable"]').text()).toBe("技能系譜目前無法顯示");
    expect(w.find('[data-testid="lineage-panel-header"]').exists()).toBe(false);
    expect(w.findAll(".lineage-chain")).toHaveLength(0);
  });

  it("a never-committed panel renders the fallback line, not an empty ledger", () => {
    const w = mount(LineagePanel, { props: { lineage: null } });
    expect(w.get('[data-testid="lineage-panel-unavailable"]').text()).toBe("技能系譜目前無法顯示");
  });

  it("an available-but-chainless payload renders the empty line, no placeholder chain", () => {
    const w = mount(LineagePanel, {
      props: { lineage: { ...AVAILABLE_SAMPLE, chains: [] } },
    });
    expect(w.get('[data-testid="lineage-panel-empty"]').text()).toBe("目前尚無可追蹤的技能系譜。");
    expect(w.findAll(".lineage-chain")).toHaveLength(0);
  });

  it("invents nothing: only payload chains render, nothing else", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.findAll(".lineage-chain")).toHaveLength(2);
    expect(w.find(`[data-testid="lineage-chain-${T_ABSENT}"]`).exists()).toBe(false);
  });
});

describe("AppClient lineage overlay wiring (skill-lineage-panel task 2.3)", () => {
  let store;
  let wrapper;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = "";
  });

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  it("the store accepts the lineage overlay name", () => {
    mountAppClient();
    expect(store.openOverlay("lineage")).toBe(true);
    expect(store.view.hudOverlay).toBe("lineage");
  });

  it("the command-line icon opens the overlay with the committed panel", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ panels: { lineage: AVAILABLE_SAMPLE } })],
    );
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="command-line-lineage"]').trigger("click");
    expect(store.view.hudOverlay).toBe("lineage");
    const header = wrapper.get('[data-testid="lineage-panel-header"]');
    expect(header.text()).toBe("已完成 1 / 2 樹");
    // The window renders inside the shared overlay host.
    expect(wrapper.get('[data-testid="overlay-host"]').attributes("data-elosern-overlay")).toBe(
      "lineage",
    );
  });

  it("an unavailable committed panel renders the reason inside the window", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ panels: { lineage: UNAVAILABLE_SAMPLE } })],
    );
    await wrapper.vm.$nextTick();
    store.openOverlay("lineage");
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="lineage-panel-unavailable"]').text()).toBe(
      "技能系譜目前無法顯示",
    );
  });
});
