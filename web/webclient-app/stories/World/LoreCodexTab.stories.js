import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import LoreCodexTab from "../../components/handbook/LoreCodexTab.vue";
import { useQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import {
  LORE_CODEX_HANDBOOK_EMPTY_SAMPLE,
  LORE_CODEX_HANDBOOK_SAMPLE,
  LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures/lore_codex_panels.js";

// LoreCodexTab (handbook-codex-tab): the 手帳's 圖鑑 tab inside the real
// HudDrawer chrome, over synthetic `lore_codex` v2 panels. The rail lists the
// eight categories with discovered counts; the wall groups the selected
// category's tiles (monsters by tier, with filled/hollow diamond stage marks,
// hatched ？ placeholders and the pinned legend); the detail shows the
// entry's art or category emblem under the stage stamp, the research track
// and the 擊敗後解鎖 locked fields. Props: codex (the committed panel or
// null), memoryScope, combat. The tab dispatches nothing.

export default {
  title: "World/LoreCodexTab",
  component: LoreCodexTab,
};

// Each story seeds its own session memory scope with its category and entry.
const renderTab = ({ category = null, selection = null, ...args }, context) => ({
  setup() {
    const scope = `story:${context.id}`;
    const memory = useQuestDrawerMemory(scope);
    memory.codexCategory = category;
    if (category && selection) memory.selectedByTab = { [`codex:${category}`]: selection };
    return () =>
      h(HudDrawer, { open: true, title: "手帳", icon: "quests", drawerKey: "quest", bodyFlush: true }, () => [
        h(LoreCodexTab, { ...args, memoryScope: scope }),
      ]);
  },
});

// The monster wall: two tiers, mixed stages, placeholders and the legend.
export const MonsterWall = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "monster", selection: "s_mon_c" },
};

// A sighted monster: the 目擊 stamp, one reached step and four locked boxes.
export const SightedDetail = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "monster", selection: "s_mon_b" },
};

// A defeated monster: the 已擊敗 stamp, both steps and every field.
export const DefeatedDetail = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "monster", selection: "s_mon_a" },
};

// A region whose hero is its bundled scene art.
export const RegionSceneArt = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "region", selection: "s_region_a" },
};

// An element with no art: the hero shows the category emblem.
export const ElementEmblem = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "element", selection: "s_elem_a" },
};

// Nothing discovered: the full placeholder wall and the empty guidance.
export const NothingDiscovered = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_EMPTY_SAMPLE, category: "monster" },
};

// Before the first `lore_codex` commit.
export const Absent = {
  render: renderTab,
  args: { codex: null },
};

// The common unavailable form: the panel's reason.
export const Unavailable = {
  render: renderTab,
  args: { codex: LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE },
};

// In combat the tab renders the same read-only codex.
export const InCombat = {
  render: renderTab,
  args: { codex: LORE_CODEX_HANDBOOK_SAMPLE, category: "monster", combat: true },
};
