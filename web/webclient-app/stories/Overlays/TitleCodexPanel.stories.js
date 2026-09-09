import { h } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import TitleCodexPanel from "../../components/TitleCodexPanel.vue";

export default {
  title: "Overlays/TitleCodexPanel",
  component: TitleCodexPanel,
};

const renderCodex = (args) => ({
  render: () => h(OverlayHost, { open: "codex" }, {
    default: () => h(TitleCodexPanel, args),
  }),
});

const codex = {
  schema_version: 1,
  available: true,
  kind: "title_codex",
  fixed_rows: [
    { key: "g_f_rank", display: "F級冒險者", category: "guild", hint: "", flavor: "公會註冊的起點。", unlocked: true, granted_tick: 120 },
    { key: "g_e_rank", display: "E級冒險者", category: "guild", hint: "通過 E 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
  ],
  epithet_rows: [
    { display: "破城先鋒", basis: "率先破門。", granted_tick: 121, equipped: false, can_remove: true },
    { display: "南門新客", basis: "初入南門。", granted_tick: 120, equipped: true, can_remove: false },
  ],
  equipped: { fixed: "g_f_rank", epithet: "南門新客" },
  full_title: "F級冒險者　南門新客",
  unlocked: 1,
  total: 2,
  pending_ballot: [
    { display: "夜襲之人", basis: "夜半三度出入敵陣。" },
    { display: "不屈之壁", basis: "重傷仍守住隘口。" },
  ],
};

export const CollectedAndLocked = { render: renderCodex, args: { codex } };
export const Unavailable = {
  render: renderCodex,
  args: { codex: { available: false, reason: { message: "稱號冊目前無法顯示" } } },
};
