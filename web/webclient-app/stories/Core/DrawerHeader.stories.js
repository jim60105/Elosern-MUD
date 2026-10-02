import { h } from "vue";
import DrawerHeader from "../../components/DrawerHeader.vue";

// DrawerHeader (webclient-drawer-frame-unification): the one presentational
// header every reference drawer and utility overlay shares — registry glyph,
// serif title, muted subtitle, one icon-only 36px close control. It emits
// `close` only; the hosts keep their focus traps and Escape handling. The
// stories are deterministic and offline: one header, a header without a
// subtitle, and every reference surface's header in the order the navigation
// and drawers open them, so the registry glyphs can be compared at a glance.
// (The rows name their text `heading` and `sub` so the showcase gate, which reads a
// story file's first title key as its story title, sees only the default
// export's.)

const SURFACES = [
  { icon: "character", heading: "角色狀態" },
  { icon: "quests", heading: "任務" },
  { icon: "inventory", heading: "背包 ‧ 裝備", sub: "錢袋 3,240 銅" },
  { icon: "skills", heading: "技能書", sub: "主動 11 ‧ 被動 3" },
  { icon: "party", heading: "同伴 ‧ 隊伍", sub: "1 / 4" },
  { icon: "shop", heading: "商店" },
  { icon: "lore", heading: "世界圖鑑" },
  { icon: "map", heading: "地圖 ‧ 冒險者公會大廳", sub: "所在位置與相鄰路徑" },
  { icon: "settings", heading: "設定", sub: "閱讀偏好與輔助顯示" },
  { icon: "lineage", heading: "技能系譜", sub: "熟練度 ‧ 見頂 ‧ 前置" },
  { icon: "codex", heading: "稱號冊", sub: "稱號 ‧ 異名 ‧ 提名中" },
  { icon: "gallery", heading: "角色肖像圖庫", sub: "記錄不同的你，也是旅途的一部分。" },
  { icon: "help", heading: "說明", sub: "分類 → 條目 → 子主題" },
];

function panel(children, width = "min(960px, 100%)") {
  return h(
    "div",
    {
      style: `width: ${width}; background: var(--surface-panel); border: 1px solid #bca57966; border-radius: 8px; overflow: hidden;`,
    },
    children,
  );
}

export default {
  title: "Core/DrawerHeader",
  component: DrawerHeader,
  parameters: {
    docs: {
      description: {
        component:
          "The shared reference-surface header: registry glyph, title, subtitle and one named close control. Presentational only — it emits `close`.",
      },
    },
  },
  args: {
    icon: "lineage",
    title: "技能系譜",
    subtitle: "熟練度 ‧ 見頂 ‧ 前置",
    surface: "overlay-host",
  },
};

export const Default = {
  render: (args) => ({
    setup: () => () => panel([h(DrawerHeader, { ...args, onClose: () => {} })]),
  }),
};

export const WithoutSubtitle = {
  args: { icon: "character", title: "角色狀態", subtitle: "", surface: "hud-drawer" },
  render: (args) => ({
    setup: () => () => panel([h(DrawerHeader, { ...args, onClose: () => {} })]),
  }),
};

export const EveryReferenceSurface = {
  render: () => ({
    setup: () => () =>
      h(
        "div",
        { style: "display: grid; gap: 12px; padding: 16px; background: var(--ink-950);" },
        SURFACES.map((surface) =>
          panel([h(DrawerHeader, { icon: surface.icon, title: surface.heading, subtitle: surface.sub || "", surface: "hud-drawer", onClose: () => {} })]),
        ),
      ),
  }),
};
