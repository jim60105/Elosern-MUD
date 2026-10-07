import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import OverviewView from "../views/OverviewView.vue";
import { GmApiError } from "../lib/api.js";
import { createSessionState } from "../lib/session.js";
import { CALL_DETAIL, DASHBOARD, SESSION } from "../stories/fixtures.js";

function mountOverview(get) {
  const api = { get: vi.fn(get), post: vi.fn() };
  const session = createSessionState(api);
  const wrapper = mount(OverviewView, {
    attachTo: document.body,
    global: { provide: { gmApi: api, gmSession: session } },
  });
  return { wrapper, api };
}

const paths = (api) => api.get.mock.calls.map(([path]) => path);

function setVisibility(state) {
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("operations dashboard overview", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility("visible");
  });
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("renders session identity and every dashboard section without the removed health API", async () => {
    const { wrapper, api } = mountOverview(async (path) => (path === "/session" ? SESSION : DASHBOARD));
    await flushPromises();
    expect(paths(api).sort()).toEqual(["/dashboard", "/session"]);
    expect(paths(api)).not.toContain("/health");
    expect(wrapper.get("[data-testid='gm-session'] [data-field='account_name']").text()).toBe("operator_01");
    const cards = wrapper.findAll("[data-testid='gm-services'] .gm-service-card");
    expect(cards.map((card) => card.attributes("data-status"))).toEqual(["ok", "warn", "neutral", "ok"]);
    const layerRows = wrapper.findAll("[data-testid='gm-llm-layers'] tbody tr");
    expect(layerRows[0].text()).toContain("npc_dialogue");
    expect(layerRows[0].get(".status-marker").text()).toBe("異常");
    expect(wrapper.get("[data-testid='gm-llm-layers']").text()).toContain("緩衝區保留 113 / 500 筆呼叫");
    const dream = layerRows.find((row) => row.text().includes("dream"));
    expect(dream.get(".status-marker").text()).toBe("尚無資料");
    expect(wrapper.findAll("[data-testid='gm-recent-calls'] tbody tr")).toHaveLength(7);
    expect(wrapper.get("[data-testid='gm-world']").text()).toContain("黃昏");
    expect(wrapper.get("[data-testid='gm-art']").text()).toContain("排程執行中");
    expect(wrapper.get("[data-testid='gm-process']").text()).toContain("可讀取");
    expect(wrapper.findAll("[data-testid='gm-issues'] > li")).toHaveLength(3);
    expect(wrapper.get("[data-testid='gm-refresh-bar']").attributes("data-state")).toBe("live");
    wrapper.unmount();
  });

  it("polls every five seconds, pauses while hidden, and resumes once", async () => {
    const { wrapper, api } = mountOverview(async (path) => (path === "/session" ? SESSION : DASHBOARD));
    await flushPromises();
    const dashboards = () => paths(api).filter((path) => path === "/dashboard").length;
    expect(dashboards()).toBe(1);
    await vi.advanceTimersByTimeAsync(5000);
    expect(dashboards()).toBe(2);
    setVisibility("hidden");
    await vi.advanceTimersByTimeAsync(20000);
    expect(dashboards()).toBe(2);
    expect(wrapper.get("[data-testid='gm-refresh-bar']").attributes("data-state")).toBe("paused");
    setVisibility("visible");
    await vi.advanceTimersByTimeAsync(0);
    expect(dashboards()).toBe(3);
    await vi.advanceTimersByTimeAsync(5000);
    expect(dashboards()).toBe(4);
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(20000);
    expect(dashboards()).toBe(4);
  });

  it("refreshes on demand without overlapping the poll", async () => {
    const { wrapper, api } = mountOverview(async (path) => (path === "/session" ? SESSION : DASHBOARD));
    await flushPromises();
    await wrapper.get("[data-testid='gm-refresh-bar'] button").trigger("click");
    await flushPromises();
    expect(paths(api).filter((path) => path === "/dashboard")).toHaveLength(2);
    wrapper.unmount();
  });

  it("localizes a slot error and keeps an offline service usable", async () => {
    const snapshot = {
      ...DASHBOARD,
      services: { ...DASHBOARD.services, sd: { ok: false, code: "sd_connection_refused", host: "sd.local.test", checked_at: null, from_cache: false } },
      art: { error: { code: "art_unavailable", message: "無法讀取美術佇列。" } },
    };
    const { wrapper } = mountOverview(async (path) => (path === "/session" ? SESSION : snapshot));
    await flushPromises();
    const errors = wrapper.findAll("[data-testid='gm-slot-error']");
    expect(errors).toHaveLength(1);
    expect(errors[0].text()).toContain("art_unavailable");
    expect(errors[0].attributes("role")).toBeUndefined();
    const sd = wrapper.get("[data-service='sd']");
    expect(sd.attributes("data-status")).toBe("crit");
    expect(sd.text()).toContain("離線");
    expect(sd.text()).toContain("sd_connection_refused");
    expect(wrapper.find("[data-testid='gm-llm-layers']").exists()).toBe(true);
    expect(wrapper.find("[data-testid='gm-world']").exists()).toBe(true);
    wrapper.unmount();
  });

  it("keeps the last good snapshot and marks it stale when a poll fails", async () => {
    let fail = false;
    const { wrapper } = mountOverview(async (path) => {
      if (path === "/session") return SESSION;
      if (fail) throw new GmApiError("network_error", { message: "無法連線到伺服器，請確認服務是否運作中。" });
      return DASHBOARD;
    });
    await flushPromises();
    fail = true;
    await vi.advanceTimersByTimeAsync(5000);
    const bar = wrapper.get("[data-testid='gm-refresh-bar']");
    expect(bar.attributes("data-state")).toBe("stale");
    expect(bar.text()).toContain("無法連線到伺服器");
    expect(wrapper.find("[data-testid='gm-llm-layers']").exists()).toBe(true);
    fail = false;
    await vi.advanceTimersByTimeAsync(5000);
    expect(wrapper.get("[data-testid='gm-refresh-bar']").attributes("data-state")).toBe("live");
    wrapper.unmount();
  });

  it("opens the payload drawer for a selected call and fetches only then", async () => {
    const { wrapper, api } = mountOverview(async (path) => {
      if (path === "/session") return SESSION;
      if (path === "/dashboard") return DASHBOARD;
      return CALL_DETAIL;
    });
    await flushPromises();
    expect(paths(api).some((path) => path.startsWith("/llm/calls/"))).toBe(false);
    const target = DASHBOARD.llm.recent[2];
    await wrapper.get(`button[data-call-id='${target.call_id}']`).trigger("click");
    await flushPromises();
    expect(paths(api)).toContain(`/llm/calls/${target.call_id}`);
    expect(wrapper.get(".gm-call-drawer").attributes("open")).toBeDefined();
    expect(wrapper.get("[data-testid='gm-call-outcome']").text()).toContain("npc_dialogue");
    wrapper.unmount();
  });

  it("holds new calls back while the pointer or focus is inside the table", async () => {
    let snapshot = DASHBOARD;
    const { wrapper } = mountOverview(async (path) => (path === "/session" ? SESSION : snapshot));
    await flushPromises();
    const region = wrapper.get("[data-testid='gm-calls-region']");
    await region.trigger("pointerenter");
    await region.trigger("focusin");
    const fresh = { ...DASHBOARD.llm.recent[0], ts: DASHBOARD.llm.recent[0].ts + 1, call_id: "ff".repeat(16) };
    snapshot = { ...DASHBOARD, llm: { ...DASHBOARD.llm, recent: [fresh, ...DASHBOARD.llm.recent] } };
    await vi.advanceTimersByTimeAsync(5000);
    expect(wrapper.findAll("[data-testid='gm-recent-calls'] tbody tr")).toHaveLength(7);
    expect(wrapper.get("[data-testid='gm-calls-new']").text()).toBe("有 1 筆新呼叫");
    await region.trigger("pointerleave");
    expect(wrapper.findAll("[data-testid='gm-recent-calls'] tbody tr")).toHaveLength(7);
    await region.trigger("focusout");
    expect(wrapper.findAll("[data-testid='gm-recent-calls'] tbody tr")).toHaveLength(8);
    expect(wrapper.find("[data-testid='gm-calls-new']").exists()).toBe(false);
    wrapper.unmount();
  });

  it("says a stale snapshot retries on return while the tab is hidden", async () => {
    let fail = false;
    const { wrapper } = mountOverview(async (path) => {
      if (path === "/session") return SESSION;
      if (fail) throw new GmApiError("network_error", { message: "斷線" });
      return DASHBOARD;
    });
    await flushPromises();
    fail = true;
    await vi.advanceTimersByTimeAsync(5000);
    setVisibility("hidden");
    await flushPromises();
    const bar = wrapper.get("[data-testid='gm-refresh-bar']");
    expect(bar.attributes("data-state")).toBe("stale");
    expect(bar.text()).toContain("分頁回到前景時重試");
    wrapper.unmount();
  });
});
