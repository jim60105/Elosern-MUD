import { h, provide } from "vue";
import SavesView from "../views/SavesView.vue";
import { FAILED_RESULT, SAVES_LISTING } from "./saves-fixtures.js";

// The 存檔 page against a synthetic listing; writes resolve without effect.
function api(listing) {
  return {
    async get() {
      return JSON.parse(JSON.stringify(listing));
    },
    async post(path) {
      if (path.endsWith("/restore")) return { save: "x", pre_restore_save: "20261007T070000-ffee00", shutdown: true };
      return {};
    },
    async download() {
      return { blob: new Blob(["tar"]), filename: "elosern-save.tar" };
    },
  };
}

export default {
  title: "GM/Pages/SavesPage",
  args: { listing: SAVES_LISTING },
  render: (args) => ({
    setup() {
      provide("gmApi", api(args.listing));
      return () => h("div", { style: { padding: "32px", maxWidth: "1600px" } }, [h(SavesView, { timeZone: "Asia/Taipei" })]);
    },
  }),
};

export const Ledger = {};
export const RestoreFailed = { args: { listing: { ...SAVES_LISTING, restore_result: FAILED_RESULT } } };
export const PendingRestore = {
  args: {
    listing: {
      ...SAVES_LISTING,
      restore_result: null,
      pending: SAVES_LISTING.saves[0].id,
      saves: SAVES_LISTING.saves.map((save, index) => ({ ...save, pending: index === 0 })),
    },
  },
};
export const Empty = { args: { listing: { saves: [], restore_result: null, pending: null, autosave_keep: 10 } } };
