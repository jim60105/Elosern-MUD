import { h } from "vue";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// InventoryPanel (H4, webclient-hud-04-reference-drawers, task 6.6): the
// 背包 · 裝備 drawer body. H4 removed the equipped-only filter, so the story
// set covers: the empty bag, a mixed bag with equipped rows, a bag at the
// 32-row ceiling (ceiling note renders), and the unavailable form.

function emptyBag() {
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows: [], wallet: 0 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 0 },
  };
}

function ceilingBag() {
  const rows = Array.from({ length: 32 }, (_, i) => ({
    item_key: `item_ceiling_${i + 1}`,
    display_name: `物品 ${i + 1}`,
    held: 1,
    equipped: i < 3,
    presentation: null,
  }));
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: 3240 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 32 },
  };
}

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(InventoryPanel, args),
    ]),
});

export default {
  title: "World/InventoryPanel",
  component: InventoryPanel,
};

export const EmptyBag = {
  render: renderPanel,
  args: { services: emptyBag() },
};

export const MixedBag = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_SAMPLE },
};

export const CeilingBag = {
  render: renderPanel,
  args: { services: ceilingBag() },
};

export const SectionAbsent = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_MINIMAL_SAMPLE },
};

export const Unavailable = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE },
};
