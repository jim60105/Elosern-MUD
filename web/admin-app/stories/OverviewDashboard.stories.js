import { h, provide } from "vue";
import OverviewView from "../views/OverviewView.vue";
import { createSessionState } from "../lib/session.js";
import { CALL_DETAIL, DASHBOARD, SESSION, fakeApi } from "./fixtures.js";

// The 總覽 operations dashboard page; `args.snapshot` is the synthetic
// /gm/api/dashboard payload the fake API serves.
export default {
  title: "GM/Pages/OverviewDashboard",
  args: { snapshot: DASHBOARD },
  render: (args) => ({
    setup() {
      const api = fakeApi((path) => {
        if (path === "/session") return SESSION;
        if (path === "/dashboard") return args.snapshot;
        return CALL_DETAIL;
      });
      provide("gmApi", api);
      provide("gmSession", createSessionState(api));
      return () => h("div", { style: { padding: "32px", maxWidth: "1600px" } }, [h(OverviewView)]);
    },
  }),
};

export const Healthy = {};
export const PartialFailures = {
  args: {
    snapshot: {
      ...DASHBOARD,
      services: {
        ...DASHBOARD.services,
        sd: { ok: false, code: "sd_connection_refused", host: "sd.local.test", checked_at: DASHBOARD.process.now - 4, from_cache: false },
      },
      art: { error: { code: "art_unavailable", message: "無法讀取美術佇列。" } },
      world: { ...DASHBOARD.world, clock: null },
    },
  },
};
