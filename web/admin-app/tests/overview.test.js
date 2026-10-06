import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import OverviewView from "../views/OverviewView.vue";
import { GmApiError } from "../lib/api.js";
import { createSessionState } from "../lib/session.js";

const SESSION = {
  account_name: "Operator_7",
  permission_level: "Developer",
  server_time: "2026-10-07T14:32:05+08:00",
  game_version: "0.1.0",
};

function mountOverview(get) {
  const api = { get: vi.fn(get), post: vi.fn() };
  const session = createSessionState(api);
  const wrapper = mount(OverviewView, { global: { provide: { gmApi: api, gmSession: session } } });
  return { wrapper, api };
}

describe("overview", () => {
  it("renders the real session and health responses", async () => {
    const { wrapper, api } = mountOverview(async (path) =>
      path === "/session" ? SESSION : { django: "ok", database: "readable" },
    );
    await flushPromises();
    expect(api.get.mock.calls.map(([path]) => path).sort()).toEqual(["/health", "/session"]);
    const session = wrapper.get("[data-testid='gm-session']");
    expect(session.get("[data-field='account_name']").text()).toBe("Operator_7");
    expect(session.get("[data-field='permission_level']").text()).toBe("Developer");
    expect(session.get("[data-field='server_time']").text()).toBe(SESSION.server_time);
    expect(session.get("time").attributes("datetime")).toBe(SESSION.server_time);
    expect(session.get("[data-field='game_version']").text()).toBe("0.1.0");
    const rows = wrapper.findAll("[data-testid='gm-health'] tbody tr");
    expect(rows.map((row) => row.findAll("td")[1].text())).toEqual(["django", "database"]);
    expect(rows.map((row) => row.get(".status-marker").classes())).toEqual([
      expect.arrayContaining(["status-marker--ok"]),
      expect.arrayContaining(["status-marker--ok"]),
    ]);
  });

  it("shows errors by code and never fabricates healthy values", async () => {
    const { wrapper } = mountOverview(async (path) => {
      if (path === "/session") return SESSION;
      throw new GmApiError("database_unreadable", { status: 503, message: "資料庫目前無法讀取。" });
    });
    await flushPromises();
    expect(wrapper.find("[data-testid='gm-health']").exists()).toBe(false);
    const error = wrapper.get(".gm-overview__health [role='alert']");
    expect(error.get("code").text()).toBe("database_unreadable");
    expect(error.text()).toContain("資料庫目前無法讀取。");
    expect(wrapper.text()).not.toContain("可讀取");
  });

  it("retries the health check after a network failure", async () => {
    let fail = true;
    const { wrapper } = mountOverview(async (path) => {
      if (path === "/session") return SESSION;
      if (fail) throw new GmApiError("network_error", { message: "無法連線" });
      return { django: "ok", database: "readable" };
    });
    await flushPromises();
    expect(wrapper.get(".gm-overview__health code").text()).toBe("network_error");
    fail = false;
    await wrapper.get(".gm-overview__health [role='alert'] button").trigger("click");
    await flushPromises();
    expect(wrapper.find("[data-testid='gm-health']").exists()).toBe(true);
  });

  it("flags a degraded health value as abnormal", async () => {
    const { wrapper } = mountOverview(async (path) =>
      path === "/session" ? SESSION : { django: "ok", database: "stale" },
    );
    await flushPromises();
    const badges = wrapper.findAll("[data-testid='gm-health'] .status-marker");
    expect(badges[1].classes()).toContain("status-marker--crit");
    expect(badges[1].text()).toBe("異常");
  });
});
