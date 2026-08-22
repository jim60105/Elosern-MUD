import { h } from "vue";
import CharacterPanel from "../../components/CharacterPanel.vue";
import { CHARACTER_PANEL_SAMPLE, CHARACTER_PANEL_UNDISGUISED_SAMPLE } from "../fixtures.js";

// CharacterPanel: the read-only expanded character surface. Prop: character
// (the committed `character` v3 panel payload — true traits, equipped items,
// disguise with displayed values distinct from true traits, guild
// rank/merit, wallet, persona). Read-only: no events.

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(CharacterPanel, args),
    ]),
});

export default {
  title: "Data/CharacterPanel",
  component: CharacterPanel,
};

export const FullPayload = {
  render: renderPanel,
  args: {
    character: CHARACTER_PANEL_SAMPLE,
  },
};

export const Undisguised = {
  render: renderPanel,
  args: {
    character: CHARACTER_PANEL_UNDISGUISED_SAMPLE,
  },
};
