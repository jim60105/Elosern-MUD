import { h } from "vue";
import LoreCodexDrawer from "../../components/LoreCodexDrawer.vue";
import {
  LORE_CODEX_PANEL_EMPTY_SAMPLE,
  LORE_CODEX_PANEL_SAMPLE,
  LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// LoreCodexDrawer: the world-codex drawer body. Prop: codex — the
// committed `lore_codex` panel (the host-free discovered-lore read model).
// Category and entry navigation are view-local state; initialCategory and
// initialEntryKey seed them for the showcase. Every state renders only what
// the panel ships: populated, a single category, a selected entry's card,
// the honest empty codex, and the registry-owned unavailable form.

const renderDrawer = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(LoreCodexDrawer, args),
    ]),
});

export default {
  title: "World/LoreCodexDrawer",
  component: LoreCodexDrawer,
};

export const PopulatedCodex = {
  render: renderDrawer,
  args: {
    codex: LORE_CODEX_PANEL_SAMPLE,
  },
};

export const CategorySelected = {
  render: renderDrawer,
  args: {
    codex: LORE_CODEX_PANEL_SAMPLE,
    initialCategory: "monster",
  },
};

export const EntrySelected = {
  render: renderDrawer,
  args: {
    codex: LORE_CODEX_PANEL_SAMPLE,
    initialCategory: "all",
    initialEntryKey: "monster:mist_wolf",
  },
};

export const EmptyCodex = {
  render: renderDrawer,
  args: {
    codex: LORE_CODEX_PANEL_EMPTY_SAMPLE,
  },
};

export const Unavailable = {
  render: renderDrawer,
  args: {
    codex: LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
  },
};
