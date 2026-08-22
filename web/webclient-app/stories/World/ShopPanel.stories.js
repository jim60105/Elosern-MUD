import { h } from "vue";
import ShopPanel from "../../components/ShopPanel.vue";
import { SERVICES_PANEL_MINIMAL_SAMPLE, SERVICES_PANEL_SAMPLE, SERVICES_PANEL_UNAVAILABLE_SAMPLE } from "../fixtures.js";

// ShopPanel (B4 world / services family): renders the `shop` section of
// the committed `services` v1 payload — open/closed status, stock rows
// with buy/sell copper prices and stock levels, held sellable rows, and
// the player wallet. Read-only display; the `buy`/`sell` controls emit the
// exact OOB action intents (the `action_id` and `payload` fields of the
// `ui_action` envelope; transport-level fields are owned by the C1 store).

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(ShopPanel, args),
    ]),
});

export default {
  title: "World/ShopPanel",
  component: ShopPanel,
};

export const FullPayload = {
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
