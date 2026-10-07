import { h } from "vue";
import GmRefreshBar from "../components/GmRefreshBar.vue";
import { NOW } from "./fixtures.js";

// GmRefreshBar: freshness of a polled page; announces transitions only.
export default {
  title: "GM/GmRefreshBar",
  component: GmRefreshBar,
  args: { state: "live", lastUpdatedAt: NOW - 3, now: NOW, intervalSeconds: 5 },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "1100px" } }, [h(GmRefreshBar, args)]),
  }),
};

export const Live = {};
export const Refreshing = { args: { state: "refreshing" } };
export const Paused = { args: { state: "paused", lastUpdatedAt: NOW - 95 } };
export const Stale = { args: { state: "stale", lastUpdatedAt: NOW - 18, errorMessage: "無法連線到伺服器，請確認服務是否運作中。" } };
export const Loading = { args: { state: "loading", lastUpdatedAt: null } };
