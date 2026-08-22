import { h } from "vue";
import InventoryPanel from "../../components/InventoryPanel.vue";
import { SERVICES_PANEL_MINIMAL_SAMPLE, SERVICES_PANEL_SAMPLE, SERVICES_PANEL_UNAVAILABLE_SAMPLE } from "../fixtures.js";

// InventoryPanel (B4 world / services family): renders the `inventory`
// section of the committed `services` v1 payload — equipped items only
// (a full bag is deferred), with the wallet shown in integer copper.
// No surface invents bag contents.

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

export const EquippedOnly = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_SAMPLE },
};

export const SectionAbsent = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_MINIMAL_SAMPLE },
};

export const SectionUnavailable = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE },
};
