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
// t_-keyed graphs with invented element prose; every rendered value still
// proves it comes from the payload.
const T_ROOT = "t_ember_arrow";
const T_ROOT_LABEL = "燼羽箭";
const T_CHILD = "t_cinder_tide";
const T_CHILD_LABEL = "燼潮波";
const T_CHILD_PREREQ = "需「焰紋術 Lv.3」";
const T_READY = "t_ember_ready";
const T_READY_LABEL = "燼芽焰";
const T_EL_FIRE = "焰流";
const T_WIND = "t_gale_lance";
const T_WIND_LABEL = "巒槍";
const T_EL_WIND = "馜流";
const T_DONE = "t_ash_crown";
const T_DONE_LABEL = "燼冠";
const T_ABSENT = "t_tide_spear";

function node(overrides = {}) {
  return {
    skill_key: T_ROOT,
    display_name_zh: T_ROOT_LABEL,
    owned: true,
    usable: true,
    ready: false,
    level: 1,
    xp_into_level: 23,
    xp_to_next_level: 27,
    capped: false,
    prereq_text_zh: "",
    depth: 0,
    ...overrides,
  };
}

const AVAILABLE_SAMPLE = {
  schema_version: 2,
  available: true,
  kind: "lineage",
  completed_count: 1,
  total_count: 3,
  graphs: [
    {
      graph_id: T_ROOT,
      group_label_zh: T_EL_FIRE,
      root_keys: [T_ROOT],
      owned_count: 1,
      total_count: 3,
      consumed: false,
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
          depth: 1,
        }),
        node({
          skill_key: T_READY,
          display_name_zh: T_READY_LABEL,
          owned: false,
          usable: false,
          ready: true,
          level: 0,
          xp_into_level: 0,
          xp_to_next_level: 50,
          depth: 1,
        }),
      ],
      edges: [
        { from_key: T_ROOT, to_key: T_CHILD, min_level: 3 },
        { from_key: T_ROOT, to_key: T_READY, min_level: 3 },
      ],
    },
    {
      graph_id: T_WIND,
      group_label_zh: T_EL_WIND,
      root_keys: [T_WIND],
      owned_count: 1,
      total_count: 1,
      consumed: false,
      nodes: [node({ skill_key: T_WIND, display_name_zh: T_WIND_LABEL })],
      edges: [],
    },
    {
      graph_id: T_DONE,
      group_label_zh: T_EL_FIRE,
      root_keys: [T_DONE],
      owned_count: 1,
      total_count: 1,
      consumed: true,
      nodes: [
        node({
          skill_key: T_DONE,
          display_name_zh: T_DONE_LABEL,
          capped: true,
          level: 10,
          xp_into_level: 0,
          xp_to_next_level: 0,
        }),
      ],
      edges: [],
    },
  ],
};

const UNAVAILABLE_SAMPLE = {
  schema_version: 2,
  available: false,
  reason: { code: "lineage_unavailable", message: "技能系譜目前無法顯示" },
};

describe("LineagePanel (skill-lineage-panel task 2.3)", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders the header counts verbatim from the payload", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-panel-header"]').text()).toBe("已完成 1 / 3 樹");
  });

  it("renders graphs collapsed with their owned/total count; no node rows", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    const toggle = w.get(`[data-testid="lineage-graph-toggle-${T_ROOT}"]`);
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(w.find(`[data-testid="lineage-graph-nodes-${T_ROOT}"]`).exists()).toBe(false);
    // Collapsed graph renders its supplied owned/total count.
    expect(w.get(`[data-testid="lineage-graph-count-${T_ROOT}"]`).text()).toBe("1/3");
    // No chain meter survives the v2 contract.
    expect(w.find(".lineage-chain__meter").exists()).toBe(false);
    expect(w.find('[data-testid^="lineage-graph-meter-"]').exists()).toBe(false);
  });

  it("a consumed graph renders the 已全數見頂 mark instead of a count", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-graph-consumed"]').text()).toBe("已全數見頂");
    expect(w.find(`[data-testid="lineage-graph-count-${T_DONE}"]`).exists()).toBe(false);
  });

  it("expanding renders per-node meters, 見頂/可解鎖 marks, and prereq lines", async () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    await w.get(`[data-testid="lineage-graph-toggle-${T_ROOT}"]`).trigger("click");
    expect(w.get(`[data-testid="lineage-graph-toggle-${T_ROOT}"]`).attributes("aria-expanded")).toBe("true");
    const nodes = w.get(`[data-testid="lineage-graph-nodes-${T_ROOT}"]`);
    expect(nodes.findAll(".lineage-node")).toHaveLength(3);
    // The capped node carries the 見頂 mark, not a meter.
    expect(w.get(`[data-testid="lineage-node-${T_ROOT}"]`).text()).toContain("（見頂）");
    // The locked node renders its payload prereq line verbatim.
    expect(w.get(`[data-testid="lineage-node-prereq-${T_CHILD}"]`).text()).toBe(T_CHILD_PREREQ);
    // The ready node renders its 可解鎖 mark.
    expect(w.get(`[data-testid="lineage-node-ready-${T_READY}"]`).text()).toBe("（可解鎖）");
    await w.get(`[data-testid="lineage-graph-toggle-${T_WIND}"]`).trigger("click");
    // The owned, uncapped node renders the payload meter pair 「23/50 → 下一階」.
    expect(w.get(`[data-testid="lineage-node-meter-${T_WIND}"]`).text()).toBe("23/50 → 下一階");
  });

  it("collapsing again removes the node rows", async () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    const toggle = w.get(`[data-testid="lineage-graph-toggle-${T_WIND}"]`);
    await toggle.trigger("click");
    expect(w.find(`[data-testid="lineage-graph-nodes-${T_WIND}"]`).exists()).toBe(true);
    await toggle.trigger("click");
    expect(w.find(`[data-testid="lineage-graph-nodes-${T_WIND}"]`).exists()).toBe(false);
  });

  it("an unavailable payload renders the registry reason and no ledger", () => {
    const w = mount(LineagePanel, { props: { lineage: UNAVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="lineage-panel-unavailable"]').text()).toBe("技能系譜目前無法顯示");
    expect(w.find('[data-testid="lineage-panel-header"]').exists()).toBe(false);
    expect(w.findAll(".lineage-graph")).toHaveLength(0);
  });

  it("a never-committed panel renders the fallback line, not an empty ledger", () => {
    const w = mount(LineagePanel, { props: { lineage: null } });
    expect(w.get('[data-testid="lineage-panel-unavailable"]').text()).toBe("技能系譜目前無法顯示");
  });

  it("an available-but-graphless payload renders the empty line, no placeholder graph", () => {
    const w = mount(LineagePanel, {
      props: { lineage: { ...AVAILABLE_SAMPLE, graphs: [] } },
    });
    expect(w.get('[data-testid="lineage-panel-empty"]').text()).toBe("目前尚無可追蹤的技能系譜。");
    expect(w.findAll(".lineage-graph")).toHaveLength(0);
  });

  it("invents nothing: only payload graphs render, nothing else", () => {
    const w = mount(LineagePanel, { props: { lineage: AVAILABLE_SAMPLE } });
    expect(w.findAll(".lineage-graph")).toHaveLength(3);
    expect(w.find(`[data-testid="lineage-graph-${T_ABSENT}"]`).exists()).toBe(false);
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

  it("the top-bar tool icon opens the overlay with the committed panel and restores focus on close", async () => {
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
    const opener = wrapper.get('[data-testid="nav-tool-lineage"]');
    opener.element.focus();
    await opener.trigger("click");
    expect(store.view.hudOverlay).toBe("lineage");
    const header = wrapper.get('[data-testid="lineage-panel-header"]');
    expect(header.text()).toBe("已完成 1 / 3 樹");
    // The window renders inside the shared overlay host.
    expect(wrapper.get('[data-testid="overlay-host"]').attributes("data-elosern-overlay")).toBe(
      "lineage",
    );
    await wrapper.get('[data-testid="overlay-host-close"]').trigger("click");
    expect(store.view.hudOverlay).toBeNull();
    expect(document.activeElement).toBe(opener.element);
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
