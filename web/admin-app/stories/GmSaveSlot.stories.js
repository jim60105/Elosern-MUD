import { h } from "vue";
import GmSaveSlot from "../components/GmSaveSlot.vue";
import { SAVES } from "./saves-fixtures.js";

// GmSaveSlot: one world save as a ledger row. Rendered inside the same
// six-column grid the 存檔 page gives its list, so the subgrid lines up.
const grid = {
  display: "grid",
  gridTemplateColumns: "9.5rem minmax(13rem, 2.2fr) minmax(13rem, 1.5fr) minmax(11rem, 1.4fr) 6.5rem max-content",
  margin: 0,
  padding: 0,
  listStyle: "none",
  background: "var(--ink-860)",
  border: "var(--line)",
  borderRadius: "var(--radius)",
};

export default {
  title: "GM/GmSaveSlot",
  component: GmSaveSlot,
  args: { save: SAVES[0], locked: false, downloadState: "idle", error: null, arrived: false, timeZone: "Asia/Taipei" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1500px", containerType: "inline-size", containerName: "gm-saves" } }, [
        h("ol", { style: grid }, [h(GmSaveSlot, args)]),
      ]),
  }),
};

export const Manual = {};
export const AutomaticWithManyCharacters = { args: { save: SAVES[1] } };
export const UnnamedWithoutCharacters = { args: { save: SAVES[2] } };
export const PendingRestore = { args: { save: { ...SAVES[0], pending: true }, locked: true } };
export const Downloading = { args: { downloadState: "busy" } };
export const WithError = {
  args: {
    error: { code: "network_error", title: "無法連線到伺服器", message: "無法連線到伺服器，請確認服務是否運作中。" },
  },
};
