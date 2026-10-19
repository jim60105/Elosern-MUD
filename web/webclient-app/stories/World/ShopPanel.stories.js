import { h } from "vue";
import ShopPanel from "../../components/ShopPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_SHOP_ROWS_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// ShopPanel (B4 world / services family): the transitional shop drawer over
// the committed `services` v7 `shop` section. Rows describe the viewed party
// member (`shop.member_id`): stock rows show the icon framed by rarity, the
// stock level, the buy price only and that member's server delta or held
// count; sellable rows list that member's unequipped copies with the sell
// price only. The `buy`/`sell` controls emit the exact OOB action intents
// naming `shop.member_id` (the `action_id` and `payload` fields of the
// `ui_action` envelope; transport-level fields are owned by the C1 store).

// The HUD drawer spans the workspace, so the frame lets the panel fill the
// canvas up to a desktop drawer body width.
const renderPanel = (args) => ({
  render: () =>
    h(
      "div",
      { style: "max-width: 1380px; border: 1px solid var(--ink-700); border-radius: 12px; padding: 20px; background: var(--surface-panel, var(--ink-900));" },
      [h(ShopPanel, args)],
    ),
});

export default {
  title: "World/ShopPanel",
  component: ShopPanel,
};

export const FullPayload = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_SAMPLE },
};

// The prototype's buy and sell views for the viewed companion 艾拉.
export const ViewedMemberRows = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_SHOP_ROWS_SAMPLE, memberName: "艾拉" },
};

export const ClosedShop = {
  render: renderPanel,
  args: {
    services: {
      ...SERVICES_PANEL_SHOP_ROWS_SAMPLE,
      shop: {
        ...SERVICES_PANEL_SHOP_ROWS_SAMPLE.shop,
        open: false,
        stock: SERVICES_PANEL_SHOP_ROWS_SAMPLE.shop.stock.map((row) => ({
          ...row,
          buy: { ...row.buy, enabled: false, disabled_reason: { code: "closed", message: "商店目前沒有營業。" }, quantity: null },
        })),
        sellable: SERVICES_PANEL_SHOP_ROWS_SAMPLE.shop.sellable.map((row) => ({
          ...row,
          sell: { ...row.sell, enabled: false, disabled_reason: { code: "closed", message: "商店目前沒有營業。" }, quantity: null },
        })),
      },
    },
    memberName: "艾拉",
  },
};

export const SectionAbsent = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_MINIMAL_SAMPLE },
};

export const SectionUnavailable = {
  render: renderPanel,
  args: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE },
};
