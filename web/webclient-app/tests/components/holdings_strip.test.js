// webclient-window-primitives: HoldingsStrip renders item_holdings server
// facts only — counts, deltas with shape prefixes, and give controls only
// for enabled receive facts; counts only in combat.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import Protocol from "../../../static/webclient/js/elosern/protocol.js";
import HoldingsStrip from "../../components/HoldingsStrip.vue";
import {
  ITEM_HOLDINGS_COMBAT,
  ITEM_HOLDINGS_CONSUMABLE,
  ITEM_HOLDINGS_EQUIPMENT,
  WINDOW_RAIL_MEMBERS,
} from "../../stories/fixtures/window_primitives.js";

describe("HoldingsStrip (webclient-window-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  function mountStrip(panel, props = {}) {
    wrapper = mount(HoldingsStrip, {
      props: { rows: panel.rows, giverId: panel.giver_id, members: WINDOW_RAIL_MEMBERS, ...props },
    });
    return wrapper;
  }

  const cell = (id) => wrapper.get(`[data-testid="holdings-strip__cell--${id}"]`);

  it("the story fixtures are valid item_holdings v1 payloads", () => {
    for (const panel of [ITEM_HOLDINGS_CONSUMABLE, ITEM_HOLDINGS_EQUIPMENT, ITEM_HOLDINGS_COMBAT]) {
      expect(Protocol.validateItemHoldingsPanel(panel)).toEqual(panel);
    }
  });

  it("renders one cell per row in order with the server count, and no delta for a null delta", () => {
    mountStrip(ITEM_HOLDINGS_CONSUMABLE);
    const cells = wrapper.findAll('[role="listitem"]');
    expect(cells.map((c) => c.get(".holdings-strip__name").text())).toEqual(["莉瑟", "艾拉", "卡恩"]);
    expect(cells.map((c) => c.get('[data-testid="holdings-strip__count"]').text())).toEqual(["5", "2", "0"]);
    expect(wrapper.find('[data-testid="holdings-strip__delta"]').exists()).toBe(false);
    // Count, name and the fixed owner/give/reason line only: no delta text.
    expect(cell(12).text()).toBe("艾拉持有 2交給艾拉");
  });

  it("offers a give control only for an enabled receive fact, never on the owner, and shows a disabled reason", async () => {
    mountStrip(ITEM_HOLDINGS_CONSUMABLE, { giveQuantity: 2 });
    expect(cell(11).text()).toContain("持有者");
    expect(cell(11).find("button").exists()).toBe(false);
    expect(cell(13).find("button").exists()).toBe(false);
    expect(cell(13).get('[data-testid="holdings-strip__reason"]').text()).toBe("對方不在這裡。");
    const give = cell(12).get('[data-testid="holdings-strip__give--12"]');
    expect(give.text()).toBe("交給艾拉 ×2");
    await give.trigger("click");
    expect(wrapper.emitted("give")).toEqual([[12]]);
  });

  it("never offers a give the server did not enable, even with a forged own-row receive", () => {
    const rows = ITEM_HOLDINGS_CONSUMABLE.rows.map((row) => ({ ...row, receive: { enabled: true, reason: null } }));
    mountStrip({ ...ITEM_HOLDINGS_CONSUMABLE, rows });
    expect(cell(11).find("button").exists()).toBe(false);
    expect(wrapper.findAll("button")).toHaveLength(2);
  });

  it("writes each server change with a ▲/▼ shape prefix and a true minus sign", () => {
    mountStrip(ITEM_HOLDINGS_EQUIPMENT);
    expect(cell(11).get('[data-testid="holdings-strip__delta"]').text()).toBe("▲ 攻擊 +2");
    const changes = cell(12).findAll(".holdings-strip__change");
    expect(changes.map((c) => c.text())).toEqual(["▲ 攻擊 +6", "▼ 敏捷 −1"]);
    expect(changes.map((c) => c.classes()[1])).toEqual(["is-up", "is-down"]);
    const none = cell(13).get('[data-testid="holdings-strip__delta"]');
    expect(none.text()).toBe("無法裝備卡恩無法使用這類武器。");
    expect(none.get('[data-testid="holdings-strip__delta-reason"]').text()).toBe("卡恩無法使用這類武器。");
  });

  it("an equipped row shows its tag and no invented delta text", () => {
    const rows = ITEM_HOLDINGS_EQUIPMENT.rows.map((row, index) =>
      index === 0 ? { ...row, equipped: true, delta: { equippable: true, changes: [] } } : row,
    );
    const panel = { ...ITEM_HOLDINGS_EQUIPMENT, rows };
    expect(Protocol.validateItemHoldingsPanel(panel)).toEqual(panel);
    mountStrip(panel);
    expect(cell(11).find('[data-testid="holdings-strip__delta"]').exists()).toBe(false);
    expect(cell(11).get(".holdings-strip__tag").text()).toBe("裝備中");
    expect(cell(11).text()).not.toMatch(/±|0$/);
  });

  it("shows counts only in combat: no delta, give, reason or tag; the owner stays named", async () => {
    const rows = ITEM_HOLDINGS_EQUIPMENT.rows.map((row, index) => ({
      ...row,
      equipped: index === 0 ? false : row.equipped,
      receive: index === 0 ? row.receive : { enabled: true, reason: null },
    }));
    mountStrip({ ...ITEM_HOLDINGS_EQUIPMENT, rows }, { combat: true });
    expect(wrapper.get('[data-testid="holdings-strip"]').attributes("data-combat")).toBe("true");
    expect(wrapper.findAll("button")).toHaveLength(0);
    expect(wrapper.find('[data-testid="holdings-strip__delta"]').exists()).toBe(false);
    expect(wrapper.findAll('[role="listitem"]').map((c) => c.text())).toEqual(["莉瑟持有者持有 1", "艾拉持有 0", "卡卡恩持有 0"]);

    mountStrip(ITEM_HOLDINGS_COMBAT, { combat: true });
    expect(wrapper.find('[data-testid="holdings-strip__reason"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("戰鬥中無法交換物品");
    // The owner stays named in text, never by colour alone.
    expect(wrapper.get('[data-testid="holdings-strip__cell--11"]').text()).toContain("持有者");
  });

  it("falls back to the member id when no name is known", () => {
    mountStrip(ITEM_HOLDINGS_CONSUMABLE, { members: [] });
    expect(cell(12).get(".holdings-strip__name").text()).toBe("#12");
  });
});
