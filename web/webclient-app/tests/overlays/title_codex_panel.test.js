// title-codex-removal: the big-window 稱號冊. Every rendered value is proven
// to come from the committed `title_codex` payload alone — the full-title
// preview, counters, hints/flavors, the ★ mark, and the 移除 affordance are
// serialized server truth. The client evaluates no gate rule: the 移除 button
// exists ONLY where the server row says `can_remove`, and no 卸裝 control
// exists anywhere. Equip/remove/ballot intents ride the single dispatch
// entry through AppClient.
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import TitleCodexPanel from "../../components/TitleCodexPanel.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

function fixedRow(overrides = {}) {
  return {
    key: "g_f_rank",
    display: "F級冒險者",
    category: "guild",
    hint: "",
    flavor: "公會註冊的起點。",
    unlocked: true,
    granted_tick: 120,
    ...overrides,
  };
}

function epithetRow(overrides = {}) {
  return {
    display: "南門新客",
    basis: "初入南門。",
    granted_tick: 121,
    equipped: true,
    can_remove: false,
    ...overrides,
  };
}

const AVAILABLE_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "title_codex",
  fixed_rows: [
    fixedRow(),
    fixedRow({
      key: "g_e_rank",
      display: "E級冒險者",
      unlocked: false,
      flavor: "",
      hint: "通過 E 級升級測驗。",
      granted_tick: 0,
    }),
  ],
  epithet_rows: [
    epithetRow({ display: "破城先鋒", basis: "率先破門。", equipped: false, can_remove: true }),
    epithetRow(),
  ],
  equipped: { fixed: "g_f_rank", epithet: "南門新客" },
  full_title: "F級冒險者　南門新客",
  unlocked: 1,
  total: 7,
  pending_ballot: [],
};

const BALLOT_SAMPLE = {
  ...AVAILABLE_SAMPLE,
  pending_ballot: [
    { display: "夜襲之人", basis: "夜半三度出入敵陣。" },
    { display: "不屈之壁", basis: "重傷仍守住隘口。" },
  ],
};

const UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "codex_unavailable", message: "稱號冊目前無法顯示" },
};

describe("TitleCodexPanel (title-codex-removal)", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders the live full-title preview and counters verbatim", () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="title-codex-preview"]').text()).toBe(
      "F級冒險者　南門新客",
    );
    expect(w.text()).toContain("已收集 1 / 7");
  });

  it("unlocked fixed cards equip by key; locked cards offer no affordance", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    // The locked card renders 🔒 + hint and is inert (no button, no emit).
    expect(w.get('[data-testid="title-codex-fixed-locked-g_e_rank"]').text()).toContain(
      "🔒",
    );
    expect(w.get('[data-testid="title-codex-fixed-locked-g_e_rank"]').text()).toContain(
      "通過 E 級升級測驗。",
    );
    expect(w.find('[data-testid="title-codex-fixed-equip-g_e_rank"]').exists()).toBe(false);
    await w.get('[data-testid="title-codex-fixed-equip-g_f_rank"]').trigger("click");
    expect(w.emitted("action")).toEqual([
      [{ action_id: "title.equip", payload: { kind: "fixed", identifier: "g_f_rank" } }],
    ]);
  });

  it("an unlocked card click updates nothing locally; the preview is payload-fed", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-fixed-equip-g_f_rank"]').trigger("click");
    // The preview still reads the committed payload (it updates when the
    // server re-commits the panel, not on click).
    expect(w.get('[data-testid="title-codex-preview"]').text()).toBe(
      "F級冒險者　南門新客",
    );
  });

  it("epithet rows equip by display and star only the equipped row", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-tab-epithet"]').trigger("click");
    expect(w.findAll('[data-testid="title-codex-star"]')).toHaveLength(1);
    await w.get('[data-testid="title-codex-epithet-equip-1"]').trigger("click");
    expect(w.emitted("action")).toEqual([
      [{ action_id: "title.equip", payload: { kind: "epithet", identifier: "南門新客" } }],
    ]);
  });

  it("the 移除 button follows the server flag only", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-tab-epithet"]').trigger("click");
    // Row 0 carries can_remove: true → button exists; row 1 (equipped,
    // can_remove false) renders NO control at all.
    expect(w.find('[data-testid="title-codex-epithet-remove-0"]').exists()).toBe(true);
    expect(w.find('[data-testid="title-codex-epithet-remove-1"]').exists()).toBe(false);
  });

  it("removal is two-step: ask shows the review card, 確認 emits title.remove", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-tab-epithet"]').trigger("click");
    await w.get('[data-testid="title-codex-epithet-remove-0"]').trigger("click");
    const card = w.get('[data-testid="title-codex-removal-card"]');
    expect(card.text()).toContain("破城先鋒");
    expect(card.text()).toContain("率先破門。");
    expect(card.text()).toContain("此操作不可恢復。");
    // Asking alone dispatches nothing.
    expect(w.emitted("action")).toBeUndefined();
    await w.get('[data-testid="title-codex-removal-confirm"]').trigger("click");
    expect(w.emitted("action")).toEqual([
      [{ action_id: "title.remove", payload: { display: "破城先鋒" } }],
    ]);
    expect(w.find('[data-testid="title-codex-removal-card"]').exists()).toBe(false);
  });

  it("取消 closes the review card without dispatching", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-tab-epithet"]').trigger("click");
    await w.get('[data-testid="title-codex-epithet-remove-0"]').trigger("click");
    await w.get('[data-testid="title-codex-removal-cancel"]').trigger("click");
    expect(w.find('[data-testid="title-codex-removal-card"]').exists()).toBe(false);
    expect(w.emitted("action")).toBeUndefined();
  });

  it("the 提名中 tab presents the ballot with accept/decline intents", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: BALLOT_SAMPLE } });
    await w.get('[data-testid="title-codex-tab-ballot"]').trigger("click");
    expect(w.get('[data-testid="title-codex-ballot-0"]').text()).toContain("1. 夜襲之人");
    await w.get('[data-testid="title-codex-ballot-accept-1"]').trigger("click");
    await w.get('[data-testid="title-codex-ballot-decline"]').trigger("click");
    expect(w.emitted("action")).toEqual([
      [{ action_id: "title.accept", payload: { index: 2 } }],
      [{ action_id: "title.decline", payload: {} }],
    ]);
  });

  it("the window carries no unequip affordance anywhere", () => {
    const w = mount(TitleCodexPanel, { props: { codex: BALLOT_SAMPLE } });
    // The only deletion/undress verb in the window is the server-gated 移除.
    expect(w.text()).not.toContain("卸");
    expect(w.text()).not.toContain("卸下");
    expect(w.text()).not.toContain("清除");
  });

  it("an unavailable payload renders the registry reason; never-committed renders the fallback", () => {
    const w = mount(TitleCodexPanel, { props: { codex: UNAVAILABLE_SAMPLE } });
    expect(w.get('[data-testid="title-codex-unavailable"]').text()).toBe(
      "稱號冊目前無法顯示",
    );
    const w2 = mount(TitleCodexPanel, { props: { codex: null } });
    expect(w2.get('[data-testid="title-codex-unavailable"]').text()).toBe(
      "稱號冊目前無法顯示",
    );
  });

  it("category tabs filter the fixed rows by the payload category", async () => {
    const w = mount(TitleCodexPanel, { props: { codex: AVAILABLE_SAMPLE } });
    await w.get('[data-testid="title-codex-category-combat"]').trigger("click");
    expect(w.find('[data-testid="title-codex-fixed-g_f_rank"]').exists()).toBe(false);
    await w.get('[data-testid="title-codex-category-guild"]').trigger("click");
    expect(w.find('[data-testid="title-codex-fixed-g_f_rank"]').exists()).toBe(true);
  });
});

describe("AppClient title codex overlay wiring (title-codex-removal)", () => {
  let store;
  let sender;
  let wrapper;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
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

  function commitCodex(codex) {
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            title_codex: codex,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  async function openCodexWindow(codex) {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    commitCodex(codex);
    await wrapper.vm.$nextTick();
    store.openOverlay("codex");
    await wrapper.vm.$nextTick();
  }

  it("the store accepts the codex overlay name", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    expect(store.openOverlay("codex")).toBe(true);
    expect(store.view.hudOverlay).toBe("codex");
  });

  it("the opener button opens the window with the committed panel", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    commitCodex(AVAILABLE_SAMPLE);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="command-line-codex"]').trigger("click");
    expect(store.view.hudOverlay).toBe("codex");
    expect(
      wrapper.vm.$el
        .querySelector('[data-testid="title-codex-preview"]')
        .textContent.trim(),
    ).toBe("F級冒險者　南門新客");
    expect(
      wrapper.vm.$el
        .querySelector('[data-testid="overlay-host"]')
        .getAttribute("data-elosern-overlay"),
    ).toBe("codex");
  });

  it("a codex equip click dispatches exactly one title.equip ui_action", async () => {
    await openCodexWindow(AVAILABLE_SAMPLE);
    await wrapper
      .get('[data-testid="title-codex-fixed-equip-g_f_rank"]')
      .trigger("click");
    const actions = sender.sent.actions.filter((e) => e.action_id === "title.equip");
    expect(actions).toHaveLength(1);
    expect(actions[0].payload).toEqual({ kind: "fixed", identifier: "g_f_rank" });
    // The input echo replays the typed command (catalog resolves the payload).
    const echo = store.narrative.filter((line) => line.kind === "in").map((l) => l.text);
    expect(echo).toContain("title equip fixed g_f_rank");
  });

  it("a confirmed removal dispatches exactly one title.remove ui_action", async () => {
    await openCodexWindow(AVAILABLE_SAMPLE);
    await wrapper.get('[data-testid="title-codex-tab-epithet"]').trigger("click");
    await wrapper
      .get('[data-testid="title-codex-epithet-remove-0"]')
      .trigger("click");
    // Asking dispatches nothing.
    expect(sender.sent.actions.filter((e) => e.action_id === "title.remove")).toHaveLength(0);
    await wrapper
      .get('[data-testid="title-codex-removal-confirm"]')
      .trigger("click");
    const actions = sender.sent.actions.filter((e) => e.action_id === "title.remove");
    expect(actions).toHaveLength(1);
    expect(actions[0].payload).toEqual({ display: "破城先鋒" });
    const echo = store.narrative.filter((line) => line.kind === "in").map((l) => l.text);
    expect(echo).toContain("title remove epithet 破城先鋒 confirm");
  });

  it("an unavailable committed panel renders the reason inside the window", async () => {
    await openCodexWindow(UNAVAILABLE_SAMPLE);
    expect(
      wrapper.vm.$el
        .querySelector('[data-testid="title-codex-unavailable"]')
        .textContent.trim(),
    ).toBe("稱號冊目前無法顯示");
  });
});
